""" Compression cost estimations based on two models: Pundir-Kumar paper, and HyStories.

- Pundir-Kumar: 10.1016/j.cherd.2025.10.050

"""

from enum import StrEnum
from dataclasses import dataclass
import warnings

from math import exp, log

from uhs_costs.design.helpers.compression_model import CompressionResult, CompressionStageResult
from uhs_costs.constants import (
    DEFAULT_CEPCI_2020,
    DEFAULT_CEPCI_2025,
    DEFAULT_TARGET_CURRENCY,
    DEFAULT_USD_TO_EUR,
)
from uhs_costs.cost_model.helpers import surface_capex


#classes

class CompressorCostMethod(StrEnum):
    PUNDIR_KUMAR = "pundir_kumar"
    HYSTORIES = "hystories"

class PundirKumarAggregationMode(StrEnum):
    SYSTEM = "system"
    PER_STAGE = "per_stage"


class CompressorPowerBasis(StrEnum):
    BRAKE = "brake"
    ELECTRIC = "electric"
    DESIGN_BRAKE = "design_brake"
    DESIGN_ELECTRIC = "design_electric"



@dataclass(frozen=True)
class CompressorCostComponent:
    """Cost result for one compressor package, stage, or train."""

    component_name: str
    stage_number: int | None

    power_kw: float
    suction_pressure_kpa: float | None
    average_density_g_per_m3: float | None

    capex_usd_2020: float | None
    capex_target_currency: float

    target_currency: str
    target_year: int

    cost_per_power_eur_per_kw: float
    h2_lhv_flow_kw: float | None
    cost_per_h2_lhv_flow_eur_per_kw: float | None

    method: str
    notes: str | None = None

    


@dataclass(frozen=True)
class CompressorCostResult:
    """Total compressor cost result."""

    method: str
    total_capex_usd_2020: float | None
    total_capex_target_currency: float

    target_currency: str
    target_year: int

    components: tuple[CompressorCostComponent, ...]

    cost_per_power_eur_per_kw: float
    h2_lhv_flow_kw: float | None
    cost_per_h2_lhv_flow_eur_per_kw: float | None

    aggregation_mode: str | None = None
    power_basis: str | None = None

    

@dataclass(frozen=True)
class PundirKumarCoefficients:
    a1: float
    a2: float
    l: float
    m: float
    n: float

# trained coefficients from 10.1016/j.cherd.2025.10.050

PUNDIR_KUMAR_CENTRIFUGAL_H2_COEFFICIENTS = {
    "20_75_kpa": PundirKumarCoefficients(
        a1=-19.468620,
        a2=21.930050,
        l=0.228298,
        m=0.055324,
        n=-0.174561,
    ),
    "75_150_kpa": PundirKumarCoefficients(
        a1=-7.482376,
        a2=10.908500,
        l=0.413955,
        m=-0.057513,
        n=-0.202380,
    ),
    "150_400_kpa": PundirKumarCoefficients(
        a1=-12.313740,
        a2=14.409890,
        l=0.358434,
        m=-0.113155,
        n=-0.094243,
    ),
    "400_750_kpa": PundirKumarCoefficients(
        a1=4.914431,
        a2=0.379640,
        l=2.055019,
        m=-0.563211,
        n=-0.562446,
    ),
    "750_1500_kpa": PundirKumarCoefficients(
        a1=4.914432,
        a2=0.379736,
        l=2.055019,
        m=-0.559173,
        n=-0.566577,
    ),
}

#warnings 

