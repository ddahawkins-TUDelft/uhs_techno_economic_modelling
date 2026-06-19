from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
import csv
import math
from typing import Any, Callable

import matplotlib.pyplot as plt

from uhs_costs.design.aquifer import construct_project as construct_aquifer_project
from uhs_costs.design.salt_cavern import construct_project as construct_salt_cavern_project
from uhs_costs.design.depleted_gas_field import construct_project as construct_dgf_project
from uhs_costs.design.lined_rock_cavern import construct_project as construct_lrc_project

from uhs_costs.cost_model.aquifer import (
    calculate_cost_components as calculate_aquifer_cost_components,
)
from uhs_costs.cost_model.salt_cavern import (
    calculate_salt_cavern_cost_components,
)
from uhs_costs.cost_model.depleted_gas_field import (
    calculate_depleted_gas_field_cost_components,
)
from uhs_costs.cost_model.lined_rock_cavern import (
    calculate_lined_rock_cavern_cost_components,
)


# =============================================================================
# Configuration
# =============================================================================

OUTPUT_DIR = Path("outputs/sensitivity_tests")
OUTPUT_CSV = OUTPUT_DIR / "cost_rate_sensitivity_results.csv"
FIGURE_DIR = OUTPUT_DIR / "figures"


DEFAULT_WTIR = 2.0
DEFAULT_HYDROGEN_PRICE_EUR_PER_KG = 4.12


@dataclass(frozen=True)
class TechnologySpec:
    technology: str
    case_name: str
    project_constructor: Callable[..., Any]
    cost_function: Callable[..., Any]
    default_storage_capacity_gwh_lhv: float
    storage_capacity_range_gwh_lhv: tuple[float, ...]
    default_withdrawal_duration_days: float
    withdrawal_duration_range_days: tuple[float, ...]


TECHNOLOGIES: tuple[TechnologySpec, ...] = (
    TechnologySpec(
        technology="salt_cavern",
        case_name="salt_cavern",
        project_constructor=construct_salt_cavern_project,
        cost_function=calculate_salt_cavern_cost_components,
        default_storage_capacity_gwh_lhv=800.0,
        storage_capacity_range_gwh_lhv=(200.0, 400.0, 800.0, 1200.0, 1600.0),
        default_withdrawal_duration_days=12.0,
        withdrawal_duration_range_days=(7.0, 12.0, 21.0, 30.0),
    ),
    TechnologySpec(
        technology="depleted_gas_field",
        case_name="depleted_gas_field",
        project_constructor=construct_dgf_project,
        cost_function=calculate_depleted_gas_field_cost_components,
        default_storage_capacity_gwh_lhv=2000.0,
        storage_capacity_range_gwh_lhv=(800.0, 2000.0, 5000.0, 10000.0),
        default_withdrawal_duration_days=60.0,
        withdrawal_duration_range_days=(30.0, 60.0, 90.0, 180.0),
    ),
    TechnologySpec(
        technology="aquifer",
        case_name="aquifer",
        project_constructor=construct_aquifer_project,
        cost_function=calculate_aquifer_cost_components,
        default_storage_capacity_gwh_lhv=1800.0,
        storage_capacity_range_gwh_lhv=(1000.0, 1800.0, 3000.0, 6000.0),
        default_withdrawal_duration_days=60.0,
        withdrawal_duration_range_days=(30.0, 60.0, 90.0, 180.0),
    ),
    TechnologySpec(
        technology="lined_rock_cavern",
        case_name="lined_rock_cavern",
        project_constructor=construct_lrc_project,
        cost_function=calculate_lined_rock_cavern_cost_components,
        default_storage_capacity_gwh_lhv=20.0,
        storage_capacity_range_gwh_lhv=(10.0, 20.0, 50.0, 100.0),
        default_withdrawal_duration_days=7.0,
        withdrawal_duration_range_days=(4.0, 7.0, 10.0, 14.0),
    ),
)

WTIR_RANGE = (1.0, 2.0, 3.0, 4.0)
HYDROGEN_PRICE_RANGE_EUR_PER_KG = (3.33, 4.12, 6.71, 7.42)

COMPONENT_GROUPS = ("Storage", "Injection", "Withdrawal")
TECHNOLOGY_LABELS = {
    "salt_cavern": "Salt cavern",
    "depleted_gas_field": "Depleted gas field",
    "aquifer": "Aquifer",
    "lined_rock_cavern": "Lined rock cavern",
}

SENSITIVITY_LABELS = {
    "storage_capacity_gwh_lhv": "Storage capacity",
    "withdrawal_duration_days": "Withdrawal duration / EPR",
    "wtir": "WTIR",
    "hydrogen_price_eur_per_kg": "Hydrogen price",
}

