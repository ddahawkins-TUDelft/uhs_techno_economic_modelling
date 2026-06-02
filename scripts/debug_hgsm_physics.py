from uhs_costs.design.hgsm_physics import calculate_storage_inventory_from_working_gas_energy

salt_cavern = calculate_storage_inventory_from_working_gas_energy(
    working_gas_capacity_kwh_lhv=3e9,
    temperature_k=342,
    maximum_pressure_pa=2.4e7,
    minimum_pressure_pa=9e6,
    abandonment_pressure_pa=0

)
print("--- Salt Cavern Results")
print(salt_cavern)

dgf = calculate_storage_inventory_from_working_gas_energy(
    working_gas_capacity_kwh_lhv=3e9,
    temperature_k=393,
    maximum_pressure_pa=2.51e7,
    minimum_pressure_pa=1.85e7,
    abandonment_pressure_pa=1.06e7

)
print('')
print("--- DGF Results")
print(dgf)