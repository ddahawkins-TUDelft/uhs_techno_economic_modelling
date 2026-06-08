
from uhs_costs.cost_model.helpers import abex, subsurface_capex, subsurface_opex
from uhs_costs.design.helpers.project import StorageProject
from uhs_costs.cost_model.default_cost_assumptions import construct_hystories_cost_assumptions
from uhs_costs.cost_model.helpers.cost_components import (
    CostBreakdown,
    CostComponent,
    CostType,
    HyStoriesGroup,
    CostDriver,
    CostUnit,
)
from uhs_costs.cost_model.surface_facilities import calculate_surface_cost_components



def calculate_depleted_gas_field_cost_components(
    project: StorageProject,
    overrides: dict[str, object] | None = None
) -> CostBreakdown:
    """Calculate decomposed HyStories-derived DGF cost components."""

    # -------------- index of objects within project --------------
    # project.compression
    # project.pressures
    # project.flows
    # project.inventory
    # project.wells
    # project.drilling
    # project.field_interconnection
    # project.purification
    # project.porous_first_fill_process

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
    #                                                   Subsurface EPC3
    #
    # --------------------------------------------------------------------------------------------------------------

    subsurface_epc3_first_fill = subsurface_capex.epc3_porous_first_gas_fill_cost_eur(
        first_gas_fill_duration_years=project.porous_first_fill_process.first_gas_fill_duration_years,
        cost_of_electricity_eur_per_mwh=assumptions.cost_of_electricity_eur_per_mwh
    )

    print(project.porous_first_fill_process.first_gas_fill_duration_years)

    components.append(
        CostComponent(
            name="subsurface_epc3_first_fill",
            value_eur=subsurface_epc3_first_fill,
            cost_type=CostType.CAPEX,
            hystories_group=HyStoriesGroup.SUBSURFACE,
            cost_driver=CostDriver.STORAGE,
            driver_value=project.inventory.working_gas_capacity_kwh_lhv,
            cost_unit=CostUnit.EUR_PER_KWH,
            notes="HyStories EPC3 first fill operational costs as investment capex mapped to storage capacity",
        )
    )

    # ---------------------------------------------------------------------------------------------------------------
    #
    #                                                   Subsurface EPC4
    #
    # --------------------------------------------------------------------------------------------------------------

    subsurface_epc4_obs_well_drilling = subsurface_capex.epc4_porous_observation_well_drilling_cost_eur(
        number_observation_wells=project.wells.number_observation_wells,
        last_cemented_casing_shoe_m=project.drilling.last_cemented_casing_shoe_m,
        material_cost_factor_withdrawal=assumptions.material_cost_factor_withdrawal,
        drilling_complexity_index=project.drilling.drilling_complexity_index
    )

    subsurface_epc4_prod_well_drilling = subsurface_capex.epc4_porous_production_well_drilling_cost_eur(
        number_production_wells=project.wells.number_production_wells,
        last_cemented_casing_shoe_m=project.drilling.last_cemented_casing_shoe_m,
        material_cost_factor_withdrawal=assumptions.material_cost_factor_withdrawal,
        drilling_complexity_index=project.drilling.drilling_complexity_index
    )

    subsurface_ep4_drilling = subsurface_epc4_obs_well_drilling + subsurface_epc4_prod_well_drilling

    components.append(
        CostComponent(
            name="subsurface_ep4_drilling",
            value_eur=subsurface_ep4_drilling,
            cost_type=CostType.CAPEX,
            hystories_group=HyStoriesGroup.SUBSURFACE,
            cost_driver=CostDriver.STORAGE,
            driver_value=project.inventory.working_gas_capacity_kwh_lhv,
            cost_unit=CostUnit.EUR_PER_KWH,
            notes="HyStories EPC4 well drilling costs mapped to storage capacity",
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
                and component.name == "subsurface_ep4_drilling"
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