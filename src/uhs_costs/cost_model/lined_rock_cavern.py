
from __future__ import annotations

from uhs_costs.cost_model.helpers import abex, subsurface_capex, subsurface_opex
from uhs_costs.design.helpers.project import StorageProject
from uhs_costs.cost_model.default_cost_assumptions import (
    construct_hystories_cost_assumptions,
    construct_lined_rock_cavern_cost_assumptions,
)
from uhs_costs.cost_model.helpers.cost_components import (
    CostBreakdown,
    CostComponent,
    CostType,
    HyStoriesGroup,
    CostDriver,
    CostUnit,
)
from uhs_costs.cost_model.surface_facilities import calculate_surface_cost_components


def calculate_lined_rock_cavern_cost_components(
    project: StorageProject,
    overrides: dict[str, object] | None = None,
    lrc_overrides: dict[str, object] | None = None,
) -> CostBreakdown:
    """Calculate decomposed lined rock cavern cost components.

    Parameters
    ----------
    project:
        Fully constructed StorageProject for a lined rock cavern.

    overrides:
        Optional overrides for generic HyStories/economic assumptions.
        These are used for shared surface components, electricity price,
        hydrogen price, contingency, ABEX, and fixed OPEX assumptions.

    lrc_overrides:
        Optional overrides for LRC-specific Huang-derived cost assumptions.

    Returns
    -------
    CostBreakdown
        Tuple-backed collection of cost components.
    """

    # ---------------------------------------------------------------------------------------------------------------
    #
    #                                                   Assumptions
    #
    # ---------------------------------------------------------------------------------------------------------------

    hystories_assumptions = construct_hystories_cost_assumptions(
        overrides=overrides,
    )

    lrc_assumptions = construct_lined_rock_cavern_cost_assumptions(
        overrides=lrc_overrides,
    )

    components: list[CostComponent] = []

    # ---------------------------------------------------------------------------------------------------------------
    #
    #                                                   Required LRC objects
    #
    # ---------------------------------------------------------------------------------------------------------------

    _validate_lined_rock_cavern_project(project)

    geometry = project.lrc_geometry
    lining = project.lrc_lining
    drainage = project.lrc_drainage
    first_fill_process = project.porous_first_fill_process

    # ---------------------------------------------------------------------------------------------------------------
    #
    #                                                   Surface EPC Components
    #
    # ---------------------------------------------------------------------------------------------------------------

    components = calculate_surface_cost_components(
        project=project,
        assumptions=hystories_assumptions,
        components=components,
    )


     # ---------------------------------------------------------------------------------------------------------------
    #
    #                                          Subsurface EPC4-like drilling costs
    #                       These costs replaces Huang's own simplified well-costs estimate and align with HyStories
    #
    # --------------------------------------------------------------------------------------------------------------

    # subsurface_epc4_obs_well_drilling = subsurface_capex.epc4_porous_observation_well_drilling_cost_eur(
    #     number_observation_wells=project.wells.number_observation_wells,
    #     last_cemented_casing_shoe_m=project.drilling.last_cemented_casing_shoe_m,
    #     material_cost_factor_withdrawal=hystories_assumptions.material_cost_factor_withdrawal,
    #     drilling_complexity_index=project.drilling.drilling_complexity_index
    # )

    # subsurface_epc4_prod_well_drilling = subsurface_capex.epc4_porous_production_well_drilling_cost_eur(
    #     number_production_wells=project.wells.number_production_wells,
    #     last_cemented_casing_shoe_m=project.drilling.last_cemented_casing_shoe_m,
    #     material_cost_factor_withdrawal=hystories_assumptions.material_cost_factor_withdrawal,
    #     drilling_complexity_index=project.drilling.drilling_complexity_index
    # )

    # subsurface_ep4_drilling = subsurface_epc4_obs_well_drilling + subsurface_epc4_prod_well_drilling

    # components.append(
    #     CostComponent(
    #         name="subsurface_ep4_drilling",
    #         value_eur=subsurface_ep4_drilling,
    #         cost_type=CostType.CAPEX,
    #         hystories_group=HyStoriesGroup.SUBSURFACE,
    #         cost_driver=CostDriver.STORAGE,
    #         driver_value=project.inventory.working_gas_capacity_kwh_lhv,
    #         cost_unit=CostUnit.EUR_PER_KWH,
    #         notes="HyStories EPC4 well drilling costs mapped to storage capacity",
    #     )
    # )

    subsurface_lrc_wells = subsurface_capex.lrc_well_capex_eur(
    number_well_heads=project.wells.number_well_heads,
    well_depth_m=project.drilling.last_cemented_casing_shoe_m,
    fixed_cost_eur_per_well=(
        lrc_assumptions.lrc_well_fixed_cost_eur_per_well
    ),
    variable_cost_eur_per_m=(
        lrc_assumptions.lrc_well_variable_cost_eur_per_m
    ),
    drilling_complexity_index=project.drilling.drilling_complexity_index,
)

    components.append(
        CostComponent(
            name="subsurface_lrc_wells",
            value_eur=subsurface_lrc_wells,
            cost_type=CostType.CAPEX,
            hystories_group=HyStoriesGroup.SUBSURFACE,
            cost_driver=CostDriver.STORAGE,
            driver_value=project.inventory.working_gas_capacity_kwh_lhv,
            cost_unit=CostUnit.EUR_PER_KWH,
            notes=(
                "LRC well CAPEX based on Huang et al. Fixed and depth-variable "
                "well costs are mapped to storage capacity."
            ),
        )
    )

    

    # ---------------------------------------------------------------------------------------------------------------
    #
    #                                                   Subsurface LRC mining
    #
    # ---------------------------------------------------------------------------------------------------------------

    subsurface_lrc_mining = subsurface_capex.lrc_mining_capex_eur(
        excavation_volume_m3=geometry.required_geometric_storage_volume_m3,
        mining_cost_eur_per_m3=lrc_assumptions.lrc_mining_cost_eur_per_m3,
    )

    components.append(
        CostComponent(
            name="subsurface_lrc_mining",
            value_eur=subsurface_lrc_mining,
            cost_type=CostType.CAPEX,
            hystories_group=HyStoriesGroup.SUBSURFACE,
            cost_driver=CostDriver.STORAGE,
            driver_value=project.inventory.working_gas_capacity_kwh_lhv,
            cost_unit=CostUnit.EUR_PER_KWH,
            notes=(
                "LRC excavation/mining CAPEX. Uses the geometric storage "
                "volume from the design layer, so the effective-volume "
                "correction should not be applied again here."
            ),
        )
    )

    # ---------------------------------------------------------------------------------------------------------------
    #
    #                                                   Subsurface LRC drainage
    #
    # ---------------------------------------------------------------------------------------------------------------

    subsurface_lrc_drainage = subsurface_capex.lrc_drainage_capex_eur(
        tunnel_drainage_length_m=drainage.tunnel_drainage_length_m,
        total_cavern_drainage_length_m=(
            drainage.total_cavern_drainage_length_m
        ),
        tunnel_drainage_cost_eur_per_m=(
            lrc_assumptions.lrc_tunnel_drainage_cost_eur_per_m
        ),
        cavern_drainage_cost_eur_per_m=(
            lrc_assumptions.lrc_cavern_drainage_cost_eur_per_m
        ),
    )

    components.append(
        CostComponent(
            name="subsurface_lrc_drainage",
            value_eur=subsurface_lrc_drainage,
            cost_type=CostType.CAPEX,
            hystories_group=HyStoriesGroup.SUBSURFACE,
            cost_driver=CostDriver.STORAGE,
            driver_value=project.inventory.working_gas_capacity_kwh_lhv,
            cost_unit=CostUnit.EUR_PER_KWH,
            notes=(
                "LRC drainage CAPEX for tunnel drainage and cavern drainage."
            ),
        )
    )

    # ---------------------------------------------------------------------------------------------------------------
    #
    #                                                   Subsurface LRC lining
    #
    # ---------------------------------------------------------------------------------------------------------------

    subsurface_lrc_lining = subsurface_capex.lrc_lining_capex_eur(
        steel_lining_mass_tonnes=lining.steel_lining_mass_tonnes,
        concrete_lining_mass_tonnes=lining.concrete_lining_mass_tonnes,
        steel_lining_cost_eur_per_tonne=(
            lrc_assumptions.lrc_steel_lining_cost_eur_per_tonne
        ),
        concrete_lining_cost_eur_per_tonne=(
            lrc_assumptions.lrc_concrete_lining_cost_eur_per_tonne
        ),
        installation_fraction=(
            lrc_assumptions.lrc_lining_installation_fraction
        ),
    )

    components.append(
        CostComponent(
            name="subsurface_lrc_lining",
            value_eur=subsurface_lrc_lining,
            cost_type=CostType.CAPEX,
            hystories_group=HyStoriesGroup.SUBSURFACE,
            cost_driver=CostDriver.STORAGE,
            driver_value=project.inventory.working_gas_capacity_kwh_lhv,
            cost_unit=CostUnit.EUR_PER_KWH,
            notes=(
                "LRC steel and concrete lining CAPEX, including the Huang "
                "installation fraction for welding and concrete pouring."
            ),
        )
    )

    # ---------------------------------------------------------------------------------------------------------------
    #
    #                                                   Subsurface EPC3-like First fill costs
    #
    # ---------------------------------------------------------------------------------------------------------------

  
    subsurface_epc3_first_gas_fill = subsurface_capex.epc3_porous_first_gas_fill_cost_eur(
        first_gas_fill_duration_years=first_fill_process.first_gas_fill_duration_years,
        cost_of_electricity_eur_per_mwh=(
            hystories_assumptions.cost_of_electricity_eur_per_mwh
        ),
    )

    components.append(
        CostComponent(
            name="subsurface_epc3_first_gas_fill",
            value_eur=subsurface_epc3_first_gas_fill,
            cost_type=CostType.CAPEX,
            hystories_group=HyStoriesGroup.SUBSURFACE,
            cost_driver=CostDriver.STORAGE,
            driver_value=project.inventory.working_gas_capacity_kwh_lhv,
            cost_unit=CostUnit.EUR_PER_KWH,
            notes=(
                "HyStories EPC3 first gas fill cost adapted for LRC commissioning. "
                "Calculated from the first-fill duration and electricity price. "
                "This does not include purchase of the hydrogen inventory."
            ),
        )
    )

    # ---------------------------------------------------------------------------------------------------------------
    #
    #                                                   Subsurface cushion gas
    #
    # ---------------------------------------------------------------------------------------------------------------

    subsurface_cushion_gas = subsurface_capex.cushion_gas_cost_eur_simple(
        cushion_gas_mass_kg=project.inventory.cushion_gas_h2_mass_kg,
        hydrogen_cost_eur_per_kg=hystories_assumptions.hydrogen_cost_eur_per_kg,
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
            notes=(
                "Recoverable cushion gas investment, calculated from the "
                "inventory model's cushion hydrogen mass."
            ),
        )
    )

    # ---------------------------------------------------------------------------------------------------------------
    #
    #                                                   Subsurface contingency
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
        contingency_fraction=hystories_assumptions.subsurface_contingency_fraction,
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
            notes=(
                "Subsurface contingency applied to LRC storage-linked CAPEX."
            ),
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
            and component.name != "subsurface_cushion_gas"
        )
    )

    subsurface_abex = abex.abex_cost_eur(
        epc_cost_eur=subsurface_abex_base_eur,
        abex_fraction=hystories_assumptions.subsurface_abex_fraction,
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
            notes=(
                "Subsurface ABEX applied to LRC subsurface CAPEX, excluding "
                "recoverable cushion gas."
            ),
        )
    )

    # ---------------------------------------------------------------------------------------------------------------
    #
    #                                                   Subsurface fixed OPEX
    #
    # ---------------------------------------------------------------------------------------------------------------

    subsurface_base_capex = sum(
            component.value_eur
            for component in components
            if (
                component.hystories_group == HyStoriesGroup.SUBSURFACE
                and component.cost_type == CostType.CAPEX
                and component.cost_driver == CostDriver.STORAGE
                and component.name == "subsurface_lrc_wells"
            )
        )

    subsurface_fixed_opex = subsurface_opex.fixed_opex_fraction_of_epc_cost_eur_per_year(
        subsurface_epc_cost_eur=subsurface_base_capex,
        fixed_opex_fraction_of_epc=hystories_assumptions.subsurface_fixed_opex_fraction_of_wells_capex
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
            notes=(
                "Annual LRC well OPEX, calculated as a fixed fraction of "
                "LRC well CAPEX."
            ),
        )
    )

    return CostBreakdown(components=tuple(components))


# =============================================================================
# Validation and internal helpers
# =============================================================================


def _validate_lined_rock_cavern_project(project: StorageProject) -> None:
    """Validate that the project contains the LRC design objects required here."""

    if project.lrc_geometry is None:
        raise ValueError("project.lrc_geometry must be defined.")

    if project.lrc_lining is None:
        raise ValueError("project.lrc_lining must be defined.")

    if project.lrc_drainage is None:
        raise ValueError("project.lrc_drainage must be defined.")

    if project.porous_first_fill_process is None:
        raise ValueError(
            "project.porous_first_fill_process must be defined for LRC first fill. "
            "Consider renaming this field to first_fill_process later."
        )

