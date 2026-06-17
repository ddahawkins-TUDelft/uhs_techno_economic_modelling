from uhs_costs.analysis.cost_rate_sensitivities import (
    DEFAULT_SENSITIVITIES,
    apply_override_to_project_kwargs,
    construct_assumptions_for_project,
    get_default_project_kwargs,
    resolve_parameter_value_from_assumptions,
)
from uhs_costs.design.helpers.project import StorageTechnology


def main():
    technology = StorageTechnology.DEPLETED_GAS_FIELD

    sensitivity = next(
        s for s in DEFAULT_SENSITIVITIES
        if s.name == "purification_factor"
    )

    kwargs = get_default_project_kwargs()

    changed_kwargs = apply_override_to_project_kwargs(
        project_kwargs=kwargs,
        sensitivity=sensitivity,
        value=2.0,
    )

    design_assumptions, cost_assumptions = construct_assumptions_for_project(
        technology=technology,
        project_kwargs=changed_kwargs,
    )

    value = resolve_parameter_value_from_assumptions(
        sensitivity=sensitivity,
        project_kwargs=changed_kwargs,
        design_assumptions=design_assumptions,
        cost_assumptions=cost_assumptions,
    )

    print("Technology:", technology)
    print("Resolved purification_factor:", value)
    print("General assumptions:", design_assumptions.general)


if __name__ == "__main__":
    main()