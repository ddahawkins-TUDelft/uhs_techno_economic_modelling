"""Export quality-screened CO2StoP UHS candidates and cost-sensitivity inputs.

Reads process_co2stop.py output without modifying it.

Pressure policy:
- SA: use CO2StoP current aquifer pressure as provisional minimum, and
  CO2StoP maximum pressure as maximum (conditional screening assumptions).
- DGF: do not silently interpret CO2StoP current pressure as an abandonment
  or operating minimum pressure. Leave both fields blank and retain the
  current pressure explicitly for subsequent verification.

Run:
    python scripts/data_preparation/export_co2stop_uhs.py
"""
from __future__ import annotations

import argparse
from pathlib import Path
import pandas as pd

BASE = Path("data/processed/co2stop")
DGF_STATUSES = {"abandoned", "depleted", "suspended"}
STRICT_DGF_STATUSES = {"abandoned", "depleted"}

COLUMNS = [
    "TRAP_ID", "TRAP_NAME", "COUNTRY", "reservoir_type", "status_normalised",
    "depth_m", "current_pressure_bar", "max_pressure_bar",
    "wells_penetrating", "wells_abandoned", "pressure_quality",
    "completeness_tier", "quality_flags",
]

# Matches the supplied site-based cost sensitivity input template.
COST_COLUMNS = [
    "storage_class", "site", "country", "source_site_id",
    "depth_m_representative", "depth_low_m", "depth_high_m", "depth_basis",
    "model_abandonment_pressure_bar", "min_storage_pressure_bar",
    "max_storage_pressure_bar", "max_to_min_pressure_ratio", "pressure_basis",
    "stored_gas_or_scenario", "observed_or_modelled", "primary_source_title",
    "primary_source_doi", "primary_source_url", "secondary_source_doi",
    "secondary_source_url", "notes",
]

# Additional data that could be useful in later model/screening extensions.
EXTRA_COLUMNS = [
    "co2stop_current_pressure_bar", "co2stop_max_pressure_bar",
    "co2stop_reservoir_type", "co2stop_status", "co2stop_pressure_quality",
    "co2stop_completeness_tier", "co2stop_quality_flags",
    "co2stop_temperature_c", "co2stop_porosity", "co2stop_permeability",
    "co2stop_total_pore_volume", "co2stop_gross_thickness_m",
    "co2stop_wells_penetrating", "co2stop_wells_abandoned",
    "minimum_pressure_assumption", "requires_pressure_review",
]


def _column(df: pd.DataFrame, name: str) -> pd.Series:
    return df[name] if name in df.columns else pd.Series(pd.NA, index=df.index)


def _as_text(df: pd.DataFrame, name: str) -> pd.Series:
    return _column(df, name).fillna("").astype(str)


def build_cost_sensitivity_input(selected: pd.DataFrame) -> pd.DataFrame:
    """Map screened rows into the site's cost-sensitivity input schema."""
    output = pd.DataFrame(index=selected.index)
    for field in COST_COLUMNS + EXTRA_COLUMNS:
        output[field] = pd.NA

    is_sa = selected["uhs_kind"].eq("saline_aquifer")
    is_dgf = selected["uhs_kind"].eq("hydrocarbon_candidate")

    output["storage_class"] = ""
    output.loc[is_sa, "storage_class"] = "SA"
    output.loc[is_dgf, "storage_class"] = "DGF"
    output["site"] = _column(selected, "TRAP_NAME")
    output["country"] = _column(selected, "COUNTRY")
    output["source_site_id"] = _column(selected, "TRAP_ID")
    output["depth_m_representative"] = pd.to_numeric(_column(selected, "depth_m"), errors="coerce")
    output["depth_low_m"] = pd.to_numeric(_column(selected, "DEPTH_MIN"), errors="coerce")
    output["depth_high_m"] = pd.to_numeric(_column(selected, "DEPTH_MAX"), errors="coerce")
    output["depth_basis"] = "CO2StoP compiled representative reservoir/trap depth; verify reference datum"

    current = pd.to_numeric(_column(selected, "current_pressure_bar"), errors="coerce")
    maximum = pd.to_numeric(_column(selected, "max_pressure_bar"), errors="coerce")
    output["max_storage_pressure_bar"] = maximum

    # Only aquifers have an accepted minimum-pressure mapping at this stage.
    output.loc[is_sa, "min_storage_pressure_bar"] = current.loc[is_sa]
    output.loc[is_sa, "max_to_min_pressure_ratio"] = (
        maximum.loc[is_sa] / current.loc[is_sa]
    )
    output["pressure_basis"] = ""
    output.loc[is_sa, "pressure_basis"] = (
        "CO2StoP current brine/formation pressure used as provisional H2 Pmin; "
        "CO2StoP maximum pressure as provisional H2 Pmax"
    )
    output.loc[is_dgf, "pressure_basis"] = (
        "CO2StoP current formation pressure and maximum pressure; "
        "abandonment and H2 operating minimum pressures not verified"
    )
    output["minimum_pressure_assumption"] = ""
    output.loc[is_sa, "minimum_pressure_assumption"] = "initial_hydrostatic_as_min"
    output.loc[is_dgf, "minimum_pressure_assumption"] = "not_assigned"
    output["requires_pressure_review"] = is_dgf

    output["stored_gas_or_scenario"] = "Hypothetical pure-H2 UHS screening conversion"
    output["observed_or_modelled"] = (
        "CO2StoP compiled geological input; prospective H2 design states assumed where noted"
    )
    output["primary_source_title"] = "CO2StoP compiled geological storage assessment database"
    # Original CO2StoP source DOI/URL not populated without verified citation metadata.
    output["notes"] = [
        (
            f"CO2StoP trap {trap_id}; {kind}; status={status}; "
            f"quality_flags={flags or 'none'}; "
            + (
                "Pmin is mapped from reported current aquifer formation pressure; "
                "hydraulic feasibility and H2 pressure ceilings not verified."
                if kind == "saline_aquifer" else
                "CO2StoP current pressure is NOT assigned as abandonment or H2 Pmin; "
                "both need independent verification before DGF cost runs."
            )
        )
        for trap_id, kind, status, flags in zip(
            _as_text(selected, "TRAP_ID"), _as_text(selected, "uhs_kind"),
            _as_text(selected, "status_normalised"), _as_text(selected, "quality_flags"),
        )
    ]

    mappings = {
        "co2stop_current_pressure_bar": "current_pressure_bar",
        "co2stop_max_pressure_bar": "max_pressure_bar",
        "co2stop_reservoir_type": "reservoir_type",
        "co2stop_status": "status_normalised",
        "co2stop_pressure_quality": "pressure_quality",
        "co2stop_completeness_tier": "completeness_tier",
        "co2stop_quality_flags": "quality_flags",
        "co2stop_temperature_c": "temperature_c",
        "co2stop_porosity": "POROSITY_MEAN",
        "co2stop_permeability": "PERM_MEAN",
        "co2stop_total_pore_volume": "TOT_PORE_VOL_MEAN",
        "co2stop_gross_thickness_m": "GROSS_THICK_MEAN",
        "co2stop_wells_penetrating": "wells_penetrating",
        "co2stop_wells_abandoned": "wells_abandoned",
    }
    for target, source in mappings.items():
        output[target] = _column(selected, source)

    return output[COST_COLUMNS + EXTRA_COLUMNS].reset_index(drop=True)


