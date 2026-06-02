"""Main techno-economic model orchestration."""

from uhs_costs.cost_model.financing import annualised_capex, fixed_om_cost
from uhs_costs.old.storage_capacity import (
    working_hydrogen_mass,
    cushion_hydrogen_mass,
    hydrogen_energy_capacity_mwh,
)
from uhs_costs.constants import HYDROGEN_LHV_KWH_PER_KG


def calculate_storage_technology_case(
    technology: dict,
    scenario: dict,
    financial: dict,
) -> dict:
    """Calculate core outputs for one technology-scenario combination."""

    volume_m3 = scenario["storage_volume_m3"]

    working_mass_kg = working_hydrogen_mass(
        volume_m3=volume_m3,
        pressure_min_bar=technology["pressure_min_bar"],
        pressure_max_bar=technology["pressure_max_bar"],
        temperature_c=technology["temperature_c"],
    )

    cushion_mass_kg = cushion_hydrogen_mass(
        volume_m3=volume_m3,
        pressure_min_bar=technology["pressure_min_bar"],
        temperature_c=technology["temperature_c"],
    )

    energy_capacity_mwh = hydrogen_energy_capacity_mwh(
        working_mass_kg,
        HYDROGEN_LHV_KWH_PER_KG,
    )

    annual_throughput_mwh = energy_capacity_mwh * scenario["annual_cycles"]

    # Placeholder until detailed cost components are implemented
    capex_eur = 0
    annualised_capex_eur = annualised_capex(
        capex=capex_eur,
        discount_rate=financial["discount_rate"],
        lifetime_years=technology["lifetime_years"],
    )

    fixed_om_eur = fixed_om_cost(
        capex=capex_eur,
        fixed_om_fraction=technology["fixed_om_fraction"],
    )

    variable_cost_eur = 0

    return {
        "working_mass_kg": working_mass_kg,
        "cushion_mass_kg": cushion_mass_kg,
        "energy_capacity_mwh": energy_capacity_mwh,
        "annual_throughput_mwh": annual_throughput_mwh,
        "capex_eur": capex_eur,
        "annualised_capex_eur_per_year": annualised_capex_eur,
        "fixed_om_eur_per_year": fixed_om_eur,
    }