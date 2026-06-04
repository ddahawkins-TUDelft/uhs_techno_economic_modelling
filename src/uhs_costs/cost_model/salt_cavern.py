
from uhs_costs.cost_model.helpers import abex, subsurface_capex, subsurface_opex, surface_capex
from uhs_costs.design.helpers.project import StorageProject, StorageTechnology
from uhs_costs.cost_model.default_cost_assumptions import construct_hystories_cost_assumptions
from uhs_costs.cost_model.helpers import surface_opex
from uhs_costs.cost_model.helpers.cost_components import (
    CostBreakdown,
    CostComponent,
    CostType,
    HyStoriesGroup,
    CostDriver,
    AllocationMethod,
    CostUnit,
    fixed_component_cost_allocation
)



def calculate_salt_cavern_cost_components(
    project: StorageProject,
    overrides: dict[str, object] | None = None
) -> CostBreakdown:
    """Calculate decomposed HyStories-derived salt cavern CAPEX components."""

    # -------------- index of objects within project --------------
    # project.compression
    # project.pressures
    # project.flows
    # project.inventory
    # project.wells
    # project.drilling
    # project.field_interconnection
    # project.salt_leaching
    # project.purification
    

    #generate default cost assumptions object
    assumptions = construct_hystories_cost_assumptions(
        storage_technology = StorageTechnology.SALT_CAVERN,
        overrides=overrides
    )


    components: list[CostComponent] = []
 
    # ---------------------------------------------------------------------------------------------------------------
    #
    #                                                   Surface EPC1
    #
    # ---------------------------------------------------------------------------------------------------------------

    surface_epc1_injection = surface_capex.epc1_compression_cost_eur(
        total_installed_compression_brake_power_mw=( project.compression.total_design_brake_power_kw / 1000 ),
        material_cost_factor_injection=assumptions.material_cost_factor_injection,
    )

    surface_epc1_withdrawal = surface_capex.epc1_withdrawal_cost_eur(
        withdrawal_flow_million_sm3_per_day=project.flows.withdrawal_flow_million_sm3_per_day,
        material_cost_factor_withdrawal=assumptions.material_cost_factor_withdrawal
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
            cost_unit=CostUnit.EUR_PER_KW,
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
            cost_unit=CostUnit.EUR_PER_KW,
            notes="HyStories EPC1 withdrawal component mapped to withdrawal capacity",
        )
    )

    components.extend(
        fixed_component_cost_allocation(
            name="surface_epc1_fixed",
            value_eur=surface_epc1_fixed,
            cost_type=CostType.CAPEX,
            hystories_group=HyStoriesGroup.SURFACE,
            cost_unit=CostUnit.EUR_PER_KW,
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
        material_cost_factor_withdrawal=assumptions.material_cost_factor_withdrawal,
        number_well_heads=project.wells.number_well_heads
    )

    surface_epc2_instrumentation = surface_capex.epc2_instrumentation_cost_eur(
        material_cost_factor_withdrawal=assumptions.material_cost_factor_withdrawal,
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
            cost_unit=CostUnit.EUR_PER_KW,
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
            cost_unit=CostUnit.EUR_PER_KW,
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
        material_cost_factor_withdrawal=assumptions.material_cost_factor_withdrawal,
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
            cost_unit=CostUnit.EUR_PER_KW,
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
            cost_unit=CostUnit.EUR_PER_KW,
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
        cost = sum(
            component.value_eur
            for component in components
            if (
                component.hystories_group == HyStoriesGroup.SURFACE
                and component.cost_type == CostType.CAPEX
                and component.cost_driver == CostDriver.WITHDRAWAL
            )
            ),
            factor_bop=assumptions.bop_fraction
    )

    surface_epc5_injection = surface_capex.epc5_proportional_cost_eur(
        cost = sum(
            component.value_eur
            for component in components
            if (
                component.hystories_group == HyStoriesGroup.SURFACE
                and component.cost_type == CostType.CAPEX
                and component.cost_driver == CostDriver.INJECTION
            )
            ),
        factor_bop=assumptions.bop_fraction
    )

    #fixed components (wells) are allowed for via the above sum loop

    components.append(
        CostComponent(
            name="surface_epc5_withdrawal",
            value_eur=surface_epc5_withdrawal,
            cost_type=CostType.CAPEX,
            hystories_group=HyStoriesGroup.SURFACE,
            cost_driver=CostDriver.WITHDRAWAL,
            driver_value=project.flows.withdrawal_flow_kw_h2_lhv,
            cost_unit=CostUnit.EUR_PER_KW,
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
            cost_unit=CostUnit.EUR_PER_KW,
            notes="HyStories EPC5 BOP mapped to injection capacity",
        )
    )

    components.extend(
        fixed_component_cost_allocation(
            name="surface_epc5_fixed_bop_component",
            value_eur=surface_epc5_fixed,
            cost_type=CostType.CAPEX,
            hystories_group=HyStoriesGroup.SURFACE,
            cost_unit=CostUnit.EUR_PER_KW,
            cost_drivers_and_values=(
                (CostDriver.WITHDRAWAL,project.flows.withdrawal_flow_kw_h2_lhv),
                (CostDriver.INJECTION,project.flows.injection_flow_kw_h2_lhv),
            ),
            allocation_method=AllocationMethod.EQUAL_SPLIT
        )
    )

    # ---------------------------------------------------------------------------------------------------------------
    #
    #                                                   Surface Contingency
    #
    # ---------------------------------------------------------------------------------------------------------------


    surface_withdrawal_base_eur = sum(
            component.value_eur
            for component in components
            if (
                component.hystories_group == HyStoriesGroup.SURFACE
                and component.cost_type == CostType.CAPEX
                and component.cost_driver == CostDriver.WITHDRAWAL
            )
        )
    surface_injection_base_eur = sum(
            component.value_eur
            for component in components
            if (
                component.hystories_group == HyStoriesGroup.SURFACE
                and component.cost_type == CostType.CAPEX
                and component.cost_driver == CostDriver.INJECTION
            )
        )

    surface_contingency_withdrawal = surface_capex.contingency_cost_eur(
        base_cost_eur=surface_withdrawal_base_eur,
        contingency_fraction=assumptions.surface_contingency_fraction
    )

    components.append(
        CostComponent(
            name="surface_contingency_withdrawal",
            value_eur=surface_contingency_withdrawal,
            cost_type=CostType.CAPEX,
            hystories_group=HyStoriesGroup.SURFACE,
            cost_driver=CostDriver.WITHDRAWAL,
            driver_value=project.flows.withdrawal_flow_kw_h2_lhv,
            cost_unit=CostUnit.EUR_PER_KW,
            notes="HyStories Withdrawal component of surface Contingencies mapped to withdrawal capacity",
        )
    )

    surface_contingency_injection = surface_capex.contingency_cost_eur(
        base_cost_eur=surface_injection_base_eur,
        contingency_fraction=assumptions.surface_contingency_fraction
    )

    components.append(
        CostComponent(
            name="surface_contingency_injection",
            value_eur=surface_contingency_injection,
            cost_type=CostType.CAPEX,
            hystories_group=HyStoriesGroup.SURFACE,
            cost_driver=CostDriver.INJECTION,
            driver_value=project.flows.injection_flow_kw_h2_lhv,
            cost_unit=CostUnit.EUR_PER_KW,
            notes="HyStories injection component of surface Contingencies mapped to injection capacity",
        )
    )

    # ---------------------------------------------------------------------------------------------------------------
    #
    #                                                   Surface ABEX
    #
    # ---------------------------------------------------------------------------------------------------------------

    surface_abex_withdrawal_base_eur = sum(
            component.value_eur
            for component in components
            if (
                component.hystories_group == HyStoriesGroup.SURFACE
                and component.cost_type == CostType.CAPEX
                and component.cost_driver == CostDriver.WITHDRAWAL
            )
        )
    surface_abex_injection_base_eur = sum(
            component.value_eur
            for component in components
            if (
                component.hystories_group == HyStoriesGroup.SURFACE
                and component.cost_type == CostType.CAPEX
                and component.cost_driver == CostDriver.INJECTION
            )
        )
    
    surface_abex_withdrawal = abex.abex_cost_eur(
        epc_cost_eur=surface_abex_withdrawal_base_eur,
        abex_fraction=assumptions.surface_abex_fraction
    )

    components.append(
        CostComponent(
            name="surface_abex_withdrawal",
            value_eur=surface_abex_withdrawal,
            cost_type=CostType.ABEX,
            hystories_group=HyStoriesGroup.SURFACE,
            cost_driver=CostDriver.WITHDRAWAL,
            driver_value=project.flows.withdrawal_flow_kw_h2_lhv,
            cost_unit=CostUnit.EUR_PER_KW,
            notes="HyStories Withdrawal component of surface ABEX mapped to withdrawal capacity",
        )
    )

    surface_abex_injection = abex.abex_cost_eur(
        epc_cost_eur=surface_abex_injection_base_eur,
        abex_fraction=assumptions.surface_abex_fraction
    )

    components.append(
        CostComponent(
            name="surface_abex_injection",
            value_eur=surface_abex_injection,
            cost_type=CostType.ABEX,
            hystories_group=HyStoriesGroup.SURFACE,
            cost_driver=CostDriver.INJECTION,
            driver_value=project.flows.injection_flow_kw_h2_lhv,
            cost_unit=CostUnit.EUR_PER_KW,
            notes="HyStories injection component of surface ABEX mapped to injection capacity",
        )
    )

    # ---------------------------------------------------------------------------------------------------------------
    #
    #                                                   Surface OPEX
    #
    # ---------------------------------------------------------------------------------------------------------------

    # ---------------------- Fixed opex ----------------------

    surface_fixed_opex_employees_fixed = surface_opex.fixed_opex_base_cost_eur_per_year(
        fixed_cost_k_eur=assumptions.surface_fixed_component_of_fixed_opex
    )

    components.extend(
        fixed_component_cost_allocation(
            name="surface_fixed_opex_employees_fixed",
            value_eur=surface_fixed_opex_employees_fixed,
            cost_type=CostType.FIXED_OPEX,
            hystories_group=HyStoriesGroup.SURFACE,
            cost_unit=CostUnit.EUR_PER_KW_YEAR,
            cost_drivers_and_values=(
                (CostDriver.WITHDRAWAL,project.flows.withdrawal_flow_kw_h2_lhv),
                (CostDriver.INJECTION,project.flows.injection_flow_kw_h2_lhv),
            ),
            allocation_method=AllocationMethod.EQUAL_SPLIT
        )
    )

    surface_base_capex_injection = sum(
            component.value_eur
            for component in components
            if (
                component.hystories_group == HyStoriesGroup.SURFACE
                and component.cost_type == CostType.CAPEX
                and component.cost_driver == CostDriver.INJECTION
                and component.name != "surface_contingency_injection"
            )
        )
    
    surface_base_capex_withdrawal = sum(
            component.value_eur
            for component in components
            if (
                component.hystories_group == HyStoriesGroup.SURFACE
                and component.cost_type == CostType.CAPEX
                and component.cost_driver == CostDriver.WITHDRAWAL
                and component.name != "surface_contingency_withdrawal"
            )
        )

    surface_fixed_opex_fraction_of_capex_injection = surface_opex.fixed_opex_fraction_of_epc_cost_eur_per_year(
        surface_epc_cost_eur=surface_base_capex_injection,
        fixed_opex_fraction_of_epc=assumptions.surface_fixed_opex_fraction_of_epc
    )

    components.append(
        CostComponent(
            name="surface_fixed_opex_fraction_of_capex_injection",
            value_eur=surface_fixed_opex_fraction_of_capex_injection,
            cost_type=CostType.FIXED_OPEX,
            hystories_group=HyStoriesGroup.SURFACE,
            cost_driver=CostDriver.INJECTION,
            driver_value=project.flows.injection_flow_kw_h2_lhv,
            cost_unit=CostUnit.EUR_PER_KW_YEAR,
            notes="HyStories injection component of surface fixed opex mapped to injection capacity, euro/year/kW_injection",
        )
    )

    surface_fixed_opex_fraction_of_capex_withdrawal = surface_opex.fixed_opex_fraction_of_epc_cost_eur_per_year(
        surface_epc_cost_eur=surface_base_capex_withdrawal,
        fixed_opex_fraction_of_epc=assumptions.surface_fixed_opex_fraction_of_epc
    )

    components.append(
        CostComponent(
            name="surface_fixed_opex_fraction_of_capex_withdrawal",
            value_eur=surface_fixed_opex_fraction_of_capex_withdrawal,
            cost_type=CostType.FIXED_OPEX,
            hystories_group=HyStoriesGroup.SURFACE,
            cost_driver=CostDriver.WITHDRAWAL,
            driver_value=project.flows.withdrawal_flow_kw_h2_lhv,
            cost_unit=CostUnit.EUR_PER_KW_YEAR,
            notes="HyStories withdrawal component of surface fixed opex mapped to withdrawal capacity, euro/year/kW_withdrawal",
        )
    )

    # ---------------------- Variable opex ----------------------

    surface_variable_opex_injection = surface_opex.variable_opex_rate_injection_eur_per_kwh_h2_lhv(
        cost_of_electricity_eur_per_mwh=assumptions.cost_of_electricity_eur_per_mwh,
        compression_ratio=project.compression.overall_pressure_ratio
    )

    components.append(
        CostComponent(
            name="surface_variable_opex_injection",
            value_eur=surface_variable_opex_injection,
            cost_type=CostType.VARIABLE_OPEX,
            hystories_group=HyStoriesGroup.SURFACE,
            cost_driver=CostDriver.INJECTION_THROUGHPUT_KWH,
            driver_value=1,
            cost_unit=CostUnit.EUR_PER_KWH,
            notes="HyStories injection component of surface variable opex mapped to injection throughput, euro/kWh_injection",
        )
    )

    surface_variable_opex_withdrawal = surface_opex.variable_opex_rate_withdrawal_eur_per_kwh_h2_lhv(
        cost_of_electricity_eur_per_mwh=assumptions.cost_of_electricity_eur_per_mwh,
        purification_coefficient=project.purification.purification_factor
    )

    components.append(
        CostComponent(
            name="surface_variable_opex_withdrawal",
            value_eur=surface_variable_opex_withdrawal,
            cost_type=CostType.VARIABLE_OPEX,
            hystories_group=HyStoriesGroup.SURFACE,
            cost_driver=CostDriver.WITHDRAWAL_THROUGHPUT_KWH,
            driver_value=1,
            cost_unit=CostUnit.EUR_PER_KWH,
            notes="HyStories withdrawal component of surface variable opex mapped to withdrawal capacity, euro/kWh_withdrawal",
        )
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
            driver_value=project.inventory.working_gas_capacity_kwh_lhv,
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
            driver_value=project.inventory.working_gas_capacity_kwh_lhv,
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
            driver_value=project.inventory.working_gas_capacity_kwh_lhv,
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
            driver_value=project.inventory.working_gas_capacity_kwh_lhv,
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
            driver_value=project.inventory.working_gas_capacity_kwh_lhv,
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
            driver_value=project.inventory.working_gas_capacity_kwh_lhv,
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
            driver_value=project.inventory.working_gas_capacity_kwh_lhv,
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
            driver_value=project.inventory.working_gas_capacity_kwh_lhv,
            cost_unit=CostUnit.EUR_PER_KWH_YEAR,
            notes="HyStories subsurface fixed opex of wells mapped to storage capacity, euro/kWh/year",
        )
    )



    return CostBreakdown(components=tuple(components))



    

