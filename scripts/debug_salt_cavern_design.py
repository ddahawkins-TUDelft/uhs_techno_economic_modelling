from uhs_costs.design.salt_cavern import construct_salt_cavern_project

result = construct_salt_cavern_project(
    working_gas_capacity_kwh_lhv=700_000_000,
    withdrawal_flow_kw_h2_lhv=3_000_000,
    injection_flow_kw_h2_lhv=1_500_000,
    case_name="debug_salt_cavern",
)

print(result)