SENSITIVITY_UNITS = {
    "storage_capacity_gwh_lhv": "GWh LHV",
    "withdrawal_duration_days": "days",
    "wtir": "ratio",
    "hydrogen_price_eur_per_kg": "EUR/kg H2",
}


# =============================================================================
# Generic helpers
# =============================================================================


def normalise_name(value: Any) -> str:
    """Convert enums, strings, and objects to lower-case comparable strings."""

    if value is None:
        return ""

    if hasattr(value, "value"):
        value = value.value

    return str(value).lower().strip()



def safe_divide(numerator: float | None, denominator: float | None) -> float | None:
    if numerator is None or denominator is None:
        return None
    if denominator == 0:
        return None
    return numerator / denominator



def derive_power_from_storage_and_duration(
    *,
    storage_capacity_gwh_lhv: float,
    withdrawal_duration_days: float,
    wtir: float,
) -> tuple[float, float]:
    """Return withdrawal and injection power in kW H2 LHV.

    Parameters
    ----------
    storage_capacity_gwh_lhv:
        Working-gas storage capacity in GWh LHV.

    withdrawal_duration_days:
        Full-discharge duration, also referred to here as EPR.

    wtir:
        Withdrawal-to-injection ratio, defined as P_withdrawal / P_injection.
    """

    if withdrawal_duration_days <= 0:
        raise ValueError("withdrawal_duration_days must be positive.")
    if wtir <= 0:
        raise ValueError("wtir must be positive.")

    storage_capacity_kwh_lhv = storage_capacity_gwh_lhv * 1_000_000.0
    withdrawal_flow_kw_h2_lhv = storage_capacity_kwh_lhv / (
        withdrawal_duration_days * 24.0
    )
    injection_flow_kw_h2_lhv = withdrawal_flow_kw_h2_lhv / wtir

    return withdrawal_flow_kw_h2_lhv, injection_flow_kw_h2_lhv



def construct_project(
    *,
    spec: TechnologySpec,
    storage_capacity_gwh_lhv: float,
    withdrawal_duration_days: float,
    wtir: float,
) -> Any:
    """Construct a StorageProject from storage capacity, EPR, and WTIR."""

    withdrawal_flow_kw_h2_lhv, injection_flow_kw_h2_lhv = (
        derive_power_from_storage_and_duration(
            storage_capacity_gwh_lhv=storage_capacity_gwh_lhv,
            withdrawal_duration_days=withdrawal_duration_days,
            wtir=wtir,
        )
    )

    return spec.project_constructor(
        working_gas_capacity_kwh_lhv=storage_capacity_gwh_lhv * 1_000_000.0,
        withdrawal_flow_kw_h2_lhv=withdrawal_flow_kw_h2_lhv,
        injection_flow_kw_h2_lhv=injection_flow_kw_h2_lhv,
        case_name=spec.case_name,
    )



def calculate_cost_breakdown(
    *,
    spec: TechnologySpec,
    project: Any,
    cost_overrides: dict[str, object] | None = None,
) -> Any:
    """Calculate a cost breakdown with optional HyStories cost overrides."""

    return spec.cost_function(
        project,
        overrides=cost_overrides,
    )


# =============================================================================
# Cost-rate extraction
# =============================================================================


def get_cost_components(cost_breakdown: Any) -> tuple[Any, ...]:
    """Return CostComponent objects from a CostBreakdown."""

    if hasattr(cost_breakdown, "components"):
        return tuple(cost_breakdown.components)

    if isinstance(cost_breakdown, tuple | list):
        return tuple(cost_breakdown)

    raise TypeError(
        f"Unsupported cost breakdown type: {type(cost_breakdown).__name__}"
    )



def get_component_group(cost_component: Any) -> str | None:
    """Map a cost component to Storage, Injection, or Withdrawal."""

    cost_driver = normalise_name(cost_component.cost_driver)
    name = normalise_name(cost_component.name)

    if "injection" in cost_driver or "injection" in name:
        return "Injection"

    if "withdrawal" in cost_driver or "withdrawal" in name:
        return "Withdrawal"

    if "storage" in cost_driver:
        return "Storage"

    if "subsurface" in name:
        return "Storage"

    return None



def get_cost_type_label(cost_component: Any) -> str:
    """Return a clean cost-type label."""

    cost_type = normalise_name(cost_component.cost_type)

    if cost_type == "capex":
        return "CAPEX"

    if cost_type == "abex":
        return "ABEX"

    if cost_type == "fixed_opex":
        return "Fixed OPEX"

    if cost_type == "variable_opex":
        return "Variable OPEX"

    raise ValueError(f"Unknown cost type: {cost_component.cost_type}")



