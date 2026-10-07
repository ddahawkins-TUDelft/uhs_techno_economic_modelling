"""HGSM-style physical storage inventory calculations.

This module calculates physical storage quantities from energy-system inputs.
It does not calculate costs.
"""

from __future__ import annotations

from dataclasses import dataclass

import uhs_costs.gas_properties.hydrogen as hydrogen
import uhs_costs.gas_properties.methane as methane
from uhs_costs.constants import HYDROGEN_LHV_KWH_PER_KG

def _validate_positive(value: float, name: str) -> None:
    if value <= 0:
        raise ValueError(f"{name} must be positive.")


def _validate_non_negative(value: float, name: str) -> None:
    if value < 0:
        raise ValueError(f"{name} cannot be negative.")

@dataclass(frozen=True)
class StorageInventory:
    """HGSM-style storage inventory derived from working gas energy capacity.

    The user-facing working-gas capacity is interpreted as recoverable
    working-gas capacity, i.e. the capacity represented in the CEM.

    If recovery_factor < 1, the physical design basis is upscaled before
    storage volumes, cushion gas, and total gas inventories are calculated.
    Physical inventory quantities therefore reflect the larger storage
    development needed to provide the target recoverable capacity.
    """

    # CEM-facing / useful storage energy capacity
    # working_gas_capacity_kwh_lhv: float
    recoverable_working_gas_capacity_kwh_lhv: float

    # Physical design basis after applying recovery factor
    physical_working_gas_capacity_kwh_lhv: float
    recovery_factor: float

    # Derived geometric / pore volume requirement
    required_storage_volume_m3: float

    # Physical working gas, hydrogen only
    working_gas_h2_volume_sm3: float
    working_gas_h2_mass_kg: float

    # Cushion gas, including residual methane where relevant
    cushion_gas_volume_sm3: float
    cushion_gas_h2_volume_sm3: float
    cushion_gas_h2_mass_kg: float

    # Total hydrogen inventory at maximum state of charge
    total_gas_h2_at_max_soc_volume_sm3: float
    total_gas_h2_at_max_soc_mass_kg: float

    # Total gas at maximum state of charge, including non-H2 cushion gas
    total_gas_at_max_soc_volume_sm3: float

    # Ratios based on standard volume equivalents, including abandonment gas
    cushion_gas_to_total_gas_volume_ratio: float
    working_gas_to_total_gas_volume_ratio: float
    cushion_to_working_gas_volume_ratio: float

    # Residual / abandonment gas, relevant mainly for depleted gas fields
    abandonment_gas_methane_volume_sm3: float | None = None

