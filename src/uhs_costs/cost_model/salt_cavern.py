
from uhs_costs.cost_model.helpers import abex, subsurface_capex, subsurface_opex#, surface_capex, surface_opex
from uhs_costs.design.helpers.project import StorageProject
from uhs_costs.cost_model.default_cost_assumptions import construct_hystories_cost_assumptions
from uhs_costs.cost_model.helpers.cost_components import (
    CostBreakdown,
    CostComponent,
    CostType,
    HyStoriesGroup,
    CostDriver,
    # AllocationMethod,
    CostUnit,
    # fixed_component_cost_allocation
)
from uhs_costs.cost_model.surface_facilities import calculate_surface_cost_components


def calculate_salt_cavern_cost_components(
    project: StorageProject,
    overrides: dict[str, object] | None = None
) -> CostBreakdown:
    """Calculate decomposed HyStories-derived salt cavern cost components."""

    # -------------- index of objects within project --------------
    # project.compression
    # project.pressures
    # project.flows
    # project.inventory
    # project.wells
    # project.drilling
    # project.field_interconnection
    # project.salt_leaching
    # project.salt_leaching_process
    # project.salt_conversion_process
    # project.purification
    

    #generate default cost assumptions object
    assumptions = construct_hystories_cost_assumptions(
        overrides=overrides
    )


    components: list[CostComponent] = []

    # ---------------------------------------------------------------------------------------------------------------
    #
    #                                                   Surface EPC Components
    #
    # ---------------------------------------------------------------------------------------------------------------

    components = calculate_surface_cost_components(
        project=project,
        assumptions=assumptions,
        components = components
    )
 
    # ---------------------------------------------------------------------------------------------------------------
    #
    #                                                   Subsurface EPC1
    #
    # ---------------------------------------------------------------------------------------------------------------

    subsurface_epc1_leaching_fixed = subsurface_capex.epc1_salt_leaching_facilities_fixed_cost_eur()

    subsurface_epc1_leaching_pipeline = subsurface_capex.epc1_salt_leaching_facilities_pipeline_cost_eur(
        fresh_water_pipeline_length_km=project.salt_leaching.fresh_water_pipeline_length_km,
        brine_disposal_pipeline_length_km=project.salt_leaching.brine_disposal_pipeline_length_km 
    )
    
    subsurface_epc1_leaching_wells = subsurface_capex.epc1_salt_leaching_facilities_wellhead_cost_eur(
        number_well_heads=project.wells.number_well_heads
    )

    # all components scale with storage therefore combined together here.
    # Fixed components are 'fixed' wrt to a storage site, therefore as the CEM invests
    # in more storage via new sites, there is the expectation that this does also scales with capacity
    # it is expected that this assumptions becomes more valid for larger investments 
    subsurface_epc1_total = (
                subsurface_epc1_leaching_fixed
                +subsurface_epc1_leaching_pipeline
                +subsurface_epc1_leaching_wells
            )

    components.append(
        CostComponent(
            name="subsurface_epc1",
            value_eur=subsurface_epc1_total,
            cost_type=CostType.CAPEX,
            hystories_group=HyStoriesGroup.SUBSURFACE,
            cost_driver=CostDriver.STORAGE,
            driver_value=project.inventory.recoverable_working_gas_capacity_kwh_lhv,
            cost_unit=CostUnit.EUR_PER_KWH,
            notes="HyStories EPC1 leaching facilities costs mapped to storage capacity",
        )
    )

    # ---------------------------------------------------------------------------------------------------------------
    #
    #                                                   Subsurface EPC2
    #
    # ---------------------------------------------------------------------------------------------------------------

    subsurface_epc2_salt_leaching = subsurface_capex.epc2_salt_leaching_cost_eur(
        number_caverns=project.wells.number_caverns,
        leaching_duration_per_cavern_months=(
            project.salt_leaching_process.leaching_duration_per_cavern_months
        ),
        total_leaching_duration_years=(
            project.salt_leaching_process.total_leaching_duration_years
        ),
        cost_of_electricity_eur_per_mwh=assumptions.cost_of_electricity_eur_per_mwh,
    )

    components.append(
        CostComponent(
            name="subsurface_epc2_salt_leaching",
            value_eur=subsurface_epc2_salt_leaching,
            cost_type=CostType.CAPEX,
            hystories_group=HyStoriesGroup.SUBSURFACE,
            cost_driver=CostDriver.STORAGE,
            driver_value=project.inventory.recoverable_working_gas_capacity_kwh_lhv,
            cost_unit=CostUnit.EUR_PER_KWH,
            notes="HyStories EPC2 leaching costs mapped to storage capacity",
        )
    )

    # ---------------------------------------------------------------------------------------------------------------
    #
    #                                                   Subsurface EPC3
    #
    # ---------------------------------------------------------------------------------------------------------------

    subsurface_epc3_salt_conversion_fixed = subsurface_capex.epc3_salt_conversion_fixed_cost_eur()
    subsurface_epc3_salt_conversion_cavern_scaled = subsurface_capex.epc3_salt_conversion_cavern_scaled_cost_eur(
        number_well_heads=project.wells.number_caverns,
        free_gas_volume_per_cavern_thousand_m3=project.salt_leaching.free_gas_volume_per_cavern_thousand_m3,
        cost_of_electricity_eur_per_mwh=assumptions.cost_of_electricity_eur_per_mwh
    )
    subsurface_epc3_salt_conversion_time_scaled = subsurface_capex.epc3_salt_conversion_time_scaled_cost_eur(
        total_conversion_duration_years=project.salt_conversion_process.total_conversion_duration_years
    )

    subsurface_epc3_total = (
        subsurface_epc3_salt_conversion_fixed
        +subsurface_epc3_salt_conversion_cavern_scaled
        +subsurface_epc3_salt_conversion_time_scaled
    )

    components.append(
        CostComponent(
            name="subsurface_epc3_total",
            value_eur=subsurface_epc3_total,
            cost_type=CostType.CAPEX,
            hystories_group=HyStoriesGroup.SUBSURFACE,
            cost_driver=CostDriver.STORAGE,
            driver_value=project.inventory.recoverable_working_gas_capacity_kwh_lhv,
            cost_unit=CostUnit.EUR_PER_KWH,
            notes="HyStories EPC3 cavern conversion costs mapped to storage capacity",
        )
    )

    # ---------------------------------------------------------------------------------------------------------------
    #
    #                                                   Subsurface EPC4
    #
    # ---------------------------------------------------------------------------------------------------------------

    subsurface_epc4_drilling = subsurface_capex.epc4_salt_development_drilling_and_leaching_completion_cost_eur(
        number_well_heads=project.wells.number_well_heads,
        last_cemented_casing_shoe_m=project.drilling.last_cemented_casing_shoe_m,
        material_cost_factor_withdrawal=assumptions.material_cost_factor_withdrawal,
        drilling_complexity_index=project.drilling.drilling_complexity_index
    )

    components.append(
        CostComponent(
            name="subsurface_epc4_drilling",
            value_eur=subsurface_epc4_drilling,
            cost_type=CostType.CAPEX,
            hystories_group=HyStoriesGroup.SUBSURFACE,
            cost_driver=CostDriver.STORAGE,
            driver_value=project.inventory.recoverable_working_gas_capacity_kwh_lhv,
            cost_unit=CostUnit.EUR_PER_KWH,
            notes="HyStories EPC4 cavern completion (drilling) costs mapped to storage capacity",
        )
    )

    # ---------------------------------------------------------------------------------------------------------------
    #
    #                                                   Subsurface CG
    #
    # ---------------------------------------------------------------------------------------------------------------

    #given the inventory model calculates cushion gas, we simplify the hystories equation to simply mass*cost_per_mass
    subsurface_cushion_gas = subsurface_capex.cushion_gas_cost_eur_simple(
        cushion_gas_mass_kg=project.inventory.cushion_gas_h2_mass_kg,
        hydrogen_cost_eur_per_kg=assumptions.hydrogen_cost_eur_per_kg
    )


    components.append(
        CostComponent(
            name="subsurface_cushion_gas",
            value_eur=subsurface_cushion_gas,
            cost_type=CostType.CAPEX,
            hystories_group=HyStoriesGroup.SUBSURFACE,
            cost_driver=CostDriver.STORAGE,
            driver_value=project.inventory.recoverable_working_gas_capacity_kwh_lhv,
            cost_unit=CostUnit.EUR_PER_KWH,
            notes="HyStories cushion gas costs mapped to storage capacity",
        )
    )

    # ---------------------------------------------------------------------------------------------------------------
    #
    #                                                   Subsurface Contingency
    #
    # ---------------------------------------------------------------------------------------------------------------

    
    subsurface_contingency = subsurface_capex.contingency_cost_eur(
        base_cost_eur=sum(
            component.value_eur
            for component in components
            if (
                component.hystories_group == HyStoriesGroup.SUBSURFACE
                and component.cost_type == CostType.CAPEX
                and component.cost_driver == CostDriver.STORAGE
            )
        ),
        contingency_fraction=assumptions.subsurface_contingency_fraction
    )

    components.append(
        CostComponent(
            name="subsurface_contingency",
            value_eur=subsurface_contingency,
            cost_type=CostType.CAPEX,
            hystories_group=HyStoriesGroup.SUBSURFACE,
            cost_driver=CostDriver.STORAGE,
            driver_value=project.inventory.recoverable_working_gas_capacity_kwh_lhv,
            cost_unit=CostUnit.EUR_PER_KWH,
            notes="HyStories subsurface_contingencies mapped to storage capacity",
        )
    )

    # ---------------------------------------------------------------------------------------------------------------
    #
    #                                                   Subsurface ABEX
    #
    # ---------------------------------------------------------------------------------------------------------------

    subsurface_abex_base_eur = sum(
            component.value_eur
            for component in components
            if (
                component.hystories_group == HyStoriesGroup.SUBSURFACE
                and component.cost_type == CostType.CAPEX
                and component.cost_driver == CostDriver.STORAGE
                and component.name != "subsurface_cushion_gas" #exclude cushion gas from abex estimates
            )
        )
    
    subsurface_abex = abex.abex_cost_eur(
        epc_cost_eur=subsurface_abex_base_eur,
        abex_fraction=assumptions.subsurface_abex_fraction
    )

    components.append(
        CostComponent(
            name="subsurface_abex",
            value_eur=subsurface_abex,
            cost_type=CostType.ABEX,
            hystories_group=HyStoriesGroup.SUBSURFACE,
            cost_driver=CostDriver.STORAGE,
            driver_value=project.inventory.recoverable_working_gas_capacity_kwh_lhv,
            cost_unit=CostUnit.EUR_PER_KWH,
            notes="HyStories subsurface ABEX (which excludes cushion gas) mapped to storage capacity",
        )
    )

    # ---------------------------------------------------------------------------------------------------------------
    #
    #                                                   Subsurface OPEX
    #
    # ---------------------------------------------------------------------------------------------------------------

    # ---------------------- Fixed opex ----------------------

    subsurface_base_capex = sum(
            component.value_eur
            for component in components
            if (
                component.hystories_group == HyStoriesGroup.SUBSURFACE
                and component.cost_type == CostType.CAPEX
                and component.cost_driver == CostDriver.STORAGE
                and component.name == "subsurface_epc4_drilling"
            )
        )

    subsurface_fixed_opex = subsurface_opex.fixed_opex_fraction_of_epc_cost_eur_per_year(
        subsurface_epc_cost_eur=subsurface_base_capex,
        fixed_opex_fraction_of_epc=assumptions.subsurface_fixed_opex_fraction_of_wells_capex
    )

    components.append(
        CostComponent(
            name="subsurface_fixed_opex",
            value_eur=subsurface_fixed_opex,
            cost_type=CostType.FIXED_OPEX,
            hystories_group=HyStoriesGroup.SUBSURFACE,
            cost_driver=CostDriver.STORAGE,
            driver_value=project.inventory.recoverable_working_gas_capacity_kwh_lhv,
            cost_unit=CostUnit.EUR_PER_KWH_YEAR,
            notes="HyStories subsurface fixed opex of wells mapped to storage capacity, euro/kWh/year",
        )
    )



    return CostBreakdown(components=tuple(components))



    