def select_pundir_kumar_h2_centrifugal_coefficients(
    suction_pressure_kpa: float,
    extrapolation_policy: str = "warn",
) -> PundirKumarCoefficients:
    """Select Pundir/Kumar H2 centrifugal coefficients by suction pressure."""

    if 20 <= suction_pressure_kpa < 75:
        return PUNDIR_KUMAR_CENTRIFUGAL_H2_COEFFICIENTS["20_75_kpa"]

    if 75 <= suction_pressure_kpa < 150:
        return PUNDIR_KUMAR_CENTRIFUGAL_H2_COEFFICIENTS["75_150_kpa"]

    if 150 <= suction_pressure_kpa < 400:
        return PUNDIR_KUMAR_CENTRIFUGAL_H2_COEFFICIENTS["150_400_kpa"]

    if 400 <= suction_pressure_kpa < 750:
        return PUNDIR_KUMAR_CENTRIFUGAL_H2_COEFFICIENTS["400_750_kpa"]

    if 750 <= suction_pressure_kpa <= 1500:
        return PUNDIR_KUMAR_CENTRIFUGAL_H2_COEFFICIENTS["750_1500_kpa"]

    if suction_pressure_kpa > 1500:
        if extrapolation_policy == "error":
            raise ValueError(
                f"Suction pressure {suction_pressure_kpa:.1f} kPa is above "
                "the Pundir/Kumar range of 1500 kPa."
            )

        if extrapolation_policy == "warn":
            warnings.warn(
                (
                    f"Suction pressure {suction_pressure_kpa:.1f} kPa is above "
                    "the Pundir/Kumar range of 1500 kPa, however inverse-exponential "
                    "curve across training data suggests upward extrapolation exhibits" 
                    "limited error. Therefore using "
                    "the 750–1500 kPa coefficient range as a high-pressure extrapolation."
                ),
                UserWarning,
                stacklevel=2,
            )

        return PUNDIR_KUMAR_CENTRIFUGAL_H2_COEFFICIENTS["750_1500_kpa"]

    raise ValueError(
        f"Suction pressure {suction_pressure_kpa:.1f} kPa is below "
        "the Pundir/Kumar range of 20 kPa. I would not extrapolate downward."
    )

def pundir_kumar_centrifugal_h2_capex_usd_2020(
    power_kw: float,
    suction_pressure_kpa: float,
    average_density_g_per_m3: float,
    coefficients: PundirKumarCoefficients,
    metallurgy_factor: float = 1.1,
) -> float:
    """Estimate installed capital cost using Pundir/Kumar Eq. 10.

    Returns
    -------
    float
        Installed capital cost in USD 2020.

    Notes
    -----
    The Pundir/Kumar equation reports capital cost in kUSD and includes
    CEPCI / 596.2. For USD 2020, CEPCI / 596.2 = 1.
    """
    if power_kw <= 0:
        raise ValueError("power_kw must be positive.")

    if suction_pressure_kpa <= 0:
        raise ValueError("suction_pressure_kpa must be positive.")

    if average_density_g_per_m3 <= 0:
        raise ValueError("average_density_g_per_m3 must be positive.")

    capex_kusd_2020 = (
        exp(
            coefficients.a1
            + coefficients.a2
            * (log(power_kw) ** coefficients.l)
            * (log(suction_pressure_kpa) ** coefficients.m)
            * (log(average_density_g_per_m3) ** coefficients.n)
        )
        * metallurgy_factor
    )

    return capex_kusd_2020 * 1000

def convert_usd_2020_to_target_currency(
    capex_usd_2020: float,
    target_cepci: float = DEFAULT_CEPCI_2025,
    reference_cepci: float = DEFAULT_CEPCI_2020,
    usd_to_eur: float = DEFAULT_USD_TO_EUR,
) -> float:
    """Convert USD 2020 CAPEX to target-year EUR.

    Current default:
    USD 2020 -> USD 2025 using CEPCI -> EUR 2025 using fixed FX rate.
    """
    if capex_usd_2020 < 0:
        raise ValueError("capex_usd_2020 cannot be negative.")

    capex_usd_target_year = capex_usd_2020 * (target_cepci / reference_cepci)
    capex_eur_target_year = capex_usd_target_year * usd_to_eur

    return capex_eur_target_year

def get_total_power_kw(
    compression_result: CompressionResult,
    power_basis: CompressorPowerBasis | str = CompressorPowerBasis.DESIGN_BRAKE,
) -> float:
    """Get total compressor power from a CompressionResult."""
    basis = CompressorPowerBasis(power_basis)

    if basis == CompressorPowerBasis.BRAKE:
        if compression_result.total_brake_power_kw is None:
            raise ValueError("CompressionResult has no total_brake_power_kw.")
        return compression_result.total_brake_power_kw

    if basis == CompressorPowerBasis.ELECTRIC:
        if compression_result.total_electric_power_kw is None:
            raise ValueError("CompressionResult has no total_electric_power_kw.")
        return compression_result.total_electric_power_kw

    if basis == CompressorPowerBasis.DESIGN_BRAKE:
        if compression_result.total_design_brake_power_kw is None:
            raise ValueError("CompressionResult has no total_design_brake_power_kw.")
        return compression_result.total_design_brake_power_kw

    if basis == CompressorPowerBasis.DESIGN_ELECTRIC:
        if compression_result.total_design_electric_power_kw is None:
            raise ValueError("CompressionResult has no total_design_electric_power_kw.")
        return compression_result.total_design_electric_power_kw

    raise ValueError(f"Unknown power basis: {basis}")