def get_cost_unit_label(cost_component: Any) -> str:
    """Return the cost unit as a string."""

    if hasattr(cost_component.cost_unit, "value"):
        return str(cost_component.cost_unit.value)

    return str(cost_component.cost_unit)



def get_cost_rate(cost_component: Any) -> float:
    """Calculate cost rate from absolute cost and driver value."""

    if cost_component.driver_value == 0:
        raise ValueError(
            f"Cannot calculate cost rate for {cost_component.name}: "
            "driver_value is zero."
        )

    return cost_component.value_eur / cost_component.driver_value



def summarise_total_capital_requirement_rates(
    cost_breakdown: Any,
) -> dict[str, dict[str, float | str | None]]:
    """Summarise CAPEX + ABEX rates for Storage, Injection, and Withdrawal."""

    rates: dict[tuple[str, str], float] = defaultdict(float)
    units: dict[tuple[str, str], str] = {}

    for component in get_cost_components(cost_breakdown):
        component_group = get_component_group(component)

        if component_group is None:
            continue

        cost_type = get_cost_type_label(component)

        if cost_type not in {"CAPEX", "ABEX"}:
            continue

        key = (component_group, cost_type)
        rates[key] += get_cost_rate(component)
        units[key] = get_cost_unit_label(component)

    summary: dict[str, dict[str, float | str | None]] = {}

    for component_group in COMPONENT_GROUPS:
        capex = rates.get((component_group, "CAPEX"), 0.0)
        abex = rates.get((component_group, "ABEX"), 0.0)
        unit = (
            units.get((component_group, "CAPEX"))
            or units.get((component_group, "ABEX"))
        )

        if unit is None and capex == 0.0 and abex == 0.0:
            summary[component_group] = {"rate": None, "unit": None}
        else:
            summary[component_group] = {
                "rate": capex + abex,
                "unit": unit,
            }

    return summary


# =============================================================================
# Sensitivity case construction
# =============================================================================


def iter_sensitivity_cases() -> list[dict[str, Any]]:
    """Create all one-at-a-time sensitivity cases."""

    cases: list[dict[str, Any]] = []

    for spec in TECHNOLOGIES:
        # Storage-capacity sensitivity.
        for value in spec.storage_capacity_range_gwh_lhv:
            cases.append(
                {
                    "sensitivity": "storage_capacity_gwh_lhv",
                    "technology": spec.technology,
                    "parameter_value": value,
                    "parameter_default": spec.default_storage_capacity_gwh_lhv,
                    "parameter_unit": SENSITIVITY_UNITS["storage_capacity_gwh_lhv"],
                    "storage_capacity_gwh_lhv": value,
                    "withdrawal_duration_days": spec.default_withdrawal_duration_days,
                    "wtir": DEFAULT_WTIR,
                    "hydrogen_price_eur_per_kg": DEFAULT_HYDROGEN_PRICE_EUR_PER_KG,
                }
            )

        # Withdrawal duration / EPR sensitivity.
        for value in spec.withdrawal_duration_range_days:
            cases.append(
                {
                    "sensitivity": "withdrawal_duration_days",
                    "technology": spec.technology,
                    "parameter_value": value,
                    "parameter_default": spec.default_withdrawal_duration_days,
                    "parameter_unit": SENSITIVITY_UNITS["withdrawal_duration_days"],
                    "storage_capacity_gwh_lhv": spec.default_storage_capacity_gwh_lhv,
                    "withdrawal_duration_days": value,
                    "wtir": DEFAULT_WTIR,
                    "hydrogen_price_eur_per_kg": DEFAULT_HYDROGEN_PRICE_EUR_PER_KG,
                }
            )

        # WTIR sensitivity.
        for value in WTIR_RANGE:
            cases.append(
                {
                    "sensitivity": "wtir",
                    "technology": spec.technology,
                    "parameter_value": value,
                    "parameter_default": DEFAULT_WTIR,
                    "parameter_unit": SENSITIVITY_UNITS["wtir"],
                    "storage_capacity_gwh_lhv": spec.default_storage_capacity_gwh_lhv,
                    "withdrawal_duration_days": spec.default_withdrawal_duration_days,
                    "wtir": value,
                    "hydrogen_price_eur_per_kg": DEFAULT_HYDROGEN_PRICE_EUR_PER_KG,
                }
            )

        # Hydrogen-price sensitivity.
        for value in HYDROGEN_PRICE_RANGE_EUR_PER_KG:
            cases.append(
                {
                    "sensitivity": "hydrogen_price_eur_per_kg",
                    "technology": spec.technology,
                    "parameter_value": value,
                    "parameter_default": DEFAULT_HYDROGEN_PRICE_EUR_PER_KG,
                    "parameter_unit": SENSITIVITY_UNITS["hydrogen_price_eur_per_kg"],
                    "storage_capacity_gwh_lhv": spec.default_storage_capacity_gwh_lhv,
                    "withdrawal_duration_days": spec.default_withdrawal_duration_days,
                    "wtir": DEFAULT_WTIR,
                    "hydrogen_price_eur_per_kg": value,
                }
            )

    return cases



