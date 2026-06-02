import pytest

from uhs_costs.constants import BAR_TO_PA
from uhs_costs.compression import (
    CompressionInput,
    CompressionMethod,
    calculate_compression,
    pressure_ratio,
    select_number_of_stages_hystories,
)


def test_pressure_ratio():
    assert pressure_ratio(40 * BAR_TO_PA, 240 * BAR_TO_PA) == pytest.approx(6.0)


def test_hystories_stage_selection():
    assert select_number_of_stages_hystories(2.0) == 1
    assert select_number_of_stages_hystories(3.0) == 2
    assert select_number_of_stages_hystories(6.0) == 3


def test_hgsm_polytropic_runs():
    inputs = CompressionInput(
        inlet_pressure_pa=40 * BAR_TO_PA,
        outlet_pressure_pa=240 * BAR_TO_PA,
        inlet_temperature_k=283.15,
        mass_flow_kg_s=3.27,
        method=CompressionMethod.HGSM_POLYTROPIC,
    )

    result = calculate_compression(inputs)

    assert result.total_electric_power_kw > 0
    assert result.number_of_stages == 3
    assert len(result.stages) == 3


def test_hystories_requires_standard_density():
    inputs = CompressionInput(
        inlet_pressure_pa=40 * BAR_TO_PA,
        outlet_pressure_pa=240 * BAR_TO_PA,
        inlet_temperature_k=283.15,
        mass_flow_kg_s=3.27,
        method=CompressionMethod.HYSTORIES_TICBP,
    )

    with pytest.raises(ValueError):
        calculate_compression(inputs)

def test_compression_result_contains_overall_amd():
    inputs = CompressionInput(
        inlet_pressure_pa=40 * BAR_TO_PA,
        outlet_pressure_pa=240 * BAR_TO_PA,
        inlet_temperature_k=283.15,
        mass_flow_kg_s=3.27,
        method=CompressionMethod.HGSM_POLYTROPIC,
    )

    result = calculate_compression(inputs)

    assert result.overall_average_density_kg_per_m3 > 0
    assert result.overall_average_density_g_per_m3 > 0
    assert result.overall_average_density_g_per_m3 == pytest.approx(
        result.overall_average_density_kg_per_m3 * 1000
    )