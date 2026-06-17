from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from uhs_costs.constants import HYDROGEN_LHV_KWH_PER_KG
from uhs_costs.design.helpers.project import StorageProject


@dataclass(frozen=True)
class GasComponent:
    name: str
    molar_mass_kg_per_mol: float
    mole_fraction: float


@dataclass(frozen=True)
class AdsorbentComponentParameters:
    """
    Langmuir parameters for a single gas component on a single adsorbent.

    The simplified PSA proxy uses:

        b_i = b_0 * exp(-delta_h / (R * T))
        q_i* = q_sat_i * (b_i * P_i) / (1 + sum_j b_j * P_j)

    where b_i has units of bar^-1 and P_i is the component partial pressure
    in bar.
    """

    b0_bar_inverse: float
    delta_h_j_per_mol: float
    qsat_mol_per_kg: float


@dataclass(frozen=True)
class AdsorbentParameters:
    name: str
    density_kg_per_m3: float
    components: Mapping[str, AdsorbentComponentParameters]


@dataclass(frozen=True)
class PSAAssumptions:
    """
    Assumptions for the simplified PSA purification proxy.

    Defaults follow the earlier Excel implementation. The fixed mole fractions
    are retained only as fallbacks/defaults. The main recovery-SoC workflow
    derives H2/CH4 composition from StorageProject inventories.
    """

    adsorption_pressure_bar: float = 40.0
    desorption_pressure_bar: float = 1.0
    temperature_k: float = 298.0
    cycle_time_s: float = 750.0
    loaded_bed_fraction: float = 0.8
    bed_volume_oversize_factor: float = 0.65
    target_hydrogen_purity: float = 0.99999

    # Used only for optional N2 background and static-composition fallbacks.
    hydrogen_mole_fraction: float = 0.96674
    methane_mole_fraction: float = 0.027
    nitrogen_mole_fraction: float = 0.00366

    gas_constant_j_per_mol_k: float = 8.31446261815324

    hydrogen_molar_mass_kg_per_mol: float = 2.01568e-3
    methane_molar_mass_kg_per_mol: float = 0.016043
    nitrogen_molar_mass_kg_per_mol: float = 0.0280134

    # 1 Sm3 is assumed to be a normal/standard cubic metre. This default is
    # close to 0 C and 1 atm. Adjust if your package uses another Sm3 convention.
    standard_molar_volume_m3_per_mol: float = 0.022414

    activated_carbon_density_kg_per_m3: float = 550.0
    zeolite_density_kg_per_m3: float = 620.0

    # Activated carbon Langmuir parameters: H2, CH4, N2.
    ac_h2_b0_bar_inverse: float = 0.00872
    ac_h2_delta_h_j_per_mol: float = -2630.0
    ac_h2_qsat_mol_per_kg: float = 1.97
    ac_ch4_b0_bar_inverse: float = 0.00024
    ac_ch4_delta_h_j_per_mol: float = -17740.0
    ac_ch4_qsat_mol_per_kg: float = 4.47
    ac_n2_b0_bar_inverse: float = 0.0007
    ac_n2_delta_h_j_per_mol: float = -12730.0
    ac_n2_qsat_mol_per_kg: float = 3.44

    # Zeolite parameters. The spreadsheet excludes methane on zeolite and
    # treats zeolite as interacting with H2 and N2.
    ze_h2_b0_bar_inverse: float = 0.01382
    ze_h2_delta_h_j_per_mol: float = -3560.0
    ze_h2_qsat_mol_per_kg: float = 0.7
    ze_n2_b0_bar_inverse: float = 0.00038
    ze_n2_delta_h_j_per_mol: float = -17140.0
    ze_n2_qsat_mol_per_kg: float = 2.39


@dataclass(frozen=True)
class CyclingAssumptions:
    """
    Assumptions for the loose methane-depletion cycling sensitivity.

    This is not a reservoir model. It assumes produced gas has the same bulk
    composition as the storage inventory at that SoC. Methane removed during
    purification is not reinjected during recharge.
    """

    n_cycles: int = 20
    n_discharge_steps: int = 100
    nitrogen_mode: str = "fixed_mole_fraction"  # "fixed_mole_fraction" or "none"


def _get_first_attr(obj: Any, names: tuple[str, ...], *, default: Any = None) -> Any:
    for name in names:
        if hasattr(obj, name):
            value = getattr(obj, name)
            if value is not None:
                return value
    if default is not None:
        return default
    raise AttributeError(
        f"None of the attributes {names} were found on {type(obj).__name__}."
    )


def h2_lhv_power_kw_to_mass_flow_kg_s(
    h2_lhv_power_kw: float,
    hydrogen_lhv_kwh_per_kg: float = HYDROGEN_LHV_KWH_PER_KG,
) -> float:
    if h2_lhv_power_kw <= 0:
        raise ValueError("h2_lhv_power_kw must be greater than zero.")
    if hydrogen_lhv_kwh_per_kg <= 0:
        raise ValueError("hydrogen_lhv_kwh_per_kg must be greater than zero.")
    return h2_lhv_power_kw / hydrogen_lhv_kwh_per_kg / 3600.0


def mass_flow_kg_s_to_molar_flow_mol_s(
    mass_flow_kg_s: float,
    molar_mass_kg_per_mol: float,
) -> float:
    if mass_flow_kg_s < 0:
        raise ValueError("mass_flow_kg_s cannot be negative.")
    if molar_mass_kg_per_mol <= 0:
        raise ValueError("molar_mass_kg_per_mol must be greater than zero.")
    return mass_flow_kg_s / molar_mass_kg_per_mol


