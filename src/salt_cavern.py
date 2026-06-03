"""Salt cavern design constructor.

This module defines salt-cavern-specific design defaults and constructs
complete StorageProject objects from the lower-level design constructors.
"""

from __future__ import annotations

from math import ceil

from uhs_costs.design.project import StorageProject, StorageTechnology
from uhs_costs.design.storage_inventory import construct_storage_inventory
from uhs_costs.design.storage_flows import construct_storage_flows
from uhs_costs.design.storage_pressures import construct_storage_pressures
from uhs_costs.design.well_design import construct_well_design
from uhs_costs.design.site_development import (
    construct_drilling_design,
    construct_field_interconnection_design,
    construct_salt_leaching_design,
)
from uhs_costs.design.purification import construct_purification
from uhs_costs.design.compression_model import (
    CompressionInput,
    CompressionMethod,
    calculate_compression,
)


# ----------------------------------------------------------------------------------------------------
#
#                               Salt cavern Design Assumptions
#
# ----------------------------------------------------------------------------------------------------

DEFAULT_TEMPERATURE_K = 342.0

DEFAULT_MINIMUM_OPERATING_PRESSURE_PA = 9.0e6 # DOI 10.2139/ssrn.5010580, DOI 10.1016/j.ijhydene.2023.04.090
DEFAULT_MAXIMUM_OPERATING_PRESSURE_PA = 2.4e7 # DOI 10.2139/ssrn.5010580, DOI 10.1016/j.ijhydene.2023.04.090
DEFAULT_ABANDONMENT_PRESSURE_PA = 0.0 # N/A for Salt Caverns

DEFAULT_PIPELINE_PRESSURE_PA = 4.0e6 # DOI 10.1016/j.ijhydene.2023.04.090, HyStories default is 5.5e6

DEFAULT_WORKING_GAS_VOLUME_PER_CAVERN_SM3 = 31_250_000.0 # HyStories D7.2-1, Table 18
DEFAULT_MAXIMUM_WITHDRAWAL_FLOW_PER_CAVERN_MILLION_SM3_PER_DAY = 2.79 # HyStories D7.2-1, Table 18

DEFAULT_LAST_CEMENTED_CASING_SHOE_M = 1_000.0 # HyStories D7.2-1, Table 18
DEFAULT_DRILLING_COMPLEXITY_INDEX = 1.0 # HyStories D7.2-1, Table 35

DEFAULT_FRESH_WATER_PIPELINE_LENGTH_KM = 15.0 # HyStories D7.2-1, Table 35
DEFAULT_BRINE_DISPOSAL_PIPELINE_LENGTH_KM = 30.0 # HyStories D7.2-1, Table 35
DEFAULT_DEBRINING_FLOWRATE_PER_CAVERN_M3_PER_HOUR = 200.0 # HyStories D7.2-1, Table 35
DEFAULT_DISTANCE_NEAREST_GAS_PLANT_KM = 2.0 # HyStories D7.2-1, Table 35

DEFAULT_FIELD_LINE_LENGTH_PER_WELL_HEAD_KM = 0.5 # HyStories D7.2-1, Table 21

DEFAULT_PURIFICATION_FACTOR = 0 # HyStories D7.2-1, Table 25 

DEFAULT_COMPRESSION_METHOD = CompressionMethod.HGSM_POLYTROPIC #using the polytropic compression method rather than the HyStories simplified approximation

# ----------------------------------------------------------------------------------------------------
#
#                               Salt cavern Costs Assumptions
#
# ----------------------------------------------------------------------------------------------------

DEFAULT_HYDROGEN_COST_EUR_PER_KG = 2.0 # HyStories D7.2-1, Table 35 

# ----------------------------------------------------------------------------------------------------
#
#                                       DESIGN CONSTRUCTOR
#
# ----------------------------------------------------------------------------------------------------