def resolve_compressor_power_kw(
    compression_result: CompressionResult | None = None,
    power_basis: CompressorPowerBasis | str = CompressorPowerBasis.DESIGN_BRAKE,
    explicit_power_kw: float | None = None,
) -> float:
    """Resolve compressor power for cost estimation.

    If explicit_power_kw is provided, it takes priority. Otherwise, power is
    extracted from compression_result using the selected power_basis.
    """
    if explicit_power_kw is not None:
        if explicit_power_kw <= 0:
            raise ValueError("explicit_power_kw must be positive.")
        return explicit_power_kw

    if compression_result is None:
        raise ValueError(
            "Either compression_result or explicit_power_kw must be provided."
        )

    return get_total_power_kw(
        compression_result=compression_result,
        power_basis=power_basis,
    )

def get_stage_power_kw(
    stage: CompressionStageResult,
    power_basis: CompressorPowerBasis | str,
) -> float:
    """Get compressor power from one stage result."""
    basis = CompressorPowerBasis(power_basis)

    if basis == CompressorPowerBasis.BRAKE:
        if stage.shaft_power_kw is None:
            raise ValueError(
                "Stage has no shaft_power_kw. Per-stage Pundir/Kumar costing "
                "requires a physical method with stage-specific power."
            )
        return stage.shaft_power_kw

    if basis == CompressorPowerBasis.ELECTRIC:
        if stage.electric_power_kw is None:
            raise ValueError(
                "Stage has no electric_power_kw. Per-stage Pundir/Kumar costing "
                "requires a physical method with stage-specific power."
            )
        return stage.electric_power_kw
    
    if basis == CompressorPowerBasis.DESIGN_BRAKE:
        if stage.design_shaft_power_kw is None:
            raise ValueError(
                "Stage has no design_brake_power_kw. Per-stage Pundir/Kumar costing "
                "requires a physical method with stage-specific power."
            )
        return stage.design_shaft_power_kw

    if basis == CompressorPowerBasis.DESIGN_ELECTRIC:
        if stage.design_electric_power_kw is None:
            raise ValueError(
                "Stage has no design_electric_power_kw. Per-stage Pundir/Kumar costing "
                "requires a physical method with stage-specific power."
            )
        return stage.design_electric_power_kw

def estimate_pundir_kumar_system_cost(
    compression_result: CompressionResult,
    cepci: float = DEFAULT_CEPCI_2025,
    metallurgy_factor: float = 1.1,
    power_basis: CompressorPowerBasis | str = CompressorPowerBasis.DESIGN_BRAKE,
    explicit_power_kw: float | None = None,
    extrapolation_policy: str = "warn",
) -> CompressorCostResult:
    """Estimate compressor cost using Pundir/Kumar in aggregate system mode."""

    power_kw = resolve_compressor_power_kw(
        compression_result=compression_result,
        power_basis=power_basis,
        explicit_power_kw=explicit_power_kw
    )
    suction_pressure_kpa = compression_result.inlet_pressure_pa / 1000
    amd_g_per_m3 = compression_result.overall_average_density_g_per_m3

    coefficients = select_pundir_kumar_h2_centrifugal_coefficients(
        suction_pressure_kpa=suction_pressure_kpa,
        extrapolation_policy=extrapolation_policy,
    )

    capex_usd_2020 = pundir_kumar_centrifugal_h2_capex_usd_2020(
        power_kw=power_kw,
        suction_pressure_kpa=suction_pressure_kpa,
        average_density_g_per_m3=amd_g_per_m3,
        coefficients=coefficients,
        metallurgy_factor=metallurgy_factor,
    )

    capex_target_currency = convert_usd_2020_to_target_currency(
        capex_usd_2020=capex_usd_2020,
        target_cepci=cepci,
    )

    cost_per_power, h2_lhv_flow_kw, cost_per_h2_lhv_flow = (
        calculate_cost_per_unit_metrics(
            capex_target_currency=capex_target_currency,
            power_kw=power_kw,
            compression_result=compression_result,
        )
    )

    component = CompressorCostComponent(
        component_name="compressor_system",
        stage_number=None,
        power_kw=power_kw,
        suction_pressure_kpa=suction_pressure_kpa,
        average_density_g_per_m3=amd_g_per_m3,
        capex_usd_2020=capex_usd_2020,
        capex_target_currency=capex_target_currency,
        target_currency=DEFAULT_TARGET_CURRENCY,
        target_year=2025,
        method="pundir_kumar",
        notes="System-level interpretation of the Pundir/Kumar correlation.",
        cost_per_power_eur_per_kw=cost_per_power,
        h2_lhv_flow_kw=h2_lhv_flow_kw,
        cost_per_h2_lhv_flow_eur_per_kw=cost_per_h2_lhv_flow,
    )

    return CompressorCostResult(
        method="pundir_kumar",
        total_capex_usd_2020=capex_usd_2020,
        total_capex_target_currency=capex_target_currency,
        target_currency=DEFAULT_TARGET_CURRENCY,
        target_year=2025,
        components=(component,),
        aggregation_mode="system",
        power_basis=str(CompressorPowerBasis(power_basis).value),
        cost_per_power_eur_per_kw=cost_per_power,
        h2_lhv_flow_kw=h2_lhv_flow_kw,
        cost_per_h2_lhv_flow_eur_per_kw=cost_per_h2_lhv_flow,
    )

