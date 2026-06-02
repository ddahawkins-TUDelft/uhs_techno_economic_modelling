"""HyStories surface OPEX equations.

This module contains atomic HyStories-derived surface OPEX components.
Functions return EUR/year unless stated otherwise.
"""

from __future__ import annotations
from math import log

from uhs_costs.constants import HYDROGEN_LHV_KWH_PER_KG



def _validate_non_negative(value: float, name: str) -> None:
    """Validate that a numeric value is non-negative."""
    if value < 0:
        raise ValueError(f"{name} cannot be negative.")
    
def _validate_compression_ratio(compression_ratio: float) -> None:
    if compression_ratio <= 1:
        raise ValueError("compression_ratio must be > 1.")
    


#----------------------------------------------------------------------------------------------------
# 
#                               fixed opex
#
#----------------------------------------------------------------------------------------------------

def fixed_opex_base_cost_eur_per_year() -> float:
    """HyStories fixed surface OPEX base component, which relates to employee wages

    Returns EUR/year.

    Component:
        2100 kEUR/year
    """
    return 2100 * 1000

def fixed_opex_fraction_of_epc_cost_eur_per_year(
    surface_epc_cost_eur: float,
    fixed_opex_fraction_of_epc: float = 0.04, #hystories default
) -> float:
    """HyStories fixed surface OPEX component proportional to EPC.

    Returns EUR/year.
    """
    _validate_non_negative(surface_epc_cost_eur, "surface_epc_cost_eur")
    _validate_non_negative(
        fixed_opex_fraction_of_epc,
        "fixed_opex_fraction_of_epc",
    )

    return fixed_opex_fraction_of_epc * surface_epc_cost_eur

#----------------------------------------------------------------------------------------------------
# 
#                               variable opex
#
#----------------------------------------------------------------------------------------------------

#implements the modified formula from 7.2 of the HyStories report

def variable_opex_rate_injection_eur_per_kwh_h2_lhv(
    cost_of_electricity_eur_per_mwh: float,
    compression_ratio: float,
) -> float:
    """HyStories variable OPEX rate per cycled hydrogen quantity.

    Returns EUR/kWh_h2_lhv.

    HyStories:
        rate = 0.746 * COE * (ln(tau) + 0.50 + K_purif)
    """
    _validate_non_negative(cost_of_electricity_eur_per_mwh, "cost_of_electricity_eur_per_mwh")
    _validate_compression_ratio(compression_ratio=compression_ratio)

    return (
        0.746
        * cost_of_electricity_eur_per_mwh
        * (
            log(compression_ratio)
            + 0.5/2 # divide the fixed components across injection and withdrawal
        ) / (1000*HYDROGEN_LHV_KWH_PER_KG) #converts tonnes H2 into kWH H2, LHV
    )

def variable_opex_rate_withdrawal_eur_per_kwh_h2_lhv(
    cost_of_electricity_eur_per_mwh: float,
    purification_coefficient: float,
) -> float:
    """HyStories variable OPEX rate per cycled hydrogen quantity.

    Returns EUR/kWh_h2_lhv.

    HyStories:
        rate = 0.746 * COE * (ln(tau) + 0.50 + K_purif)
    """
    _validate_non_negative(cost_of_electricity_eur_per_mwh, "cost_of_electricity_eur_per_mwh")
    _validate_non_negative(purification_coefficient, "purification_coefficient")

    return (
        0.746
        * cost_of_electricity_eur_per_mwh
        * (
            purification_coefficient
            + 0.5/2 # divide the fixed components across injection and withdrawal
        ) / (1000*HYDROGEN_LHV_KWH_PER_KG) #converts tonnes H2 into kWH H2, LHV
    )