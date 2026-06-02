"""Debug script for salt cavern compression and compressor cost estimation.

Run from project root:

    pixi run python scripts/debug_compression_cost.py

This script compares:
1. HGSM single-stage polytropic compression.
2. HGSM multi-stage polytropic compression.
3. HyStories TICBP compression.
4. Pundir/Kumar compressor cost on different power estimates.
5. Decomposed HyStories EPC1 compression cost on different power estimates.

It also reports:
- CAPEX EUR2025
- EUR/kW of selected compressor power basis
- EUR/kW_H2,LHV based on hydrogen throughput
"""

from __future__ import annotations

from uhs_costs.constants import (
    BAR_TO_PA,
    DEFAULT_CEPCI_2025,
)
from uhs_costs.physical_model.compression import (
    CompressionInput,
    CompressionMethod,
    calculate_compression,
)
from uhs_costs.physical_model.compressor_cost_estimation import (
    CompressorCostMethod,
    CompressorPowerBasis,
    PundirKumarAggregationMode,
    estimate_compressor_cost,
)


def kw(value: float | None) -> str:
    """Format kW values."""
    if value is None:
        return ""
    return f"{value:,.1f}"


def money(value: float | None) -> str:
    """Format monetary values."""
    if value is None:
        return ""
    return f"{value:,.0f}"


def print_compression_summary(title: str, result) -> None:
    """Print a compact compression result summary."""
    print("\n" + "=" * 100)
    print(title)
    print("=" * 100)

    print(f"Method:                    {result.method}")
    print(f"Overall pressure ratio:    {result.overall_pressure_ratio:.3f}")
    print(f"Number of stages:          {result.number_of_stages}")
    print(f"Mass flow:                 {result.mass_flow_kg_s:.4f} kg/s")
    print(f"H2 LHV flow:               {result.h2_lhv_flow_kw:,.1f} kW_H2,LHV")
    print(f"Required brake power:      {result.total_brake_power_kw:,.1f} kW")
    print(f"Required electric power:   {result.total_electric_power_kw:,.1f} kW")
    print(f"Design power factor:       {result.design_power_factor:.2f}")
    print(f"Design brake power:        {result.total_design_brake_power_kw:,.1f} kW")
    print(f"Design electric power:     {result.total_design_electric_power_kw:,.1f} kW")
    print(f"Overall AMD:               {result.overall_average_density_g_per_m3:,.1f} g/m3")

    if result.injection_flow_million_sm3_per_day is not None:
        print(
            "Injection flow:            "
            f"{result.injection_flow_million_sm3_per_day:.4f} million Sm3/day"
        )

    print("\nStage details:")
    for stage in result.stages:
        print(
            f"  Stage {stage.stage_number}: "
            f"{stage.inlet_pressure_pa / BAR_TO_PA:,.2f} bar → "
            f"{stage.outlet_pressure_pa / BAR_TO_PA:,.2f} bar | "
            f"ratio={stage.pressure_ratio:.3f} | "
            f"AMD={stage.average_density_g_per_m3:,.1f} g/m3 | "
            f"shaft={kw(stage.shaft_power_kw)} kW | "
            f"design_shaft={kw(stage.design_shaft_power_kw)} kW | "
            f"electric={kw(stage.electric_power_kw)} kW | "
            f"design_electric={kw(stage.design_electric_power_kw)} kW"
        )


def print_cost_summary(title: str, result) -> None:
    """Print a compact compressor cost result summary."""
    print("\n" + "-" * 100)
    print(title)
    print("-" * 100)

    print(f"Cost method:               {result.method}")
    print(f"Aggregation mode:          {result.aggregation_mode}")
    print(f"Power basis:               {result.power_basis}")
    print(
        f"Total CAPEX {result.target_currency}{result.target_year}: "
        f"{result.total_capex_target_currency:,.0f}"
    )

    if result.total_capex_usd_2020 is not None:
        print(f"Total CAPEX USD2020:       {result.total_capex_usd_2020:,.0f}")

    print(
        f"Cost per power basis:      "
        f"{result.cost_per_power_eur_per_kw:,.0f} "
        f"{result.target_currency}/kW_{result.power_basis}"
    )

    if result.cost_per_h2_lhv_flow_eur_per_kw is not None:
        print(
            f"Cost per H2 LHV flow:      "
            f"{result.cost_per_h2_lhv_flow_eur_per_kw:,.0f} "
            f"{result.target_currency}/kW_H2,LHV"
        )

    print("\nCost components:")
    for component in result.components:
        print(
            f"  {component.component_name}: "
            f"stage={component.stage_number} | "
            f"power={component.power_kw:,.1f} kW | "
            f"Ps={component.suction_pressure_kpa} kPa | "
            f"AMD={component.average_density_g_per_m3} g/m3 | "
            f"CAPEX={component.capex_target_currency:,.0f} "
            f"{component.target_currency}{component.target_year} | "
            f"EUR/kW_power={component.cost_per_power_eur_per_kw:,.0f}"
        )


