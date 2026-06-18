from uhs_costs.design.salt_cavern import construct_project as construct_salt_cavern_project
from uhs_costs.analysis.pressure_constraint import (
    calculate_pressure_limited_flow_curves_for_projects,
    plot_curves,
    plot_soc_change_bounds,
    plot_soc_endpoint_bounds,
    save_results,
)
from uhs_costs.design.helpers.project import StorageProject, StorageTechnology

from uhs_costs.design.default_design_assumptions import HyStoriesDesignAssumptions, construct_hystories_design_assumptions


from pathlib import Path


# =============================================================================
# Main
# =============================================================================


def main() -> None:

    salt_cavern_project_700 = construct_salt_cavern_project(
        working_gas_capacity_kwh_lhv=700_000_000,
        withdrawal_flow_kw_h2_lhv=3_000_000,
        injection_flow_kw_h2_lhv=1_500_000,
        case_name="90_to_240_bar",
    )

    low_pressure_range_assumptions =  construct_hystories_design_assumptions(
        storage_technology=StorageTechnology.SALT_CAVERN,
        general_overrides={
            'reference_reservoir_depth_m': 1000,
            'minimum_operating_pressure_pa': 12.0e6,
            'maximum_operating_pressure_pa': 20e6,
            'abandonment_pressure_pa': 0,
        }
    )

    salt_cavern_project_low_pressure = construct_salt_cavern_project(
        working_gas_capacity_kwh_lhv=1_000_000_000,
        withdrawal_flow_kw_h2_lhv=3_000_000,
        injection_flow_kw_h2_lhv=1_500_000,
        assumptions=low_pressure_range_assumptions,
        case_name="120_to_200_bar",
    )

    high_pressure_range_assumptions =  construct_hystories_design_assumptions(
        storage_technology=StorageTechnology.SALT_CAVERN,
        general_overrides={
            'reference_reservoir_depth_m': 1000,
            'minimum_operating_pressure_pa': 6.0e6,
            'maximum_operating_pressure_pa': 25e6,
            'abandonment_pressure_pa': 0,
        }
    )

    salt_cavern_project_high_pressure = construct_salt_cavern_project(
        working_gas_capacity_kwh_lhv=1_000_000_000,
        withdrawal_flow_kw_h2_lhv=3_000_000,
        injection_flow_kw_h2_lhv=1_500_000,
        assumptions=high_pressure_range_assumptions,
        case_name="60_to_250_bar",
    )

    output_dir = Path("outputs/pressure_constraints")
    output_dir.mkdir(parents=True, exist_ok=True)


    projects: dict[str, StorageProject] = {
        "90_to_240_bar": salt_cavern_project_700,
        "120_to_200_bar": salt_cavern_project_low_pressure,
        "60_to_250_bar": salt_cavern_project_high_pressure,
    }

    if not projects:
        raise ValueError(
            "No projects provided. Add StorageProject objects to the `projects` "
            "dictionary in main()."
        )

    # Optional plotting colours. Matplotlib colour names, hex codes, or RGB tuples
    # are all supported.
    project_colours = {
        "90_to_240_bar": (13/255, 8/255, 135/255),
        "120_to_200_bar": (204/255, 71/255, 120/255),
        "60_to_250_bar": (248/255, 149/255, 64/255),
    }
    bound_colours = {
        "min": "tab:red",
        "max": "tab:green",
    }

    results_by_project = calculate_pressure_limited_flow_curves_for_projects(
        projects=projects,
        pressure_step_pa=1e5,                 
        pressure_change_limit_pa_per_day=10e5, 
    )

    save_results(
        results_by_project=results_by_project,
        output_dir=output_dir,
    )

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
        line_colors=project_colours,
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
        line_colors=project_colours,
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
        line_colors=project_colours,
        output_path=output_dir / "injection_capacity_by_soc.png",
    )

    plot_soc_change_bounds(
        results=results_by_project,
        x="soc",
        xlabel="State of charge at time t [-]",
        ylabel="Signed 24-hour change in state of charge [-]",
        title="Pressure-constrained 24-hour SoC change bounds",
        line_colors=project_colours,
        show_linear_fit=False,
        output_path=output_dir / "soc_change_bounds_by_soc.png",
    )

    plot_soc_endpoint_bounds(
        results=results_by_project,
        x="soc",
        xlabel="State of charge at time t [-]",
        ylabel="Admissible state of charge at t+24 [-]",
        title="Pressure-constrained future SoC bounds",
        min_color=bound_colours["min"],
        max_color=bound_colours["max"],
        min_fit_color=bound_colours["min"],
        max_fit_color=bound_colours["max"],
        output_path=output_dir / "soc_endpoint_bounds_by_soc.png",
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
        line_colors=project_colours,
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
        line_colors=project_colours,
        output_path=output_dir / "inventory_by_pressure.png",
    )




if __name__ == "__main__":
    main()