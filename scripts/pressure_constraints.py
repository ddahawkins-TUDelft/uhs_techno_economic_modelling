from uhs_costs.design.salt_cavern import construct_project as construct_salt_cavern_project
from uhs_costs.analysis.pressure_constraint import calculate_pressure_limited_flow_curves_for_projects, plot_curves, save_results
from uhs_costs.design.helpers.project import StorageProject


from pathlib import Path


# =============================================================================
# Main
# =============================================================================


def main() -> None:

    salt_cavern_project_700 = construct_salt_cavern_project(
        working_gas_capacity_kwh_lhv=700_000_000,
        withdrawal_flow_kw_h2_lhv=3_000_000,
        injection_flow_kw_h2_lhv=1_500_000,
        case_name="salt_cavern_700GWh",
    )

    salt_cavern_project_1000 = construct_salt_cavern_project(
        working_gas_capacity_kwh_lhv=1_000_000_000,
        withdrawal_flow_kw_h2_lhv=3_000_000,
        injection_flow_kw_h2_lhv=1_500_000,
        case_name="salt_cavern_1TWh",
    )

    output_dir = Path("outputs/pressure_constraints")
    output_dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Replace this section with however you currently create/load projects.
    # ------------------------------------------------------------------
    #
    # Example:
    #
    # from scripts.create_projects import (
    #     salt_cavern_project_500_gwh,
    #     salt_cavern_project_700_gwh,
    #     salt_cavern_project_1000_gwh,
    # )
    #
    # projects = {
    #     "500 GWh": salt_cavern_project_500_gwh,
    #     "700 GWh": salt_cavern_project_700_gwh,
    #     "1000 GWh": salt_cavern_project_1000_gwh,
    # }
    #
    # ------------------------------------------------------------------

    projects: dict[str, StorageProject] = {
        "700GWh": salt_cavern_project_700,
        "1TWh": salt_cavern_project_1000,
    }

    if not projects:
        raise ValueError(
            "No projects provided. Add StorageProject objects to the `projects` "
            "dictionary in main()."
        )

    results_by_project = calculate_pressure_limited_flow_curves_for_projects(
        projects=projects,
        pressure_step_pa=1e5,                 
        pressure_change_limit_pa_per_day=10e5, 
    )

    save_results(
        results_by_project=results_by_project,
        output_dir=output_dir,
    )

    print("Electrical cost per unit of hydrogen through:",projects["1TWh"].compression.electricity_kwh_per_kwh_h2_lhv, "[kWh/kWh]")
    print("This translates to an injection process efficiency via 1/(1+λ):",1/(1+projects["1TWh"].compression.electricity_kwh_per_kwh_h2_lhv), "%")

    plot_curves(
        results=results_by_project,
        projects=projects,
        show_design_capacity=True,
        x="soc",
        y="withdrawal_kw_lhv",
        y_scale=1 / 1e6,
        xlabel="State of charge [-]",
        ylabel="Average 24-hour  Withdrawal capacity [GW LHV]",
        title="Pressure-constrained withdrawal capacity",
        output_path=output_dir / "withdrawal_capacity_by_soc.png",
    )

    plot_curves(
        results=results_by_project,
        projects=projects,
        x="soc",
        y="withdrawal_gw_per_twh",
        xlabel="State of charge [-]",
        ylabel="Average 24-hour withdrawal capacity [GW/TWh]",
        title="Capacity-normalised pressure-constrained withdrawal capacity",
        output_path=output_dir / "withdrawal_capacity_per_twh_by_soc.png",
    )

    plot_curves(
        results=results_by_project,
        projects=projects,
        show_design_capacity=True,
        x="soc",
        y="injection_kw_lhv",
        y_scale=1 / 1e6,
        xlabel="State of charge [-]",
        ylabel="Average Injection capacity over 24-hours [GW LHV]",
        title="Pressure-constrained injection capacity",
        output_path=output_dir / "injection_capacity_by_soc.png",
    )

    plot_curves(
        results=results_by_project,
        projects=projects,
        show_design_capacity=True,
        x="pressure_bar",
        y="withdrawal_kw_lhv",
        y_scale=1 / 1e6,
        xlabel="Pressure [bar]",
        ylabel="Average Withdrawal capacity over 24-hours [GW LHV]",
        title="Pressure-constrained withdrawal capacity",
        output_path=output_dir / "withdrawal_capacity_by_pressure.png",
    )

    plot_curves(
        results=results_by_project,
        x="pressure_bar",
        y="h2_inventory_kWh",
        y_scale=1 / 1e6,
        xlabel="Pressure [bar]",
        ylabel="Hydrogen inventory [GWh]",
        title="Hydrogen inventory as a function of pressure",
        output_path=output_dir / "inventory_by_pressure.png",
    )




if __name__ == "__main__":
    main()