def estimate_hystories_epc1_compression_cost_per_stage(
    compression_result,
    material_cost_factor_injection: float = 0.0,
):
    """Estimate decomposed HyStories EPC1 compression cost stage-by-stage.

    This is diagnostic. Because the decomposed HyStories compression component
    is linear in compressor power, the summed-stage result should match the
    result obtained from total multi-stage design brake power.
    """
    stage_costs = []

    for stage in compression_result.stages:
        if stage.design_shaft_power_kw is None:
            raise ValueError(
                "Stage has no design_shaft_power_kw. Cannot estimate stage-by-stage "
                "HyStories EPC1 compression cost."
            )

        stage_cost = estimate_compressor_cost(
            method=CompressorCostMethod.HYSTORIES,
            explicit_power_kw=stage.design_shaft_power_kw,
            material_cost_factor_injection=material_cost_factor_injection,
        )

        stage_costs.append((stage.stage_number, stage.design_shaft_power_kw, stage_cost))

    return stage_costs


def main() -> None:
    """Run salt cavern compression and cost debug case."""

    # ------------------------------------------------------------------
    # Salt cavern debug case
    # ------------------------------------------------------------------
    inlet_pressure_bar_abs = 40.0
    outlet_pressure_bar_abs = 240.0
    inlet_temperature_k = 283.15
    mass_flow_kg_s = 3.27

    cepci = DEFAULT_CEPCI_2025
    metallurgy_factor = 1.1
    extrapolation_policy = "warn"
    material_cost_factor_injection = 0.0

    print("\nSalt cavern compressor cost debug case")
    print("=" * 100)
    print(f"Inlet pressure:             {inlet_pressure_bar_abs:.1f} bar abs")
    print(f"Outlet pressure:            {outlet_pressure_bar_abs:.1f} bar abs")
    print(f"Inlet temperature:          {inlet_temperature_k:.2f} K")
    print(f"Mass flow:                  {mass_flow_kg_s:.4f} kg/s")
    print(f"CEPCI target:               {cepci}")
    print(f"Metallurgy factor:          {metallurgy_factor}")
    print(f"Extrapolation policy:       {extrapolation_policy}")
    print(f"HyStories injection MCF:    {material_cost_factor_injection}")

    # ------------------------------------------------------------------
    # Physical compression models
    # ------------------------------------------------------------------
    hgsm_single_stage_inputs = CompressionInput(
        inlet_pressure_pa=inlet_pressure_bar_abs * BAR_TO_PA,
        outlet_pressure_pa=outlet_pressure_bar_abs * BAR_TO_PA,
        inlet_temperature_k=inlet_temperature_k,
        mass_flow_kg_s=mass_flow_kg_s,
        method=CompressionMethod.HGSM_POLYTROPIC,
        number_of_stages=1,
    )

    hgsm_single_stage_result = calculate_compression(hgsm_single_stage_inputs)
    print_compression_summary(
        "HGSM single-stage polytropic compression",
        hgsm_single_stage_result,
    )

    hgsm_two_stage_inputs = CompressionInput(
        inlet_pressure_pa=inlet_pressure_bar_abs * BAR_TO_PA,
        outlet_pressure_pa=outlet_pressure_bar_abs * BAR_TO_PA,
        inlet_temperature_k=inlet_temperature_k,
        mass_flow_kg_s=mass_flow_kg_s,
        method=CompressionMethod.HGSM_POLYTROPIC,
        number_of_stages=2,
    )

    hgsm_two_stage_result = calculate_compression(hgsm_two_stage_inputs)
    print_compression_summary(
        "HGSM two-stage polytropic compression",
        hgsm_two_stage_result,
    )

    hgsm_multi_stage_inputs = CompressionInput(
        inlet_pressure_pa=inlet_pressure_bar_abs * BAR_TO_PA,
        outlet_pressure_pa=outlet_pressure_bar_abs * BAR_TO_PA,
        inlet_temperature_k=inlet_temperature_k,
        mass_flow_kg_s=mass_flow_kg_s,
        method=CompressionMethod.HGSM_POLYTROPIC,
        number_of_stages=None,
    )

    hgsm_multi_stage_result = calculate_compression(hgsm_multi_stage_inputs)
    print_compression_summary(
        "HGSM multi-stage polytropic compression",
        hgsm_multi_stage_result,
    )

    hystories_inputs = CompressionInput(
        inlet_pressure_pa=inlet_pressure_bar_abs * BAR_TO_PA,
        outlet_pressure_pa=outlet_pressure_bar_abs * BAR_TO_PA,
        inlet_temperature_k=inlet_temperature_k,
        mass_flow_kg_s=mass_flow_kg_s,
        method=CompressionMethod.HYSTORIES_TICBP,
        number_of_stages=None,
    )

    hystories_result = calculate_compression(hystories_inputs)
    print_compression_summary("HyStories TICBP compression", hystories_result)

    # ------------------------------------------------------------------
    # Cost model permutations
    # ------------------------------------------------------------------
    cost_cases = []

    pundir_single_stage_system = estimate_compressor_cost(
        method=CompressorCostMethod.PUNDIR_KUMAR,
        compression_result=hgsm_single_stage_result,
        cepci=cepci,
        aggregation_mode=PundirKumarAggregationMode.SYSTEM,
        power_basis=CompressorPowerBasis.DESIGN_BRAKE,
        metallurgy_factor=metallurgy_factor,
        extrapolation_policy=extrapolation_policy,
    )
    cost_cases.append(
        (
            "Pundir/Kumar on HGSM single-stage, system, design brake",
            pundir_single_stage_system,
        )
    )

    pundir_multi_stage_sum = estimate_compressor_cost(
        method=CompressorCostMethod.PUNDIR_KUMAR,
        compression_result=hgsm_multi_stage_result,
        cepci=cepci,
        aggregation_mode=PundirKumarAggregationMode.PER_STAGE,
        power_basis=CompressorPowerBasis.DESIGN_BRAKE,
        metallurgy_factor=metallurgy_factor,
        extrapolation_policy=extrapolation_policy,
    )
    cost_cases.append(
        (
            "Pundir/Kumar on HGSM multi-stage, sum, design brake",
            pundir_multi_stage_sum,
        )
    )

    pundir_hystories_system = estimate_compressor_cost(
        method=CompressorCostMethod.PUNDIR_KUMAR,
        compression_result=hystories_result,
        cepci=cepci,
        aggregation_mode=PundirKumarAggregationMode.SYSTEM,
        power_basis=CompressorPowerBasis.DESIGN_BRAKE,
        metallurgy_factor=metallurgy_factor,
        extrapolation_policy=extrapolation_policy,
    )
    cost_cases.append(
        (
            "Pundir/Kumar on HyStories TICBP, system, design brake",
            pundir_hystories_system,
        )
    )

    hystories_cost_on_hgsm_single_stage = estimate_compressor_cost(
        method=CompressorCostMethod.HYSTORIES,
        compression_result=hgsm_single_stage_result,
        power_basis=CompressorPowerBasis.DESIGN_BRAKE,
        material_cost_factor_injection=material_cost_factor_injection,
    )
    cost_cases.append(
        (
            "HyStories EPC1 on HGSM single-stage, system, design brake",
            hystories_cost_on_hgsm_single_stage,
        )
    )

    hystories_cost_on_hgsm_multi_stage = estimate_compressor_cost(
        method=CompressorCostMethod.HYSTORIES,
        compression_result=hgsm_multi_stage_result,
        power_basis=CompressorPowerBasis.DESIGN_BRAKE,
        material_cost_factor_injection=material_cost_factor_injection,
    )
    cost_cases.append(
        (
            "HyStories EPC1 on HGSM multi-stage, total, design brake",
            hystories_cost_on_hgsm_multi_stage,
        )
    )

    hystories_cost_on_hystories = estimate_compressor_cost(
        method=CompressorCostMethod.HYSTORIES,
        compression_result=hystories_result,
        power_basis=CompressorPowerBasis.DESIGN_BRAKE,
        material_cost_factor_injection=material_cost_factor_injection,
    )
    cost_cases.append(
        (
            "HyStories EPC1 on HyStories TICBP, system, design brake",
            hystories_cost_on_hystories,
        )
    )


    # ------------------------------------------------------------------
    # Diagnostic: HyStories EPC1 compression stage-by-stage on HGSM multi-stage
    # ------------------------------------------------------------------
    hystories_stage_costs_on_hgsm = estimate_hystories_epc1_compression_cost_per_stage(
        compression_result=hgsm_multi_stage_result,
        material_cost_factor_injection=material_cost_factor_injection,
    )

    print("\n" + "-" * 100)
    print("HyStories EPC1 compression on HGSM multi-stage design brake, stage-by-stage")
    print("-" * 100)

    total_stage_power = 0.0
    total_stage_cost = 0.0

    for stage_number, stage_power_kw, stage_cost in hystories_stage_costs_on_hgsm:
        total_stage_power += stage_power_kw
        total_stage_cost += stage_cost.total_capex_target_currency

        print(
            f"Stage {stage_number}: "
            f"design brake power={stage_power_kw:,.1f} kW | "
            f"CAPEX EUR2025={stage_cost.total_capex_target_currency:,.0f} | "
            f"EUR/kW_power={stage_cost.cost_per_power_eur_per_kw:,.0f}"
        )

    print(
        f"Summed stages: "
        f"design brake power={total_stage_power:,.1f} kW | "
        f"CAPEX EUR2025={total_stage_cost:,.0f}"
    )


    # ------------------------------------------------------------------
    # Detailed cost summaries
    # ------------------------------------------------------------------
    for title, cost_result in cost_cases:
        print_cost_summary(title, cost_result)

    # ------------------------------------------------------------------
    # Compact comparison
    # ------------------------------------------------------------------
    print("\n" + "=" * 100)
    print("Compact comparison")
    print("=" * 100)

    rows = [
        (
            "HGSM single-stage, design physical power",
            hgsm_single_stage_result.total_design_brake_power_kw,
            hgsm_single_stage_result.total_design_electric_power_kw,
            None,
        ),
        (
            "HGSM two-stage, design physical power",
            hgsm_two_stage_result.total_design_brake_power_kw,
            hgsm_two_stage_result.total_design_electric_power_kw,
            None,
        ),
        (
            "HGSM multi-stage, design physical power",
            hgsm_multi_stage_result.total_design_brake_power_kw,
            hgsm_multi_stage_result.total_design_electric_power_kw,
            None,
        ),
        (
            "HyStories required/design power",
            hystories_result.total_design_brake_power_kw,
            hystories_result.total_design_electric_power_kw,
            None,
        ),
    ]

    for title, cost_result in cost_cases:
        rows.append((title, None, None, cost_result))

    print(
        f"{'Case':70s} "
        f"{'Brake kW':>14s} "
        f"{'Electric kW':>14s} "
        f"{'CAPEX EUR2025':>17s} "
        f"{'EUR/kW_power':>16s} "
        f"{'EUR/kW_H2,LHV':>17s}"
    )
    print("-" * 155)

    for name, brake_kw, electric_kw, cost_result in rows:
        brake_text = kw(brake_kw)
        electric_text = kw(electric_kw)

        if cost_result is None:
            capex_text = ""
            eur_per_power_text = ""
            eur_per_h2_text = ""
        else:
            capex_text = money(cost_result.total_capex_target_currency)
            eur_per_power_text = money(cost_result.cost_per_power_eur_per_kw)
            eur_per_h2_text = money(cost_result.cost_per_h2_lhv_flow_eur_per_kw)

        print(
            f"{name:70s} "
            f"{brake_text:>14s} "
            f"{electric_text:>14s} "
            f"{capex_text:>17s} "
            f"{eur_per_power_text:>16s} "
            f"{eur_per_h2_text:>17s}"
        )

if __name__ == "__main__":
    main()