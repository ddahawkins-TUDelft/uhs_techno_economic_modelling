"""HyStories subsurface cost equations.

This module contains atomic HyStories-derived subsurface cost components.

The functions return EUR, even where the HyStories equations are reported in kEUR.
They do not apply contingency unless explicitly stated.

The goal is to support both:
1. original HyStories-style aggregation; and
2. decomposed allocation across storage, injection, withdrawal, fixed, and other CEM-relevant categories.
"""

from __future__ import annotations

from math import ceil

#----------------------------------------------------------------------------------------------------
# 
#                                               Helpers
#
#----------------------------------------------------------------------------------------------------


def _validate_positive(value: float, name: str) -> None:
    """Validate that a numeric value is positive."""
    if value <= 0:
        raise ValueError(f"{name} must be positive.")


def _validate_non_negative(value: float, name: str) -> None:
    """Validate that a numeric value is non-negative."""
    if value < 0:
        raise ValueError(f"{name} cannot be negative.")


def _validate_positive_int(value: int, name: str) -> None:
    """Validate that an integer value is positive."""
    if value <= 0:
        raise ValueError(f"{name} must be positive.")
    
#----------------------------------------------------------------------------------------------------
# 
#                                               EPC4 Solution Mining 
#                                                   (salt caverns)
#
#----------------------------------------------------------------------------------------------------

def epc4_salt_development_drilling_and_leaching_completion_cost_eur(
    number_well_heads: int,
    last_cemented_casing_shoe_m: float,
    material_cost_factor_withdrawal: float = 1.0,
    drilling_complexity_index: float = 1.0,
) -> float:
    """HyStories EPC4 Salt: development drilling and leaching completion.

    Returns EUR.
    """
    _validate_positive_int(number_well_heads, "number_well_heads")
    _validate_positive(last_cemented_casing_shoe_m, "last_cemented_casing_shoe_m")
    _validate_non_negative(material_cost_factor_withdrawal, "material_cost_factor_withdrawal")
    _validate_positive(drilling_complexity_index, "drilling_complexity_index")

    cost_keur = (
        number_well_heads
        * (
            1781
            + 196 * material_cost_factor_withdrawal
            + 86 * (18 + 12 * last_cemented_casing_shoe_m / 500)
        )
        * drilling_complexity_index
    )

    return cost_keur * 1000

#----------------------------------------------------------------------------------------------------
# 
#                                               EPC1 Leaching Capex
#                                                   (salt caverns)
#
#----------------------------------------------------------------------------------------------------

def epc1_salt_leaching_facilities_fixed_cost_eur() -> float:
    """HyStories EPC1 Salt fixed component for leaching facilities.

    Returns EUR.
    """
    return 50_000 * 1000


def epc1_salt_leaching_facilities_wellhead_cost_eur(
    number_well_heads: int,
) -> float:
    """HyStories EPC1 Salt wellhead/cavern-scaled component.

    Returns EUR.
    """
    _validate_positive_int(number_well_heads, "number_well_heads")
    return 2350 * number_well_heads * 1000


def epc1_salt_leaching_facilities_pipeline_cost_eur(
    fresh_water_pipeline_length_km: float,
    brine_disposal_pipeline_length_km: float,
) -> float:
    """HyStories EPC1 Salt pipeline-scaled component.

    Returns EUR.
    """
    _validate_non_negative(fresh_water_pipeline_length_km, "fresh_water_pipeline_length_km")
    _validate_non_negative(brine_disposal_pipeline_length_km, "brine_disposal_pipeline_length_km")

    cost_keur = 640 * (
        fresh_water_pipeline_length_km
        + brine_disposal_pipeline_length_km
    )

    return cost_keur * 1000

#----------------------------------------------------------------------------------------------------
# 
#                                               EPC3 Debrining and First Fill
#                                                   (salt caverns)
#
#----------------------------------------------------------------------------------------------------

def salt_debrining_duration_one_cavern_days(
    free_gas_volume_per_cavern_thousand_m3: float,
    debrining_flowrate_per_cavern_m3_per_hour: float,
) -> float:
    """HyStories salt cavern debrining duration for one cavern in days."""
    _validate_positive(free_gas_volume_per_cavern_thousand_m3, "free_gas_volume_per_cavern_thousand_m3")
    _validate_positive(debrining_flowrate_per_cavern_m3_per_hour, "debrining_flowrate_per_cavern_m3_per_hour")

    return (
        (1100 / 24)
        * free_gas_volume_per_cavern_thousand_m3
        / debrining_flowrate_per_cavern_m3_per_hour
    )


