from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.optimize import brentq

from uhs_costs.constants import (
    HYDROGEN_LHV_KWH_PER_KG,
    SECONDS_PER_DAY,
    STANDARD_PRESSURE_PA,
    STANDARD_TEMPERATURE_K,
)
from uhs_costs.design.helpers.project import StorageProject
from uhs_costs.gas_properties import hydrogen, methane


BAR_TO_PA = 1e5


@dataclass
class PressureLimitedFlowPoint:
    pressure_pa: float
    pressure_bar: float
    soc: float
    h2_inventory_kWh: float
    h2_inventory_kg: float
    withdrawal_kg_per_day: float
    injection_kg_per_day: float
    withdrawal_kg_s: float
    injection_kg_s: float
    withdrawal_kwh_per_day: float
    injection_kwh_per_day: float
    withdrawal_kw_lhv: float
    injection_kw_lhv: float


def total_pressure_from_inventories(
    m_h2_kg: float,
    m_ch4_kg: float,
    volume_m3: float,
    temperature_k: float,
) -> float:
    """
    Estimate total storage pressure from fixed methane inventory and variable H2 inventory.

    Methane and hydrogen are treated as immiscible pressure-contributing gas components
    sharing the same effective storage volume and temperature. Methane is fixed;
    only hydrogen moves in and out.
    """
    if volume_m3 <= 0:
        raise ValueError("volume_m3 must be greater than zero.")

    if m_h2_kg < 0:
        raise ValueError("m_h2_kg cannot be negative.")

    if m_ch4_kg < 0:
        raise ValueError("m_ch4_kg cannot be negative.")

    if m_h2_kg > 0:
        rho_h2 = m_h2_kg / volume_m3
        p_h2 = hydrogen.pressure_from_density(
            density_kg_m3=rho_h2,
            temperature_k=temperature_k,
        )
    else:
        p_h2 = 0.0

    if m_ch4_kg > 0:
        rho_ch4 = m_ch4_kg / volume_m3
        p_ch4 = methane.pressure_from_density(
            density_kg_m3=rho_ch4,
            temperature_k=temperature_k,
        )
    else:
        p_ch4 = 0.0

    return p_h2 + p_ch4


def hydrogen_inventory_from_total_pressure(
    target_pressure_pa: float,
    m_ch4_fixed_kg: float,
    volume_m3: float,
    temperature_k: float,
    h2_upper_bound_kg: float,
) -> float:
    """
    Find the hydrogen inventory required to reach a target total pressure.

    The methane mass is fixed. The hydrogen inventory is solved numerically.
    """

    def residual(m_h2_kg: float) -> float:
        return (
            total_pressure_from_inventories(
                m_h2_kg=m_h2_kg,
                m_ch4_kg=m_ch4_fixed_kg,
                volume_m3=volume_m3,
                temperature_k=temperature_k,
            )
            - target_pressure_pa
        )

    residual_at_zero = residual(0.0)

    if residual_at_zero > 0:
        methane_only_pressure_bar = residual_at_zero + target_pressure_pa
        methane_only_pressure_bar /= BAR_TO_PA

        raise ValueError(
            "Target pressure is below the pressure caused by fixed methane alone. "
            f"Methane-only pressure is approximately {methane_only_pressure_bar:.2f} bar. "
            "This implies the assumed methane residual/cushion mass is too high "
            "for the specified operating pressure."
        )

    upper_bound = h2_upper_bound_kg
    residual_at_upper = residual(upper_bound)

    while residual_at_upper < 0:
        upper_bound *= 2
        residual_at_upper = residual(upper_bound)

    return brentq(
        residual,
        0.0,
        upper_bound,
    )


def methane_mass_from_standard_volume(
    methane_volume_sm3: float | None,
) -> float:
    """
    Convert methane standard volume [Sm3] to methane mass [kg].

    Sm3 is an accounting volume at standard conditions, not the physical
    reservoir volume.
    """
    if methane_volume_sm3 is None:
        return 0.0

    if methane_volume_sm3 < 0:
        raise ValueError("methane_volume_sm3 cannot be negative.")

    if methane_volume_sm3 == 0:
        return 0.0

    return methane_volume_sm3 * methane.density(
        pressure_pa=STANDARD_PRESSURE_PA,
        temperature_k=STANDARD_TEMPERATURE_K,
    )


