"""Site development data classes and constructor, covering drilling and field interconnection

For use and import into inputs.py
"""

from __future__ import annotations
from math import ceil, sqrt, pi

from dataclasses import dataclass


@dataclass(frozen=True)
class DrillingDesign:
    last_cemented_casing_shoe_m: float
    drilling_complexity_index: float 

@dataclass(frozen=True)
class FieldInterconnectionDesign:
    field_line_length_per_well_head_km: float
    field_line_length_km: float 

@dataclass(frozen=True)
class SaltLeachingDesign:
    fresh_water_pipeline_length_km: float
    brine_disposal_pipeline_length_km: float
    free_gas_volume_per_cavern_thousand_m3: float


@dataclass(frozen=True)
class SaltLeachingProcess:
    leaching_duration_per_cavern_months: float
    total_leaching_duration_years: float
    number_working_leaching_pumps: int


@dataclass(frozen=True)
class SaltConversionProcess:
    debrining_flowrate_per_cavern_m3_per_hour: float
    debrining_duration_per_cavern_days: float
    total_conversion_duration_years: float


@dataclass(frozen=True)
class PorousFirstFillProcess:
    first_gas_fill_duration_years: float

@dataclass(frozen=True)
class LinedRockCavernGeometry:
    required_effective_storage_volume_m3: float
    effective_volume_fraction: float

    required_geometric_storage_volume_m3: float
    maximum_cavern_radius_m: float
    cavern_height_m: float
    maximum_single_cavern_geometric_volume_m3: float

    number_caverns: int
    geometric_volume_per_cavern_m3: float
    effective_volume_per_cavern_m3: float
    cavern_radius_m: float

    inner_surface_area_per_cavern_m2: float
    total_inner_surface_area_m2: float


@dataclass(frozen=True)
class LinedRockCavernLiningDesign:
    steel_lining_thickness_m: float
    concrete_lining_thickness_m: float
    steel_density_kg_per_m3: float
    concrete_density_kg_per_m3: float

    total_lined_surface_area_m2: float
    steel_lining_volume_m3: float
    concrete_lining_volume_m3: float
    steel_lining_mass_kg: float
    concrete_lining_mass_kg: float
    steel_lining_mass_tonnes: float
    concrete_lining_mass_tonnes: float


@dataclass(frozen=True)
class LinedRockCavernDrainageDesign:
    tunnel_drainage_length_m: float
    cavern_drainage_length_per_cavern_m: float
    number_caverns: int

    total_cavern_drainage_length_m: float
    total_drainage_length_m: float


def construct_drilling_design(
        last_cemented_casing_shoe_m: float,
        drilling_complexity_index: float = 1.0
):
    
    _validate_positive(last_cemented_casing_shoe_m, 'last_cemented_casing_show_m')
    _validate_positive(drilling_complexity_index, 'drilling_complexity_index')

    return DrillingDesign(
        last_cemented_casing_shoe_m=last_cemented_casing_shoe_m,
        drilling_complexity_index=drilling_complexity_index
    )

def construct_field_interconnection_design(
        field_line_length_per_well_head_km: float,
        field_line_length_km: float,
):
    
    _validate_positive(field_line_length_per_well_head_km, 'field_line_length_per_well_head_km')
    _validate_positive(field_line_length_km, 'field_line_length_km')

    return FieldInterconnectionDesign(
        field_line_length_per_well_head_km = field_line_length_per_well_head_km,
        field_line_length_km=field_line_length_km,
    )

def construct_salt_leaching_design(
        fresh_water_pipeline_length_km: float,
        brine_disposal_pipeline_length_km: float,
        free_gas_volume_per_cavern_thousand_m3: float
):
    
    _validate_positive(fresh_water_pipeline_length_km, 'fresh_water_pipeline_length_km')
    _validate_positive(brine_disposal_pipeline_length_km, 'brine_disposal_pipeline_length_km')
    _validate_positive(free_gas_volume_per_cavern_thousand_m3,"free_gas_volume_per_cavern_thousand_m3")


    return SaltLeachingDesign(
        fresh_water_pipeline_length_km=fresh_water_pipeline_length_km,
        brine_disposal_pipeline_length_km=brine_disposal_pipeline_length_km,
        free_gas_volume_per_cavern_thousand_m3=free_gas_volume_per_cavern_thousand_m3
    )

def construct_salt_leaching_process(
    free_gas_volume_per_cavern_thousand_m3: float,
    number_caverns: int,
    number_working_leaching_pumps: int = 4,
) -> SaltLeachingProcess:
    
    _validate_positive( free_gas_volume_per_cavern_thousand_m3,"free_gas_volume_per_cavern_thousand_m3" )
    _validate_positive_int(number_caverns, "number_caverns")
    _validate_positive_int( number_working_leaching_pumps, "number_working_leaching_pumps" )

    leaching_duration_per_cavern_months = (
        8 + free_gas_volume_per_cavern_thousand_m3 / 20
    )

    total_leaching_duration_years = (
        leaching_duration_per_cavern_months
        / 12
        * ceil(number_caverns / number_working_leaching_pumps)
    )

    return SaltLeachingProcess(
        leaching_duration_per_cavern_months=leaching_duration_per_cavern_months,
        total_leaching_duration_years=total_leaching_duration_years,
        number_working_leaching_pumps=number_working_leaching_pumps,
    )