def estimate_pundir_kumar_per_stage_cost(
    compression_result: CompressionResult,
    cepci: float = DEFAULT_CEPCI_2025,
    metallurgy_factor: float = 1.1,
    power_basis: CompressorPowerBasis | str = CompressorPowerBasis.DESIGN_BRAKE,
    extrapolation_policy: str = "warn",
) -> CompressorCostResult:
    """Estimate compressor cost by applying Pundir/Kumar to each stage."""

    components: list[CompressorCostComponent] = []

    for stage in compression_result.stages:
        power_kw = get_stage_power_kw(stage, power_basis)
        suction_pressure_kpa = stage.inlet_pressure_pa / 1000
        amd_g_per_m3 = stage.average_density_g_per_m3

        coefficients = select_pundir_kumar_h2_centrifugal_coefficients(
            suction_pressure_kpa=suction_pressure_kpa,
            extrapolation_policy=extrapolation_policy,
        )

        capex_usd_2020 = pundir_kumar_centrifugal_h2_capex_usd_2020(
            power_kw=power_kw,
            suction_pressure_kpa=suction_pressure_kpa,
            average_density_g_per_m3=amd_g_per_m3,
            coefficients=coefficients,
            metallurgy_factor=metallurgy_factor,
        )

        capex_target_currency = convert_usd_2020_to_target_currency(
            capex_usd_2020=capex_usd_2020,
            target_cepci=cepci
        )

        cost_per_power, h2_lhv_flow_kw, cost_per_h2_lhv_flow = (
            calculate_cost_per_unit_metrics(
                capex_target_currency=capex_target_currency,
                power_kw=power_kw,
                compression_result=compression_result,
            )
        )

        components.append(
            CompressorCostComponent(
                component_name=f"compressor_stage_{stage.stage_number}",
                stage_number=stage.stage_number,
                power_kw=power_kw,
                suction_pressure_kpa=suction_pressure_kpa,
                average_density_g_per_m3=amd_g_per_m3,
                capex_usd_2020=capex_usd_2020,
                capex_target_currency=capex_target_currency,
                target_currency=DEFAULT_TARGET_CURRENCY,
                target_year=2025,
                method="pundir_kumar",
                cost_per_power_eur_per_kw=cost_per_power,
                h2_lhv_flow_kw=h2_lhv_flow_kw,
                cost_per_h2_lhv_flow_eur_per_kw=cost_per_h2_lhv_flow,
                notes=(
                    "Per-stage interpretation of the Pundir/Kumar correlation. "
                    "This may reduce economies of scale relative to system mode."
                ),
            )
        )

    total_capex_usd_2020 = sum(
        component.capex_usd_2020
        for component in components
        if component.capex_usd_2020 is not None
    )
    total_capex_target_currency = sum(
        component.capex_target_currency for component in components
    )

    total_power_kw = sum(component.power_kw for component in components)

    result_cost_per_power, result_h2_lhv_flow_kw, result_cost_per_h2_lhv_flow = (
        calculate_cost_per_unit_metrics(
            capex_target_currency=total_capex_target_currency,
            power_kw=total_power_kw,
            compression_result=compression_result,
        )
    )

    return CompressorCostResult(
        method="pundir_kumar",
        total_capex_usd_2020=total_capex_usd_2020,
        total_capex_target_currency=total_capex_target_currency,
        target_currency=DEFAULT_TARGET_CURRENCY,
        target_year=2025,
        components=tuple(components),
        aggregation_mode="per_stage",
        power_basis=str(CompressorPowerBasis(power_basis).value),
        cost_per_power_eur_per_kw=result_cost_per_power,
        h2_lhv_flow_kw=result_h2_lhv_flow_kw,
        cost_per_h2_lhv_flow_eur_per_kw=result_cost_per_h2_lhv_flow,
    )

