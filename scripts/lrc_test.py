from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable
from typing import Any

from uhs_costs.design.lined_rock_cavern import construct_project

from uhs_costs.cost_model.lined_rock_cavern import calculate_lined_rock_cavern_cost_components

def main() -> None:
    lrc_project = construct_project(
        working_gas_capacity_kwh_lhv=700_000_000,
        withdrawal_flow_kw_h2_lhv=3_000_000,
        injection_flow_kw_h2_lhv=1_500_000,
        case_name="lrc",
    )

    # print(lrc_project)

    lrc_cost_breakdown = calculate_lined_rock_cavern_cost_components(lrc_project)

    print(lrc_cost_breakdown)



if __name__ == "__main__":
    main()