"""Compile a traceable, incomplete CO2StoP reservoir screening dataset.

Run from the repository root:
    python scripts/data_preparation/compile_co2stop.py
    python scripts/data_preparation/compile_co2stop.py --input-dir data/resources/co2stop \
        --output-dir data/processed/co2stop

Requires pandas. Does not impute missing data or assign hydrogen operating pressures.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

CORE = {
    "traps": "Hydrocarbon_Traps.csv",
    "units": "Hydrocarbon_Storage_Units.csv",
    "formations": "Hydrocarbon_Formations.csv",
}
OPTIONAL = {
    "status": ("Dic_Status.csv", "Status", "STATUS"),
    "trap_type": ("Dic_Assess_TrapType.csv", "Type", "ASSESS_UNIT_TYPE"),
    "unit_type": ("Dic_Assess_Type.csv", "Type", "ASSESS_UNIT_TYPE"),
    "content": ("Dic_Content.csv", "Content", None),
}

TRAP_COLUMNS = [
    "TRAP_ID", "STORAGE_UNIT_ID", "TRAP_NAME", "COUNTRY", "COUNTRYCODE",
    "ASSESS_UNIT_TYPE", "STATUS", "DISCOV_YR", "FIRST_YR_PROD", "LAST_YR_PROD",
    "DEPTH_MIN", "DEPTH_MEAN", "DEPTH_MAX",
    "PRESSURE_MIN", "PRESSURE_MEAN", "PRESSURE_MAX",
    "MAX_PRESSURE_MIN", "MAX_PRESSURE_MEAN", "MAX_PRESSURE_MAX",
    "TEMP_C_MEAN", "SALINITY_BRINE", "NO_WELLS_PENETR",
    "NO_ADAND_WELL_PENETR", "PERM_MEAN", "POROSITY_MEAN",
    "TOT_PORE_VOL_MEAN", "GROSS_THICK_MEAN", "LITHOLOGY", "SEAL",
    "EST_CAP_ENT_PRESS", "MIN_SEAL_THICK", "REMARKS",
    "MIN_UR_GAS", "MEAN_UR_GAS", "MAX_UR_GAS",
    "MIN_UR_OIL", "MEAN_UR_OIL", "MAX_UR_OIL",
]
UNIT_COLUMNS = [
    "STORAGE_UNIT_ID", "FORMATION_ID", "STORAGE_UNIT_NAME",
    "ASSESS_UNIT_TYPE", "DEPTH_MEAN", "PRESSURE_MEAN",
    "MAX_PRESSURE_MEAN", "TEMP_C_MEAN", "NO_WELLS_PENETR",
    "NO_ADAND_WELL_PENETR", "REMARKS",
]
FORMATION_COLUMNS = [
    "FORMATION_ID", "FORMATION_NAME", "GEOLOGICAL_BASIN", "ON_OFFSHOR",
    "ASSESS_UNIT_TYPE", "REMARKS",
]
NUMERIC_COLUMNS = [
    "DEPTH_MIN", "DEPTH_MEAN", "DEPTH_MAX", "PRESSURE_MIN", "PRESSURE_MEAN",
    "PRESSURE_MAX", "MAX_PRESSURE_MIN", "MAX_PRESSURE_MEAN", "MAX_PRESSURE_MAX",
    "TEMP_C_MEAN", "NO_WELLS_PENETR", "NO_ADAND_WELL_PENETR",
    "PERM_MEAN", "POROSITY_MEAN", "TOT_PORE_VOL_MEAN", "GROSS_THICK_MEAN",
    "EST_CAP_ENT_PRESS", "MIN_SEAL_THICK", "MIN_UR_GAS", "MEAN_UR_GAS",
    "MAX_UR_GAS", "MIN_UR_OIL", "MEAN_UR_OIL", "MAX_UR_OIL",
]


def read_csv(path: Path) -> pd.DataFrame:
    if not path.is_file():
        raise FileNotFoundError(f"Missing required input: {path}")
    return pd.read_csv(path, encoding="utf-8-sig", low_memory=False)


def select_columns(df: pd.DataFrame, columns: list[str], label: str) -> pd.DataFrame:
    missing = sorted(set(columns) - set(df.columns))
    if missing:
        raise ValueError(f"{label} missing expected columns: {missing}")
    return df.loc[:, columns].copy()


def assert_unique(df: pd.DataFrame, key: str, label: str) -> None:
    if df[key].isna().any() or df[key].duplicated().any():
        raise ValueError(f"{label} must have unique, non-null {key} values")


def validate_dictionary(path: Path, value_col: str, observed: pd.Series, name: str) -> None:
    if not path.exists():
        print(f"NOTE: optional lookup not found: {path.name}")
        return
    dictionary = read_csv(path)
    if value_col not in dictionary:
        print(f"WARNING: {path.name} lacks {value_col}")
        return
    known = set(dictionary[value_col].dropna().astype(str).str.strip().str.casefold())
    found = set(observed.dropna().astype(str).str.strip().str.casefold())
    unexpected = sorted(found - known)
    if unexpected:
        print(f"NOTE: {name} has values not in {path.name}: {unexpected}")


def compile_data(input_dir: Path, output_dir: Path) -> None:
    raw = {name: read_csv(input_dir / file) for name, file in CORE.items()}
    traps = select_columns(raw["traps"], TRAP_COLUMNS, "traps")
    units = select_columns(raw["units"], UNIT_COLUMNS, "storage units")
    formations = select_columns(raw["formations"], FORMATION_COLUMNS, "formations")
    assert_unique(traps, "TRAP_ID", "Traps")
    assert_unique(units, "STORAGE_UNIT_ID", "Storage units")
    assert_unique(formations, "FORMATION_ID", "Formations")

    # Parent values are preserved with explicit prefixes and never substituted
    # into a missing trap measurement.
    units = units.rename(columns={
        col: f"unit_{col.lower()}" for col in UNIT_COLUMNS if col != "STORAGE_UNIT_ID"
    })
    formations = formations.rename(columns={
        col: f"formation_{col.lower()}" for col in FORMATION_COLUMNS if col != "FORMATION_ID"
    })
    result = traps.merge(units, on="STORAGE_UNIT_ID", how="left", validate="many_to_one", indicator="_unit_join")
    result = result.merge(
        formations, left_on="unit_formation_id", right_on="FORMATION_ID",
        how="left", validate="many_to_one", indicator="_formation_join",
    )
    if len(result) != len(traps):
        raise RuntimeError("Unexpected row count change during joins")

    # Keep original reported values, including zeros; flags are *not* corrections.
    for col in NUMERIC_COLUMNS:
        result[col] = pd.to_numeric(result[col], errors="coerce")
    for col in ("unit_depth_mean", "unit_pressure_mean", "unit_max_pressure_mean"):
        result[col] = pd.to_numeric(result[col], errors="coerce")

    kind = result["ASSESS_UNIT_TYPE"].fillna("").astype(str).str.casefold()
    result["reservoir_class"] = "unclassified"
    result.loc[kind.str.contains("hydrocarbon"), "reservoir_class"] = "hydrocarbon_trap"
    result.loc[kind.str.contains("aquifer"), "reservoir_class"] = "aquifer_trap"
    # This is *not* a DGF vs oil classification.
    status = result["STATUS"].fillna("Unspecified").astype(str).str.strip()
    result["status_normalised"] = status.str.casefold().str.replace(r"\s+", " ", regex=True)
    result["is_depleted_or_abandoned"] = result["status_normalised"].isin(["depleted", "abandoned"])
    result["is_abandoned"] = result["status_normalised"].eq("abandoned")

    for col, label in [
        ("DEPTH_MEAN", "depth"), ("PRESSURE_MEAN", "current_pressure"),
        ("MAX_PRESSURE_MEAN", "max_pressure")
    ]:
        result[f"has_{label}"] = result[col].gt(0)
        result[f"zero_{label}_reported"] = result[col].eq(0)
    result["complete_pressure_depth"] = (
        result["has_depth"] & result["has_current_pressure"] & result["has_max_pressure"]
    )
    result["has_depth_and_max_pressure"] = result["has_depth"] & result["has_max_pressure"]
    result["current_exceeds_max"] = (
        result["has_current_pressure"] & result["has_max_pressure"]
        & (result["PRESSURE_MEAN"] > result["MAX_PRESSURE_MEAN"])
    )
    result["pressure_depth_ratio_bar_per_m"] = (
        result["PRESSURE_MEAN"].where(result["has_current_pressure"])
        / result["DEPTH_MEAN"].where(result["has_depth"])
    )
    # Review flag only; low pressures may be entirely valid in depleted gas fields.
    result["aquifer_low_pressure_review"] = (
        result["reservoir_class"].eq("aquifer_trap")
        & result["pressure_depth_ratio_bar_per_m"].lt(0.05)
    )
    result["depth_max_below_min"] = (
        result["DEPTH_MIN"].gt(0) & result["DEPTH_MAX"].gt(0)
        & result["DEPTH_MAX"].lt(result["DEPTH_MIN"])
    )
    result["pressure_review_needed"] = (
        result["current_exceeds_max"] | result["aquifer_low_pressure_review"]
    )
    # Current pressure is not automatically promoted to abandonment pressure.
    result["current_pressure_interpretation"] = "current reported pressure; abandonment unverified"
    result.loc[result["is_depleted_or_abandoned"], "current_pressure_interpretation"] = (
        "depleted/abandoned status; potential abandonment pressure, verify source"
    )

    for key, (filename, value_col, observed_col) in OPTIONAL.items():
        if observed_col:
            series = result[observed_col] if key != "unit_type" else result["unit_assess_unit_type"]
            validate_dictionary(input_dir / filename, value_col, series, key)
        elif not (input_dir / filename).exists():
            print(f"NOTE: optional lookup not found: {filename}")
    output_dir.mkdir(parents=True, exist_ok=True)
    for col in ["REMARKS", "unit_remarks", "formation_remarks"]:
        result[col] = result[col].str.replace(r"[\r\n]+", " ", regex=True)
    result.to_csv(output_dir / "reservoir_candidates.csv", index=False)

    def stats(frame: pd.DataFrame) -> dict[str, object]:
        return {
            "n_traps": len(frame),
            "n_depth": int(frame["has_depth"].sum()),
            "n_current_pressure": int(frame["has_current_pressure"].sum()),
            "n_max_pressure": int(frame["has_max_pressure"].sum()),
            "n_depth_and_max": int(frame["has_depth_and_max_pressure"].sum()),
            "n_all_three": int(frame["complete_pressure_depth"].sum()),
            "n_well_count_present": int(frame["NO_WELLS_PENETR"].notna().sum()),
            "n_unit_joined": int(frame["_unit_join"].eq("both").sum()),
            "n_formation_joined": int(frame["_formation_join"].eq("both").sum()),
            "n_current_gt_max": int(frame["current_exceeds_max"].sum()),
            "n_aquifer_low_pressure_review": int(frame["aquifer_low_pressure_review"].sum()),
        }

    summary_rows = []
    for dimension in ("overall", "reservoir_class", "status_normalised", "COUNTRYCODE"):
        groups = [("all", result)] if dimension == "overall" else result.groupby(dimension, dropna=False)
        for value, part in groups:
            summary_rows.append({"group_by": dimension, "group": value, **stats(part)})
    summary = pd.DataFrame(summary_rows)
    summary.to_csv(output_dir / "reservoir_quality_summary.csv", index=False)
    print(f"Input: {len(traps)} traps, {len(raw['units'])} units, {len(raw['formations'])} formations")
    print(f"Joined parent units: {stats(result)['n_unit_joined']}; formations: {stats(result)['n_formation_joined']}")
    print(f"Complete depth/current/max: {stats(result)['n_all_three']}")
    print(f"Review flags: {stats(result)['n_current_gt_max']} current > max, "
          f"{stats(result)['n_aquifer_low_pressure_review']} low-pressure aquifers")
    print(f"Wrote {output_dir / 'reservoir_candidates.csv'}")
    print(f"Wrote {output_dir / 'reservoir_quality_summary.csv'}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-dir", type=Path, default=Path("data/resources/co2stop"))
    parser.add_argument("--output-dir", type=Path, default=Path("data/processed/co2stop"))
    args = parser.parse_args()
    compile_data(args.input_dir, args.output_dir)


if __name__ == "__main__":
    main()