def calculate_pressure_limited_flow_curve(
    project: StorageProject,
    pressure_step_pa: float = 1 * BAR_TO_PA,
    pressure_change_limit_pa_per_day: float = 10 * BAR_TO_PA,
) -> pd.DataFrame:
    """
    Calculate pressure-limited injection and withdrawal curves for one StorageProject.

    The pressure-change limit is interpreted as a daily pressure ramp limit.
    Outputs `withdrawal_kw_lhv` and `injection_kw_lhv` are therefore average daily
    LHV power values implied by that pressure limit.
    """
    if pressure_step_pa <= 0:
        raise ValueError("pressure_step_pa must be greater than zero.")

    if pressure_change_limit_pa_per_day <= 0:
        raise ValueError("pressure_change_limit_pa_per_day must be greater than zero.")

    p_min_pa = project.pressures.minimum_operating_pressure_pa
    p_max_pa = project.pressures.maximum_operating_pressure_pa
    temperature_k = project.wells.well_temperature_k
    volume_m3 = project.inventory.required_storage_volume_m3

    if p_max_pa <= p_min_pa:
        raise ValueError("Maximum operating pressure must be greater than minimum pressure.")

    m_ch4_fixed_kg = methane_mass_from_standard_volume(
        project.inventory.abandonment_gas_methane_volume_sm3
    )

    rho_h2_max = hydrogen.density(
        pressure_pa=p_max_pa,
        temperature_k=temperature_k,
    )

    h2_upper_bound_kg = rho_h2_max * volume_m3 * 1.1

    m_h2_min = hydrogen_inventory_from_total_pressure(
        target_pressure_pa=p_min_pa,
        m_ch4_fixed_kg=m_ch4_fixed_kg,
        volume_m3=volume_m3,
        temperature_k=temperature_k,
        h2_upper_bound_kg=h2_upper_bound_kg,
    )

    m_h2_max = hydrogen_inventory_from_total_pressure(
        target_pressure_pa=p_max_pa,
        m_ch4_fixed_kg=m_ch4_fixed_kg,
        volume_m3=volume_m3,
        temperature_k=temperature_k,
        h2_upper_bound_kg=h2_upper_bound_kg,
    )

    if m_h2_max <= m_h2_min:
        raise ValueError("Maximum H2 inventory must be greater than minimum H2 inventory.")

    pressures_pa = np.arange(
        p_min_pa,
        p_max_pa,
        pressure_step_pa,
    )

    pressures_pa = np.append(pressures_pa, p_max_pa)
    pressures_pa = np.unique(pressures_pa)

    points: list[PressureLimitedFlowPoint] = []

    for p_current in pressures_pa:
        m_h2_current = hydrogen_inventory_from_total_pressure(
            target_pressure_pa=p_current,
            m_ch4_fixed_kg=m_ch4_fixed_kg,
            volume_m3=volume_m3,
            temperature_k=temperature_k,
            h2_upper_bound_kg=h2_upper_bound_kg,
        )

        soc = (m_h2_current - m_h2_min) / (m_h2_max - m_h2_min)

        p_after_withdrawal = max(
            # p_min_pa,
            0,
            p_current - pressure_change_limit_pa_per_day,
        )

        p_after_injection = min(
            # p_max_pa,
            1e12,
            p_current + pressure_change_limit_pa_per_day,
        )

        m_h2_after_withdrawal = hydrogen_inventory_from_total_pressure(
            target_pressure_pa=p_after_withdrawal,
            m_ch4_fixed_kg=m_ch4_fixed_kg,
            volume_m3=volume_m3,
            temperature_k=temperature_k,
            h2_upper_bound_kg=h2_upper_bound_kg,
        )

        m_h2_after_injection = hydrogen_inventory_from_total_pressure(
            target_pressure_pa=p_after_injection,
            m_ch4_fixed_kg=m_ch4_fixed_kg,
            volume_m3=volume_m3,
            temperature_k=temperature_k,
            h2_upper_bound_kg=h2_upper_bound_kg,
        )

        withdrawal_kg_per_day = m_h2_current - m_h2_after_withdrawal
        injection_kg_per_day = m_h2_after_injection - m_h2_current

        withdrawal_kg_s = withdrawal_kg_per_day / SECONDS_PER_DAY
        injection_kg_s = injection_kg_per_day / SECONDS_PER_DAY

        withdrawal_kwh_per_day = withdrawal_kg_per_day * HYDROGEN_LHV_KWH_PER_KG
        injection_kwh_per_day = injection_kg_per_day * HYDROGEN_LHV_KWH_PER_KG

        withdrawal_kw_lhv = withdrawal_kwh_per_day / 24
        injection_kw_lhv = injection_kwh_per_day / 24

        points.append(
            PressureLimitedFlowPoint(
                pressure_pa=p_current,
                pressure_bar=p_current / BAR_TO_PA,
                soc=soc,
                h2_inventory_kWh=m_h2_current*HYDROGEN_LHV_KWH_PER_KG,
                h2_inventory_kg=m_h2_current,
                withdrawal_kg_per_day=withdrawal_kg_per_day,
                injection_kg_per_day=injection_kg_per_day,
                withdrawal_kg_s=withdrawal_kg_s,
                injection_kg_s=injection_kg_s,
                withdrawal_kwh_per_day=withdrawal_kwh_per_day,
                injection_kwh_per_day=injection_kwh_per_day,
                withdrawal_kw_lhv=withdrawal_kw_lhv,
                injection_kw_lhv=injection_kw_lhv,
            )
        )

    return pd.DataFrame([point.__dict__ for point in points])