def construct_salt_conversion_process(
    number_well_heads: int,
    free_gas_volume_per_cavern_thousand_m3: float,
    debrining_flowrate_per_cavern_m3_per_hour: float,
) -> SaltConversionProcess:
    _validate_positive_int(number_well_heads, "number_well_heads")
    _validate_positive(
        free_gas_volume_per_cavern_thousand_m3,
        "free_gas_volume_per_cavern_thousand_m3",
    )
    _validate_positive(
        debrining_flowrate_per_cavern_m3_per_hour,
        "debrining_flowrate_per_cavern_m3_per_hour",
    )

    debrining_duration_per_cavern_days = (
        (1100 / 24)
        * free_gas_volume_per_cavern_thousand_m3
        / debrining_flowrate_per_cavern_m3_per_hour
    )

    total_conversion_duration_years = (
        debrining_duration_per_cavern_days * ceil(number_well_heads / 2)
        + 60
    ) / 365

    return SaltConversionProcess(
        debrining_flowrate_per_cavern_m3_per_hour=(
            debrining_flowrate_per_cavern_m3_per_hour
        ),
        debrining_duration_per_cavern_days=debrining_duration_per_cavern_days,
        total_conversion_duration_years=total_conversion_duration_years,
    )

def construct_porous_first_fill_process(
    working_gas_volume_million_sm3: float,
    cushion_gas_volume_million_sm3: float,
    injection_flow_million_sm3_per_day: float, #HyStories implements this wrt to Withdrawal_flow / WTIR = injection, 
                                            #i have skipped the step and instead derived it from injection
    injection_availability_factor: float, #an additional factor beyond the hystories model that accounts for
                                            # injection uptime during first fill, availability of h2 supply,
                                            # discontinuous injection to allow for geological structures to settle
) -> PorousFirstFillProcess:
    _validate_positive(
        working_gas_volume_million_sm3,
        "working_gas_volume_million_sm3",
    )
    _validate_non_negative(
        cushion_gas_volume_million_sm3,
        "cushion_gas_volume_million_sm3",
    )
    _validate_positive(
        injection_flow_million_sm3_per_day,
        "injection_flow_million_sm3_per_day",
    )
   
    first_gas_fill_duration_years = (
        60
        + 1.10
        * (working_gas_volume_million_sm3 + cushion_gas_volume_million_sm3)
        / (injection_flow_million_sm3_per_day*injection_availability_factor)
    ) / 365
    
    UserWarning('FGF costs scaled with injection rate, not just storage capacity!')

    return PorousFirstFillProcess(
        first_gas_fill_duration_years=first_gas_fill_duration_years,
    )

def construct_lined_rock_cavern_geometry(
    required_effective_storage_volume_m3: float,
    maximum_cavern_radius_m: float = 20.0,
    cavern_height_m: float = 100.0,
    effective_volume_fraction: float = 0.95,
) -> LinedRockCavernGeometry:
    """Construct LRC geometry from the required effective gas-storage volume.

    The required volume should come from `inventory.required_storage_volume_m3`.
    The radius and height define the maximum single-cavern module, not the
    storage requirement itself.
    """

    _validate_positive(
        required_effective_storage_volume_m3,
        "required_effective_storage_volume_m3",
    )
    _validate_positive(maximum_cavern_radius_m, "maximum_cavern_radius_m")
    _validate_positive(cavern_height_m, "cavern_height_m")
    _validate_fraction(effective_volume_fraction, "effective_volume_fraction")

    required_geometric_storage_volume_m3 = (
        required_effective_storage_volume_m3 / effective_volume_fraction
    )

    maximum_single_cavern_geometric_volume_m3 = (
        pi * maximum_cavern_radius_m**2 * cavern_height_m
    )

    number_caverns = ceil(
        required_geometric_storage_volume_m3
        / maximum_single_cavern_geometric_volume_m3
    )

    geometric_volume_per_cavern_m3 = (
        required_geometric_storage_volume_m3 / number_caverns
    )

    effective_volume_per_cavern_m3 = (
        geometric_volume_per_cavern_m3 * effective_volume_fraction
    )

    cavern_radius_m = sqrt(
        geometric_volume_per_cavern_m3 / (pi * cavern_height_m)
    )

    inner_surface_area_per_cavern_m2 = (
        2 * pi * cavern_radius_m * cavern_height_m
        + 2 * pi * cavern_radius_m**2
    )

    total_inner_surface_area_m2 = (
        inner_surface_area_per_cavern_m2 * number_caverns
    )

    return LinedRockCavernGeometry(
        required_effective_storage_volume_m3=required_effective_storage_volume_m3,
        effective_volume_fraction=effective_volume_fraction,
        required_geometric_storage_volume_m3=required_geometric_storage_volume_m3,
        maximum_cavern_radius_m=maximum_cavern_radius_m,
        cavern_height_m=cavern_height_m,
        maximum_single_cavern_geometric_volume_m3=(
            maximum_single_cavern_geometric_volume_m3
        ),
        number_caverns=number_caverns,
        geometric_volume_per_cavern_m3=geometric_volume_per_cavern_m3,
        effective_volume_per_cavern_m3=effective_volume_per_cavern_m3,
        cavern_radius_m=cavern_radius_m,
        inner_surface_area_per_cavern_m2=inner_surface_area_per_cavern_m2,
        total_inner_surface_area_m2=total_inner_surface_area_m2,
    )


