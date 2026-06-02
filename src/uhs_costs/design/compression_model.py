"""Physical compression calculations for hydrogen storage models.

This module contains compressor physics only:
- pressure ratios
- compressor stage selection
- stage pressure calculations
- polytropic compressor work
- compressor power
- HyStories TICBP compressor power method


It deliberately does not contain:
- CAPEX correlations
- CEPCI conversion
- currency conversion
- Pundir/Kumar coefficients

Note: the HGSM compressor model uses multi-stage compression which is 
thermodynamically more efficient and therefore outputs are lower. 
The HyStories model in contrast uses an approximation which appears 
closer to single stage compression and hence a higher value.

Cost calculations should live in a separate cost module.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from math import ceil

import warnings

from uhs_costs.constants import (
    GAS_CONSTANT_J_PER_MOL_K,
    MOLAR_MASS_H2_KG_PER_MOL,
    SECONDS_PER_DAY,
    HYDROGEN_STANDARD_DENSITY_KG_PER_M3,
    DEFAULT_COMPRESSOR_DESIGN_POWER_FACTOR,
    HYDROGEN_LHV_KWH_PER_KG
    
)
from uhs_costs.gas_properties.hydrogen import (
    density,
    z_factor,
)

# -------------------------------------------------------------------------------------------------------
#
#                                           CLASSES
#
# -------------------------------------------------------------------------------------------------------

class CompressionMethod(StrEnum):
    """Available physical compression calculation methods."""

    HGSM_POLYTROPIC = "hgsm_polytropic" #Hydrogen Geological Storage Model = HGSM
    HYSTORIES_TICBP = "hystories_ticbp"

@dataclass(frozen=True)
class CompressionInput:
    """Input data for physical compression calculations.

    Parameters
    ----------
    inlet_pressure_pa:
        Compressor inlet pressure in Pa, absolute.
    outlet_pressure_pa:
        Compressor outlet pressure in Pa, absolute.
    inlet_temperature_k:
        Compressor inlet temperature in K.
    mass_flow_kg_s:
        Hydrogen mass flowrate in kg/s.
    method:
        Physical compression method.
    number_of_stages:
        Optional manual override. If None, HyStories stage thresholds are used.
    """

    inlet_pressure_pa: float
    outlet_pressure_pa: float
    inlet_temperature_k: float
    mass_flow_kg_s: float

    method: CompressionMethod | str = CompressionMethod.HGSM_POLYTROPIC
    number_of_stages: int | None = None

    polytropic_efficiency: float = 0.8 #assumption 
    isentropic_index: float = 1.4 #assumption
    mechanical_efficiency: float = 0.95 #assumption 
    motor_efficiency: float = 0.95 #assumption
    design_power_factor: float = DEFAULT_COMPRESSOR_DESIGN_POWER_FACTOR #assumption of 1.1 https://doi.org/10.1115/1.4025069

    split_into_trains: bool = False
    max_train_power_kw: float = 15000.0 #assumption

@dataclass(frozen=True)
class CompressionStageResult:
    """Physical results for one compression stage."""

    stage_number: int
    inlet_pressure_pa: float
    outlet_pressure_pa: float
    inlet_temperature_k: float

    pressure_ratio: float
    inlet_z: float
    outlet_z: float
    average_z: float
    average_density_kg_per_m3: float
    average_density_g_per_m3: float

    specific_work_j_per_kg: float | None
    shaft_power_kw: float | None
    electric_power_kw: float | None
    design_shaft_power_kw: float | None
    design_electric_power_kw: float | None

@dataclass(frozen=True)
class CompressionResult:
    """Common result object for physical compression calculations."""

    method: CompressionMethod
    inlet_pressure_pa: float
    outlet_pressure_pa: float
    inlet_temperature_k: float
    mass_flow_kg_s: float

    overall_pressure_ratio: float
    overall_average_density_kg_per_m3: float
    overall_average_density_g_per_m3: float
    number_of_stages: int
    stages: tuple[CompressionStageResult, ...]

    total_specific_work_j_per_kg: float | None
    total_shaft_power_kw: float | None
    total_brake_power_kw: float | None
    total_electric_power_kw: float | None

    number_of_trains: int
    power_per_train_kw: float | None

    
    design_power_factor: float
    total_design_brake_power_kw: float | None
    total_design_electric_power_kw: float | None
    design_power_per_train_kw: float | None

    injection_flow_million_sm3_per_day: float | None
    h2_lhv_flow_kw: float | None

# -------------------------------------------------------------------------------------------------------
#
#                                           FUNCTIONS
#
# -------------------------------------------------------------------------------------------------------
def pressure_ratio(
    inlet_pressure_pa: float,
    outlet_pressure_pa: float,
) -> float:
    """Calculate compression pressure ratio using absolute pressures."""
    if inlet_pressure_pa <= 0 or outlet_pressure_pa <= 0:
        raise ValueError("Pressures must be positive absolute pressures.")

    if outlet_pressure_pa <= inlet_pressure_pa:
        raise ValueError("Outlet pressure must exceed inlet pressure.")

    return outlet_pressure_pa / inlet_pressure_pa

def validate_design_power_factor(design_power_factor: float) -> None:
    """Validate compressor design power factor."""
    if design_power_factor < 1:
        raise ValueError("design_power_factor should be >= 1. Use 1.0 for no margin.")

def select_number_of_stages_hystories(
    overall_pressure_ratio: float,
) -> int:
    """Select number of compression stages using HyStories thresholds.

    HyStories D7.2-1 uses approximately:
    - tau <= 2.34: 1 stage
    - 2.34 < tau <= 4.54: 2 stages
    - 4.54 < tau <= 9.67: 3 stages

    These thresholds are linked to limiting discharge temperature.
    """
    if overall_pressure_ratio <= 1:
        raise ValueError("overall_pressure_ratio must be greater than 1.")

    if overall_pressure_ratio <= 2.34:
        return 1

    if overall_pressure_ratio <= 4.54:
        return 2

    if overall_pressure_ratio <= 9.67:
        return 3

    raise ValueError(
        "Overall pressure ratio is above the HyStories staging range. "
        "Provide number_of_stages manually."
    )

def equal_stage_pressure_ratio(
    overall_pressure_ratio: float,
    number_of_stages: int,
) -> float:
    """Calculate equal pressure ratio per compression stage."""
    if overall_pressure_ratio <= 1:
        raise ValueError("overall_pressure_ratio must be greater than 1.")

    if number_of_stages <= 0:
        raise ValueError("number_of_stages must be positive.")

    return overall_pressure_ratio ** (1 / number_of_stages)

def stage_pressure_pairs_pa(
    inlet_pressure_pa: float,
    outlet_pressure_pa: float,
    number_of_stages: int,
) -> tuple[tuple[float, float], ...]:
    """Return inlet/outlet pressure pairs for equal-ratio compression stages."""
    tau = pressure_ratio(inlet_pressure_pa, outlet_pressure_pa)
    stage_tau = equal_stage_pressure_ratio(tau, number_of_stages)

    stages: list[tuple[float, float]] = []
    p_in = inlet_pressure_pa

    for _ in range(number_of_stages):
        p_out = p_in * stage_tau
        stages.append((p_in, p_out))
        p_in = p_out

    return tuple(stages)

#HGSM Functions

def polytropic_exponent(
    isentropic_index: float,
    polytropic_efficiency: float,
) -> float:
    """Calculate the polytropic exponent.

    n = 1 / (1 - (k - 1) / (k * eta_p))
    """
    if isentropic_index <= 1:
        raise ValueError("isentropic_index must be greater than 1.")

    if not 0 < polytropic_efficiency <= 1:
        raise ValueError("polytropic_efficiency must be in the interval (0, 1].")

    return 1 / (
        1 - (isentropic_index - 1) / (isentropic_index * polytropic_efficiency)
    )

def thermodynamic_ratio(
    polytropic_exponent_value: float,
) -> float:
    """Calculate n / (n - 1), used in the compressor work equation."""
    if polytropic_exponent_value <= 1:
        raise ValueError("polytropic_exponent_value must be greater than 1.")

    return polytropic_exponent_value / (polytropic_exponent_value - 1)

def average_hydrogen_density_kg_per_m3(
    inlet_pressure_pa: float,
    outlet_pressure_pa: float,
    inlet_temperature_k: float,
    outlet_temperature_k: float | None = None,
) -> float:
    """Calculate average hydrogen density between inlet and outlet conditions.

    If no outlet temperature is provided, outlet properties are evaluated at
    inlet temperature. This is equivalent to assuming intercooling back to the
    inlet temperature for property evaluation.
    """
    if outlet_temperature_k is None:
        outlet_temperature_k = inlet_temperature_k

    inlet_density = density(
        inlet_pressure_pa,
        inlet_temperature_k,
    )
    outlet_density = density(
        outlet_pressure_pa,
        outlet_temperature_k,
    )

    return 0.5 * (inlet_density + outlet_density)

def specific_work_polytropic_j_per_kg(
    inlet_pressure_pa: float,
    outlet_pressure_pa: float,
    inlet_temperature_k: float,
    polytropic_efficiency: float = 0.8,
    isentropic_index: float = 1.4,
) -> float:
    """Calculate polytropic compressor specific work in J/kg.

    w = n/(n-1) * Z_avg * R*T/M * [(P_out/P_in)^((n-1)/n) - 1]
    """
    tau = pressure_ratio(inlet_pressure_pa, outlet_pressure_pa)

    n_poly = polytropic_exponent(
        isentropic_index=isentropic_index,
        polytropic_efficiency=polytropic_efficiency,
    )
    ratio = thermodynamic_ratio(n_poly)

    inlet_z = z_factor(inlet_pressure_pa, inlet_temperature_k)
    outlet_z = z_factor(outlet_pressure_pa, inlet_temperature_k)
    average_z = 0.5 * (inlet_z + outlet_z)

    return (
        ratio
        * average_z
        * GAS_CONSTANT_J_PER_MOL_K
        * inlet_temperature_k
        / MOLAR_MASS_H2_KG_PER_MOL
        * (tau ** (1 / ratio) - 1)
    )

def compression_power_kw(
    specific_work_j_per_kg: float,
    mass_flow_kg_s: float,
    mechanical_efficiency: float = 0.95,
    motor_efficiency: float = 0.95,
) -> tuple[float, float]:
    """Calculate shaft and electric compression power in kW.

    Returns
    -------
    tuple[float, float]
        shaft_power_kw, electric_power_kw
    """
    if specific_work_j_per_kg < 0:
        raise ValueError("specific_work_j_per_kg cannot be negative.")

    if mass_flow_kg_s <= 0:
        raise ValueError("mass_flow_kg_s must be positive.")

    if not 0 < mechanical_efficiency <= 1:
        raise ValueError("mechanical_efficiency must be in the interval (0, 1].")

    if not 0 < motor_efficiency <= 1:
        raise ValueError("motor_efficiency must be in the interval (0, 1].")

    shaft_power_kw = specific_work_j_per_kg * mass_flow_kg_s / 1000
    electric_power_kw = shaft_power_kw / (mechanical_efficiency * motor_efficiency)

    return shaft_power_kw, electric_power_kw

#HyStories Functions

def hydrogen_mass_flow_to_million_sm3_per_day(
    mass_flow_kg_s: float,
    standard_density_kg_per_m3: float,
) -> float:
    """Convert hydrogen mass flow [kg/s] to million standard m3/day."""
    if mass_flow_kg_s <= 0:
        raise ValueError("mass_flow_kg_s must be positive.")

    if standard_density_kg_per_m3 <= 0:
        raise ValueError("standard_density_kg_per_m3 must be positive.")

    flow_m3_per_s = mass_flow_kg_s / standard_density_kg_per_m3
    flow_m3_per_day = flow_m3_per_s * SECONDS_PER_DAY

    return flow_m3_per_day / 1_000_000

def hydrogen_lhv_flow_kw(
    mass_flow_kg_s: float,
    hydrogen_lhv_kwh_per_kg: float = HYDROGEN_LHV_KWH_PER_KG,
) -> float:
    """Convert hydrogen mass flow to LHV energy flow in MW.

    kg/s * kWh/kg = kWh/s
    kWh/s * 3600 = kW
    kW / 1000 = MW

    Therefore:
        MW_H2,LHV = kg/s * kWh/kg * 3.6
    """
    if mass_flow_kg_s <= 0:
        raise ValueError("mass_flow_kg_s must be positive.")

    if hydrogen_lhv_kwh_per_kg <= 0:
        raise ValueError("hydrogen_lhv_kwh_per_kg must be positive.")

    return mass_flow_kg_s * hydrogen_lhv_kwh_per_kg * 3600

def hystories_installed_brake_power_kw(
    injection_flow_million_sm3_per_day: float,
    overall_pressure_ratio: float,
    number_of_stages: int,
) -> float:
    """Calculate HyStories total installed compression brake power in kW.

    HyStories D7.2-1 uses:

    TICBP [MW] = 4.545 * n * Qi * (tau ** (0.350 / n) - 1)

    where:
    - n is the number of compression stages,
    - Qi is the maximum injection flowrate in million Sm3/day,
    - tau is the overall compression ratio.
    """
    if injection_flow_million_sm3_per_day <= 0:
        raise ValueError("injection_flow_million_sm3_per_day must be positive.")

    if overall_pressure_ratio <= 1:
        raise ValueError("overall_pressure_ratio must be greater than 1.")

    if number_of_stages <= 0:
        raise ValueError("number_of_stages must be positive.")

    power_mw = (
        4.545
        * number_of_stages
        * injection_flow_million_sm3_per_day
        * (overall_pressure_ratio ** (0.350 / number_of_stages) - 1)
    )

    return power_mw * 1000

#compression stage metadata

def build_stage_result(
    stage_number: int,
    inlet_pressure_pa: float,
    outlet_pressure_pa: float,
    inlet_temperature_k: float,
    specific_work_j_per_kg: float | None,
    shaft_power_kw: float | None,
    electric_power_kw: float | None,
    design_power_factor: float = 1.0,
) -> CompressionStageResult:
    """Build common stage metadata for either compression method."""
    inlet_z = z_factor(inlet_pressure_pa, inlet_temperature_k)
    outlet_z = z_factor(outlet_pressure_pa, inlet_temperature_k)
    average_z = 0.5 * (inlet_z + outlet_z)

    average_density_kg_per_m3 = average_hydrogen_density_kg_per_m3(
        inlet_pressure_pa=inlet_pressure_pa,
        outlet_pressure_pa=outlet_pressure_pa,
        inlet_temperature_k=inlet_temperature_k,
    )

    design_shaft_power_kw = (
    None if shaft_power_kw is None else shaft_power_kw * design_power_factor
    )

    design_electric_power_kw = (
        None if electric_power_kw is None else electric_power_kw * design_power_factor
    )

    return CompressionStageResult(
        stage_number=stage_number,
        inlet_pressure_pa=inlet_pressure_pa,
        outlet_pressure_pa=outlet_pressure_pa,
        inlet_temperature_k=inlet_temperature_k,
        pressure_ratio=pressure_ratio(inlet_pressure_pa, outlet_pressure_pa),
        inlet_z=inlet_z,
        outlet_z=outlet_z,
        average_z=average_z,
        average_density_kg_per_m3=average_density_kg_per_m3,
        average_density_g_per_m3=average_density_kg_per_m3 * 1000,
        specific_work_j_per_kg=specific_work_j_per_kg,
        shaft_power_kw=shaft_power_kw,
        electric_power_kw=electric_power_kw,
        design_shaft_power_kw=design_shaft_power_kw,
        design_electric_power_kw=design_electric_power_kw,
    )

def calculate_hgsm_polytropic_compression(
    inputs: CompressionInput,
) -> CompressionResult:
    """Calculate compression performance using HGSM-style polytropic physics."""
    validate_design_power_factor(inputs.design_power_factor)
    
    tau = pressure_ratio(inputs.inlet_pressure_pa, inputs.outlet_pressure_pa)

    overall_average_density_kg_per_m3 = average_hydrogen_density_kg_per_m3(
    inlet_pressure_pa=inputs.inlet_pressure_pa,
    outlet_pressure_pa=inputs.outlet_pressure_pa,
    inlet_temperature_k=inputs.inlet_temperature_k,
    )

    overall_average_density_g_per_m3 = overall_average_density_kg_per_m3 * 1000

    h2_lhv_flow = hydrogen_lhv_flow_kw(inputs.mass_flow_kg_s)

    injection_flow = hydrogen_mass_flow_to_million_sm3_per_day(
        mass_flow_kg_s=inputs.mass_flow_kg_s,
        standard_density_kg_per_m3=HYDROGEN_STANDARD_DENSITY_KG_PER_M3,
    )

    number_of_stages = inputs.number_of_stages
    if number_of_stages is None:
        number_of_stages = select_number_of_stages_hystories(tau)

    stage_pairs = stage_pressure_pairs_pa(
        inlet_pressure_pa=inputs.inlet_pressure_pa,
        outlet_pressure_pa=inputs.outlet_pressure_pa,
        number_of_stages=number_of_stages,
    )

    stages: list[CompressionStageResult] = []
    total_specific_work = 0.0
    total_shaft_power = 0.0
    total_electric_power = 0.0

    for stage_number, (p_in, p_out) in enumerate(stage_pairs, start=1):
        specific_work = specific_work_polytropic_j_per_kg(
            inlet_pressure_pa=p_in,
            outlet_pressure_pa=p_out,
            inlet_temperature_k=inputs.inlet_temperature_k,
            polytropic_efficiency=inputs.polytropic_efficiency,
            isentropic_index=inputs.isentropic_index,
        )

        shaft_power, electric_power = compression_power_kw(
            specific_work_j_per_kg=specific_work,
            mass_flow_kg_s=inputs.mass_flow_kg_s,
            mechanical_efficiency=inputs.mechanical_efficiency,
            motor_efficiency=inputs.motor_efficiency,
        )

        total_specific_work += specific_work
        total_shaft_power += shaft_power
        total_electric_power += electric_power

        stages.append(
            build_stage_result(
                stage_number=stage_number,
                inlet_pressure_pa=p_in,
                outlet_pressure_pa=p_out,
                inlet_temperature_k=inputs.inlet_temperature_k,
                specific_work_j_per_kg=specific_work,
                shaft_power_kw=shaft_power,
                electric_power_kw=electric_power,
                design_power_factor=inputs.design_power_factor
            )
        )

    total_design_shaft_power = total_shaft_power * inputs.design_power_factor
    total_design_electric_power = total_electric_power * inputs.design_power_factor

    number_of_trains = 1
    power_per_train_kw = total_electric_power
    design_power_per_train_kw = total_design_electric_power


    if inputs.split_into_trains:
        number_of_trains = ceil(total_design_electric_power / inputs.max_train_power_kw)
        power_per_train_kw = total_design_electric_power / number_of_trains

    return CompressionResult(
        method=CompressionMethod.HGSM_POLYTROPIC,
        inlet_pressure_pa=inputs.inlet_pressure_pa,
        outlet_pressure_pa=inputs.outlet_pressure_pa,
        inlet_temperature_k=inputs.inlet_temperature_k,
        mass_flow_kg_s=inputs.mass_flow_kg_s,
        overall_pressure_ratio=tau,
        overall_average_density_kg_per_m3=overall_average_density_kg_per_m3,
        overall_average_density_g_per_m3=overall_average_density_g_per_m3,
        number_of_stages=number_of_stages,
        stages=tuple(stages),
        total_specific_work_j_per_kg=total_specific_work,
        total_shaft_power_kw=total_shaft_power,
        total_brake_power_kw=total_shaft_power,
        total_electric_power_kw=total_electric_power,
        design_power_factor=inputs.design_power_factor,
        total_design_brake_power_kw=total_design_shaft_power,
        total_design_electric_power_kw=total_design_electric_power,
        number_of_trains=number_of_trains,
        power_per_train_kw=power_per_train_kw,
        design_power_per_train_kw=design_power_per_train_kw,
        injection_flow_million_sm3_per_day=injection_flow,
        h2_lhv_flow_kw=h2_lhv_flow
    )

def calculate_hystories_ticbp_compression(
    inputs: CompressionInput,
    standard_density_kg_per_m3: float,
) -> CompressionResult:
    """Calculate compression performance using the HyStories TICBP method.

    The HyStories formula gives total installed compression brake power.
    It does not provide stage-specific thermodynamic work, so stage results
    include pressure and density metadata but no stage-specific power.
    """

    validate_design_power_factor(inputs.design_power_factor)

    if inputs.design_power_factor != 1.0:
        warnings.warn(
            (
                "design_power_factor was provided for HyStories TICBP mode, but it "
                "will not be applied. HyStories TICBP is interpreted here as a "
                "total installed/design compression brake power estimate, so applying "
                "an additional design factor would likely double-count conservatism. "
                "Design power is therefore set equal to HyStories TICBP."
            ),
            UserWarning,
            stacklevel=2,
        )

    tau = pressure_ratio(inputs.inlet_pressure_pa, inputs.outlet_pressure_pa)

    h2_lhv_flow = hydrogen_lhv_flow_kw(inputs.mass_flow_kg_s)

    overall_average_density_kg_per_m3 = average_hydrogen_density_kg_per_m3(
    inlet_pressure_pa=inputs.inlet_pressure_pa,
    outlet_pressure_pa=inputs.outlet_pressure_pa,
    inlet_temperature_k=inputs.inlet_temperature_k,
)

    overall_average_density_g_per_m3 = overall_average_density_kg_per_m3 * 1000

    number_of_stages = inputs.number_of_stages
    if number_of_stages is None:
        number_of_stages = select_number_of_stages_hystories(tau)

    injection_flow = hydrogen_mass_flow_to_million_sm3_per_day(
        mass_flow_kg_s=inputs.mass_flow_kg_s,
        standard_density_kg_per_m3=standard_density_kg_per_m3,
    )

    brake_power_kw = hystories_installed_brake_power_kw(
        injection_flow_million_sm3_per_day=injection_flow,
        overall_pressure_ratio=tau,
        number_of_stages=number_of_stages,
    )

    if not 0 < inputs.motor_efficiency <= 1:
        raise ValueError("motor_efficiency must be in the interval (0, 1].")

    electric_power_kw = brake_power_kw / inputs.motor_efficiency

    # HyStories TICBP is already interpreted as total installed/design brake power.
    # Therefore, by default we do not apply an additional design factor.
    effective_design_power_factor = 1.0

    design_brake_power_kw = brake_power_kw * effective_design_power_factor
    design_electric_power_kw = electric_power_kw * effective_design_power_factor

    stage_pairs = stage_pressure_pairs_pa(
        inlet_pressure_pa=inputs.inlet_pressure_pa,
        outlet_pressure_pa=inputs.outlet_pressure_pa,
        number_of_stages=number_of_stages,
    )

    stages = tuple(
        build_stage_result(
            stage_number=stage_number,
            inlet_pressure_pa=p_in,
            outlet_pressure_pa=p_out,
            inlet_temperature_k=inputs.inlet_temperature_k,
            specific_work_j_per_kg=None,
            shaft_power_kw=None,
            electric_power_kw=None,
        )
        for stage_number, (p_in, p_out) in enumerate(stage_pairs, start=1)
    )

    number_of_trains = 1
    power_per_train_kw = electric_power_kw
    design_power_per_train_kw = power_per_train_kw * effective_design_power_factor

    if inputs.split_into_trains:
        number_of_trains = ceil(electric_power_kw / inputs.max_train_power_kw)
        power_per_train_kw = electric_power_kw / number_of_trains
        design_power_per_train_kw = power_per_train_kw * effective_design_power_factor


    return CompressionResult(
        method=CompressionMethod.HYSTORIES_TICBP,
        inlet_pressure_pa=inputs.inlet_pressure_pa,
        outlet_pressure_pa=inputs.outlet_pressure_pa,
        inlet_temperature_k=inputs.inlet_temperature_k,
        mass_flow_kg_s=inputs.mass_flow_kg_s,
        overall_pressure_ratio=tau,
        overall_average_density_kg_per_m3=overall_average_density_kg_per_m3,
        overall_average_density_g_per_m3=overall_average_density_g_per_m3,
        number_of_stages=number_of_stages,
        stages=stages,
        total_specific_work_j_per_kg=None,
        total_shaft_power_kw=None,
        total_brake_power_kw=brake_power_kw,
        total_electric_power_kw=electric_power_kw,
        number_of_trains=number_of_trains,
        power_per_train_kw=power_per_train_kw,
        injection_flow_million_sm3_per_day=injection_flow,
        design_power_factor=effective_design_power_factor,
        total_design_brake_power_kw=design_brake_power_kw,
        total_design_electric_power_kw=design_electric_power_kw,
        design_power_per_train_kw=design_power_per_train_kw,
        h2_lhv_flow_kw=h2_lhv_flow,
    )

def calculate_compression(
    inputs: CompressionInput,
    standard_density_kg_per_m3: float = HYDROGEN_STANDARD_DENSITY_KG_PER_M3,
) -> CompressionResult:
    """Calculate physical compression performance using the selected method.

    Parameters
    ----------
    inputs:
        Compression input data.
    standard_density_kg_per_m3:
        Required only for the HyStories TICBP method.
    """
    method = CompressionMethod(inputs.method)

    if method == CompressionMethod.HGSM_POLYTROPIC:
        return calculate_hgsm_polytropic_compression(inputs)

    if method == CompressionMethod.HYSTORIES_TICBP:
        if standard_density_kg_per_m3 is None:
            raise ValueError(
                "standard_density_kg_per_m3 is required for the "
                "hystories_ticbp method."
            )

        return calculate_hystories_ticbp_compression(
            inputs=inputs,
            standard_density_kg_per_m3=standard_density_kg_per_m3,
        )

    raise ValueError(f"Unknown compression method: {method}")