def calculate_pressure_limited_flow_curves_for_projects(
    projects: Mapping[str, StorageProject],
    *,
    pressure_step_pa: float = 1 * BAR_TO_PA,
    pressure_change_limit_pa_per_day: float = 10 * BAR_TO_PA,
    print_cem_constraints: bool = True,
    conservative_cem_fit: bool = True,
) -> dict[str, pd.DataFrame]:
    """
    Calculate pressure-limited flow curves for several StorageProject objects.

    If print_cem_constraints=True, also fit and print linear CEM-ready
    24-hour pressure-ramp constraints using:

        SoC_t     = stored hydrogen energy [kWh]
        SoC_max   = installed storage capacity [kWh]
    """
    if not projects:
        raise ValueError("No projects provided.")

    results_by_project: dict[str, pd.DataFrame] = {}

    for label, project in projects.items():
        df = calculate_pressure_limited_flow_curve(
            project=project,
            pressure_step_pa=pressure_step_pa,
            pressure_change_limit_pa_per_day=pressure_change_limit_pa_per_day,
        )

        df = add_capacity_normalised_columns(
            df=df,
            working_gas_capacity_kwh_lhv=project.inventory.working_gas_capacity_kwh_lhv,
        )

        results_by_project[label] = df

    if print_cem_constraints:
        print_cem_pressure_constraint(
            results_by_project=results_by_project,
            direction="withdrawal",
            y="withdrawal_kw_per_kwh",
            conservative=conservative_cem_fit,
        )

        print_cem_pressure_constraint(
            results_by_project=results_by_project,
            direction="injection",
            y="injection_kw_per_kwh",
            conservative=conservative_cem_fit,
        )

    return results_by_project