def construct_storage_inventory(
    working_gas_capacity_kwh_lhv: float,
    temperature_k: float,
    maximum_pressure_pa: float,
    minimum_pressure_pa: float,
    abandonment_pressure_pa: float | None = None,
    recovery_factor: float = 1.0,
) -> StorageInventory:
    """Calculate HGSM-style storage inventory from target working gas energy.

    working_gas_capacity_kwh_lhv is interpreted as recoverable, CEM-facing
    working-gas capacity.

    If recovery_factor < 1, physical storage quantities are calculated using:

        physical_working_gas_capacity = recoverable_working_gas_capacity
                                        / recovery_factor

    This means required storage volume, cushion gas, and total gas inventories
    are sized on the physical design basis, while final cost rates can still be
    reported per unit of recoverable working-gas capacity.
    """
    _validate_positive(working_gas_capacity_kwh_lhv, "working_gas_capacity_kwh_lhv")
    _validate_positive(minimum_pressure_pa, "minimum_pressure_pa")
    _validate_positive(maximum_pressure_pa, "maximum_pressure_pa")
    _validate_positive(temperature_k, "temperature_k")

    if maximum_pressure_pa <= minimum_pressure_pa:
        raise ValueError("maximum_pressure_pa must be greater than minimum_pressure_pa.")

    if abandonment_pressure_pa is None:
        abandonment_pressure_pa = 0.0

    _validate_non_negative(abandonment_pressure_pa, "abandonment_pressure_pa")

    if abandonment_pressure_pa >= minimum_pressure_pa:
        raise ValueError(
            "abandonment_pressure_pa must be lower than minimum_pressure_pa. "
            "Otherwise there is no positive H2 cushion partial pressure at minimum SOC."
        )

    if not 0 < recovery_factor <= 1:
        raise ValueError(
            f"recovery_factor must be in the interval (0, 1], got {recovery_factor}."
        )

    recoverable_working_gas_capacity_kwh_lhv = working_gas_capacity_kwh_lhv
    physical_working_gas_capacity_kwh_lhv = (
        recoverable_working_gas_capacity_kwh_lhv / recovery_factor
    )

    # Partial pressures
    methane_partial_pressure_pa = abandonment_pressure_pa
    h2_min_soc_partial_pressure_pa = minimum_pressure_pa - methane_partial_pressure_pa
    h2_max_soc_partial_pressure_pa = maximum_pressure_pa - methane_partial_pressure_pa

    # Physical working mass of hydrogen.
    # This is based on the recovery-adjusted physical design basis.
    working_gas_h2_mass_kg = (
        physical_working_gas_capacity_kwh_lhv / HYDROGEN_LHV_KWH_PER_KG
    )

    working_gas_h2_mol = working_gas_h2_mass_kg / hydrogen.molar_mass()

    # Molar densities within the storage volume
    h2_molar_density_min_soc = hydrogen.molar_density(
        pressure_pa=h2_min_soc_partial_pressure_pa,
        temperature_k=temperature_k,
    )

    h2_molar_density_max_soc = hydrogen.molar_density(
        pressure_pa=h2_max_soc_partial_pressure_pa,
        temperature_k=temperature_k,
    )

    h2_molar_density_swing = h2_molar_density_max_soc - h2_molar_density_min_soc

    if h2_molar_density_swing <= 0:
        raise ValueError("H2 molar density swing must be positive.")

    # Size volume based on the physical working gas swing.
    required_storage_volume_m3 = working_gas_h2_mol / h2_molar_density_swing

    # H2 cushion gas based on partial pressure
    cushion_gas_h2_mol = h2_molar_density_min_soc * required_storage_volume_m3
    cushion_gas_h2_mass_kg = cushion_gas_h2_mol * hydrogen.molar_mass()

    # Methane abandonment inventory, if relevant.
    if abandonment_pressure_pa > 0:
        methane_molar_density = methane.molar_density(
            pressure_pa=abandonment_pressure_pa,
            temperature_k=temperature_k,
        )
        abandonment_gas_methane_mol = (
            methane_molar_density * required_storage_volume_m3
        )
        abandonment_gas_methane_volume_sm3 = methane.standard_volume_m3_from_mol(
            mol=abandonment_gas_methane_mol,
        )
    else:
        abandonment_gas_methane_volume_sm3 = None

    # Convert H2 moles/masses to standard volumes.
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

    abandonment_volume_for_ratios = abandonment_gas_methane_volume_sm3 or 0.0

    cushion_gas_volume_sm3 = (
        cushion_gas_h2_volume_sm3 + abandonment_volume_for_ratios
    )
    total_gas_at_max_soc_volume_sm3 = (
        working_gas_h2_volume_sm3 + cushion_gas_volume_sm3
    )

    return StorageInventory(
        
        # working_gas_capacity_kwh_lhv=recoverable_working_gas_capacity_kwh_lhv, # Keep this as the CEM-facing capacity for backwards compatibility.
        recoverable_working_gas_capacity_kwh_lhv=recoverable_working_gas_capacity_kwh_lhv,
        physical_working_gas_capacity_kwh_lhv=physical_working_gas_capacity_kwh_lhv,
        recovery_factor=recovery_factor,
        required_storage_volume_m3=required_storage_volume_m3,
        working_gas_h2_volume_sm3=working_gas_h2_volume_sm3,
        working_gas_h2_mass_kg=working_gas_h2_mass_kg,
        abandonment_gas_methane_volume_sm3=abandonment_gas_methane_volume_sm3,
        cushion_gas_volume_sm3=cushion_gas_volume_sm3,
        cushion_gas_h2_volume_sm3=cushion_gas_h2_volume_sm3,
        cushion_gas_h2_mass_kg=cushion_gas_h2_mass_kg,
        total_gas_h2_at_max_soc_volume_sm3=total_gas_h2_at_max_soc_volume_sm3,
        total_gas_h2_at_max_soc_mass_kg=total_gas_h2_at_max_soc_mass_kg,
        total_gas_at_max_soc_volume_sm3=total_gas_at_max_soc_volume_sm3,
        cushion_gas_to_total_gas_volume_ratio=(
            cushion_gas_volume_sm3 / total_gas_at_max_soc_volume_sm3
        ),
        working_gas_to_total_gas_volume_ratio=(
            working_gas_h2_volume_sm3 / total_gas_at_max_soc_volume_sm3
        ),
        cushion_to_working_gas_volume_ratio=(
            cushion_gas_volume_sm3 / working_gas_h2_volume_sm3
        ),
    )