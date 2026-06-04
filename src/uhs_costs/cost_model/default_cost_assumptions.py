from dataclasses import dataclass

from uhs_costs.design.helpers.project import StorageTechnology


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

    #OPEX
    surface_fixed_component_of_fixed_opex = 2100
    surface_fixed_opex_fraction_of_epc: float = 0.04
    subsurface_fixed_opex_fraction_of_wells_capex: float = 0.03


    # Contingency / BOP / indirects
    surface_contingency_fraction: float = 0.20
    subsurface_contingency_fraction: float = 0.20
    bop_fraction: float = 0.05

    #abex
    surface_abex_fraction: float = 0.20
    subsurface_abex_fraction: float = 0.20
    
def construct_hystories_cost_assumptions(
    storage_technology: StorageTechnology,
    overrides: dict[str, object] | None = None,
) -> HyStoriesCostAssumptions:
    
    assumptions = HyStoriesCostAssumptions()

    if overrides is not None:
        for key, value in overrides.items():
            if not hasattr(assumptions, key):
                raise ValueError(
                    f"'{key}' is not a valid HyStoriesCostAssumptions field."
                )
            setattr(assumptions, key, value)

    return assumptions