def plot_curves(
    results: pd.DataFrame | Mapping[str, pd.DataFrame],
    x: str = "soc",
    y: str = "withdrawal_kw_lhv",
    *,
    title: str | None = None,
    xlabel: str | None = None,
    ylabel: str | None = None,
    y_scale: float = 1.0,
    x_scale: float = 1.0,
    projects: Mapping[str, StorageProject] | None = None,
    show_design_capacity: bool = False,
    horizontal_lines: Mapping[str, float] | None = None,
    output_path: str | Path | None = None,
    show: bool = True,
) -> None:
    """
    Flexibly plot any dataframe column against any other column.

    If show_design_capacity=True and projects are provided, design capacity
    reference lines are added for withdrawal_kw_lhv or injection_kw_lhv.
    """
    if isinstance(results, pd.DataFrame):
        labelled_results = {"case": results}
    else:
        labelled_results = dict(results)

    if not labelled_results:
        raise ValueError("No results provided for plotting.")

    fig, ax = plt.subplots(figsize=(8, 5))

    for label, df in labelled_results.items():
        if x not in df.columns:
            raise ValueError(
                f"Column {x!r} not found in dataframe for {label!r}. "
                f"Available columns: {list(df.columns)}"
            )

        if y not in df.columns:
            raise ValueError(
                f"Column {y!r} not found in dataframe for {label!r}. "
                f"Available columns: {list(df.columns)}"
            )

        ax.plot(
            df[x] * x_scale,
            df[y] * y_scale,
            label=label,
        )

    # User-specified horizontal lines
    if horizontal_lines is not None:
        for label, value in horizontal_lines.items():
            ax.axhline(
                value * y_scale,
                linestyle="--",
                label=label,
            )

    # Automatically inferred design-capacity lines
    if show_design_capacity:
        if projects is None:
            raise ValueError(
                "projects must be provided when show_design_capacity=True."
            )

        for label, project in projects.items():
            if y == "withdrawal_kw_lhv":
                design_capacity_kw = project.flows.withdrawal_flow_kw_h2_lhv
                design_label = f"{label} design withdrawal"

            elif y == "injection_kw_lhv":
                design_capacity_kw = project.flows.injection_flow_kw_h2_lhv
                design_label = f"{label} design injection"

            else:
                continue

            ax.axhline(
                design_capacity_kw * y_scale,
                linestyle="--",
                label=design_label,
            )

    ax.set_xlabel(xlabel or x)
    ax.set_ylabel(ylabel or y)

    if title is not None:
        ax.set_title(title)

    if (
        len(labelled_results) > 1
        or horizontal_lines is not None
        or show_design_capacity
    ):
        ax.legend()

    ax.grid(True, alpha=0.3)
    fig.tight_layout()

    if output_path is not None:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(output_path, dpi=300)

    if show:
        plt.show()
    else:
        plt.close(fig)
