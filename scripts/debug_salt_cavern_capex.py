from collections import defaultdict

from uhs_costs.design.salt_cavern import construct_salt_cavern_project
from uhs_costs.cost_model.recipes import calculate_salt_cavern_cost_components
from uhs_costs.cost_model.cost_components import CostType


# --------------------------------------------------------------------------------------------------
#
#                                           Formatting helpers
#
# --------------------------------------------------------------------------------------------------


def enum_value(value) -> str:
    """Return enum.value if available, otherwise str(value)."""
    return value.value if hasattr(value, "value") else str(value)


def truncate(text: str, width: int) -> str:
    """Truncate long text for fixed-width console tables."""
    if len(text) <= width:
        return text

    return text[: max(width - 1, 0)] + "…"


def component_value(component) -> float:
    """Return component value, supporting either value_eur or value naming."""
    if hasattr(component, "value_eur"):
        return component.value_eur

    if hasattr(component, "value"):
        return component.value

    raise AttributeError("CostComponent has neither value_eur nor value.")


def component_unit(component) -> str:
    """Return component cost unit, supporting either cost_unit or unit naming."""
    if hasattr(component, "cost_unit"):
        return enum_value(component.cost_unit)

    if hasattr(component, "unit"):
        return enum_value(component.unit)

    return ""


def component_value_per_driver(component) -> float:
    """Return component value divided by its driver value."""
    if component.driver_value is None or component.driver_value <= 0:
        raise ValueError(
            f"Component {component.name} has invalid driver_value: "
            f"{component.driver_value}"
        )

    return component_value(component) / component.driver_value


def format_value(value: float) -> str:
    """Format source values before driver division."""
    return f"{value:,.0f}"


def format_rate(value: float) -> str:
    """Format value / driver outputs."""
    return f"{value:,.6f}"


def format_driver_value(value: float | None) -> str:
    if value is None:
        return ""

    return f"{value:,.2f}"


def print_separator(width: int) -> None:
    print("-" * width)


# --------------------------------------------------------------------------------------------------
#
#                                           Component table
#
# --------------------------------------------------------------------------------------------------


def print_component_table(breakdown) -> None:
    print("\n" + "=" * 145)
    print("Component-level costs")
    print("=" * 145)

    component_width = 42
    group_width = 12
    type_width = 14
    driver_width = 26
    value_width = 18
    driver_value_width = 18
    per_driver_width = 18
    unit_width = 18

    header = (
        f"{'Component':{component_width}s} "
        f"{'Group':{group_width}s} "
        f"{'Type':{type_width}s} "
        f"{'Driver':{driver_width}s} "
        f"{'Value':>{value_width}s} "
        f"{'Driver value':>{driver_value_width}s} "
        f"{'Value / driver':>{per_driver_width}s} "
        f"{'Unit':{unit_width}s}"
    )
    print(header)
    print_separator(len(header))

    for component in breakdown.components:
        value = component_value(component)
        driver_value = component.driver_value
        value_per_driver = component_value_per_driver(component)

        print(
            f"{truncate(component.name, component_width):{component_width}s} "
            f"{enum_value(component.hystories_group):{group_width}s} "
            f"{enum_value(component.cost_type):{type_width}s} "
            f"{truncate(enum_value(component.cost_driver), driver_width):{driver_width}s} "
            f"{format_value(value):>{value_width}s} "
            f"{format_driver_value(driver_value):>{driver_value_width}s} "
            f"{format_rate(value_per_driver):>{per_driver_width}s} "
            f"{truncate(component_unit(component), unit_width):{unit_width}s}"
        )


# --------------------------------------------------------------------------------------------------
#
#                                           Driver/type/unit totals
#
# --------------------------------------------------------------------------------------------------


def print_driver_type_unit_totals(breakdown) -> None:
    """Print totals grouped by driver, cost type, and resulting cost unit.

    The reported value is always:
        sum(component.value_eur) / driver_value

    For variable OPEX, driver_value can be 1, so the reported value is simply
    the rate itself.
    """
    totals = defaultdict(float)
    driver_values = {}

    for component in breakdown.components:
        key = (
            component.cost_driver,
            component.cost_type,
            component_unit(component),
        )

        totals[key] += component_value(component)

        if component.driver_value is not None:
            existing_driver_value = driver_values.get(component.cost_driver)

            if (
                existing_driver_value is not None
                and abs(existing_driver_value - component.driver_value) > 1e-9
            ):
                raise ValueError(
                    f"Inconsistent driver values for {component.cost_driver}: "
                    f"{existing_driver_value} vs {component.driver_value}"
                )

            driver_values[component.cost_driver] = component.driver_value

    print("\n" + "=" * 130)
    print("Cost by driver, type, and unit")
    print("=" * 130)

    driver_width = 26
    type_width = 14
    value_width = 18
    driver_value_width = 18
    per_driver_width = 18
    unit_width = 18

    header = (
        f"{'Driver':{driver_width}s} "
        f"{'Type':{type_width}s} "
        f"{'Total value':>{value_width}s} "
        f"{'Driver value':>{driver_value_width}s} "
        f"{'Value / driver':>{per_driver_width}s} "
        f"{'Unit':{unit_width}s}"
    )
    print(header)
    print_separator(len(header))

    for (driver, cost_type, unit), total_value in sorted(
        totals.items(),
        key=lambda item: (
            enum_value(item[0][0]),
            enum_value(item[0][1]),
            item[0][2],
        ),
    ):
        driver_value = driver_values.get(driver)

        if driver_value is None or driver_value <= 0:
            raise ValueError(
                f"Invalid driver value for grouped driver {driver}: {driver_value}"
            )

        value_per_driver = total_value / driver_value

        print(
            f"{truncate(enum_value(driver), driver_width):{driver_width}s} "
            f"{enum_value(cost_type):{type_width}s} "
            f"{format_value(total_value):>{value_width}s} "
            f"{format_driver_value(driver_value):>{driver_value_width}s} "
            f"{format_rate(value_per_driver):>{per_driver_width}s} "
            f"{truncate(unit, unit_width):{unit_width}s}"
        )


