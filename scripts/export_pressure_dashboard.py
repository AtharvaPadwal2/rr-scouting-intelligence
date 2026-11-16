from pathlib import Path
import json
import math
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'data' / 'processed' / 'rr_official'
FRONTEND = ROOT / 'frontend'

if (FRONTEND / 'src' / 'app').is_dir():
    APP = FRONTEND / 'src' / 'app'
elif (FRONTEND / 'app').is_dir():
    APP = FRONTEND / 'app'
else:
    raise SystemExit('Next.js app directory not found: expected frontend/app or frontend/src/app')

OUT = FRONTEND / 'public' / 'data'
OUT.mkdir(parents=True, exist_ok=True)

FILES = {
    'batting': DATA / 'pressure_batting_reliability.csv',
    'bowling': DATA / 'pressure_bowling_reliability.csv',
}

mix_paths = {
    'batting': DATA / 'batting_competition_mix.csv',
    'bowling': DATA / 'bowling_competition_mix.csv',
}

roster_path = DATA / 'ipl_2026_roster_proxy.csv'
roster_count = int(pd.read_csv(roster_path)['player_id'].nunique()) if roster_path.exists() else None


def safe_float(value, fallback=0.0):
    try:
        result = float(value)
        return result if math.isfinite(result) else fallback
    except (ValueError, TypeError):
        return fallback


def make_players(group):
    path = FILES[group]
    if not path.exists():
        raise SystemExit(f'Missing data file: {path}. Run analyze_ranking_reliability.py first.')

    frame = pd.read_csv(path, low_memory=False)
    required = {'player_id', 'player_name', 'base_rank', 'base_adjusted_score',
                'balls', 'matches', 'positive_match_pct', 'top_10_scenario_pct'}
    missing = required.difference(frame.columns)
    if missing:
        raise SystemExit(f'{path.name} missing columns: {sorted(missing)}')

    frame = frame.sort_values('base_rank').copy()
    frame['impact_percentile'] = frame['base_adjusted_score'].rank(pct=True).mul(100)

    ipl_share = {}
    mix_path = mix_paths[group]
    if mix_path.exists():
        mix = pd.read_csv(mix_path, low_memory=False)
        key = 'striker_id' if group == 'batting' else 'bowler_id'
        if {key, 'comp_name', 'deliveries'}.issubset(mix.columns):
            mix['deliveries'] = pd.to_numeric(mix['deliveries'], errors='coerce').fillna(0)
            mix['is_ipl'] = mix['comp_name'].fillna('').astype(str).str.fullmatch(r'IPL 20\d{2}', case=False)
            total = mix.groupby(key)['deliveries'].sum()
            ipl = mix[mix['is_ipl']].groupby(key)['deliveries'].sum()
            ipl_share = (ipl / total.replace(0, float('nan')) * 100).fillna(0).to_dict()

    result = []
    for row in frame.to_dict('records'):
        pid = int(row['player_id'])
        impact = safe_float(row['impact_percentile'])
        consistency = safe_float(row['positive_match_pct'])
        stability = safe_float(row['top_10_scenario_pct'])
        balls = int(safe_float(row['balls']))
        matches = int(safe_float(row['matches']))
        axes = [
            {'axis': 'Impact', 'value': round(impact, 1)},
            {'axis': 'Consistency', 'value': round(max(0, min(100, consistency)), 1)},
            {'axis': 'Delivery confidence', 'value': round(100 * balls / (balls + 120), 1)},
            {'axis': 'Match breadth', 'value': round(100 * min(matches / 30, 1), 1)},
            {'axis': 'Rank stability', 'value': round(max(0, min(100, stability)), 1)},
        ]
        player = {
            'id': str(pid), 'name': str(row['player_name']),
            'team': str(row.get('ipl_2026_team') or 'Unknown'),
            'role': group, 'rank': int(safe_float(row['base_rank'])),
            'adjustedScore': round(safe_float(row['base_adjusted_score']), 2),
            'balls': balls, 'matches': matches,
            'positiveMatchPct': round(consistency, 2),
            'top10StabilityPct': round(stability, 2),
            'iplEvidencePct': round(safe_float(ipl_share.get(pid)), 1) if ipl_share else None,
            'radar': axes,
        }
        result.append(player)
    return result

batting = make_players('batting')
bowling = make_players('bowling')
payload = {
    'meta': {
        'title': 'RR Pressure Intelligence',
        'methodology': 'Structural-pressure exploratory analysis; not verified game pressure or current contract availability.',
        'batters': len(batting), 'bowlers': len(bowling),
        'ipl2026MappedPlayers': roster_count,
    },
    'batting': batting,
    'bowling': bowling,
}
path = OUT / 'pressure-overview.json'
path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding='utf-8')
print('Exported:', path)
print('Next.js app directory:', APP)
print('Batters:', len(batting), '| Bowlers:', len(bowling))
print('Open: http://localhost:3000/dashboard/pressure-intelligence')