def save_results(
    results_by_project: Mapping[str, pd.DataFrame],
    output_dir: str | Path,
) -> pd.DataFrame:
    """
    Save each project dataframe and a combined dataframe.

    Returns the combined dataframe.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    combined = pd.concat(
        [
            df.assign(project=label)
            for label, df in results_by_project.items()
        ],
        ignore_index=True,
    )

    for label, df in results_by_project.items():
        safe_label = label.lower().replace(" ", "_").replace("/", "_")
        df.to_csv(
            output_dir / f"pressure_limited_flow_{safe_label}.csv",
            index=False,
        )

    combined.to_csv(
        output_dir / "pressure_limited_flow_all_projects.csv",
        index=False,
    )

    return combined

def add_capacity_normalised_columns(
    df: pd.DataFrame,
    working_gas_capacity_kwh_lhv: float,
) -> pd.DataFrame:
    """
    Add capacity-normalised pressure-limit columns.

    Power-per-capacity is reported as GW/TWh, which is equivalent to:
        (kW / 1e6) / (kWh / 1e9)
    """
    df = df.copy()

    working_gas_capacity_gwh = working_gas_capacity_kwh_lhv / 1e6
    working_gas_capacity_twh = working_gas_capacity_kwh_lhv / 1e9

    df["working_gas_capacity_kwh_lhv"] = working_gas_capacity_kwh_lhv
    df["working_gas_capacity_gwh_lhv"] = working_gas_capacity_gwh
    df["working_gas_capacity_twh_lhv"] = working_gas_capacity_twh

    df["withdrawal_gw_lhv"] = df["withdrawal_kw_lhv"] / 1e6
    df["injection_gw_lhv"] = df["injection_kw_lhv"] / 1e6

    df["withdrawal_gw_per_twh"] = (
        df["withdrawal_gw_lhv"] / working_gas_capacity_twh
    )

    df["injection_gw_per_twh"] = (
        df["injection_gw_lhv"] / working_gas_capacity_twh
    )

    df["withdrawal_gwh_per_day"] = df["withdrawal_kwh_per_day"] / 1e6
    df["injection_gwh_per_day"] = df["injection_kwh_per_day"] / 1e6

    df["withdrawal_gwh_per_day_per_twh"] = (
        df["withdrawal_gwh_per_day"] / working_gas_capacity_twh
    )

    df["injection_gwh_per_day_per_twh"] = (
        df["injection_gwh_per_day"] / working_gas_capacity_twh
    )

    df["withdrawal_kw_per_kwh"] = (
        df["withdrawal_kw_lhv"] / working_gas_capacity_kwh_lhv
    )

    df["injection_kw_per_kwh"] = (
        df["injection_kw_lhv"] / working_gas_capacity_kwh_lhv
    )

    return df

def fit_capacity_normalised_pressure_limit(
    results_by_project: Mapping[str, pd.DataFrame],
    *,
    y: str,
    x: str = "soc",
    soc_min: float = 0.0,
    soc_max: float = 1.0,
    conservative: bool = True,
) -> tuple[float, float]:
    """
    Fit a linear capacity-normalised pressure-limit curve.

    Fits:
        y = intercept + slope * x

    Usually:
        x = fractional SoC [-]
        y = pressure-limited capacity [kW/kWh]

    If conservative=True, the intercept is shifted downward so that the fitted
    line never exceeds the calculated pressure-limit curve over the fitted range.
    """
    combined = pd.concat(
        [
            df.assign(project=label)
            for label, df in results_by_project.items()
        ],
        ignore_index=True,
    )

    fit_df = combined[
        (combined[x] >= soc_min)
        & (combined[x] <= soc_max)
    ].copy()

    if fit_df.empty:
        raise ValueError(
            "No data available for fitting. Check soc_min, soc_max, and input data."
        )

    if y not in fit_df.columns:
        raise ValueError(
            f"Column {y!r} not found. Available columns: {list(fit_df.columns)}"
        )

    slope, intercept = np.polyfit(
        fit_df[x].to_numpy(),
        fit_df[y].to_numpy(),
        deg=1,
    )

    if conservative:
        y_pred = intercept + slope * fit_df[x].to_numpy()
        y_true = fit_df[y].to_numpy()

        max_overestimate = np.max(y_pred - y_true)

        if max_overestimate > 0:
            intercept -= max_overestimate

    return intercept, slope


def print_cem_pressure_constraint(
    results_by_project: Mapping[str, pd.DataFrame],
    *,
    direction: str,
    y: str,
    soc_min: float = 0.0,
    soc_max: float = 1.0,
    conservative: bool = True,
) -> None:
    """
    Print CEM-ready 24-hour pressure-ramp constraint coefficients.

    Here we use the user's preferred notation:

        SoC_t     = stored hydrogen energy at time t [kWh]
        SoC_max   = installed storage energy capacity [kWh]

    The fitted pressure-limit curve is:

        capacity_limit_kw_per_kwh = a + b * fractional_soc

    where:

        fractional_soc = SoC_t / SoC_max

    The 24-hour energy-change limit is:

        delta_SoC_24h_kwh <= 24 * (a + b * SoC_t / SoC_max) * SoC_max

    which simplifies to:

        delta_SoC_24h_kwh <= 24a * SoC_max + 24b * SoC_t

    This is linear.
    """
    if direction not in {"withdrawal", "injection"}:
        raise ValueError("direction must be either 'withdrawal' or 'injection'.")

    intercept, slope = fit_capacity_normalised_pressure_limit(
        results_by_project=results_by_project,
        y=y,
        x="soc",
        soc_min=soc_min,
        soc_max=soc_max,
        conservative=conservative,
    )

    coefficient_soc_max = 24 * intercept
    coefficient_soc_t = 24 * slope

    print()
    print("=" * 88)
    print(f"CEM pressure-ramp constraint: {direction}")
    print("=" * 88)
    print()
    print("Fitted capacity-normalised pressure-limit curve:")
    print(f"    {y} = {intercept:.12f} + ({slope:.12f}) * fractional_soc_t")
    print()
    print("Using:")
    print("    fractional_soc_t = SoC_t / SoC_max")
    print("    SoC_t             = stored hydrogen energy at time t [kWh]")
    print("    SoC_t_plus_24     = stored hydrogen energy 24 hours later [kWh]")
    print("    SoC_max           = installed storage capacity [kWh]")
    print()

    if direction == "withdrawal":
        print("CEM constraint:")
        print(
            "    SoC_t - SoC_t_plus_24 <= "
            f"{coefficient_soc_max:.12f} * SoC_max "
            f"+ ({coefficient_soc_t:.12f}) * SoC_t"
        )
    else:
        print("CEM constraint:")
        print(
            "    SoC_t_plus_24 - SoC_t <= "
            f"{coefficient_soc_max:.12f} * SoC_max "
            f"+ ({coefficient_soc_t:.12f}) * SoC_t"
        )

    print()
    print("Units:")
    print("    left-hand side: kWh over 24 hours")
    print("    SoC_t:          kWh")
    print("    SoC_max:        kWh")
    print("    coefficients:   kWh per kWh over 24 hours")
    print()
    print("=" * 88)
    print()