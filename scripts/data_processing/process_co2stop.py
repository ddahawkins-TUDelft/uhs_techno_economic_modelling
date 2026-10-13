"""Quality-control CO2StoP reservoir candidates without assigning H2 operating pressures.

Run from repository root:
    python scripts/data_preparation/process_co2stop.py
    python scripts/data_preparation/process_co2stop.py --input data/processed/co2stop/reservoir_candidates.csv

Outputs: reservoir_processed.csv (all traps), reservoir_model_candidates.csv
(excludes only explicitly identified oil fields), reservoir_corrections.csv,
reservoir_processing_summary.csv. Original source columns are unchanged.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import re
import numpy as np
import pandas as pd

# Ratio of measured aquifer current pressure to reference hydrostatic pressure.
# Below this: flag unusual aquifer formation pressure; Danish cases receive a documented MPa-to-bar correction.
AQUIFER_HYDROSTATIC_RATIO_THRESHOLD = 0.20
HYDROSTATIC_GRADIENT_BAR_PER_M = 0.10  # screening only; NOT exported as a diagnostic pressure
DEPTH_REVIEW_RANGE_M = (100.0, 6000.0)

NUMERIC_SOURCE = {
    'depth_m': 'DEPTH_MEAN',
    'current_pressure_bar': 'PRESSURE_MEAN',
    'max_pressure_bar': 'MAX_PRESSURE_MEAN',
    'wells_penetrating': 'NO_WELLS_PENETR',
    'wells_abandoned': 'NO_ADAND_WELL_PENETR',
}


def add_flag(flags: dict[str, list[str]], ids: pd.Series, mask: pd.Series, flag: str) -> None:
    for record_id in ids[mask.fillna(False)]:
        flags[record_id].append(flag)


def process(source: Path, output_dir: Path) -> None:
    raw = pd.read_csv(source, encoding='utf-8-sig', low_memory=False)
    required = ['TRAP_ID', 'COUNTRY', 'STATUS', 'ASSESS_UNIT_TYPE', 'REMARKS', *NUMERIC_SOURCE.values()]
    missing = sorted(set(required) - set(raw.columns))
    if missing:
        raise ValueError(f'Missing columns from compiled input: {missing}')
    if raw.TRAP_ID.isna().any() or raw.TRAP_ID.duplicated().any():
        raise ValueError('TRAP_ID must be unique and non-null')
    out = raw.copy()
    changes: list[dict] = []
    flags = {str(x): [] for x in out.TRAP_ID}
    ids = out.TRAP_ID.astype(str)

    # Preserve raw numerical columns and create validated working copies.
    for dest, src in NUMERIC_SOURCE.items():
        original = pd.to_numeric(out[src], errors='coerce')
        out[dest] = original
        if dest in {'depth_m', 'current_pressure_bar', 'max_pressure_bar'}:
            mask = original.le(0)
            out.loc[mask, dest] = np.nan
            for i in out.index[mask.fillna(False)]:
                changes.append({'TRAP_ID': out.at[i,'TRAP_ID'], 'field': dest,
                                'source_field': src, 'original_value': original.at[i],
                                'processed_value': '', 'rule': 'nonpositive_to_missing',
                                'reason': 'Nonphysical or placeholder source value; original retained'})
        else:
            mask = original.lt(0) | (original.notna() & (original % 1 != 0))
            out.loc[mask, dest] = np.nan
            for i in out.index[mask.fillna(False)]:
                changes.append({'TRAP_ID': out.at[i,'TRAP_ID'], 'field': dest,
                                'source_field': src, 'original_value': original.at[i],
                                'processed_value': '', 'rule': 'invalid_count_to_missing',
                                'reason': 'Negative/non-integer well count; original retained'})
            add_flag(flags, ids, original.isna(), f'{dest}_unreported')

    # Classification: ONLY clear oil-only fields are excluded from model candidates.
    r = out.REMARKS.fillna('').astype(str).str.casefold()
    source_kind = out.ASSESS_UNIT_TYPE.fillna('').astype(str).str.casefold()
    aquifer = source_kind.str.contains('aquifer')
    gas_name = r.str.contains(r'\bgas\s+field\s+name\s*:', regex=True)
    oil_name = r.str.contains(r'\boil\s+field\s+name\s*:', regex=True)
    mixed_explicit = r.str.contains(r'\boil\s*(?:and|&)\s*gas\b|\bgas\s*(?:and|&)\s*oil\b', regex=True)
    out['reservoir_type'] = 'hydrocarbon_unknown'
    out.loc[aquifer, 'reservoir_type'] = 'saline_aquifer'
    out.loc[~aquifer & gas_name & ~oil_name & ~mixed_explicit, 'reservoir_type'] = 'gas_field'
    out.loc[~aquifer & oil_name & ~gas_name & ~mixed_explicit, 'reservoir_type'] = 'oil_field'
    out.loc[~aquifer & (mixed_explicit | (gas_name & oil_name)), 'reservoir_type'] = 'oil_and_gas'
    out['type_evidence'] = 'no_explicit_gas_or_oil_description'
    out.loc[aquifer, 'type_evidence'] = 'aquifer_daughter_unit'
    out.loc[~aquifer & gas_name & ~oil_name, 'type_evidence'] = 'remarks_gas_field_name'
    out.loc[~aquifer & oil_name & ~gas_name, 'type_evidence'] = 'remarks_oil_field_name'
    out.loc[~aquifer & (mixed_explicit | (gas_name & oil_name)), 'type_evidence'] = 'remarks_mixed_hydrocarbons'
    out['include_model_candidate'] = out.reservoir_type.ne('oil_field')

    # The Danish aquifer pressure entries identified by the source-consistency
    # screen are reported in MPa despite the database's bar-labelled columns.
    # Apply MPa -> bar to BOTH pressure values on exactly those records.
    # This operation starts from unchanged source columns on every run.
    hyd_pre = out.depth_m * HYDROSTATIC_GRADIENT_BAR_PER_M
    danish_unit_fix = (
        out.COUNTRY.astype(str).str.casefold().eq('denmark')
        & aquifer
        & out.depth_m.gt(0)
        & out.current_pressure_bar.gt(0)
        & out.max_pressure_bar.gt(0)
        & ((out.current_pressure_bar / hyd_pre) < AQUIFER_HYDROSTATIC_RATIO_THRESHOLD)
        & (out.max_pressure_bar < hyd_pre)
    )
    for field, source_field in [('current_pressure_bar', 'PRESSURE_MEAN'),
                                ('max_pressure_bar', 'MAX_PRESSURE_MEAN')]:
        for i in out.index[danish_unit_fix]:
            previous = float(out.at[i, field])
            converted = previous * 10.0
            out.at[i, field] = converted
            changes.append({
                'TRAP_ID': out.at[i, 'TRAP_ID'], 'field': field,
                'source_field': source_field, 'original_value': previous,
                'processed_value': converted, 'rule': 'danish_aquifer_mpa_to_bar',
                'reason': 'Confirmed Danish aquifer source pressure units MPa; multiply by 10 to bar',
            })
    add_flag(flags, ids, danish_unit_fix, 'danish_pressure_units_corrected_mpa_to_bar')

    # No diagnostic pressure columns added; hydrostatic is computed locally only for flagging.
    hyd = out.depth_m * HYDROSTATIC_GRADIENT_BAR_PER_M
    aquifer_ratio = out.current_pressure_bar / hyd
    add_flag(flags, ids, aquifer & (aquifer_ratio < AQUIFER_HYDROSTATIC_RATIO_THRESHOLD), 'aquifer_pressure_below_0p2_hydrostatic')
    add_flag(flags, ids, aquifer & (aquifer_ratio > 2.0), 'aquifer_pressure_above_2x_hydrostatic')
    add_flag(flags, ids, aquifer & (out.max_pressure_bar < hyd), 'aquifer_max_below_hydrostatic')
    add_flag(flags, ids, out.current_pressure_bar.gt(out.max_pressure_bar), 'current_above_max')
    add_flag(flags, ids, out.current_pressure_bar.eq(out.max_pressure_bar), 'no_pressure_headroom')
    add_flag(flags, ids, out.depth_m.notna() & ~out.depth_m.between(*DEPTH_REVIEW_RANGE_M), 'depth_outside_review_range')

    # Compare against parents only as an independent flag. No substitution or imputation.
    for child, parent, field in [('depth_m','unit_depth_mean','depth'),
                                  ('current_pressure_bar','unit_pressure_mean','current_pressure'),
                                  ('max_pressure_bar','unit_max_pressure_mean','max_pressure')]:
        if parent in out.columns:
            p = pd.to_numeric(out[parent], errors='coerce')
            comparison = out[child].notna() & p.gt(0)
            mismatch = comparison & ((out[child] - p).abs() / np.maximum(out[child].abs(), p.abs()) > 0.5)
            add_flag(flags, ids, mismatch, f'{field}_parent_difference_over_50pct')
    out['quality_flags'] = ids.map(lambda x: ';'.join(sorted(set(flags[x]))))
    out['depth_quality'] = np.select([out.depth_m.isna(), out.quality_flags.str.contains('depth_outside')], ['missing','review'], default='valid')
    pressure_flags = r'aquifer_pressure|aquifer_max|current_above_max|no_pressure_headroom|_parent_difference_over_50pct'
    out['pressure_quality'] = np.select([
        out.current_pressure_bar.isna() | out.max_pressure_bar.isna(),
        out.quality_flags.str.contains(pressure_flags, regex=True),
    ], ['missing','review'], default='valid')
    # Well-count completeness is informational and does not affect quality grading.
    out['reservoir_quality'] = np.where(out.quality_flags.eq(''), 'no_flags', 'review_flags')
    out['completeness_tier'] = np.select([
        out.depth_m.notna() & out.current_pressure_bar.notna() & out.max_pressure_bar.notna(),
        out.depth_m.notna() & (out.current_pressure_bar.notna() | out.max_pressure_bar.notna()),
    ], ['A','B'], default='C')
    # Status is retained, but does not imply an observed abandonment pressure.
    out['abandonment_pressure_verified'] = False

    output_dir.mkdir(parents=True, exist_ok=True)
    out.to_csv(output_dir / 'reservoir_processed.csv', index=False)
    out.loc[out.include_model_candidate].to_csv(output_dir / 'reservoir_model_candidates.csv', index=False)
    audit_cols = ['TRAP_ID','field','source_field','original_value','processed_value','rule','reason']
    pd.DataFrame(changes, columns=audit_cols).to_csv(output_dir / 'reservoir_corrections.csv', index=False)
    summary = out.groupby(['COUNTRY','reservoir_type','STATUS'], dropna=False).agg(
        records=('TRAP_ID','size'),
        model_candidates=('include_model_candidate','sum'),
        complete_A=('completeness_tier', lambda s: int(s.eq('A').sum())),
        valid_depth=('depth_m',lambda s:int(s.notna().sum())),
        valid_current_pressure=('current_pressure_bar',lambda s:int(s.notna().sum())),
        valid_max_pressure=('max_pressure_bar',lambda s:int(s.notna().sum())),
        reported_well_counts=('wells_penetrating',lambda s:int(s.notna().sum())),
        flagged=('quality_flags',lambda s:int(s.ne('').sum())),
    ).reset_index()
    summary.to_csv(output_dir / 'reservoir_processing_summary.csv', index=False)
    print(f'Input: {len(out)}; model candidates (oil-only excluded): {int(out.include_model_candidate.sum())}')
    print('Reservoir classes:', out.reservoir_type.value_counts().to_dict())
    print('Completeness tiers:', out.completeness_tier.value_counts().to_dict())
    print('Danish aquifer pressure pairs converted MPa -> bar:', int(danish_unit_fix.sum()))
    print('Remaining aquifer pressure ratio flags:', out.quality_flags.str.contains('aquifer_pressure_below_0p2').sum())
    print('Source value normalisations:', len(changes))
    print(f'Wrote outputs to {output_dir}')


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, default=Path('data/processed/co2stop/reservoir_candidates.csv'))
    parser.add_argument('--output-dir', type=Path, default=Path('data/processed/co2stop'))
    args = parser.parse_args()
    process(args.input, args.output_dir)


if __name__ == '__main__':
    main()