def standard_volume_sm3_to_mol(
    volume_sm3: float,
    *,
    standard_molar_volume_m3_per_mol: float,
) -> float:
    if volume_sm3 < 0:
        raise ValueError("volume_sm3 cannot be negative.")
    if standard_molar_volume_m3_per_mol <= 0:
        raise ValueError("standard_molar_volume_m3_per_mol must be greater than zero.")
    return volume_sm3 / standard_molar_volume_m3_per_mol


def langmuir_b_bar_inverse(
    *,
    b0_bar_inverse: float,
    delta_h_j_per_mol: float,
    temperature_k: float,
    gas_constant_j_per_mol_k: float,
) -> float:
    if temperature_k <= 0:
        raise ValueError("temperature_k must be greater than zero.")
    if gas_constant_j_per_mol_k <= 0:
        raise ValueError("gas_constant_j_per_mol_k must be greater than zero.")
    return b0_bar_inverse * float(
        np.exp(-delta_h_j_per_mol / (gas_constant_j_per_mol_k * temperature_k))
    )


def equilibrium_loading_mol_per_kg(
    *,
    qsat_mol_per_kg: float,
    bi_pi: float,
    denominator: float,
) -> float:
    if denominator <= 0:
        raise ValueError("denominator must be greater than zero.")
    return qsat_mol_per_kg * bi_pi / denominator


def _adsorbent_map(assumptions: PSAAssumptions) -> dict[str, AdsorbentParameters]:
    return {
        "activated_carbon": AdsorbentParameters(
            name="activated_carbon",
            density_kg_per_m3=assumptions.activated_carbon_density_kg_per_m3,
            components={
                "hydrogen": AdsorbentComponentParameters(
                    assumptions.ac_h2_b0_bar_inverse,
                    assumptions.ac_h2_delta_h_j_per_mol,
                    assumptions.ac_h2_qsat_mol_per_kg,
                ),
                "methane": AdsorbentComponentParameters(
                    assumptions.ac_ch4_b0_bar_inverse,
                    assumptions.ac_ch4_delta_h_j_per_mol,
                    assumptions.ac_ch4_qsat_mol_per_kg,
                ),
            },
        ),
        "zeolite": AdsorbentParameters(
            name="zeolite",
            density_kg_per_m3=assumptions.zeolite_density_kg_per_m3,
            components={
                "hydrogen": AdsorbentComponentParameters(
                    assumptions.ze_h2_b0_bar_inverse,
                    assumptions.ze_h2_delta_h_j_per_mol,
                    assumptions.ze_h2_qsat_mol_per_kg,
                ),
                "nitrogen": AdsorbentComponentParameters(
                    assumptions.ze_n2_b0_bar_inverse,
                    assumptions.ze_n2_delta_h_j_per_mol,
                    assumptions.ze_n2_qsat_mol_per_kg,
                ),
            },
        ),
    }


def _component_map_from_fractions(
    *,
    y_h2: float,
    y_ch4: float,
    y_n2: float,
    assumptions: PSAAssumptions,
) -> dict[str, GasComponent]:
    total = y_h2 + y_ch4 + y_n2
    if not np.isclose(total, 1.0, rtol=0.0, atol=1e-6):
        raise ValueError(f"Gas mole fractions must sum to 1. Got {total}.")
    if min(y_h2, y_ch4, y_n2) < 0:
        raise ValueError("Gas mole fractions cannot be negative.")
    return {
        "hydrogen": GasComponent("hydrogen", assumptions.hydrogen_molar_mass_kg_per_mol, y_h2),
        "methane": GasComponent("methane", assumptions.methane_molar_mass_kg_per_mol, y_ch4),
        "nitrogen": GasComponent("nitrogen", assumptions.nitrogen_molar_mass_kg_per_mol, y_n2),
    }


def calculate_adsorbent_loadings_for_composition(
    *,
    y_h2: float,
    y_ch4: float,
    y_n2: float,
    assumptions: PSAAssumptions | None = None,
) -> pd.DataFrame:
    """
    Calculate adsorption, desorption and delta q* for one gas composition.
    """
    if assumptions is None:
        assumptions = PSAAssumptions()
    if assumptions.adsorption_pressure_bar <= assumptions.desorption_pressure_bar:
        raise ValueError("Adsorption pressure must exceed desorption pressure.")
    if not (0 < assumptions.loaded_bed_fraction <= 1):
        raise ValueError("loaded_bed_fraction must be in the interval (0, 1].")
    if assumptions.bed_volume_oversize_factor <= 0:
        raise ValueError("bed_volume_oversize_factor must be greater than zero.")

    components = _component_map_from_fractions(
        y_h2=y_h2,
        y_ch4=y_ch4,
        y_n2=y_n2,
        assumptions=assumptions,
    )
    adsorbents = _adsorbent_map(assumptions)

    rows: list[dict[str, float | str]] = []

    for adsorbent_name, adsorbent in adsorbents.items():
        bi_pi_ads: dict[str, float] = {}
        bi_pi_des: dict[str, float] = {}
        b_values: dict[str, float] = {}

        for component_name, params in adsorbent.components.items():
            component = components[component_name]
            b_value = langmuir_b_bar_inverse(
                b0_bar_inverse=params.b0_bar_inverse,
                delta_h_j_per_mol=params.delta_h_j_per_mol,
                temperature_k=assumptions.temperature_k,
                gas_constant_j_per_mol_k=assumptions.gas_constant_j_per_mol_k,
            )
            b_values[component_name] = b_value
            bi_pi_ads[component_name] = (
                b_value * assumptions.adsorption_pressure_bar * component.mole_fraction
            )
            bi_pi_des[component_name] = (
                b_value * assumptions.desorption_pressure_bar * component.mole_fraction
            )

        denominator_ads = 1.0 + sum(bi_pi_ads.values())
        denominator_des = 1.0 + sum(bi_pi_des.values())

        for component_name, params in adsorbent.components.items():
            q_ads = equilibrium_loading_mol_per_kg(
                qsat_mol_per_kg=params.qsat_mol_per_kg,
                bi_pi=bi_pi_ads[component_name],
                denominator=denominator_ads,
            )
            q_des = equilibrium_loading_mol_per_kg(
                qsat_mol_per_kg=params.qsat_mol_per_kg,
                bi_pi=bi_pi_des[component_name],
                denominator=denominator_des,
            )
            rows.append(
                {
                    "adsorbent": adsorbent_name,
                    "component": component_name,
                    "mole_fraction": components[component_name].mole_fraction,
                    "b_bar_inverse": b_values[component_name],
                    "bi_pi_adsorption": bi_pi_ads[component_name],
                    "bi_pi_desorption": bi_pi_des[component_name],
                    "q_adsorption_mol_per_kg": q_ads,
                    "q_desorption_mol_per_kg": q_des,
                    "delta_q_mol_per_kg": q_ads - q_des,
                    "adsorbent_density_kg_per_m3": adsorbent.density_kg_per_m3,
                }
            )

    return pd.DataFrame(rows)