def construct_salt_cavern_project(
    working_gas_capacity_kwh_lhv: float,
    withdrawal_flow_kw_h2_lhv: float,
    injection_flow_kw_h2_lhv: float,
    case_name: str | None = None,

    #DEFAULTS
    temperature_k: float = DEFAULT_TEMPERATURE_K,
    minimum_operating_pressure_pa: float = DEFAULT_MINIMUM_OPERATING_PRESSURE_PA,
    maximum_operating_pressure_pa: float = DEFAULT_MAXIMUM_OPERATING_PRESSURE_PA,
    abandonment_pressure_pa: float = DEFAULT_ABANDONMENT_PRESSURE_PA,
    pipeline_pressure_pa: float = DEFAULT_PIPELINE_PRESSURE_PA,

    working_gas_volume_per_cavern_sm3: float = DEFAULT_WORKING_GAS_VOLUME_PER_CAVERN_SM3,

    maximum_withdrawal_flow_per_cavern_million_sm3_per_day: float = DEFAULT_MAXIMUM_WITHDRAWAL_FLOW_PER_CAVERN_MILLION_SM3_PER_DAY,

    last_cemented_casing_shoe_m: float = DEFAULT_LAST_CEMENTED_CASING_SHOE_M,
    drilling_complexity_index: float = DEFAULT_DRILLING_COMPLEXITY_INDEX,

    fresh_water_pipeline_length_km: float = DEFAULT_FRESH_WATER_PIPELINE_LENGTH_KM,
    brine_disposal_pipeline_length_km: float = DEFAULT_BRINE_DISPOSAL_PIPELINE_LENGTH_KM,
    
    debrining_flowrate_per_cavern_m3_per_hour: float = DEFAULT_DEBRINING_FLOWRATE_PER_CAVERN_M3_PER_HOUR,

    compression_method: CompressionMethod = DEFAULT_COMPRESSION_METHOD,

    purification_factor: float = DEFAULT_PURIFICATION_FACTOR,

    field_line_length_per_well_head_km = DEFAULT_FIELD_LINE_LENGTH_PER_WELL_HEAD_KM

) -> StorageProject:
    """Construct a complete salt cavern StorageProject.

    Primary user-facing inputs are energy capacity and injection/withdrawal
    rates. Technology-specific defaults are supplied by this module and can be
    overridden through keyword arguments.
    """

    #construct StorageInventory
    inventory = construct_storage_inventory(
        working_gas_capacity_kwh_lhv=working_gas_capacity_kwh_lhv,
        temperature_k=temperature_k,
        maximum_pressure_pa=maximum_operating_pressure_pa,
        minimum_pressure_pa=minimum_operating_pressure_pa,
        abandonment_pressure_pa=abandonment_pressure_pa,
    )

    #construct StorageFlows
    flows = construct_storage_flows(
        withdrawal_flow_kw_h2_lhv=withdrawal_flow_kw_h2_lhv,
        injection_flow_kw_h2_lhv=injection_flow_kw_h2_lhv,
    )

    #construct StoragePressures
    pressures = construct_storage_pressures(
        maximum_operating_pressure_pa=maximum_operating_pressure_pa,
        minimum_operating_pressure_pa=minimum_operating_pressure_pa,
        abandonment_pressure_pa=abandonment_pressure_pa,
        pipeline_pressure_pa=pipeline_pressure_pa,
    )

    purification = construct_purification(
        purification_factor=purification_factor
    )

    #determine number of caverns, number of well heads, and actual per cavern withdrawal requirements
    number_caverns_for_storage_capacity_requirements = ceil(inventory.working_gas_h2_volume_sm3 / working_gas_volume_per_cavern_sm3)
    number_caverns_for_withdrawal_requirements = ceil(flows.withdrawal_flow_million_sm3_per_day / maximum_withdrawal_flow_per_cavern_million_sm3_per_day)
    number_caverns = max(number_caverns_for_storage_capacity_requirements, number_caverns_for_withdrawal_requirements)
    # withdrawal_flow_per_cavern_million_sm3_per_day = flows.withdrawal_flow_million_sm3_per_day / number_caverns
    
    number_well_heads = number_caverns  #HyStories assumes one well per cavern

    #construct WellDesign
    wells = construct_well_design(
        number_well_heads=number_well_heads,
        number_caverns=number_caverns,
    )

    #construct DrillingDesign
    drilling = construct_drilling_design(
        last_cemented_casing_shoe_m=last_cemented_casing_shoe_m,
        drilling_complexity_index=drilling_complexity_index,
    )

    #construct FieldInterconnectionDesign
    field_interconnection = construct_field_interconnection_design(
        field_line_length_per_well_head_km=field_line_length_per_well_head_km,
        field_line_length_km=field_line_length_per_well_head_km*wells.number_well_heads,
    )

    #construct SaltLeachingDesign
    salt_leaching = construct_salt_leaching_design(
        free_gas_volume_per_cavern_thousand_m3=(inventory.required_storage_volume_m3 / number_caverns / 1_000 ),
        fresh_water_pipeline_length_km=fresh_water_pipeline_length_km,
        brine_disposal_pipeline_length_km=brine_disposal_pipeline_length_km,
        debrining_flowrate_per_cavern_m3_per_hour=debrining_flowrate_per_cavern_m3_per_hour,
    )

    #construct CompressionResult
    compression = calculate_compression(
        CompressionInput(
            inlet_pressure_pa=pipeline_pressure_pa,
            outlet_pressure_pa=maximum_operating_pressure_pa,
            inlet_temperature_k=temperature_k,
            mass_flow_kg_s=flows.injection_flow_kg_per_s,
            method=compression_method,
        )
    )

    #return fully defined storage project
    return StorageProject(
        technology=StorageTechnology.SALT_CAVERN,
        case_name=case_name,
        inventory=inventory,
        flows=flows,
        pressures=pressures,
        wells=wells,
        drilling=drilling,
        field_interconnection=field_interconnection,
        salt_leaching=salt_leaching,
        compression=compression,
        purification=purification
    )
