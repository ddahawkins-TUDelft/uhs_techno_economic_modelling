"""Methane thermodynamic properties.

This module wraps CoolProp calls so the rest of the model does not need
to interact with CoolProp directly.
"""

from CoolProp.CoolProp import PropsSI

from uhs_costs.constants import BAR_TO_PA, CELSIUS_TO_KELVIN

METHANE = 'Methane'

def celsius_to_kelvin(temperature_c: float) -> float:
    """Convert temperature from degrees Celsius to Kelvin."""
    return temperature_c + CELSIUS_TO_KELVIN


def pressure_bar_to_pa(pressure_bar: float) -> float:
    """Convert pressure from bar to pascal."""
    return pressure_bar * BAR_TO_PA

def density(
        pressure_pa: float,
        temperature_k: float,

) -> float:
    
    """Return methane density in kg/m3.

    Parameters
    ----------
    pressure_bar:
        Absolute pressure in bar.
    temperature_c:
        Temperature in degrees Celsius.

    Returns
    -------
    float
        Methane density in kg/m3.
    """
    return PropsSI(
        "D",
        "P",
        pressure_pa,
        "T",
        temperature_k,
        METHANE,
    )

def z_factor(
    pressure_pa: float,
    temperature_k: float,
) -> float:
    """Return Methane compressibility factor Z."""
    return PropsSI(
        "Z",
        "P",
        pressure_pa,
        "T",
        temperature_k,
        METHANE,
    )

def isothermal_compressibility(
    pressure_pa: float,
    temperature_k: float,
) -> float:
    """Return isothermal compressibility in 1/Pa."""
    return PropsSI(
        "isothermal_compressibility",
        "P",
        pressure_pa,
        "T",
        temperature_k,
        METHANE,
    )

def molar_density(
    pressure_pa: float,
    temperature_k: float,
) -> float:
    """Return molar volume in mol/m3."""
    return PropsSI(
        "DMOLAR",
        "P",
        pressure_pa,
        "T",
        temperature_k,
        METHANE,
    )

def molar_mass() -> float:
    """Return molar mass in kg/mol."""
    return PropsSI(
        "M",
        METHANE,
    )

def standard_volume_m3_from_mol(
    mol: float,
    standard_pressure_pa: float = 101_325.0,
    standard_temperature_k: float = 288.15,
) -> float:
    """Convert moles of gas to standard volume using ideal gas law.

    Returns standard volume in m3.

    Uses:
        V = nRT / P

    This is appropriate for standard-volume equivalents such as Sm3.
    """
    if mol < 0:
        raise ValueError("mol cannot be negative.")

    if standard_pressure_pa <= 0:
        raise ValueError("standard_pressure_pa must be positive.")

    if standard_temperature_k <= 0:
        raise ValueError("standard_temperature_k must be positive.")

    gas_constant_j_per_mol_k = 8.314462618

    return mol * gas_constant_j_per_mol_k * standard_temperature_k / standard_pressure_pa

def pressure_from_density(
    density_kg_m3: float,
    temperature_k: float,
) -> float:
    return PropsSI(
        "P",
        "Dmass", density_kg_m3,
        "T", temperature_k,
        METHANE,
    )