def _get_working_h2_inventory_mol(
    project: StorageProject,
    assumptions: PSAAssumptions,
) -> float:
    working_gas_capacity_kwh = _get_first_attr(
        project.inventory,
        (
            "working_gas_capacity_kwh_lhv",
            "working_gas_capacity_kwh",
            "working_gas_kwh_lhv",
        ),
    )
    working_h2_kg = working_gas_capacity_kwh / HYDROGEN_LHV_KWH_PER_KG
    return working_h2_kg / assumptions.hydrogen_molar_mass_kg_per_mol


def _get_cushion_h2_inventory_mol(
    project: StorageProject,
    assumptions: PSAAssumptions,
) -> float:
    """
    Return H2 cushion inventory [mol] if present, otherwise 0.

    Several possible attribute names are supported because the design module has
    been refactored a few times. This intentionally avoids using total cushion
    gas attributes unless they explicitly refer to hydrogen.
    """
    volume_sm3 = _get_first_attr(
        project.inventory,
        (
            "cushion_gas_hydrogen_volume_sm3",
            "hydrogen_cushion_gas_volume_sm3",
            "cushion_hydrogen_volume_sm3",
            "h2_cushion_gas_volume_sm3",
            "cushion_gas_h2_volume_sm3",
        ),
        default=0.0,
    )
    return standard_volume_sm3_to_mol(
        float(volume_sm3),
        standard_molar_volume_m3_per_mol=assumptions.standard_molar_volume_m3_per_mol,
    )


def _get_methane_inventory_mol(
    project: StorageProject,
    assumptions: PSAAssumptions,
) -> float:
    volume_sm3 = _get_first_attr(
        project.inventory,
        (
            "abandonment_gas_methane_volume_sm3",
            "methane_abandonment_gas_volume_sm3",
            "cushion_gas_methane_volume_sm3",
            "methane_cushion_gas_volume_sm3",
            "ch4_cushion_gas_volume_sm3",
        ),
        default=0.0,
    )
    return standard_volume_sm3_to_mol(
        float(volume_sm3),
        standard_molar_volume_m3_per_mol=assumptions.standard_molar_volume_m3_per_mol,
    )


def _get_withdrawal_flow_kw_h2_lhv(project: StorageProject) -> float:
    return float(
        _get_first_attr(
            project.flows,
            (
                "withdrawal_flow_kw_h2_lhv",
                "withdrawal_capacity_kw_h2_lhv",
                "withdrawal_flow_kw",
                "withdrawal_capacity_kw",
            ),
        )
    )


def composition_from_inventories(
    *,
    hydrogen_inventory_mol: float,
    methane_inventory_mol: float,
    nitrogen_mode: str,
    assumptions: PSAAssumptions,
) -> dict[str, float]:
    """
    Convert H2 and CH4 storage inventories into feed-gas mole fractions.

    nitrogen_mode="none" gives an H2/CH4-only composition. nitrogen_mode=
    "fixed_mole_fraction" reserves assumptions.nitrogen_mole_fraction for N2
    and scales H2/CH4 to the remaining fraction.
    """
    if hydrogen_inventory_mol < 0 or methane_inventory_mol < 0:
        raise ValueError("Inventories cannot be negative.")

    h2_ch4_total = hydrogen_inventory_mol + methane_inventory_mol
    if h2_ch4_total <= 0:
        raise ValueError("At least one of H2 or CH4 inventory must be positive.")

    if nitrogen_mode == "none":
        y_n2 = 0.0
    elif nitrogen_mode == "fixed_mole_fraction":
        y_n2 = assumptions.nitrogen_mole_fraction
        if y_n2 < 0 or y_n2 >= 1:
            raise ValueError("nitrogen_mole_fraction must be in [0, 1).")
    else:
        raise ValueError("nitrogen_mode must be 'none' or 'fixed_mole_fraction'.")

    remaining = 1.0 - y_n2
    y_h2 = remaining * hydrogen_inventory_mol / h2_ch4_total
    y_ch4 = remaining * methane_inventory_mol / h2_ch4_total

    return {"hydrogen": float(y_h2), "methane": float(y_ch4), "nitrogen": float(y_n2)}