def make_files(inp: Path, out: Path) -> None:
    d = pd.read_csv(inp)
    out.mkdir(parents=True, exist_ok=True)
    t = d["reservoir_type"].fillna("")
    status = d["status_normalised"].fillna("")

    oil_text = (_as_text(d, "REMARKS") + " " + _as_text(d, "TRAP_NAME")).str.contains(
        r"\boil\s+field\b|\boilfield\b", case=False, regex=True
    )
    gas_text = (_as_text(d, "REMARKS") + " " + _as_text(d, "TRAP_NAME")).str.contains(
        r"\bgas\s+field\b|\bgasfield\b", case=False, regex=True
    )
    explicit_oil_only = t.eq("oil_field") | (oil_text & ~gas_text & ~t.eq("oil_and_gas"))
    is_sa = t.eq("saline_aquifer")
    is_hc = ~is_sa & ~explicit_oil_only

    d["uhs_kind"] = "hydrocarbon_candidate"
    d.loc[is_sa, "uhs_kind"] = "saline_aquifer"
    d.loc[explicit_oil_only, "uhs_kind"] = "excluded_explicit_oil_field"
    d["eligible_expanded"] = is_sa | (is_hc & status.isin(DGF_STATUSES))
    d["eligible_strict"] = is_sa | (is_hc & status.isin(STRICT_DGF_STATUSES))

    depth = pd.to_numeric(d["depth_m"], errors="coerce")
    p0 = pd.to_numeric(d["current_pressure_bar"], errors="coerce")
    pmax = pd.to_numeric(d["max_pressure_bar"], errors="coerce")
    flags = _as_text(d, "quality_flags")
    critical = flags.str.contains(
        "aquifer_pressure_below_0p2_hydrostatic|aquifer_max_below_hydrostatic|no_pressure_headroom",
        regex=True,
    )
    d["numerically_ready"] = depth.gt(0) & p0.gt(0) & pmax.gt(p0) & ~critical

    # A DGF being 'numerically ready' in the original screen means it has
    # available geological pressures, NOT a populated DGF cost-model pressure triple.
    col = [*COLUMNS, "uhs_kind", "numerically_ready"]
    col = [x for x in col if x in d.columns]
    results = []
    for label in ("strict", "expanded"):
        eligible = d[d[f"eligible_{label}"]].copy()
        ready = eligible[eligible["numerically_ready"]].copy()
        eligible[col].to_csv(out / f"uhs_{label}_candidates.csv", index=False)
        ready[col].to_csv(out / f"uhs_{label}_numerically_ready.csv", index=False)

        compact = ready[[
            "TRAP_ID", "TRAP_NAME", "COUNTRY", "uhs_kind", "status_normalised",
            "depth_m", "current_pressure_bar", "max_pressure_bar",
            "wells_penetrating", "wells_abandoned",
        ]].copy()
        compact.to_csv(out / f"uhs_{label}_model_input.csv", index=False)

        cost_input = build_cost_sensitivity_input(ready)
        cost_input.to_csv(out / f"uhs_{label}_cost_sensitivities_input.csv", index=False)
        # Immediately runnable subset only has complete reservoir pressure
        # mapping for saline aquifers; DGF rows require manual pressure choices.
        cost_input.loc[
            cost_input["storage_class"].eq("SA")
        ].to_csv(out / f"uhs_{label}_aquifer_cost_sensitivities_input.csv", index=False)

        for subname, subset in (("eligible", eligible), ("numerically_ready", ready)):
            for kind, part in subset.groupby("uhs_kind"):
                results.append({
                    "scope": label, "selection": subname,
                    "type": kind, "records": len(part),
                })
    pd.DataFrame(results).to_csv(out / "uhs_export_summary.csv", index=False)
    print(pd.DataFrame(results).to_string(index=False))
    print("Outputs:", out)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=BASE / "reservoir_processed.csv")
    parser.add_argument("--output-dir", type=Path, default=BASE)
    args = parser.parse_args()
    make_files(args.input, args.output_dir)
