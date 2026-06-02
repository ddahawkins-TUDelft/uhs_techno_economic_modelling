from uhs_costs.gas_properties.hydrogen import (
    celsius_to_kelvin,
    pressure_bar_to_pa,
    hydrogen_density,
    hydrogen_z_factor,
)


def test_celsius_to_kelvin():
    assert celsius_to_kelvin(0) == 273.15


def test_pressure_bar_to_pa():
    assert pressure_bar_to_pa(1) == 100000


def test_hydrogen_density_positive():
    rho = hydrogen_density(100, 40)
    assert rho > 0


def test_hydrogen_z_factor_positive():
    z = hydrogen_z_factor(100, 40)
    assert z > 0