import uhs_costs.cost_model.surface_capex
import uhs_costs.cost_model.subsurface_capex
import uhs_costs.cost_model.surface_opex
import uhs_costs.cost_model.subsurface_opex
import uhs_costs.cost_model.default_cost_assumptions
import uhs_costs.cost_model.abex

from dataclasses import dataclass
from enum import StrEnum

class CostDriver(StrEnum):
    INJECTION = "injection_capacity_kw"
    STORAGE = "storage_capacity_kWh"
    WITHDRAWAL = "withdrawal_capacity_kw"

    INJECTION_THROUGHPUT_KWH = "injection_throughput_kwh"
    WITHDRAWAL_THROUGHPUT_KWH = "withdrawal_throughput_kwh"

class CostUnit(StrEnum):
    EUR_PER_KW = "EUR/kW"
    EUR_PER_KWH = "EUR/kWh"
    EUR_PER_KW_YEAR = "EUR/kW/year"
    EUR_PER_KWH_YEAR = "EUR/kWh/year"

class AllocationMethod(StrEnum):
    DIRECT = "direct"
    EQUAL_SPLIT = "equal_split"
    WEIGHTED_SPLIT = "weighted_split"

class HyStoriesGroup(StrEnum):
    SURFACE = "surface"
    SUBSURFACE = "subsurface"

class CostType(StrEnum):
    CAPEX = "capex"
    FIXED_OPEX = "fixed_opex"
    VARIABLE_OPEX = "variable_opex"
    ABEX = "abex"

@dataclass(frozen=True)
class CostComponent:
    name: str
    value_eur: float

    cost_type: CostType
    hystories_group: HyStoriesGroup

    cost_driver: CostDriver
    driver_value: float 

    cost_unit: CostUnit

    allocation_method: AllocationMethod | None = None
    allocation_share: float | None = None

    notes: str | None = None

@dataclass(frozen=True)
class CostBreakdown:
    components: tuple[CostComponent, ...]

    @property
    def total_eur(self) -> float:
        return sum(component.value_eur for component in self.components)

    def total_by_hystories_group(self, group: HyStoriesGroup) -> float:
        return sum(
            component.value_eur
            for component in self.components
            if component.hystories_group == group
        )

    def total_by_cost_type(self, cost_type: CostType) -> float:
        return sum(
            component.value_eur
            for component in self.components
            if component.cost_type == cost_type
        )
       
    def cost_per_unit_driver(self, cost_driver: CostDriver, driver_value: float) -> float:
            
        return sum(
                component.value_eur
                for component in self.components
                if component.cost_driver == cost_driver
            ) / driver_value
    
    
#Helper for splitting out fixed components
def fixed_component_cost_allocation(
    name: str,
    value_eur: float,
    cost_type: CostType,
    hystories_group: HyStoriesGroup,
    cost_drivers_and_values: tuple[tuple[CostDriver, float], ...],
    cost_unit: CostUnit,
    allocation_method: AllocationMethod,
) -> tuple[CostComponent, ...]:
    """Allocate a fixed cost component across one or more cost drivers."""

    if value_eur < 0:
        raise ValueError("value_eur cannot be negative.")

    if len(cost_drivers_and_values) == 0:
        raise ValueError("cost_drivers_and_values cannot be empty.")

    for cost_driver, driver_value in cost_drivers_and_values:
        if driver_value <= 0:
            raise ValueError(
                f"driver_value for {cost_driver} must be positive."
            )

    if allocation_method == AllocationMethod.DIRECT:
        if len(cost_drivers_and_values) != 1:
            raise ValueError(
                "DIRECT allocation is only valid for exactly one cost driver."
            )

        allocation_shares = (1.0,)

    elif allocation_method == AllocationMethod.EQUAL_SPLIT:
        allocation_shares = tuple(
            1 / len(cost_drivers_and_values)
            for _ in cost_drivers_and_values
        )

    elif allocation_method == AllocationMethod.WEIGHTED_SPLIT:
        total_driver_value = sum(
            driver_value
            for _, driver_value in cost_drivers_and_values
        )

        allocation_shares = tuple(
            driver_value / total_driver_value
            for _, driver_value in cost_drivers_and_values
        )

    else:
        raise ValueError(
            f"{allocation_method} is not a valid allocation method for component {name}."
        )

    components: list[CostComponent] = []

    for (cost_driver, driver_value), allocation_share in zip(
        cost_drivers_and_values,
        allocation_shares,
        strict=True,
    ):
        components.append(
            CostComponent(
                name=f"{name}_{cost_driver.value}_allocation",
                value_eur=value_eur * allocation_share,
                cost_type=cost_type,
                hystories_group=hystories_group,
                cost_driver=cost_driver,
                driver_value=driver_value,
                allocation_method=allocation_method,
                cost_unit=cost_unit,
                allocation_share=allocation_share,
                notes=(
                    f"HyStories {name} component allocated to {cost_driver.value} "
                    f"using {allocation_method.value}."
                ),
            )
        )

    return tuple(components)