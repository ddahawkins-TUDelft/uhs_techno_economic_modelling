from dataclasses import dataclass


@dataclass(frozen=True)
class HyStoriesCostAssumptions:
    """Economic and cost-model assumptions for HyStories-derived equations."""

    # Currency/cost basis
    target_currency: str = "EUR"
    target_year: int = 2025

    # Material cost factors
    material_cost_factor_injection: float = 1.0
    material_cost_factor_withdrawal: float = 1.0

    # Energy and commodity prices
    cost_of_electricity_eur_per_mwh: float = 60.0
    hydrogen_cost_eur_per_kg: float = 2.0

    # Surface OPEX
    surface_fixed_opex_fraction_of_epc: float = 0.04
    purification_coefficient: float = 0.0
    variable_opex_fixed_component_injection_share: float = 0.5

    # Subsurface OPEX
    well_intervention_fraction_of_wells_capex: float = 0.02
    monitoring_fraction_of_wells_capex: float = 0.01
    total_subsurface_fixed_opex_fraction_of_wells_capex: float = 0.03

    # Contingency / BOP / indirects
    surface_contingency_fraction: float = 0.20
    subsurface_contingency_fraction: float = 0.20
    bop_fraction: float = 0.05