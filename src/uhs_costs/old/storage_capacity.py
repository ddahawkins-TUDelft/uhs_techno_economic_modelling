"""Storage capacity calculations for underground hydrogen storage."""

from uhs_costs.constants import HYDROGEN_LHV_KWH_PER_KG
from uhs_costs.gas_properties.hydrogen import hydrogen_density

def hydrogen_mass_at_conditions(
    volume_m3: float,
    pressure_bar: float,
    temperature_c: float,
) -> float:
    """Calculate hydrogen mass in kg for a given volume, pressure, and temperature."""
    density = hydrogen_density(pressure_bar, temperature_c)
    return density * volume_m3

def working_hydrogen_mass(
    volume_m3: float,
    pressure_min_bar: float,
    pressure_max_bar: float,
    temperature_c: float,
) -> float:
    """Calculate working hydrogen mass in kg.

    Working mass is approximated as the difference between gas mass at maximum
    and minimum operating pressure.
    """
    mass_max = hydrogen_mass_at_conditions(volume_m3, pressure_max_bar, temperature_c)
    mass_min = hydrogen_mass_at_conditions(volume_m3, pressure_min_bar, temperature_c)
    return mass_max - mass_min

def cushion_hydrogen_mass(
    volume_m3: float,
    pressure_min_bar: float,
    temperature_c: float,
) -> float:
    """Calculate cushion hydrogen mass in kg.

    This assumes the cushion gas corresponds to the gas remaining at minimum
    operating pressure.
    """
    return hydrogen_mass_at_conditions(volume_m3, pressure_min_bar, temperature_c)

def hydrogen_energy_capacity_kwh(
    hydrogen_mass_kg: float,
    lhv_kwh_per_kg: float = HYDROGEN_LHV_KWH_PER_KG,
) -> float:
    """Convert hydrogen mass to lower-heating-value energy content in kWh."""
    return hydrogen_mass_kg * lhv_kwh_per_kg

def hydrogen_energy_capacity_mwh(
    hydrogen_mass_kg: float,
    lhv_kwh_per_kg: float = HYDROGEN_LHV_KWH_PER_KG,
) -> float:
    """Convert hydrogen mass to lower-heating-value energy content in kWh."""
    return hydrogen_energy_capacity_kwh(hydrogen_mass_kg, lhv_kwh_per_kg) / 1000

