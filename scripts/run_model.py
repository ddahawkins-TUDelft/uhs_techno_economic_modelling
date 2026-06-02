from pathlib import Path

import pandas as pd

from uhs_costs.io import read_yaml
from uhs_costs.old.model import calculate_storage_technology_case


ROOT = Path(__file__).resolve().parents[1]


def main():
    financial = read_yaml(ROOT / "config" / "financial.yaml")
    technologies = read_yaml(ROOT / "config" / "technologies.yaml")
    scenarios = read_yaml(ROOT / "config" / "scenarios.yaml")

    results = []

    for technology_id, technology in technologies.items():
        for scenario_id, scenario in scenarios.items():
            result = calculate_storage_technology_case(
                technology=technology,
                scenario=scenario,
                financial=financial,
            )

            result["technology_id"] = technology_id
            result["technology_name"] = technology["name"]
            result["scenario_id"] = scenario_id

            results.append(result)

    df = pd.DataFrame(results)

    output_path = ROOT / "outputs" / "tables" / "storage_cost_summary.csv"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False)

    print(df)
    print(f"\nSaved results to: {output_path}")


if __name__ == "__main__":
    main()