def get_spec_by_technology(technology: str) -> TechnologySpec:
    for spec in TECHNOLOGIES:
        if spec.technology == technology:
            return spec

    raise KeyError(f"Unknown technology: {technology}")



def run_sensitivity_cases() -> list[dict[str, Any]]:
    """Run all sensitivity cases and return tidy output rows."""

    rows: list[dict[str, Any]] = []

    for case in iter_sensitivity_cases():
        spec = get_spec_by_technology(case["technology"])

        project = construct_project(
            spec=spec,
            storage_capacity_gwh_lhv=case["storage_capacity_gwh_lhv"],
            withdrawal_duration_days=case["withdrawal_duration_days"],
            wtir=case["wtir"],
        )

        cost_overrides = {
            "hydrogen_cost_eur_per_kg": case["hydrogen_price_eur_per_kg"],
        }

        cost_breakdown = calculate_cost_breakdown(
            spec=spec,
            project=project,
            cost_overrides=cost_overrides,
        )

        tcr_summary = summarise_total_capital_requirement_rates(cost_breakdown)

        withdrawal_flow_kw, injection_flow_kw = derive_power_from_storage_and_duration(
            storage_capacity_gwh_lhv=case["storage_capacity_gwh_lhv"],
            withdrawal_duration_days=case["withdrawal_duration_days"],
            wtir=case["wtir"],
        )

        parameter_ratio = safe_divide(
            float(case["parameter_value"]),
            float(case["parameter_default"]),
        )

        is_default_case = math.isclose(
            float(case["parameter_value"]),
            float(case["parameter_default"]),
            rel_tol=1e-9,
            abs_tol=1e-12,
        )

        for component_group, result in tcr_summary.items():
            rows.append(
                {
                    "sensitivity": case["sensitivity"],
                    "sensitivity_label": SENSITIVITY_LABELS[case["sensitivity"]],
                    "technology": case["technology"],
                    "technology_label": TECHNOLOGY_LABELS[case["technology"]],
                    "component_group": component_group,
                    "parameter_value": case["parameter_value"],
                    "parameter_default": case["parameter_default"],
                    "parameter_ratio_to_default": parameter_ratio,
                    "parameter_unit": case["parameter_unit"],
                    "is_default_case": is_default_case,
                    "storage_capacity_gwh_lhv": case["storage_capacity_gwh_lhv"],
                    "withdrawal_duration_days": case["withdrawal_duration_days"],
                    "wtir": case["wtir"],
                    "hydrogen_price_eur_per_kg": case["hydrogen_price_eur_per_kg"],
                    "withdrawal_flow_gw_h2_lhv": withdrawal_flow_kw / 1_000_000.0,
                    "injection_flow_gw_h2_lhv": injection_flow_kw / 1_000_000.0,
                    "total_capital_requirement_rate": result["rate"],
                    "cost_unit": result["unit"],
                    "rate_relative_to_default": None,
                }
            )

    add_relative_rates(rows)
    return rows



def add_relative_rates(rows: list[dict[str, Any]]) -> None:
    """Add rate_relative_to_default to rows in-place."""

    default_rates: dict[tuple[str, str, str], float] = {}

    for row in rows:
        if not row["is_default_case"]:
            continue

        rate = row["total_capital_requirement_rate"]
        if rate is None:
            continue

        key = (
            row["sensitivity"],
            row["technology"],
            row["component_group"],
        )
        default_rates[key] = float(rate)

    for row in rows:
        rate = row["total_capital_requirement_rate"]
        key = (
            row["sensitivity"],
            row["technology"],
            row["component_group"],
        )
        default_rate = default_rates.get(key)
        row["rate_relative_to_default"] = safe_divide(rate, default_rate)


# =============================================================================
# Output
# =============================================================================


