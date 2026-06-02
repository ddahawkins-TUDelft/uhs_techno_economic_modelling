from uhs_costs.design_builders import build_salt_cavern_design_from_energy

design = build_salt_cavern_design_from_energy(
    working_gas_capacity_kwh_lhv=1_000_000_000,
    withdrawal_flow_kw_h2_lhv=500_000,
    injection_flow_kw_h2_lhv=250_000,
    cushion_gas_to_total_gas_ratio=0.30,
    working_gas_volume_per_cavern_million_sm3=31.25,
    withdrawal_flow_per_cavern_million_sm3_per_day=1.0,
    minimum_operating_pressure_bar=80,
    maximum_operating_pressure_bar=240,
    inlet_pressure_bar=40,
    outlet_pressure_bar=240,
    case_name="debug_salt",
)

print(design)