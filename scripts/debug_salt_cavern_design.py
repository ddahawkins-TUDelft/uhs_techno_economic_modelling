from salt_cavern import construct_salt_cavern_project

result = construct_salt_cavern_project(
    working_gas_capacity_kwh_lhv=3.00e9,
    withdrawal_flow_kw_h2_lhv=1.00e7,
    injection_flow_kw_h2_lhv=2.78e6,
    case_name='debug_salt_cavern'
)

print(result)