def _delta_q(
    loading_df: pd.DataFrame,
    *,
    adsorbent: str,
    component: str,
    allow_zero: bool = False,
) -> float:
    mask = (loading_df["adsorbent"] == adsorbent) & (loading_df["component"] == component)
    if not mask.any():
        raise ValueError(f"No loading found for {adsorbent=} and {component=}.")
    value = float(loading_df.loc[mask, "delta_q_mol_per_kg"].iloc[0])
    if allow_zero and value >= 0:
        return value
    if value <= 0:
        raise ValueError(
            f"delta_q_mol_per_kg must be greater than zero for {adsorbent}/{component}."
        )
    return value


def calculate_purification_point(
    *,
    project: StorageProject,
    project_label: str,
    soc: float,
    y_h2: float,
    y_ch4: float,
    y_n2: float,
    assumptions: PSAAssumptions,
    withdrawal_flow_kw_h2_lhv: float | None = None,
    hydrogen_inventory_mol: float | None = None,
    methane_inventory_mol: float | None = None,
) -> tuple[dict[str, Any], pd.DataFrame]:
    """
    Calculate PSA recovery and bed sizes for one SoC/composition point.
    """
    if withdrawal_flow_kw_h2_lhv is None:
        withdrawal_flow_kw_h2_lhv = _get_withdrawal_flow_kw_h2_lhv(project)
    if y_h2 <= 0:
        raise ValueError("Hydrogen mole fraction must be greater than zero.")
    if assumptions.target_hydrogen_purity <= 0 or assumptions.target_hydrogen_purity > 1:
        raise ValueError("target_hydrogen_purity must be in the interval (0, 1].")

    loading_df = calculate_adsorbent_loadings_for_composition(
        y_h2=y_h2,
        y_ch4=y_ch4,
        y_n2=y_n2,
        assumptions=assumptions,
    )

    h2_mass_flow_kg_s = h2_lhv_power_kw_to_mass_flow_kg_s(withdrawal_flow_kw_h2_lhv)
    h2_molar_flow_mol_s = mass_flow_kg_s_to_molar_flow_mol_s(
        h2_mass_flow_kg_s,
        assumptions.hydrogen_molar_mass_kg_per_mol,
    )

    psa_feed_in_mol_s = h2_molar_flow_mol_s / y_h2
    psa_feed_out_mol_s_at_target_purity = h2_molar_flow_mol_s / assumptions.target_hydrogen_purity

    methane_removal_mol_s = psa_feed_in_mol_s * y_ch4
    nitrogen_removal_mol_s = psa_feed_in_mol_s * y_n2

    ac_delta_q_ch4 = _delta_q(loading_df, adsorbent="activated_carbon", component="methane")
    ze_delta_q_n2 = _delta_q(loading_df, adsorbent="zeolite", component="nitrogen", allow_zero=True)
    ac_delta_q_h2 = _delta_q(loading_df, adsorbent="activated_carbon", component="hydrogen")
    ze_delta_q_h2 = _delta_q(loading_df, adsorbent="zeolite", component="hydrogen")

    activated_carbon_mass_kg = 0.0
    if methane_removal_mol_s > 0:
        activated_carbon_mass_kg = (
            methane_removal_mol_s
            * assumptions.cycle_time_s
            / (ac_delta_q_ch4 * assumptions.loaded_bed_fraction)
        )

    zeolite_mass_kg = 0.0
    if nitrogen_removal_mol_s > 0:
        if ze_delta_q_n2 <= 0:
            raise ValueError("N2 removal requested but zeolite N2 delta_q is not positive.")
        zeolite_mass_kg = (
            nitrogen_removal_mol_s
            * assumptions.cycle_time_s
            / (ze_delta_q_n2 * assumptions.loaded_bed_fraction)
        )

    hydrogen_feed_per_cycle_mol = h2_molar_flow_mol_s * assumptions.cycle_time_s
    hydrogen_tied_up_in_beds_mol = (
        activated_carbon_mass_kg * ac_delta_q_h2
        + zeolite_mass_kg * ze_delta_q_h2
    )

    hydrogen_loss_fraction = hydrogen_tied_up_in_beds_mol / hydrogen_feed_per_cycle_mol
    hydrogen_recovery = 1.0 - hydrogen_loss_fraction

    hydrogen_loss_mol_s = hydrogen_tied_up_in_beds_mol / assumptions.cycle_time_s

    tail_gas_total_mol_s = (
        hydrogen_loss_mol_s
        + methane_removal_mol_s
        + nitrogen_removal_mol_s
    )
    tail_gas_hydrogen_mole_fraction = 0.0
    tail_gas_methane_mole_fraction = 0.0
    tail_gas_nitrogen_mole_fraction = 0.0
    if tail_gas_total_mol_s > 0:

        tail_gas_hydrogen_mole_fraction = hydrogen_loss_mol_s / tail_gas_total_mol_s
        tail_gas_methane_mole_fraction = methane_removal_mol_s / tail_gas_total_mol_s
        tail_gas_nitrogen_mole_fraction = nitrogen_removal_mol_s / tail_gas_total_mol_s
      

    activated_carbon_bed_volume_m3 = (
        activated_carbon_mass_kg
        / assumptions.activated_carbon_density_kg_per_m3
        / assumptions.bed_volume_oversize_factor
    )
    zeolite_bed_volume_m3 = (
        zeolite_mass_kg
        / assumptions.zeolite_density_kg_per_m3
        / assumptions.bed_volume_oversize_factor
    )

    row: dict[str, Any] = {
        "project": project_label,
        "soc": float(soc),
        "hydrogen_inventory_mol": hydrogen_inventory_mol,
        "methane_inventory_mol": methane_inventory_mol,
        "y_h2": float(y_h2),
        "y_ch4": float(y_ch4),
        "y_n2": float(y_n2),
        "withdrawal_flow_kw_h2_lhv": float(withdrawal_flow_kw_h2_lhv),
        "hydrogen_withdrawal_flow_kg_s": float(h2_mass_flow_kg_s),
        "hydrogen_withdrawal_flow_mol_s": float(h2_molar_flow_mol_s),
        "psa_feed_in_mol_s": float(psa_feed_in_mol_s),
        "psa_feed_out_mol_s_at_target_purity": float(psa_feed_out_mol_s_at_target_purity),
        "methane_removal_mol_s": float(methane_removal_mol_s),
        "nitrogen_removal_mol_s": float(nitrogen_removal_mol_s),
        "activated_carbon_mass_kg": float(activated_carbon_mass_kg),
        "zeolite_mass_kg": float(zeolite_mass_kg),
        "activated_carbon_bed_volume_m3": float(activated_carbon_bed_volume_m3),
        "zeolite_bed_volume_m3": float(zeolite_bed_volume_m3),
        "hydrogen_feed_per_cycle_mol": float(hydrogen_feed_per_cycle_mol),
        "hydrogen_tied_up_in_beds_mol": float(hydrogen_tied_up_in_beds_mol),
        "hydrogen_recovery": float(hydrogen_recovery),
        "hydrogen_loss_fraction": float(hydrogen_loss_fraction),
        "target_hydrogen_purity": float(assumptions.target_hydrogen_purity),
        "tail_gas_hydrogen_mole_fraction": float(tail_gas_hydrogen_mole_fraction),
        "tail_gas_methane_mole_fraction": float(tail_gas_methane_mole_fraction),
        "tail_gas_nitrogen_mole_fraction": float(tail_gas_nitrogen_mole_fraction)

    }

    loading_df = loading_df.assign(project=project_label, soc=float(soc))

    return row, loading_df


