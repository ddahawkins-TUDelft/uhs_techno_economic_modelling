
from uhs_costs.design.project import StorageProject
from uhs_costs.cost_model.assumptions import HyStoriesCostAssumptions
from uhs_costs.cost_model import surface_capex, subsurface_capex
from uhs_costs.cost_model.cost_components import (
    CostBreakdown,
    CostComponent,
    CostType,
    HyStoriesGroup,
    CostDriver,
    AllocationMethod,
    fixed_component_cost_allocation
)


DEFAULT_ASSUMPTIONS = HyStoriesCostAssumptions 

def calculate_salt_cavern_capex_components(
    project: StorageProject,
) -> CostBreakdown:
    """Calculate decomposed HyStories-derived salt cavern CAPEX components."""

    # compression = project.compression
    # pressures = project.pressures
    # flows = project.flows
    # inventory = project.inventory
    # wells = project.wells
    # drilling = project.drilling
    # field_interconnection = project.field_interconnection
    # salt_leaching = project.salt_leaching
    # purification = project.purification


    components: list[CostComponent] = []
 
    # ---------------------------------------------------------------------------------------------------------------
    #
    #                                                   Surface EPC1
    #
    # ---------------------------------------------------------------------------------------------------------------

    surface_epc1_injection = surface_capex.epc1_compression_cost_eur(
        total_installed_compression_brake_power_mw=( project.compression.total_design_brake_power_kw / 1000 ),
        material_cost_factor_injection=DEFAULT_ASSUMPTIONS.material_cost_factor_injection,
    )

    surface_epc1_withdrawal = surface_capex.epc1_withdrawal_cost_eur(
        withdrawal_flow_million_sm3_per_day=project.flows.withdrawal_flow_million_sm3_per_day,
        material_cost_factor_withdrawal=DEFAULT_ASSUMPTIONS.material_cost_factor_withdrawal
    )

    surface_epc1_fixed = surface_capex.epc1_fixed_cost_eur()

    components.append(
        CostComponent(
            name="surface_epc1_injection",
            value_eur=surface_epc1_injection,
            cost_type=CostType.CAPEX,
            hystories_group=HyStoriesGroup.SURFACE,
            cost_driver=CostDriver.INJECTION,
            driver_value=project.flows.injection_flow_kw_h2_lhv,
            notes="HyStories EPC1 compression component mapped to injection capacity.",
        )
    )

    components.append(
        CostComponent(
            name="surface_epc1_withdrawal",
            value_eur=surface_epc1_withdrawal,
            cost_type=CostType.CAPEX,
            hystories_group=HyStoriesGroup.SURFACE,
            cost_driver=CostDriver.WITHDRAWAL,
            driver_value=project.flows.withdrawal_flow_kw_h2_lhv,
            notes="HyStories EPC1 withdrawal component mapped to withdrawal capacity",
        )
    )

    components.extend(
        fixed_component_cost_allocation(
            name="surface_epc1_fixed",
            value_eur=surface_epc1_fixed,
            cost_type=CostType.CAPEX,
            hystories_group=HyStoriesGroup.SURFACE,
            cost_drivers_and_values=(
                (CostDriver.WITHDRAWAL,project.flows.withdrawal_flow_kw_h2_lhv),
                (CostDriver.INJECTION,project.flows.injection_flow_kw_h2_lhv),
            ),
            allocation_method=AllocationMethod.EQUAL_SPLIT
        )
    )

    # ---------------------------------------------------------------------------------------------------------------
    #
    #                                                   Surface EPC2
    #
    # ---------------------------------------------------------------------------------------------------------------

    surface_epc2_fieldlines = surface_capex.epc2_fieldlines_cost_eur(
        withdrawal_flow_million_sm3_per_day=project.flows.withdrawal_flow_million_sm3_per_day,
        operating_pressure_ratio=project.pressures.operating_pressure_ratio,
        material_cost_factor_withdrawal=DEFAULT_ASSUMPTIONS.material_cost_factor_withdrawal,
        number_well_heads=project.wells.number_well_heads
    )

    surface_epc2_instrumentation = surface_capex.epc2_instrumentation_cost_eur(
        material_cost_factor_withdrawal=DEFAULT_ASSUMPTIONS.material_cost_factor_withdrawal,
        number_well_heads=project.wells.number_well_heads
    )

    components.append(
        CostComponent(
            name="surface_epc2_fieldlines",
            value_eur=surface_epc2_fieldlines,
            cost_type=CostType.CAPEX,
            hystories_group=HyStoriesGroup.SURFACE,
            cost_driver=CostDriver.WITHDRAWAL,
            driver_value=project.flows.withdrawal_flow_kw_h2_lhv,
            notes="HyStories EPC2 fieldlines component mapped to withdrawal capacity",
        )
    )

    components.append(
        CostComponent(
            name="surface_epc2_instrumentation",
            value_eur=surface_epc2_instrumentation,
            cost_type=CostType.CAPEX,
            hystories_group=HyStoriesGroup.SURFACE,
            cost_driver=CostDriver.WITHDRAWAL,
            driver_value=project.flows.withdrawal_flow_kw_h2_lhv,
            notes="HyStories EPC2 instrumentation component mapped to withdrawal capacity",
        )
    )

    # ---------------------------------------------------------------------------------------------------------------
    #
    #                                                   Surface EPC3
    #
    # ---------------------------------------------------------------------------------------------------------------

    surface_epc3_well_interconnection = surface_capex.epc3_well_interconnection_cost_eur(
        withdrawal_flow_million_sm3_per_day=project.flows.withdrawal_flow_million_sm3_per_day,
        operating_pressure_ratio=project.pressures.operating_pressure_ratio,
        material_cost_factor_withdrawal=DEFAULT_ASSUMPTIONS.material_cost_factor_withdrawal,
        filled_lines_length_km=project.field_interconnection.field_line_length_km
    )

    components.append(
        CostComponent(
            name="surface_epc3_well_interconnection",
            value_eur=surface_epc3_well_interconnection,
            cost_type=CostType.CAPEX,
            hystories_group=HyStoriesGroup.SURFACE,
            cost_driver=CostDriver.WITHDRAWAL,
            driver_value=project.flows.withdrawal_flow_kw_h2_lhv,
            notes="HyStories EPC3 well interconnection component mapped to withdrawal capacity",
        )
    )

    # ---------------------------------------------------------------------------------------------------------------
    #
    #                                                   Surface EPC4
    #
    # ---------------------------------------------------------------------------------------------------------------

    surface_epc4_purification = surface_capex.epc4_purification_cost_eur(
        withdrawal_flow_million_sm3_per_day=project.flows.withdrawal_flow_million_sm3_per_day,
        purification_factor=project.purification.purification_factor
    )

    components.append(
        CostComponent(
            name="surface_epc4_purification",
            value_eur=surface_epc4_purification,
            cost_type=CostType.CAPEX,
            hystories_group=HyStoriesGroup.SURFACE,
            cost_driver=CostDriver.WITHDRAWAL,
            driver_value=project.flows.withdrawal_flow_kw_h2_lhv,
            notes="HyStories EPC4 purification component mapped to withdrawal capacity",
        )
    )

    # ---------------------------------------------------------------------------------------------------------------
    #
    #                                            Surface Balance of Plant
    #
    # ---------------------------------------------------------------------------------------------------------------

    surface_epc5_fixed = surface_capex.epc5_fixed_cost_eur()

    surface_epc5_withdrawal = surface_capex.epc5_proportional_cost_eur(
        cost = (
            surface_epc1_withdrawal
            +surface_epc2_fieldlines
            +surface_epc2_instrumentation
            +surface_epc3_well_interconnection
            +surface_epc4_purification
            ),
            factor_bop=DEFAULT_ASSUMPTIONS.bop_fraction
    )

    surface_epc5_injection = surface_capex.epc5_proportional_cost_eur(
        cost = (surface_epc1_injection),
        factor_bop=DEFAULT_ASSUMPTIONS.bop_fraction
    )

    surface_epc5_fixed_wells = surface_capex.epc5_proportional_cost_eur(
        cost = surface_epc1_fixed,
        factor_bop=DEFAULT_ASSUMPTIONS.bop_fraction
    )

    components.append(
        CostComponent(
            name="surface_epc5_withdrawal",
            value_eur=surface_epc5_withdrawal,
            cost_type=CostType.CAPEX,
            hystories_group=HyStoriesGroup.SURFACE,
            cost_driver=CostDriver.WITHDRAWAL,
            driver_value=project.flows.withdrawal_flow_kw_h2_lhv,
            notes="HyStories EPC5 BOP mapped to withdrawal capacity",
        )
    )

    components.append(
        CostComponent(
            name="surface_epc5_injection",
            value_eur=surface_epc5_injection,
            cost_type=CostType.CAPEX,
            hystories_group=HyStoriesGroup.SURFACE,
            cost_driver=CostDriver.INJECTION,
            driver_value=project.flows.injection_flow_kw_h2_lhv,
            notes="HyStories EPC5 BOP mapped to injection capacity",
        )
    )

    components.extend(
        fixed_component_cost_allocation(
            name="surface_epc5_fixed_component_of_well_costs",
            value_eur=surface_epc5_fixed_wells,
            cost_type=CostType.CAPEX,
            hystories_group=HyStoriesGroup.SURFACE,
            cost_drivers_and_values=(
                (CostDriver.WITHDRAWAL,project.flows.withdrawal_flow_kw_h2_lhv),
                (CostDriver.INJECTION,project.flows.injection_flow_kw_h2_lhv),
            ),
            allocation_method=AllocationMethod.EQUAL_SPLIT
        )
    )

    components.extend(
        fixed_component_cost_allocation(
            name="surface_epc5_fixed_bop_component",
            value_eur=surface_epc5_fixed,
            cost_type=CostType.CAPEX,
            hystories_group=HyStoriesGroup.SURFACE,
            cost_drivers_and_values=(
                (CostDriver.WITHDRAWAL,project.flows.withdrawal_flow_kw_h2_lhv),
                (CostDriver.INJECTION,project.flows.injection_flow_kw_h2_lhv),
            ),
            allocation_method=AllocationMethod.EQUAL_SPLIT
        )
    )

    # ---------------------------------------------------------------------------------------------------------------
    #
    #                                                   Subsurface EPC1
    #
    # ---------------------------------------------------------------------------------------------------------------

    subsurface_epc1_leaching_fixed = subsurface_capex.epc1_salt_leaching_facilities_fixed_cost_eur()

    subsurface_epc1_leaching_fixed = subsurface_capex.epc1_salt_leaching_facilities_pipeline_cost_eur(
        brine_disposal_pipeline_length_km=project.salt_leaching.brine_disposal_pipeline_length_km )


    return CostBreakdown(components=tuple(components))