def estimate_pundir_kumar_compressor_cost(
    compression_result: CompressionResult,
    cepci: float,
    aggregation_mode: PundirKumarAggregationMode | str = PundirKumarAggregationMode.SYSTEM,
    power_basis: CompressorPowerBasis | str = CompressorPowerBasis.DESIGN_BRAKE,
    metallurgy_factor: float = 1.1,
    extrapolation_policy: str = "warn",
    explicit_power_kw: float | None = None,
) -> CompressorCostResult:
    """Estimate compressor CAPEX using Pundir/Kumar from a CompressionResult."""

    mode = PundirKumarAggregationMode(aggregation_mode)

    if mode == PundirKumarAggregationMode.SYSTEM:
        return estimate_pundir_kumar_system_cost(
            compression_result=compression_result,
            cepci=cepci,
            metallurgy_factor=metallurgy_factor,
            power_basis=power_basis,
            extrapolation_policy=extrapolation_policy,
            explicit_power_kw=explicit_power_kw,
        )

    if mode == PundirKumarAggregationMode.PER_STAGE:
        if explicit_power_kw is not None:
            raise ValueError(
                "explicit_power_kw is only compatible with system aggregation mode. "
                "Per-stage Pundir/Kumar costing uses stage-specific powers."
            )

        return estimate_pundir_kumar_per_stage_cost(
            compression_result=compression_result,
            cepci=cepci,
            metallurgy_factor=metallurgy_factor,
            power_basis=power_basis,
            extrapolation_policy=extrapolation_policy,
        )

    raise ValueError(f"Unknown aggregation mode: {mode}")

def estimate_hystories_epc1_compression_cost(
    compression_result: CompressionResult | None = None,
    power_basis: CompressorPowerBasis | str = CompressorPowerBasis.DESIGN_BRAKE,
    explicit_power_kw: float | None = None,
    material_cost_factor_injection: float = 0.0,
) -> CompressorCostResult:
    power_kw = resolve_compressor_power_kw(
        compression_result=compression_result,
        power_basis=power_basis,
        explicit_power_kw=explicit_power_kw,
    )

    power_mw = power_kw / 1000

    capex_eur = surface_capex.epc1_compression_cost_eur(
        total_installed_compression_brake_power_mw=power_mw,
        material_cost_factor_injection=material_cost_factor_injection,
    )

    cost_per_power, h2_lhv_flow_kw, cost_per_h2_lhv_flow = (
        calculate_cost_per_unit_metrics(
            capex_target_currency=capex_eur,
            power_kw=power_kw,
            compression_result=compression_result,
        )
    )

    component = CompressorCostComponent(
        component_name="hystories_epc1_compression",
        stage_number=None,
        power_kw=power_kw,
        suction_pressure_kpa=(
            None
            if compression_result is None
            else compression_result.inlet_pressure_pa / 1000
        ),
        average_density_g_per_m3=(
            None
            if compression_result is None
            else compression_result.overall_average_density_g_per_m3
        ),
        capex_usd_2020=None,
        capex_target_currency=capex_eur,
        target_currency=DEFAULT_TARGET_CURRENCY,
        target_year=2025,
        method="hystories_epc1",
        cost_per_power_eur_per_kw=cost_per_power,
        h2_lhv_flow_kw=h2_lhv_flow_kw,
        cost_per_h2_lhv_flow_eur_per_kw=cost_per_h2_lhv_flow,
        notes=(
            "Decomposed HyStories EPC1 compression-scaling component only. "
            "This excludes the EPC1 fixed component and EPC1 withdrawal-flow component."
        ),
    )

    return CompressorCostResult(
        method="hystories_epc1_compression",
        total_capex_usd_2020=None,
        total_capex_target_currency=capex_eur,
        target_currency=DEFAULT_TARGET_CURRENCY,
        target_year=2025,
        components=(component,),
        aggregation_mode="system",
        power_basis=(
            "explicit_power_kw"
            if explicit_power_kw is not None
            else str(CompressorPowerBasis(power_basis).value)
        ),
        cost_per_power_eur_per_kw=cost_per_power,
        h2_lhv_flow_kw=h2_lhv_flow_kw,
        cost_per_h2_lhv_flow_eur_per_kw=cost_per_h2_lhv_flow,
    )