def write_rows_to_csv(rows: list[dict[str, Any]], output_csv: Path) -> None:
    """Write tidy sensitivity rows to CSV."""

    output_csv.parent.mkdir(parents=True, exist_ok=True)

    if not rows:
        raise ValueError("No rows available to write.")

    fieldnames = list(rows[0].keys())

    with output_csv.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)



def get_technology_colours() -> dict[str, Any]:
    """Assign plasma colours to technologies."""

    cmap = plt.colormaps["plasma"]
    n = len(TECHNOLOGIES)

    return {
        spec.technology: cmap(0.15 + 0.70 * index / max(n - 1, 1))
        for index, spec in enumerate(TECHNOLOGIES)
    }



def plot_sensitivity_figures(rows: list[dict[str, Any]], figure_dir: Path) -> None:
    """Create one figure per sensitivity test.

    Each figure contains three panels, one each for Storage, Injection, and
    Withdrawal total capital requirement. The y-axis is normalised to the
    default case so that technologies with different absolute cost rates can be
    compared in one journal-friendly figure.
    """

    figure_dir.mkdir(parents=True, exist_ok=True)
    colours = get_technology_colours()
    markers = {
        "salt_cavern": "o",
        "depleted_gas_field": "s",
        "aquifer": "^",
        "lined_rock_cavern": "D",
    }

    sensitivity_order = (
        "storage_capacity_gwh_lhv",
        "withdrawal_duration_days",
        "wtir",
        "hydrogen_price_eur_per_kg",
    )

    for sensitivity in sensitivity_order:
        sensitivity_rows = [row for row in rows if row["sensitivity"] == sensitivity]
        if not sensitivity_rows:
            continue

        fig, axes = plt.subplots(
            nrows=1,
            ncols=3,
            figsize=(9.5, 3.2),
            sharex=True,
            sharey=True,
        )

        for axis, component_group in zip(axes, COMPONENT_GROUPS, strict=True):
            component_rows = [
                row
                for row in sensitivity_rows
                if row["component_group"] == component_group
                and row["rate_relative_to_default"] is not None
                and row["parameter_ratio_to_default"] is not None
            ]

            for spec in TECHNOLOGIES:
                tech_rows = [
                    row
                    for row in component_rows
                    if row["technology"] == spec.technology
                ]
                tech_rows = sorted(
                    tech_rows,
                    key=lambda row: float(row["parameter_ratio_to_default"]),
                )

                if not tech_rows:
                    continue

                x_values = [float(row["parameter_ratio_to_default"]) for row in tech_rows]
                y_values = [float(row["rate_relative_to_default"]) for row in tech_rows]

                axis.plot(
                    x_values,
                    y_values,
                    marker=markers[spec.technology],
                    markersize=4.5,
                    linewidth=1.6,
                    color=colours[spec.technology],
                    label=TECHNOLOGY_LABELS[spec.technology],
                )

                default_rows = [row for row in tech_rows if row["is_default_case"]]
                if default_rows:
                    default_row = default_rows[0]
                    axis.scatter(
                        [float(default_row["parameter_ratio_to_default"])],
                        [float(default_row["rate_relative_to_default"])],
                        marker="x",
                        s=55,
                        linewidths=1.8,
                        color=colours[spec.technology],
                        zorder=5,
                    )

            axis.axhline(1.0, color="0.35", linewidth=0.8, linestyle=":")
            axis.axvline(1.0, color="0.35", linewidth=0.8, linestyle=":")
            axis.set_title(component_group)
            axis.set_xlabel("Parameter / default")
            axis.grid(True, linewidth=0.4, alpha=0.35)

        axes[0].set_ylabel("TCR rate / default")

        handles, labels = axes[-1].get_legend_handles_labels()
        fig.legend(
            handles,
            labels,
            loc="lower center",
            ncol=4,
            frameon=False,
            bbox_to_anchor=(0.5, -0.06),
        )

        fig.suptitle(SENSITIVITY_LABELS[sensitivity], y=1.04)
        fig.tight_layout()

        output_stem = figure_dir / f"{sensitivity}_tcr_relative"
        fig.savefig(output_stem.with_suffix(".png"), dpi=300, bbox_inches="tight")
        fig.savefig(output_stem.with_suffix(".pdf"), bbox_inches="tight")
        plt.close(fig)



def main() -> None:
    rows = run_sensitivity_cases()
    write_rows_to_csv(rows, OUTPUT_CSV)
    plot_sensitivity_figures(rows, FIGURE_DIR)

    print(f"Saved sensitivity results to: {OUTPUT_CSV}")
    print(f"Saved sensitivity figures to: {FIGURE_DIR}")


if __name__ == "__main__":
    main()
