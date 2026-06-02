"""Well design data class and constructor.

For use and import into inputs.py
"""

from __future__ import annotations

from dataclasses import dataclass

@dataclass(frozen=True)
class WellDesign:
    number_well_heads: int
    # Salt cavern-specific
    number_caverns: int | None = None

    # Porous / DGF / aquifer-specific
    number_production_wells: int | None = None
    number_observation_wells: int | None = None

def construct_well_design(
    number_well_heads: float,
    number_caverns: float | None = None,
    number_production_wells: float | None = None,
    number_observation_wells: float | None = None
) -> WellDesign:
    
    _validate_positive(number_well_heads,'number_well_heads')

    if number_caverns is not None:
        _validate_positive(number_caverns,'number_caverns')

    if number_production_wells is not None:
        _validate_positive(number_production_wells,'number_production_wells')

    if number_observation_wells is not None:
        _validate_positive(number_observation_wells,'number_observation_wells')

    return WellDesign(
        number_well_heads=number_well_heads,
        number_caverns=number_caverns,
        number_production_wells=number_production_wells,
        number_observation_wells=number_observation_wells
    )
    
def _validate_positive(value: float, name: str) -> None:
    if value <= 0:
        raise ValueError(f"{name} must be positive.")