def calculate_purification_recovery_curve(
    project: StorageProject,
    *,
    assumptions: PSAAssumptions | None = None,
    project_label: str | None = None,
    n_points: int = 101,
    nitrogen_mode: str = "fixed_mole_fraction",
    methane_inventory_mol_override: float | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Calculate an SoC-dependent purification recovery curve.

    H2 inventory is modelled as:

        H2_cushion + SoC * H2_working_gas

    CH4 inventory is fixed by default from the StorageProject methane cushion /
    abandonment gas volume, but can be overridden for cycling sensitivities.
    """
    if assumptions is None:
        assumptions = PSAAssumptions()
    if project_label is None:
        project_label = project.case_name or str(project.technology)
    if n_points < 2:
        raise ValueError("n_points must be at least 2.")

    h2_working_mol = _get_working_h2_inventory_mol(project, assumptions)
    h2_cushion_mol = _get_cushion_h2_inventory_mol(project, assumptions)
    methane_inventory_mol = (
        _get_methane_inventory_mol(project, assumptions)
        if methane_inventory_mol_override is None
        else float(methane_inventory_mol_override)
    )

    rows: list[dict[str, Any]] = []
    loading_frames: list[pd.DataFrame] = []

    for soc in np.linspace(0.0, 1.0, n_points):
        h2_inventory_mol = h2_cushion_mol + soc * h2_working_mol
        composition = composition_from_inventories(
            hydrogen_inventory_mol=h2_inventory_mol,
            methane_inventory_mol=methane_inventory_mol,
            nitrogen_mode=nitrogen_mode,
            assumptions=assumptions,
        )
        row, loading_df = calculate_purification_point(
            project=project,
            project_label=project_label,
            soc=float(soc),
            y_h2=composition["hydrogen"],
            y_ch4=composition["methane"],
            y_n2=composition["nitrogen"],
            assumptions=assumptions,
            hydrogen_inventory_mol=float(h2_inventory_mol),
            methane_inventory_mol=float(methane_inventory_mol),
        )
        row["h2_working_inventory_mol"] = float(h2_working_mol)
        row["h2_cushion_inventory_mol"] = float(h2_cushion_mol)
        rows.append(row)
        loading_frames.append(loading_df)

    return pd.DataFrame(rows), pd.concat(loading_frames, ignore_index=True)


def calculate_purification_recovery_curves_for_projects(
    projects: Mapping[str, StorageProject],
    *,
    assumptions: PSAAssumptions | None = None,
    n_points: int = 101,
    nitrogen_mode: str = "fixed_mole_fraction",
) -> tuple[pd.DataFrame, pd.DataFrame]:
    if not projects:
        raise ValueError("No projects provided.")
    curves: list[pd.DataFrame] = []
    loadings: list[pd.DataFrame] = []
    for label, project in projects.items():
        curve, loading = calculate_purification_recovery_curve(
            project=project,
            assumptions=assumptions,
            project_label=label,
            n_points=n_points,
            nitrogen_mode=nitrogen_mode,
        )
        curves.append(curve)
        loadings.append(loading)
    return pd.concat(curves, ignore_index=True), pd.concat(loadings, ignore_index=True)


def summarise_purification_recovery_curves(curves: pd.DataFrame) -> pd.DataFrame:
    required = {"project", "soc", "hydrogen_recovery", "y_ch4", "activated_carbon_bed_volume_m3", "zeolite_bed_volume_m3"}
    missing = required - set(curves.columns)
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    rows: list[dict[str, Any]] = []
    for project, df in curves.groupby("project", sort=False):
        curve = df.sort_values("soc")
        soc = curve["soc"].to_numpy()
        recovery = curve["hydrogen_recovery"].to_numpy()
        if soc[0] == soc[-1]:
            mean_recovery = float(recovery.mean())
        else:
            mean_recovery = float(np.trapezoid(recovery, soc) / (soc[-1] - soc[0]))

        rows.append(
            {
                "project": project,
                "min_hydrogen_recovery": float(recovery.min()),
                "mean_hydrogen_recovery": mean_recovery,
                "hydrogen_recovery_at_soc_0": float(np.interp(0.0, soc, recovery)),
                "hydrogen_recovery_at_soc_50": float(np.interp(0.5, soc, recovery)),
                "hydrogen_recovery_at_soc_100": float(np.interp(1.0, soc, recovery)),
                "max_y_ch4": float(curve["y_ch4"].max()),
                "y_ch4_at_soc_0": float(np.interp(0.0, soc, curve["y_ch4"].to_numpy())),
                "y_ch4_at_soc_50": float(np.interp(0.5, soc, curve["y_ch4"].to_numpy())),
                "y_ch4_at_soc_100": float(np.interp(1.0, soc, curve["y_ch4"].to_numpy())),
                "max_activated_carbon_bed_volume_m3": float(curve["activated_carbon_bed_volume_m3"].max()),
                "max_zeolite_bed_volume_m3": float(curve["zeolite_bed_volume_m3"].max()),
            }
        )
    return pd.DataFrame(rows)


def save_purification_recovery_curve_results(
    *,
    curves: pd.DataFrame,
    loadings: pd.DataFrame,
    output_dir: str | Path,
    summary: pd.DataFrame | None = None,
) -> tuple[Path, Path, Path]:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    if summary is None:
        summary = summarise_purification_recovery_curves(curves)

    curve_path = output_dir / "purification_recovery_curve.csv"
    loading_path = output_dir / "purification_recovery_curve_loadings.csv"
    summary_path = output_dir / "purification_recovery_curve_summary.csv"

    curves.to_csv(curve_path, index=False)
    loadings.to_csv(loading_path, index=False)
    summary.to_csv(summary_path, index=False)

    return curve_path, loading_path, summary_path


def simulate_methane_depletion_cycles(
    project: StorageProject,
    *,
    assumptions: PSAAssumptions | None = None,
    cycling: CyclingAssumptions | None = None,
    project_label: str | None = None,
    n_curve_points: int = 101,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Simulate repeated full discharge/recharge cycles with methane removal.

    Returns
    -------
    tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]
        cycle_curves, cycle_summary, discharge_steps
    """
    if assumptions is None:
        assumptions = PSAAssumptions()
    if cycling is None:
        cycling = CyclingAssumptions()
    if project_label is None:
        project_label = project.case_name or str(project.technology)
    if cycling.n_cycles < 1:
        raise ValueError("n_cycles must be at least 1.")
    if cycling.n_discharge_steps < 1:
        raise ValueError("n_discharge_steps must be at least 1.")

    h2_working_mol = _get_working_h2_inventory_mol(project, assumptions)
    h2_cushion_mol = _get_cushion_h2_inventory_mol(project, assumptions)
    methane_inventory_mol = _get_methane_inventory_mol(project, assumptions)
    initial_methane_mol = methane_inventory_mol

    curve_frames: list[pd.DataFrame] = []
    step_rows: list[dict[str, Any]] = []
    summary_rows: list[dict[str, Any]] = []

    for cycle_number in range(1, cycling.n_cycles + 1):
        cycle_start_methane_mol = methane_inventory_mol

        curve, _ = calculate_purification_recovery_curve(
            project=project,
            assumptions=assumptions,
            project_label=project_label,
            n_points=n_curve_points,
            nitrogen_mode=cycling.nitrogen_mode,
            methane_inventory_mol_override=methane_inventory_mol,
        )
        curve = curve.assign(
            cycle=cycle_number,
            methane_inventory_mol_at_cycle_start=float(cycle_start_methane_mol),
            methane_inventory_fraction_remaining_at_cycle_start=(
                float(cycle_start_methane_mol / initial_methane_mol)
                if initial_methane_mol > 0
                else np.nan
            ),
        )
        curve_frames.append(curve)

        # Discharge from SoC 1 -> 0. Use midpoint compositions for each small
        # working-gas withdrawal interval.
        d_h2_working_mol = h2_working_mol / cycling.n_discharge_steps
        methane_removed_this_cycle = 0.0

        for step in range(1, cycling.n_discharge_steps + 1):
            soc_mid = 1.0 - (step - 0.5) / cycling.n_discharge_steps
            h2_inventory_mid_mol = h2_cushion_mol + soc_mid * h2_working_mol
            composition = composition_from_inventories(
                hydrogen_inventory_mol=h2_inventory_mid_mol,
                methane_inventory_mol=methane_inventory_mol,
                nitrogen_mode=cycling.nitrogen_mode,
                assumptions=assumptions,
            )
            y_h2 = composition["hydrogen"]
            y_ch4 = composition["methane"]
            total_produced_gas_mol = d_h2_working_mol / y_h2
            methane_withdrawn_mol = min(
                methane_inventory_mol,
                total_produced_gas_mol * y_ch4,
            )
            methane_inventory_mol -= methane_withdrawn_mol
            methane_removed_this_cycle += methane_withdrawn_mol

            step_rows.append(
                {
                    "project": project_label,
                    "cycle": cycle_number,
                    "step": step,
                    "soc_midpoint": float(soc_mid),
                    "y_h2_midpoint": float(y_h2),
                    "y_ch4_midpoint": float(y_ch4),
                    "y_n2_midpoint": float(composition["nitrogen"]),
                    "h2_working_withdrawn_mol": float(d_h2_working_mol),
                    "total_produced_gas_mol": float(total_produced_gas_mol),
                    "methane_withdrawn_mol": float(methane_withdrawn_mol),
                    "methane_inventory_mol_after_step": float(methane_inventory_mol),
                    "methane_inventory_fraction_remaining_after_step": (
                        float(methane_inventory_mol / initial_methane_mol)
                        if initial_methane_mol > 0
                        else np.nan
                    ),
                }
            )

        cycle_summary = summarise_purification_recovery_curves(curve)
        summary_rows.append(
            {
                **cycle_summary.iloc[0].to_dict(),
                "cycle": cycle_number,
                "methane_inventory_mol_at_cycle_start": float(cycle_start_methane_mol),
                "methane_inventory_mol_at_cycle_end": float(methane_inventory_mol),
                "methane_removed_this_cycle_mol": float(methane_removed_this_cycle),
                "methane_inventory_fraction_remaining_at_cycle_start": (
                    float(cycle_start_methane_mol / initial_methane_mol)
                    if initial_methane_mol > 0
                    else np.nan
                ),
                "methane_inventory_fraction_remaining_at_cycle_end": (
                    float(methane_inventory_mol / initial_methane_mol)
                    if initial_methane_mol > 0
                    else np.nan
                ),
            }
        )

        # Recharge restores the working H2 inventory but not methane. Because
        # the next iteration recomputes compositions from the full SoC curve,
        # no explicit H2 state update is needed here.

    return (
        pd.concat(curve_frames, ignore_index=True),
        pd.DataFrame(summary_rows),
        pd.DataFrame(step_rows),
    )


def simulate_methane_depletion_cycles_for_projects(
    projects: Mapping[str, StorageProject],
    *,
    assumptions: PSAAssumptions | None = None,
    cycling: CyclingAssumptions | None = None,
    n_curve_points: int = 101,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    if not projects:
        raise ValueError("No projects provided.")
    all_curves: list[pd.DataFrame] = []
    all_summaries: list[pd.DataFrame] = []
    all_steps: list[pd.DataFrame] = []
    for label, project in projects.items():
        curves, summary, steps = simulate_methane_depletion_cycles(
            project=project,
            assumptions=assumptions,
            cycling=cycling,
            project_label=label,
            n_curve_points=n_curve_points,
        )
        all_curves.append(curves)
        all_summaries.append(summary)
        all_steps.append(steps)
    return (
        pd.concat(all_curves, ignore_index=True),
        pd.concat(all_summaries, ignore_index=True),
        pd.concat(all_steps, ignore_index=True),
    )


def save_methane_depletion_cycle_results(
    *,
    cycle_curves: pd.DataFrame,
    cycle_summary: pd.DataFrame,
    discharge_steps: pd.DataFrame,
    output_dir: str | Path,
) -> tuple[Path, Path, Path]:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    curves_path = output_dir / "methane_depletion_cycle_recovery_curves.csv"
    summary_path = output_dir / "methane_depletion_cycle_summary.csv"
    steps_path = output_dir / "methane_depletion_discharge_steps.csv"
    cycle_curves.to_csv(curves_path, index=False)
    cycle_summary.to_csv(summary_path, index=False)
    discharge_steps.to_csv(steps_path, index=False)
    return curves_path, summary_path, steps_path


def _plot_grouped_lines(
    df: pd.DataFrame,
    *,
    x: str,
    y: str,
    group: str,
    title: str,
    xlabel: str,
    ylabel: str,
    output_path: str | Path | None = None,
    show: bool = True,
) -> None:
    fig, ax = plt.subplots(figsize=(8, 5))
    for label, group_df in df.groupby(group, sort=False):
        ax.plot(group_df[x], group_df[y], label=str(label))
    ax.set_title(title)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.grid(True, alpha=0.3)
    ax.legend()
    fig.tight_layout()
    if output_path is not None:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(output_path, dpi=300)
    if show:
        plt.show()
    else:
        plt.close(fig)


def plot_purification_recovery_curve(
    curves: pd.DataFrame,
    *,
    output_path: str | Path | None = None,
    show: bool = True,
) -> None:
    _plot_grouped_lines(
        curves,
        x="soc",
        y="hydrogen_recovery",
        group="project",
        title="PSA hydrogen recovery across state of charge",
        xlabel="State of charge [-]",
        ylabel="Hydrogen recovery [-]",
        output_path=output_path,
        show=show,
    )


def plot_purification_composition_curve(
    curves: pd.DataFrame,
    *,
    output_path: str | Path | None = None,
    show: bool = True,
) -> None:
    fig, ax = plt.subplots(figsize=(8, 5))
    for project, df in curves.groupby("project", sort=False):
        curve = df.sort_values("soc")
        ax.plot(curve["soc"], curve["y_h2"], label=f"{project} H2")
        ax.plot(curve["soc"], curve["y_ch4"], linestyle="--", label=f"{project} CH4")
        if curve["y_n2"].max() > 0:
            ax.plot(curve["soc"], curve["y_n2"], linestyle=":", label=f"{project} N2")
    ax.set_title("Withdrawal gas composition across state of charge")
    ax.set_xlabel("State of charge [-]")
    ax.set_ylabel("Mole fraction [-]")
    ax.grid(True, alpha=0.3)
    ax.legend()
    fig.tight_layout()
    if output_path is not None:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(output_path, dpi=300)
    if show:
        plt.show()
    else:
        plt.close(fig)


def plot_purification_bed_size_curve(
    curves: pd.DataFrame,
    *,
    output_path: str | Path | None = None,
    show: bool = True,
) -> None:
    fig, ax = plt.subplots(figsize=(8, 5))
    for project, df in curves.groupby("project", sort=False):
        curve = df.sort_values("soc")
        ax.plot(
            curve["soc"],
            curve["activated_carbon_bed_volume_m3"],
            label=f"{project} activated carbon",
        )
        ax.plot(
            curve["soc"],
            curve["zeolite_bed_volume_m3"],
            linestyle="--",
            label=f"{project} zeolite",
        )
    ax.set_title("PSA bed volume across state of charge")
    ax.set_xlabel("State of charge [-]")
    ax.set_ylabel("Bed volume [m3]")
    ax.grid(True, alpha=0.3)
    ax.legend()
    fig.tight_layout()
    if output_path is not None:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(output_path, dpi=300)
    if show:
        plt.show()
    else:
        plt.close(fig)


def plot_cycle_recovery_curves(
    cycle_curves: pd.DataFrame,
    *,
    project: str | None = None,
    cycles_to_plot: tuple[int, ...] | None = (1, 2, 5, 10, 20),
    output_path: str | Path | None = None,
    show: bool = True,
) -> None:
    df = cycle_curves.copy()
    if project is not None:
        df = df[df["project"] == project]
    if cycles_to_plot is not None:
        available = set(df["cycle"].unique())
        selected = [cycle for cycle in cycles_to_plot if cycle in available]
        if selected:
            df = df[df["cycle"].isin(selected)]

    fig, ax = plt.subplots(figsize=(8, 5))
    for (project_label, cycle), group_df in df.groupby(["project", "cycle"], sort=False):
        curve = group_df.sort_values("soc")
        ax.plot(curve["soc"], curve["hydrogen_recovery"], label=f"{project_label}, cycle {cycle}")
    ax.set_title("Methane-depletion sensitivity: recovery curve by cycle")
    ax.set_xlabel("State of charge [-]")
    ax.set_ylabel("Hydrogen recovery [-]")
    ax.grid(True, alpha=0.3)
    ax.legend()
    fig.tight_layout()
    if output_path is not None:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(output_path, dpi=300)
    if show:
        plt.show()
    else:
        plt.close(fig)


def plot_cycle_methane_inventory(cycle_summary: pd.DataFrame, *, output_path: str | Path | None = None, show: bool = True) -> None:
    fig, ax = plt.subplots(figsize=(8, 5))
    for project, df in cycle_summary.groupby("project", sort=False):
        ax.plot(
            df["cycle"],
            df["methane_inventory_fraction_remaining_at_cycle_end"],
            marker="o",
            label=project,
        )
    ax.set_title("Methane cushion inventory remaining after full cycles")
    ax.set_xlabel("Cycle number [-]")
    ax.set_ylabel("Methane inventory remaining [-]")
    ax.grid(True, alpha=0.3)
    ax.legend()
    fig.tight_layout()
    if output_path is not None:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(output_path, dpi=300)
    if show:
        plt.show()
    else:
        plt.close(fig)

def plot_cycle_tail_gas_composition(
    cycle_curves: pd.DataFrame,
    *,
    project: str | None = None,
    cycles_to_plot: list[int] | None = None,
    output_path: str | Path | None = None,
    show: bool = True,
) -> None:
    """
    Plot tail-gas composition across SoC for selected methane-depletion cycles.

    Expected columns
    ----------------
    cycle
    soc
    tail_gas_hydrogen_mole_fraction
    tail_gas_methane_mole_fraction
    tail_gas_nitrogen_mole_fraction

    If `project` is provided, only that project is plotted.
    """

    import matplotlib.pyplot as plt

    required_columns = {
        "cycle",
        "soc",
        "tail_gas_hydrogen_mole_fraction",
        "tail_gas_methane_mole_fraction",
        "tail_gas_nitrogen_mole_fraction",
    }

    missing = required_columns - set(cycle_curves.columns)
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    df = cycle_curves.copy()

    if project is not None:
        if "project" not in df.columns:
            raise ValueError("Column 'project' is required when filtering by project.")
        df = df[df["project"] == project].copy()

    if df.empty:
        raise ValueError("No cycle-curve data available for plotting.")

    if cycles_to_plot is None:
        available_cycles = sorted(df["cycle"].unique())
        if len(available_cycles) <= 5:
            cycles_to_plot = available_cycles
        else:
            cycles_to_plot = [
                available_cycles[0],
                available_cycles[len(available_cycles) // 4],
                available_cycles[len(available_cycles) // 2],
                available_cycles[(3 * len(available_cycles)) // 4],
                available_cycles[-1],
            ]

    plot_df = df[df["cycle"].isin(cycles_to_plot)].copy()

    if plot_df.empty:
        raise ValueError("No rows match the requested cycles_to_plot.")

    fig, ax = plt.subplots(figsize=(8, 5))

    for cycle in cycles_to_plot:
        cycle_df = plot_df[plot_df["cycle"] == cycle].sort_values("soc")

        if cycle_df.empty:
            continue

        ax.plot(
            cycle_df["soc"],
            cycle_df["tail_gas_hydrogen_mole_fraction"],
            label=f"Cycle {cycle}",
        )

    ax.set_xlabel("State of charge [-]")
    ax.set_ylabel("Tail-gas H₂ mole fraction [-]")
    ax.set_title("Tail-gas hydrogen content across methane-depletion cycles")
    ax.grid(True, alpha=0.3)
    ax.legend()

    fig.tight_layout()

    if output_path is not None:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(output_path, dpi=300)

    if show:
        plt.show()
    else:
        plt.close(fig)