def estimate_hystories_compressor_cost(
    compression_result: CompressionResult | None = None,
    power_basis: CompressorPowerBasis | str = CompressorPowerBasis.DESIGN_BRAKE,
    explicit_power_kw: float | None = None,
    material_cost_factor_injection: float = 0.0,
) -> CompressorCostResult:
    """Estimate compressor cost using the decomposed HyStories EPC1 compression component."""
    return estimate_hystories_epc1_compression_cost(
        compression_result=compression_result,
        power_basis=power_basis,
        explicit_power_kw=explicit_power_kw,
        material_cost_factor_injection=material_cost_factor_injection,
    )

def estimate_compressor_cost(
    method: CompressorCostMethod | str,
    compression_result: CompressionResult | None = None,
    cepci: float = DEFAULT_CEPCI_2025,
    aggregation_mode: PundirKumarAggregationMode | str = PundirKumarAggregationMode.SYSTEM,
    power_basis: CompressorPowerBasis | str = CompressorPowerBasis.DESIGN_BRAKE,
    explicit_power_kw: float | None = None,
    metallurgy_factor: float = 1.1,
    extrapolation_policy: str = "warn",
    material_cost_factor_injection: float = 0.0,
) -> CompressorCostResult:
    """Estimate compressor cost using the selected cost method."""

    method = CompressorCostMethod(method)

    if method == CompressorCostMethod.PUNDIR_KUMAR:
        if compression_result is None:
            raise ValueError("Pundir/Kumar cost estimation requires compression_result.")

        return estimate_pundir_kumar_compressor_cost(
            compression_result=compression_result,
            cepci=cepci,
            aggregation_mode=aggregation_mode,
            power_basis=power_basis,
            metallurgy_factor=metallurgy_factor,
            extrapolation_policy=extrapolation_policy,
            explicit_power_kw=explicit_power_kw,
        )

    if method == CompressorCostMethod.HYSTORIES:
        return estimate_hystories_compressor_cost(
            compression_result=compression_result,
            power_basis=power_basis,
            explicit_power_kw=explicit_power_kw,
            material_cost_factor_injection=material_cost_factor_injection,
        )
    

    raise ValueError(f"Unknown compressor cost method: {method}")

def cost_per_power_eur_per_kw(
    capex_eur: float,
    power_kw: float,
) -> float:
    """Calculate CAPEX per compressor power rating in EUR/kW."""
    if capex_eur < 0:
        raise ValueError("capex_eur cannot be negative.")

    if power_kw <= 0:
        raise ValueError("power_kw must be positive.")

    return capex_eur / power_kw

def cost_per_h2_lhv_flow_eur_per_kw(
    capex_eur: float,
    h2_lhv_flow_kw: float,
) -> float:
    """Calculate CAPEX per hydrogen LHV flowrate in EUR/kW_H2,LHV."""
    if capex_eur < 0:
        raise ValueError("capex_eur cannot be negative.")

    if h2_lhv_flow_kw <= 0:
        raise ValueError("h2_lhv_flow_kw must be positive.")

    return capex_eur / h2_lhv_flow_kw

def calculate_cost_per_unit_metrics(
    capex_target_currency: float,
    power_kw: float,
    compression_result: CompressionResult | None = None,
) -> tuple[float, float | None, float | None]:
    """Calculate normalised compressor cost metrics.

    Returns
    -------
    tuple
        cost_per_power_eur_per_kw,
        h2_lhv_flow_kw,
        cost_per_h2_lhv_flow_eur_per_kw
    """
    cost_per_power = cost_per_power_eur_per_kw(
        capex_eur=capex_target_currency,
        power_kw=power_kw,
    )

    if compression_result is None:
        return cost_per_power, None, None

    h2_lhv_flow_kw = compression_result.h2_lhv_flow_kw

    cost_per_h2_lhv_flow = cost_per_h2_lhv_flow_eur_per_kw(
        capex_eur=capex_target_currency,
        h2_lhv_flow_kw=h2_lhv_flow_kw,
    )

    return cost_per_power, h2_lhv_flow_kw, cost_per_h2_lhv_flow