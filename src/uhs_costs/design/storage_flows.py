from dataclasses import dataclass

from uhs_costs.constants import (
    HYDROGEN_LHV_KWH_PER_KG,
    HYDROGEN_STANDARD_DENSITY_KG_PER_M3,
    HOURS_PER_DAY,
)


@dataclass(frozen=True)
class StorageFlows:
    """Storage injection and withdrawal flow rates.

    The kW values are the primary energy-system inputs.
    The standard-volume flow rates and WTIR are derived quantities.
    """

    withdrawal_flow_kw_h2_lhv: float
    injection_flow_kw_h2_lhv: float

    withdrawal_flow_million_sm3_per_day: float
    injection_flow_million_sm3_per_day: float

    withdrawal_flow_kg_per_s: float
    injection_flow_kg_per_s: float

    withdrawal_to_injection_ratio: float


def construct_storage_flows(
    withdrawal_flow_kw_h2_lhv: float,
    injection_flow_kw_h2_lhv: float,
) -> StorageFlows:
    """Construct complete storage-flow inputs from LHV flow rates."""
    _validate_positive(withdrawal_flow_kw_h2_lhv, "withdrawal_flow_kw_h2_lhv")
    _validate_positive(injection_flow_kw_h2_lhv, "injection_flow_kw_h2_lhv")

    return StorageFlows(
        withdrawal_flow_kw_h2_lhv=withdrawal_flow_kw_h2_lhv,
        injection_flow_kw_h2_lhv=injection_flow_kw_h2_lhv,
        withdrawal_flow_million_sm3_per_day=(
            _flow_kw_lhv_to_million_sm3_per_day(withdrawal_flow_kw_h2_lhv)
        ),
        injection_flow_million_sm3_per_day=(
            _flow_kw_lhv_to_million_sm3_per_day(injection_flow_kw_h2_lhv)
        ),
        withdrawal_to_injection_ratio=(
            withdrawal_flow_kw_h2_lhv / injection_flow_kw_h2_lhv
        ),
        withdrawal_flow_kg_per_s=_flow_kw_lhv_to_mass_flow_kg_s(withdrawal_flow_kw_h2_lhv),
        injection_flow_kg_per_s=_flow_kw_lhv_to_mass_flow_kg_s(injection_flow_kw_h2_lhv)
    )


def _flow_kw_lhv_to_million_sm3_per_day(
    flow_kw_h2_lhv: float,
) -> float:
    """Convert kW_H2,LHV to million Sm3/day."""
    _validate_positive(flow_kw_h2_lhv, "flow_kw_h2_lhv")

    return (
        flow_kw_h2_lhv
        * HOURS_PER_DAY
        / HYDROGEN_LHV_KWH_PER_KG
        / HYDROGEN_STANDARD_DENSITY_KG_PER_M3
        / 1_000_000
    )

def _flow_kw_lhv_to_mass_flow_kg_s(
    flow_kw_h2_lhv: float,
) -> float:
    """Convert kW_H2,LHV to kg/s H2.

    kW = kWh/hour, so:
        kg/hour = kW / kWh_per_kg
        kg/s = kg/hour / 3600
    """
    _validate_positive(flow_kw_h2_lhv, "flow_kw_h2_lhv")

    return flow_kw_h2_lhv / HYDROGEN_LHV_KWH_PER_KG / 3600


def _validate_positive(value: float, name: str) -> None:
    """Validate that a numeric value is positive."""
    if value <= 0:
        raise ValueError(f"{name} must be positive.")