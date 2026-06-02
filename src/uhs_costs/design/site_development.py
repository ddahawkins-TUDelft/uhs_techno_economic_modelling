"""Site development data classes and constructor, covering drilling and field interconnection

For use and import into inputs.py
"""

from __future__ import annotations

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
    debrining_flowrate_per_cavern_m3_per_hour: float
    free_gas_volume_per_cavern_thousand_m3: float


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
        debrining_flowrate_per_cavern_m3_per_hour: float,
        free_gas_volume_per_cavern_thousand_m3: float
):
    
    _validate_positive(fresh_water_pipeline_length_km, 'fresh_water_pipeline_length_km')
    _validate_positive(brine_disposal_pipeline_length_km, 'brine_disposal_pipeline_length_km')
    _validate_positive(debrining_flowrate_per_cavern_m3_per_hour, 'debrining_flowrate_per_cavern_m3_per_hour')
    _validate_positive(free_gas_volume_per_cavern_thousand_m3,"free_gas_volume_per_cavern_thousand_m3")


    return SaltLeachingDesign(
        fresh_water_pipeline_length_km=fresh_water_pipeline_length_km,
        brine_disposal_pipeline_length_km=brine_disposal_pipeline_length_km,
        debrining_flowrate_per_cavern_m3_per_hour=debrining_flowrate_per_cavern_m3_per_hour,
        free_gas_volume_per_cavern_thousand_m3=free_gas_volume_per_cavern_thousand_m3
    )

def _validate_positive(value: float, name: str) -> None:
    if value <= 0:
        raise ValueError(f"{name} must be positive.")