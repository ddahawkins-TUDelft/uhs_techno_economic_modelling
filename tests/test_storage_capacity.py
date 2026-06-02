from uhs_costs.old.storage_capacity import (
    working_hydrogen_mass,
    cushion_hydrogen_mass,
    hydrogen_energy_capacity_kwh,
)


def test_working_hydrogen_mass_positive():
    mass = working_hydrogen_mass(
        volume_m3=1000,
        pressure_min_bar=50,
        pressure_max_bar=200,
        temperature_c=40,
    )
    assert mass > 0


def test_cushion_hydrogen_mass_positive():
    mass = cushion_hydrogen_mass(
        volume_m3=1000,
        pressure_min_bar=50,
        temperature_c=40,
    )
    assert mass > 0


def test_hydrogen_energy_capacity_kwh():
    energy = hydrogen_energy_capacity_kwh(1)
    assert energy == 33.33