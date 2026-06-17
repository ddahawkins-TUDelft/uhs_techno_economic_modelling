"""
Manual runner for PSA purification recovery across SoC and methane-depletion
cycling sensitivities.

Run from the repository root, for example:

    pixi run python scripts/purification_efficiency.py

Edit build_projects() to select the StorageProject designs you want to analyse.
"""

from __future__ import annotations

from pathlib import Path

from uhs_costs.analysis.pressure_swing_adsorption import (
    CyclingAssumptions,
    PSAAssumptions,
    calculate_purification_recovery_curves_for_projects,
    plot_cycle_methane_inventory,
    plot_cycle_recovery_curves,
    plot_purification_bed_size_curve,
    plot_purification_composition_curve,
    plot_purification_recovery_curve,
    save_methane_depletion_cycle_results,
    save_purification_recovery_curve_results,
    simulate_methane_depletion_cycles_for_projects,
    summarise_purification_recovery_curves,
    plot_cycle_tail_gas_composition
)
from uhs_costs.design.depleted_gas_field import construct_project as construct_dgf_project


OUTPUT_DIR = Path("outputs") / "purification_efficiency"

# Set this to "none" if you want a cleaner H2/CH4-only case.
NITROGEN_MODE = "fixed_mole_fraction" #"none"

# Toggle cycling sensitivity outputs.
RUN_METHANE_DEPLETION_CYCLES = True


def build_projects():
    """
    Return a mapping of label -> StorageProject.

    Keep construction here so the reusable analysis module remains independent
    of any one technology/design constructor.
    """
    projects = {}

    dgf_project_700 = construct_dgf_project(
        working_gas_capacity_kwh_lhv=700_000_000,
        withdrawal_flow_kw_h2_lhv=3_000_000,
        injection_flow_kw_h2_lhv=1_500_000,
        case_name="dgf_700GWh",
    )

    projects["dgf_700"] = dgf_project_700

    if not projects:
        raise RuntimeError(
            "No projects configured. Edit build_projects() in "
            "scripts/purification_efficiency.py to construct your StorageProject."
        )

    return projects


def main() -> None:
    projects = build_projects()

    psa_assumptions = PSAAssumptions()

    curves, loadings = calculate_purification_recovery_curves_for_projects(
        projects,
        assumptions=psa_assumptions,
        n_points=101,
        nitrogen_mode=NITROGEN_MODE,
    )
    summary = summarise_purification_recovery_curves(curves)

    curve_path, loading_path, summary_path = save_purification_recovery_curve_results(
        curves=curves,
        loadings=loadings,
        summary=summary,
        output_dir=OUTPUT_DIR,
    )

    plot_purification_recovery_curve(
        curves,
        output_path=OUTPUT_DIR / "purification_recovery_curve.png",
        show=True,
    )
    plot_purification_composition_curve(
        curves,
        output_path=OUTPUT_DIR / "purification_composition_curve.png",
        show=True,
    )
    plot_purification_bed_size_curve(
        curves,
        output_path=OUTPUT_DIR / "purification_bed_size_curve.png",
        show=True,
    )

    print("\nPurification recovery curve summary")
    print(summary.to_string(index=False))
    print(f"\nSaved recovery curve to: {curve_path}")
    print(f"Saved loading curve data to: {loading_path}")
    print(f"Saved recovery summary to: {summary_path}")

    if RUN_METHANE_DEPLETION_CYCLES:
        cycling_assumptions = CyclingAssumptions(
            n_cycles=20,
            n_discharge_steps=100,
            nitrogen_mode=NITROGEN_MODE,
        )

        cycle_curves, cycle_summary, discharge_steps = simulate_methane_depletion_cycles_for_projects(
            projects,
            assumptions=psa_assumptions,
            cycling=cycling_assumptions,
            n_curve_points=101,
        )

        cycle_output_dir = OUTPUT_DIR / "methane_depletion"
        cycle_curves_path, cycle_summary_path, discharge_steps_path = save_methane_depletion_cycle_results(
            cycle_curves=cycle_curves,
            cycle_summary=cycle_summary,
            discharge_steps=discharge_steps,
            output_dir=cycle_output_dir,
        )

        plot_cycle_recovery_curves(
            cycle_curves,
            cycles_to_plot=(1, 2, 5, 10, 20),
            output_path=cycle_output_dir / "methane_depletion_recovery_curves.png",
            show=True,
        )
        plot_cycle_methane_inventory(
            cycle_summary,
            output_path=cycle_output_dir / "methane_inventory_remaining.png",
            show=True,
        )

        plot_cycle_tail_gas_composition(
            cycle_curves,
            output_path=cycle_output_dir / "tail_gas_hydrogen_content_by_cycle.png",
            show=True,
        )

        print("\nMethane-depletion cycle summary")
        print(cycle_summary.to_string(index=False))
        print(f"\nSaved cycle recovery curves to: {cycle_curves_path}")
        print(f"Saved cycle summary to: {cycle_summary_path}")
        print(f"Saved discharge-step data to: {discharge_steps_path}")


if __name__ == "__main__":
    main()
