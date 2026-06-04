"""Site development data classes and constructor, covering drilling and field interconnection

For use and import into inputs.py
"""

from __future__ import annotations
from math import ceil

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
    withdrawal_flow_million_sm3_per_day: float,
    withdrawal_to_injection_ratio: float,
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
        withdrawal_flow_million_sm3_per_day,
        "withdrawal_flow_million_sm3_per_day",
    )
    _validate_positive(
        withdrawal_to_injection_ratio,
        "withdrawal_to_injection_ratio",
    )

    first_gas_fill_duration_years = (
        60
        + 1.10
        * withdrawal_to_injection_ratio
        * (working_gas_volume_million_sm3 + cushion_gas_volume_million_sm3)
        / withdrawal_flow_million_sm3_per_day
    ) / 365

    raise Exception('construct_porous_first_fill_process within site_development.py needs to be decomposed into injection and withdrawal elements ')

    return PorousFirstFillProcess(
        first_gas_fill_duration_years=first_gas_fill_duration_years,
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
    
    