def salt_total_conversion_duration_years(
    number_well_heads: int,
    free_gas_volume_per_cavern_thousand_m3: float,
    debrining_flowrate_per_cavern_m3_per_hour: float,
) -> float:
    """HyStories total salt cavern conversion duration in years.

    Assumes two caverns can be debrined in parallel, following HyStories.
    """
    _validate_positive_int(number_well_heads, "number_well_heads")

    duration_one_cavern_days = salt_debrining_duration_one_cavern_days(
        free_gas_volume_per_cavern_thousand_m3=free_gas_volume_per_cavern_thousand_m3,
        debrining_flowrate_per_cavern_m3_per_hour=debrining_flowrate_per_cavern_m3_per_hour,
    )

    return (
        duration_one_cavern_days * ceil(number_well_heads / 2)
        + 60
    ) / 365


def epc3_salt_conversion_time_scaled_cost_eur(
    total_conversion_duration_years: float,
) -> float:
    """HyStories EPC3 Salt time-scaled conversion component.

    Returns EUR.
    """
    _validate_positive(total_conversion_duration_years, "total_conversion_duration_years")
    return 6750 * total_conversion_duration_years * 1000


def epc3_salt_conversion_fixed_cost_eur() -> float:
    """HyStories EPC3 Salt fixed conversion component.

    Returns EUR.
    """
    return 1700 * 1000


def epc3_salt_conversion_cavern_scaled_cost_eur(
    number_well_heads: int,
    free_gas_volume_per_cavern_thousand_m3: float,
    cost_of_electricity_eur_per_mwh: float = 60.0,
) -> float:
    """HyStories EPC3 Salt cavern-scaled conversion component.

    Returns EUR.
    """
    _validate_positive_int(number_well_heads, "number_well_heads")
    _validate_positive(free_gas_volume_per_cavern_thousand_m3, "free_gas_volume_per_cavern_thousand_m3")
    _validate_positive(cost_of_electricity_eur_per_mwh, "cost_of_electricity_eur_per_mwh")

    cost_keur = number_well_heads * (
        1.42
        * cost_of_electricity_eur_per_mwh
        / 60
        * free_gas_volume_per_cavern_thousand_m3
        + 2780
    )

    return cost_keur * 1000

#----------------------------------------------------------------------------------------------------
# 
#                                               EPC4 Drilling
#                                               (DGF / Aquifers)
#
#----------------------------------------------------------------------------------------------------

def epc4_porous_production_well_drilling_cost_eur(
    number_production_wells: int,
    last_cemented_casing_shoe_m: float,
    material_cost_factor_withdrawal: float = 0.0,
    drilling_complexity_index: float = 1.0,
) -> float:
    """HyStories EPC4 Porous production-well drilling component.

    Returns EUR.
    """
    _validate_positive_int(number_production_wells, "number_production_wells")
    _validate_positive(last_cemented_casing_shoe_m, "last_cemented_casing_shoe_m")
    _validate_non_negative(material_cost_factor_withdrawal, "material_cost_factor_withdrawal")
    _validate_positive(drilling_complexity_index, "drilling_complexity_index")

    cost_keur = (
        number_production_wells
        * (
            1018
            + 960 * material_cost_factor_withdrawal
            + 86 * (19 + 12 * last_cemented_casing_shoe_m / 600)
        )
        * drilling_complexity_index
    )

    return cost_keur * 1000


def epc4_porous_observation_well_drilling_cost_eur(
    number_observation_wells: int,
    last_cemented_casing_shoe_m: float,
    material_cost_factor_withdrawal: float = 0.0,
    drilling_complexity_index: float = 1.0,
) -> float:
    """HyStories EPC4 Porous observation-well drilling component.

    Returns EUR.
    """
    _validate_positive_int(number_observation_wells, "number_observation_wells")
    _validate_positive(last_cemented_casing_shoe_m, "last_cemented_casing_shoe_m")
    _validate_non_negative(material_cost_factor_withdrawal, "material_cost_factor_withdrawal")
    _validate_positive(drilling_complexity_index, "drilling_complexity_index")

    cost_keur = (
        number_observation_wells
        * (
            628
            + 618 * material_cost_factor_withdrawal
            + 46 * (21 + 6 * last_cemented_casing_shoe_m / 600)
        )
        * drilling_complexity_index
    )

    return cost_keur * 1000