def construct_lined_rock_cavern_lining_design(
    geometry: LinedRockCavernGeometry,
    steel_lining_thickness_m: float = 0.015,
    concrete_lining_thickness_m: float = 0.5,
    steel_density_kg_per_m3: float = 7850.0,
    concrete_density_kg_per_m3: float = 2500.0,
) -> LinedRockCavernLiningDesign:
    """Construct LRC lining material quantities.

    Huang estimates steel and concrete quantities from internal surface area
    multiplied by lining thickness.
    """

    _validate_positive(steel_lining_thickness_m, "steel_lining_thickness_m")
    _validate_positive(concrete_lining_thickness_m, "concrete_lining_thickness_m")
    _validate_positive(steel_density_kg_per_m3, "steel_density_kg_per_m3")
    _validate_positive(concrete_density_kg_per_m3, "concrete_density_kg_per_m3")

    total_lined_surface_area_m2 = geometry.total_inner_surface_area_m2

    steel_lining_volume_m3 = (
        total_lined_surface_area_m2 * steel_lining_thickness_m
    )

    concrete_lining_volume_m3 = (
        total_lined_surface_area_m2 * concrete_lining_thickness_m
    )

    steel_lining_mass_kg = steel_lining_volume_m3 * steel_density_kg_per_m3
    concrete_lining_mass_kg = concrete_lining_volume_m3 * concrete_density_kg_per_m3

    return LinedRockCavernLiningDesign(
        steel_lining_thickness_m=steel_lining_thickness_m,
        concrete_lining_thickness_m=concrete_lining_thickness_m,
        steel_density_kg_per_m3=steel_density_kg_per_m3,
        concrete_density_kg_per_m3=concrete_density_kg_per_m3,
        total_lined_surface_area_m2=total_lined_surface_area_m2,
        steel_lining_volume_m3=steel_lining_volume_m3,
        concrete_lining_volume_m3=concrete_lining_volume_m3,
        steel_lining_mass_kg=steel_lining_mass_kg,
        concrete_lining_mass_kg=concrete_lining_mass_kg,
        steel_lining_mass_tonnes=steel_lining_mass_kg / 1000,
        concrete_lining_mass_tonnes=concrete_lining_mass_kg / 1000,
    )


def construct_lined_rock_cavern_drainage_design(
    geometry: LinedRockCavernGeometry,
    tunnel_drainage_length_m: float = 0.0,
    cavern_drainage_length_per_cavern_m: float = 100.0,
) -> LinedRockCavernDrainageDesign:
    """Construct LRC drainage lengths.

    Drainage cost can later be calculated as:
    tunnel drainage length × tunnel drainage cost per metre
    + cavern drainage length × cavern drainage cost per metre.
    """

    _validate_non_negative(tunnel_drainage_length_m, "tunnel_drainage_length_m")
    _validate_non_negative(
        cavern_drainage_length_per_cavern_m,
        "cavern_drainage_length_per_cavern_m",
    )

    total_cavern_drainage_length_m = (
        geometry.number_caverns * cavern_drainage_length_per_cavern_m
    )

    total_drainage_length_m = (
        tunnel_drainage_length_m + total_cavern_drainage_length_m
    )

    return LinedRockCavernDrainageDesign(
        tunnel_drainage_length_m=tunnel_drainage_length_m,
        cavern_drainage_length_per_cavern_m=cavern_drainage_length_per_cavern_m,
        number_caverns=geometry.number_caverns,
        total_cavern_drainage_length_m=total_cavern_drainage_length_m,
        total_drainage_length_m=total_drainage_length_m,
    )

    
# VALIDATORS

def _validate_positive(value: float, name: str) -> None:
    if value <= 0:
        raise ValueError(f"{name} must be positive.")
    
def _validate_non_negative(value: float, name: str) -> None:
    if value < 0:
        raise ValueError(f"{name} must be >= 0.")
    
def _validate_positive_int(value: int, name: str) -> None:
    if value <= 0:
        raise ValueError(f"{name} must be positive.")
    
    
def _validate_fraction(value: float, name: str) -> None:
    if value <= 0 or value > 1:
        raise ValueError(f"{name} must be in the interval (0, 1].")