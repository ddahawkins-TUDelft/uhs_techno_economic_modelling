from __future__ import annotations

from dataclasses import dataclass, fields, replace
from typing import Any, Mapping, TypeVar

from uhs_costs.design.helpers.project import StorageTechnology
from uhs_costs.design.helpers.compression_model import CompressionMethod


# =============================================================================
# Assumption dataclasses
# =============================================================================


@dataclass(frozen=True)
class GeneralDesignAssumptions:
    """Technology-independent design and physical assumptions."""

    # Physical characteristics
    temperature_k: float = 0

    # Design pressure constraints
    minimum_operating_pressure_pa: float = 0
    maximum_operating_pressure_pa: float = 0
    abandonment_pressure_pa: float = 0

    # Pipeline assumptions
    pipeline_pressure_pa: float = 4.0e6

    # Wells / field lines
    field_line_length_per_well_head_km: float = 0.5
    drilling_complexity_index: float = 1.0

    #cleaning
    purification_factor: float = 0.0

    # Compression
    compression_method: CompressionMethod = CompressionMethod.HGSM_POLYTROPIC


@dataclass(frozen=True)
class SaltCavernDesignAssumptions:
    """Technology-specific design assumptions for salt caverns."""

    # Cavern constraints
    working_gas_volume_per_cavern_sm3: float = 31_250_000.0
    maximum_withdrawal_flow_per_cavern_million_sm3_per_day: float = 2.79

    # Drilling constraints
    last_cemented_casing_shoe_m: float = 1_000.0

    # Leaching constraints
    fresh_water_pipeline_length_km: float = 15.0
    brine_disposal_pipeline_length_km: float = 30.0
    debrining_flowrate_per_cavern_m3_per_hour: float = 200.0
    distance_nearest_gas_plant_km: float = 2.0
    number_leaching_pumps: int = 4


@dataclass(frozen=True)
class PorousMediaDesignAssumptions:
    """Technology-specific design assumptions for depleted gas fields and aquifers.

    Add porous-media-specific assumptions here once they are needed. For example:

    cushion_gas_fraction: float
    number_existing_wells: int
    number_new_wells: int
    reservoir_depth_m: float
    reservoir_permeability_md: float
    """

    pass


TechnologySpecificDesignAssumptions = (
    SaltCavernDesignAssumptions | PorousMediaDesignAssumptions
)


@dataclass(frozen=True)
class HyStoriesDesignAssumptions:
    """Complete HyStories design assumptions.

    This wrapper keeps general assumptions separate from assumptions that are
    only meaningful for a specific storage technology.
    """

    storage_technology: StorageTechnology
    general: GeneralDesignAssumptions
    technology_specific: TechnologySpecificDesignAssumptions


# =============================================================================
# Constructors
# =============================================================================


def construct_hystories_design_assumptions(
    storage_technology: StorageTechnology,
    general_overrides: Mapping[str, Any] | None = None,
    technology_overrides: Mapping[str, Any] | None = None,
) -> HyStoriesDesignAssumptions:
    """Construct default HyStories design assumptions for a storage technology.

    Parameters
    ----------
    storage_technology:
        Storage technology for which assumptions should be constructed.

    general_overrides:
        Optional overrides for technology-independent assumptions.

    technology_overrides:
        Optional overrides for technology-specific assumptions.

    Returns
    -------
    HyStoriesDesignAssumptions
        Complete design assumptions object.
    """

    general = construct_general_design_assumptions(
        storage_technology=storage_technology,
        overrides=general_overrides,
    )

    technology_specific = construct_technology_specific_design_assumptions(
        storage_technology=storage_technology,
        overrides=technology_overrides,
    )

    return HyStoriesDesignAssumptions(
        storage_technology=storage_technology,
        general=general,
        technology_specific=technology_specific,
    )


def construct_general_design_assumptions(
    storage_technology: StorageTechnology,
    overrides: Mapping[str, Any] | None = None,
) -> GeneralDesignAssumptions:
    """Construct general assumptions, including technology-dependent defaults."""

    if storage_technology in {
        StorageTechnology.SALT_CAVERN,
        StorageTechnology.LINED_ROCK_CAVERN,
    }:
        assumptions = GeneralDesignAssumptions(
            purification_factor=0.0,
            abandonment_pressure_pa=0.0,
        )

    elif storage_technology in {
        StorageTechnology.DEPLETED_GAS_FIELD,
        StorageTechnology.AQUIFER,
    }:
        assumptions = GeneralDesignAssumptions(
            purification_factor=1.5,
            # Replace this later if porous media need a non-zero abandonment pressure.
            abandonment_pressure_pa=0.0,
        )

    else:
        raise ValueError(
            f"{storage_technology} is not a valid input for storage_technology"
        )

    return apply_dataclass_overrides(assumptions, overrides)


def construct_technology_specific_design_assumptions(
    storage_technology: StorageTechnology,
    overrides: Mapping[str, Any] | None = None,
) -> TechnologySpecificDesignAssumptions:
    """Construct technology-specific design assumptions."""

    if storage_technology == StorageTechnology.SALT_CAVERN:
        assumptions = SaltCavernDesignAssumptions()

    elif storage_technology in {
        StorageTechnology.DEPLETED_GAS_FIELD,
        StorageTechnology.AQUIFER,
    }:
        assumptions = PorousMediaDesignAssumptions()

    elif storage_technology == StorageTechnology.LINED_ROCK_CAVERN:
        raise NotImplementedError(
            "Lined rock cavern design assumptions have not yet been implemented."
        )

    else:
        raise ValueError(
            f"{storage_technology} is not a valid input for storage_technology"
        )

    return apply_dataclass_overrides(assumptions, overrides)


# =============================================================================
# Override helper
# =============================================================================


T = TypeVar("T")


def apply_dataclass_overrides(
    instance: T,
    overrides: Mapping[str, Any] | None = None,
) -> T:
    """Apply user overrides to a frozen dataclass instance.

    This preserves immutability by returning a new instance rather than mutating
    the original one.

    Parameters
    ----------
    instance:
        Dataclass instance to update.

    overrides:
        Mapping of field names to replacement values.

    Returns
    -------
    T
        Updated dataclass instance.

    Raises
    ------
    ValueError
        If any override key is not a valid field on the dataclass.
    """

    if overrides is None:
        return instance

    valid_field_names = {field.name for field in fields(instance)}
    override_field_names = set(overrides)

    invalid_field_names = override_field_names - valid_field_names

    if invalid_field_names:
        invalid_fields = ", ".join(sorted(invalid_field_names))
        class_name = type(instance).__name__

        raise ValueError(
            f"Invalid override field(s) for {class_name}: {invalid_fields}"
        )

    return replace(instance, **overrides)