from dataclasses import dataclass
from enum import StrEnum

from uhs_costs.design.storage_inventory import StorageInventory
from uhs_costs.design.storage_flows import StorageFlows
from uhs_costs.design.storage_pressures import StoragePressures
from uhs_costs.design.well_design import WellDesign
from uhs_costs.design.site_development import (
    DrillingDesign, 
    FieldInterconnectionDesign,
    SaltLeachingDesign, 
    )
from uhs_costs.design.compression_model import CompressionResult
from uhs_costs.design.purification import Purification


class StorageTechnology(StrEnum):
    SALT_CAVERN = "salt_cavern"
    DEPLETED_GAS_FIELD = "depleted_gas_field"
    AQUIFER = "aquifer"
    LINED_ROCK_CAVERN = "lined_rock_cavern"

@dataclass(frozen=True)
class StorageProject:
    technology: StorageTechnology
    case_name: str | None
    inventory: StorageInventory 
    flows: StorageFlows
    pressures: StoragePressures
    wells: WellDesign | None = None
    drilling: DrillingDesign | None = None
    field_interconnection: FieldInterconnectionDesign | None = None
    salt_leaching: SaltLeachingDesign | None = None
    compression: CompressionResult | None = None
    purification: Purification | None = None


