from pathlib import Path

from uhs_costs.design.salt_cavern import construct_project as construct_salt_cavern_project
from uhs_costs.design.lined_rock_cavern import construct_project as construct_lrc_project
from uhs_costs.design.depleted_gas_field import construct_project as construct_dgf_project
from uhs_costs.design.aquifer import construct_project as construct_aquifer_project


from uhs_costs.design.helpers.project import StorageProject

from uhs_costs.analysis.injection_efficiency import (
    calculate_injection_efficiency_curves_for_projects,
    save_injection_efficiency_results,
    plot_injection_efficiency_curve,
    plot_compression_intensity_curve,
)


def main() -> None:
    salt_cavern_project = construct_salt_cavern_project(
        working_gas_capacity_kwh_lhv=800_000_000,
        withdrawal_flow_kw_h2_lhv=800_000_000/(24*12),
        injection_flow_kw_h2_lhv=800_000_000/(24*12)/2,
        case_name="salt_cavern",
    )

    lrc_project = construct_lrc_project(
        working_gas_capacity_kwh_lhv=20_000_000, 
        withdrawal_flow_kw_h2_lhv=20_000_000/(24*7),
        injection_flow_kw_h2_lhv=20_000_000/(24*7)/2,
        case_name="lined_rock_cavern",
    )

    dgf_project = construct_dgf_project(
        working_gas_capacity_kwh_lhv=2_000_000_000,
        withdrawal_flow_kw_h2_lhv=2_000_000_000/(24*60),
        injection_flow_kw_h2_lhv=2_000_000_000/(24*60)/2,
        case_name="depleted_gas_field",
    )

    aquifer_project = construct_aquifer_project(
        working_gas_capacity_kwh_lhv=1_800_000_000,
        withdrawal_flow_kw_h2_lhv=1_800_000_000/(24*60),
        injection_flow_kw_h2_lhv=1_800_000_000/(24*60)/2,
        case_name="aquifer",
    )

    # salt_cavern_project_1000 = construct_salt_cavern_project(
    #     working_gas_capacity_kwh_lhv=1_000_000_000,
    #     withdrawal_flow_kw_h2_lhv=3_000_000,
    #     injection_flow_kw_h2_lhv=1_500_000,
    #     case_name="salt_cavern_1TWh",
    # )

    projects: dict[str, StorageProject] = {
        "salt_cavern": salt_cavern_project,
        "dgf": dgf_project,
        "lrc": lrc_project,
        "aquifer": aquifer_project,

    }

    if not projects:
        raise ValueError(
            "No projects provided. Add StorageProject objects to the `projects` "
            "dictionary in main()."
        )

    output_dir = Path("outputs/injection_efficiency")
    output_dir.mkdir(parents=True, exist_ok=True)

    results_by_project = calculate_injection_efficiency_curves_for_projects(
        projects=projects,
        n_points=101,
    )

    combined, summary = save_injection_efficiency_results(
        results_by_project=results_by_project,
        output_dir=output_dir,
    )

    print()
    print("=" * 88)
    print("Injection efficiency summary")
    print("=" * 88)
    print(
        summary[
            [
                "project",
                "min_efficiency",
                "mean_efficiency",
                "efficiency_at_soc_50",
                "max_compression_intensity_kwh_e_per_kwh_h2",
                "mean_compression_intensity_kwh_e_per_kwh_h2",
                "compression_intensity_at_soc_50_kwh_e_per_kwh_h2",
            ]
        ].to_string(index=False)
    )
    print("=" * 88)
    print()

    plot_injection_efficiency_curve(
        results=results_by_project,
        title="Injection efficiency across state of charge",
        xlabel="State of charge [-]",
        ylabel="Injection efficiency [-]",
        output_path=output_dir / "injection_efficiency_by_soc.png",
        show=True,
    )

    plot_compression_intensity_curve(
        results=results_by_project,
        title="Compression electricity intensity across state of charge",
        xlabel="State of charge [-]",
        ylabel="Compression intensity [kWh_e/kWh_H2,LHV]",
        output_path=output_dir / "compression_intensity_by_soc.png",
        show=True,
    )


if __name__ == "__main__":
    main()