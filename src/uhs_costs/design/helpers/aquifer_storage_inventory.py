
"""First-order saline-aquifer hydrogen storage inventory calculations.

Unlike the fixed-volume storage inventory model, this formulation allows
the fraction of pore volume occupied by hydrogen to vary between minimum
and maximum operating states.

The saturation endpoints describe an effective developed storage region;
they are screening assumptions, not dynamically simulated states.
"""

from __future__ import annotations

import math

import uhs_costs.gas_properties.hydrogen as hydrogen
from uhs_costs.constants import HYDROGEN_LHV_KWH_PER_KG
from uhs_costs.design.helpers.storage_inventory import StorageInventory


def construct_aquifer_storage_inventory(
    working_gas_capacity_kwh_lhv: float,
    temperature_k: float,
    maximum_pressure_pa: float,
    minimum_pressure_pa: float,
    recovery_factor: float = 1.0,
    minimum_gas_saturation: float = 0.60,
    maximum_gas_saturation: float = 0.80,
) -> StorageInventory:
    """Calculate an aquifer inventory from working capacity and gas saturation.

    The working-gas capacity input is the recoverable, CEM-facing capacity.
    Physical working capacity is increased by 1 / recovery_factor before
    determining the required pore volume and hydrogen cushion inventory.

    The calculation assumes:
    - a fixed effective developed pore volume;
    - hydrogen gas saturation varies between the two operating states;
    - hydrogen pressure equals the specified reservoir pressure;
    - all cushion gas is hydrogen (no abandonment methane).

    Hydraulic feasibility and well deliverability are not evaluated here.
    """

    for name, value in (
        ("working_gas_capacity_kwh_lhv", working_gas_capacity_kwh_lhv),
        ("temperature_k", temperature_k),
        ("maximum_pressure_pa", maximum_pressure_pa),
        ("minimum_pressure_pa", minimum_pressure_pa),
    ):
        if not math.isfinite(value) or value <= 0:
            raise ValueError(f"{name} must be finite and positive.")

    if maximum_pressure_pa <= minimum_pressure_pa:
        raise ValueError(
            "maximum_pressure_pa must be greater than minimum_pressure_pa."
        )

    if not math.isfinite(recovery_factor) or not 0 < recovery_factor <= 1:
        raise ValueError("recovery_factor must be in the interval (0, 1].")

    if not (
        math.isfinite(minimum_gas_saturation)
        and math.isfinite(maximum_gas_saturation)
        and 0 < minimum_gas_saturation < maximum_gas_saturation <= 1
    ):
        raise ValueError(
            "Gas saturations must satisfy "
            "0 < minimum_gas_saturation < maximum_gas_saturation <= 1."
        )

    # Recoverable (CEM-facing) versus physical working capacity.
    recoverable_working_gas_capacity_kwh_lhv = working_gas_capacity_kwh_lhv

    physical_working_gas_capacity_kwh_lhv = (
        recoverable_working_gas_capacity_kwh_lhv / recovery_factor
    )

    working_gas_h2_mass_kg = (
        physical_working_gas_capacity_kwh_lhv / HYDROGEN_LHV_KWH_PER_KG
    )

    working_gas_h2_mol = working_gas_h2_mass_kg / hydrogen.molar_mass()

    # Real-gas molar densities at the operating pressure limits.
    h2_molar_density_min_soc = hydrogen.molar_density(
        pressure_pa=minimum_pressure_pa,
        temperature_k=temperature_k,
    )

    h2_molar_density_max_soc = hydrogen.molar_density(
        pressure_pa=maximum_pressure_pa,
        temperature_k=temperature_k,
    )

    # Change in hydrogen inventory per unit of developed pore volume.
    effective_molar_density_swing = (
        maximum_gas_saturation * h2_molar_density_max_soc
        - minimum_gas_saturation * h2_molar_density_min_soc
    )

    if (
        not math.isfinite(effective_molar_density_swing)
        or effective_molar_density_swing <= 0
    ):
        raise ValueError(
            "Saturation-weighted H2 molar density swing must be positive."
        )

    # Effective developed pore volume, not bulk-rock or gas-filled volume.
    required_storage_volume_m3 = (
        working_gas_h2_mol / effective_molar_density_swing
    )

    # H2 inventory remaining at minimum SOC.
    cushion_gas_h2_mol = (
        minimum_gas_saturation
        * h2_molar_density_min_soc
        * required_storage_volume_m3
    )

    cushion_gas_h2_mass_kg = (
        cushion_gas_h2_mol * hydrogen.molar_mass()
    )

    # Standard-condition hydrogen volumes.
    working_gas_h2_volume_sm3 = hydrogen.standard_volume_m3_from_mol(
        mol=working_gas_h2_mol,
    )

    cushion_gas_h2_volume_sm3 = hydrogen.standard_volume_m3_from_mol(
        mol=cushion_gas_h2_mol,
    )

    total_gas_h2_at_max_soc_mass_kg = (
        working_gas_h2_mass_kg + cushion_gas_h2_mass_kg
    )

    total_gas_h2_at_max_soc_volume_sm3 = (
        working_gas_h2_volume_sm3 + cushion_gas_h2_volume_sm3
    )

    # No methane or other non-H2 cushion component is assumed.
    cushion_gas_volume_sm3 = cushion_gas_h2_volume_sm3

    total_gas_at_max_soc_volume_sm3 = (
        total_gas_h2_at_max_soc_volume_sm3
    )

    return StorageInventory(
        recoverable_working_gas_capacity_kwh_lhv=(
            recoverable_working_gas_capacity_kwh_lhv
        ),
        physical_working_gas_capacity_kwh_lhv=(
            physical_working_gas_capacity_kwh_lhv
        ),
        recovery_factor=recovery_factor,
        required_storage_volume_m3=required_storage_volume_m3,
        working_gas_h2_volume_sm3=working_gas_h2_volume_sm3,
        working_gas_h2_mass_kg=working_gas_h2_mass_kg,
        cushion_gas_volume_sm3=cushion_gas_volume_sm3,
        cushion_gas_h2_volume_sm3=cushion_gas_h2_volume_sm3,
        cushion_gas_h2_mass_kg=cushion_gas_h2_mass_kg,
        total_gas_h2_at_max_soc_volume_sm3=(
            total_gas_h2_at_max_soc_volume_sm3
        ),
        total_gas_h2_at_max_soc_mass_kg=(
            total_gas_h2_at_max_soc_mass_kg
        ),
        total_gas_at_max_soc_volume_sm3=(
            total_gas_at_max_soc_volume_sm3
        ),
        cushion_gas_to_total_gas_volume_ratio=(
            cushion_gas_volume_sm3 / total_gas_at_max_soc_volume_sm3
        ),
        working_gas_to_total_gas_volume_ratio=(
            working_gas_h2_volume_sm3 / total_gas_at_max_soc_volume_sm3
        ),
        cushion_to_working_gas_volume_ratio=(
            cushion_gas_volume_sm3 / working_gas_h2_volume_sm3
        ),
        abandonment_gas_methane_volume_sm3=None,
    )
