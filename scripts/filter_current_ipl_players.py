"""Filter RR exploratory pressure data to IPL 2026 franchise-mapped players.

Run from the project root:
    python scripts/filter_current_ipl_players.py

IMPORTANT: This is IPL 2026 mapping membership, NOT verified current IPL 2027
retention/contract status. Do not describe outputs as a confirmed auction list.
"""
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / 'data' / 'raw'
OUT = ROOT / 'data' / 'processed' / 'rr_official'
OUT.mkdir(parents=True, exist_ok=True)

mapping = pd.read_csv(RAW / 'competition_team_player_mapping.csv', low_memory=False)
competitions = pd.read_csv(RAW / 'competitions.csv', low_memory=False)
ipl_ids = competitions.loc[
    competitions['comp_name'].astype(str).str.fullmatch(r'IPL 2026', case=False, na=False),
    'comp_id'
]
if len(ipl_ids) != 1:
    raise ValueError(f'Expected one IPL 2026 competition ID, found {len(ipl_ids)}')

ipl = mapping.loc[mapping['comp_id'].eq(ipl_ids.iloc[0]),
                  ['player_id', 'player_name', 'team_name']].copy()
ipl['player_id'] = pd.to_numeric(ipl['player_id'], errors='raise').astype('int64')
if ipl['player_id'].duplicated().any():
    conflict = ipl.loc[ipl['player_id'].duplicated(keep=False)]
    raise ValueError(f'IPL player mapped to multiple teams; review:\n{conflict}')
ipl = ipl.rename(columns={'team_name': 'ipl_2026_team',
                          'player_name': 'ipl_2026_name'})
ipl['membership_basis'] = 'Official data pack: IPL 2026 competition mapping'
ipl['current_contract_verified'] = False
ipl['auction_2027_eligible_verified'] = False
ipl.to_csv(OUT / 'ipl_2026_roster_proxy.csv', index=False)

print('IPL 2026 mapped players:', len(ipl))
print('Franchises:', ipl['ipl_2026_team'].nunique())

for discipline, id_col in [('batting', 'striker_id'), ('bowling', 'bowler_id')]:
    filename = OUT / f'pressure_{discipline}_named.csv'
    df = pd.read_csv(filename, low_memory=False)
    df[id_col] = pd.to_numeric(df[id_col], errors='coerce').astype('Int64')
    eligible = df.merge(ipl, how='inner', left_on=id_col, right_on='player_id',
                        validate='many_to_one').drop(columns=['player_id'])
    qualified = eligible['sample_qualified'].astype(str).str.lower().eq('true')
    eligible['sample_qualified'] = qualified
    eligible.to_csv(OUT / f'ipl_2026_{discipline}_pool.csv', index=False)
    if discipline == 'batting':
        sort_col, ascending = 'strike_rate_high', False
        cols = ['player_name', 'ipl_2026_team', 'matches_high',
                'balls_high', 'strike_rate_high', 'sr_change']
    else:
        sort_col, ascending = 'batter_runs_per_over_high', True
        cols = ['player_name', 'ipl_2026_team', 'matches_high',
                'legal_balls_high', 'wickets_high', 'batter_runs_per_over_high']
    leaders = eligible.loc[qualified].sort_values(sort_col, ascending=ascending)
    leaders.to_csv(OUT / f'ipl_2026_{discipline}_exploratory_leaders.csv', index=False)
    print(f'\n{discipline.upper()}: {len(eligible)} mapped, {qualified.sum()} sample-qualified')
    print(leaders[[c for c in cols if c in leaders]].head(15).to_string(index=False))

print('\nWARNING: these are exploratory rankings and historical IPL 2026 mappings.')
print('Verify current contracts/trades and improve pressure model before final submission.')
