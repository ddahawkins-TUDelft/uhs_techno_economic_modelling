from dataclasses import dataclass

from uhs_costs.constants import BAR_TO_PA


@dataclass(frozen=True)
class StoragePressures:
    maximum_operating_pressure_pa: float
    minimum_operating_pressure_pa: float
    abandonment_pressure_pa: float
    minimum_operating_pressure_bar: float
    maximum_operating_pressure_bar: float
    operating_pressure_ratio: float

    pipeline_pressure_pa: float
    pipeline_pressure_bar: float
    maximum_compression_ratio: float
    

def construct_storage_pressures(
    maximum_operating_pressure_pa: float,
    minimum_operating_pressure_pa: float,
    abandonment_pressure_pa: float,
    pipeline_pressure_pa: float
) -> StoragePressures:
    """Construct complete storage-pressure inputs."""
    _validate_positive(maximum_operating_pressure_pa, "maximum_operating_pressure_pa")
    _validate_positive(minimum_operating_pressure_pa, "minimum_operating_pressure_pa")
    _validate_positive(pipeline_pressure_pa, 'pipeline_pressure_pa')

    if abandonment_pressure_pa < 0:
        raise ValueError("Abdonment pressure cannot be negative.")

    if abandonment_pressure_pa >= minimum_operating_pressure_pa:
        raise ValueError("Abandonment pressure cannot exceed nor equal minimum operating pressure.")
    
    if minimum_operating_pressure_pa >= maximum_operating_pressure_pa:
        raise ValueError("Minimum operating pressure cannot exceed not equal maximum operating pressure.")

    return StoragePressures(
        maximum_operating_pressure_pa=maximum_operating_pressure_pa,
        minimum_operating_pressure_pa=minimum_operating_pressure_pa,
        abandonment_pressure_pa=abandonment_pressure_pa,
        minimum_operating_pressure_bar = minimum_operating_pressure_pa/BAR_TO_PA,
        maximum_operating_pressure_bar = maximum_operating_pressure_pa/BAR_TO_PA,
        operating_pressure_ratio = maximum_operating_pressure_pa / minimum_operating_pressure_pa,

        pipeline_pressure_pa = pipeline_pressure_pa,
        pipeline_pressure_bar = pipeline_pressure_pa / BAR_TO_PA,
        maximum_compression_ratio = maximum_operating_pressure_pa / pipeline_pressure_pa
    )


def _validate_positive(value: float, name: str) -> None:
    """Validate that a numeric value is positive."""
    if value <= 0:
        raise ValueError(f"{name} must be positive.")