# --------------------------------------------------------------------------------------------------
#
#                                           HyStories group/type/unit totals
#
# --------------------------------------------------------------------------------------------------


def print_hystories_group_type_unit_totals(breakdown) -> None:
    """Print totals by HyStories group, type, and resulting cost unit.

    This table reports raw totals, not divided by driver, because a HyStories
    group may combine different drivers.
    """
    totals = defaultdict(float)

    for component in breakdown.components:
        key = (
            component.hystories_group,
            component.cost_type,
            component_unit(component),
        )
        totals[key] += component_value(component)

    print("\n" + "=" * 115)
    print("Raw totals by HyStories group, type, and unit")
    print("=" * 115)

    group_width = 15
    type_width = 14
    value_width = 18
    unit_width = 18

    header = (
        f"{'Group':{group_width}s} "
        f"{'Type':{type_width}s} "
        f"{'Raw total':>{value_width}s} "
        f"{'Unit after driver':{unit_width}s}"
    )
    print(header)
    print_separator(len(header))

    for (group, cost_type, unit), total_value in sorted(
        totals.items(),
        key=lambda item: (
            enum_value(item[0][0]),
            enum_value(item[0][1]),
            item[0][2],
        ),
    ):
        print(
            f"{enum_value(group):{group_width}s} "
            f"{enum_value(cost_type):{type_width}s} "
            f"{format_value(total_value):>{value_width}s} "
            f"{truncate(unit, unit_width):{unit_width}s}"
        )


# --------------------------------------------------------------------------------------------------
#
#                                           Totals
#
# --------------------------------------------------------------------------------------------------


def print_raw_totals_by_type(breakdown) -> None:
    """Print raw totals by cost type before driver division."""
    totals = defaultdict(float)

    for component in breakdown.components:
        totals[component.cost_type] += component_value(component)

    print("\n" + "=" * 90)
    print("Raw totals by cost type")
    print("=" * 90)

    for cost_type, total_value in sorted(
        totals.items(),
        key=lambda item: enum_value(item[0]),
    ):
        print(f"{enum_value(cost_type):15s}: {total_value:,.0f}")


def raw_total_by_cost_type(breakdown, cost_type: CostType) -> float:
    return sum(
        component_value(component)
        for component in breakdown.components
        if component.cost_type == cost_type
    )


def raw_total_all_components(breakdown) -> float:
    return sum(component_value(component) for component in breakdown.components)


# --------------------------------------------------------------------------------------------------
#
#                                           Main
#
# --------------------------------------------------------------------------------------------------


def main() -> None:
    project = construct_salt_cavern_project(
        working_gas_capacity_kwh_lhv=700_000_000,
        withdrawal_flow_kw_h2_lhv=3_000_000,
        injection_flow_kw_h2_lhv=1_500_000,
        case_name="debug_salt_cavern",
    )

    breakdown = calculate_salt_cavern_cost_components(project)

    raw_total = raw_total_all_components(breakdown)
    raw_capex_total = raw_total_by_cost_type(breakdown, CostType.CAPEX)

    print(f"\nCase: {project.case_name}")
    print(f"Number of components: {len(breakdown.components)}")
    print(f"Raw total across all components: {raw_total:,.0f}")
    print(f"Raw CAPEX total: {raw_capex_total:,.0f}")

    print_component_table(breakdown)
    print_driver_type_unit_totals(breakdown)
    print_hystories_group_type_unit_totals(breakdown)
    print_raw_totals_by_type(breakdown)

    if getattr(project, "salt_leaching_process", None) is not None:
        print("\nSalt leaching process")
        print(project.salt_leaching_process)

    if getattr(project, "salt_conversion_process", None) is not None:
        print("\nSalt conversion process")
        print(project.salt_conversion_process)


if __name__ == "__main__":
    main()