#----------------------------------------------------------------------------------------------------
# 
#                                               EPC3 First Fill
#                                               (DGF / Aquifers)
#
#----------------------------------------------------------------------------------------------------

def porous_first_gas_fill_duration_years(
    working_gas_volume_million_sm3: float,
    cushion_gas_volume_million_sm3: float,
    withdrawal_flow_million_sm3_per_day: float,
    withdrawal_to_injection_ratio: float,
) -> float:
    """HyStories porous-media first gas fill duration in years."""
    _validate_positive(working_gas_volume_million_sm3, "working_gas_volume_million_sm3")
    _validate_non_negative(cushion_gas_volume_million_sm3, "cushion_gas_volume_million_sm3")
    _validate_positive(withdrawal_flow_million_sm3_per_day, "withdrawal_flow_million_sm3_per_day")
    _validate_positive(withdrawal_to_injection_ratio, "withdrawal_to_injection_ratio")

    return (
        60
        + 1.10
        * withdrawal_to_injection_ratio
        * (working_gas_volume_million_sm3 + cushion_gas_volume_million_sm3)
        / withdrawal_flow_million_sm3_per_day
    ) / 365


def epc3_porous_first_gas_fill_cost_eur(
    first_gas_fill_duration_years: float,
    cost_of_electricity_eur_per_mwh: float = 60.0,
) -> float:
    """HyStories EPC3 Porous first gas fill cost.

    Returns EUR.

    Note: based on the visible HyStories formula:
    EPC3_Porous [k€] = 2400 * dFGF + 2100 * COE / 60.
    """
    _validate_positive(first_gas_fill_duration_years, "first_gas_fill_duration_years")
    _validate_positive(cost_of_electricity_eur_per_mwh, "cost_of_electricity_eur_per_mwh")

    cost_keur = (
        2400 * first_gas_fill_duration_years
        + 2100 * cost_of_electricity_eur_per_mwh / 60
    )

    return cost_keur * 1000

#----------------------------------------------------------------------------------------------------
# 
#                                               CG 
#                                         (Cushion Gas)
#
#----------------------------------------------------------------------------------------------------

def cushion_gas_cost_eur(
    cushion_gas_to_total_gas_ratio: float,
    working_gas_volume_million_sm3: float,
    hydrogen_cost_eur_per_kg: float = 2.0,
    hydrogen_tonnes_per_million_sm3: float = 85.0,
) -> float:
    """HyStories cushion gas cost.

    Returns EUR.
    """
    if not 0 <= cushion_gas_to_total_gas_ratio < 1:
        raise ValueError("cushion_gas_to_total_gas_ratio must be in [0, 1).")

    _validate_positive(working_gas_volume_million_sm3, "working_gas_volume_million_sm3")
    _validate_positive(hydrogen_cost_eur_per_kg, "hydrogen_cost_eur_per_kg")
    _validate_positive(hydrogen_tonnes_per_million_sm3, "hydrogen_tonnes_per_million_sm3")

    cushion_gas_volume_million_sm3 = (
        cushion_gas_to_total_gas_ratio
        / (1 - cushion_gas_to_total_gas_ratio)
        * working_gas_volume_million_sm3
    )

    hydrogen_kg = (
        cushion_gas_volume_million_sm3
        * hydrogen_tonnes_per_million_sm3
        * 1000
    )

    return hydrogen_kg * hydrogen_cost_eur_per_kg

#----------------------------------------------------------------------------------------------------
# 
#                                Contingencies
#
#----------------------------------------------------------------------------------------------------

def subsurface_contingency_cost_eur(
    base_cost_eur: float,
    contingency_fraction: float = 0.20,
) -> float:
    """HyStories subsurface contingency cost.

    Returns EUR.
    """
    _validate_non_negative(base_cost_eur, "base_cost_eur")
    _validate_non_negative(contingency_fraction, "contingency_fraction")

    return contingency_fraction * base_cost_eur