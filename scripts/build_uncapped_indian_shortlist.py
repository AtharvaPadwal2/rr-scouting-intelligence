from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'data' / 'processed' / 'rr_official'
DATA.mkdir(parents=True, exist_ok=True)

REGISTRY = DATA / 'uncapped_indian_eligibility_registry.csv'
FIELDS = ['player_id', 'player_name', 'indian_status', 'uncapped_status',
          'unattached_status', 'registration_status', 'evidence_url', 'verified_on', 'notes']


def read_candidates(filename, role):
    path = DATA / filename
    if not path.exists():
        raise FileNotFoundError(f'Missing {path}; first run screen_auction_candidates.py')
    df = pd.read_csv(path, low_memory=False)
    needed = {'player_id', 'player_name', 'adjusted_score'}
    if not needed.issubset(df):
        raise ValueError(f'{filename} missing {sorted(needed - set(df))}')
    if 'screening_status' in df:
        df = df.loc[~df['screening_status'].eq('EXCLUDE')].copy()
    df['player_id'] = pd.to_numeric(df['player_id'], errors='coerce').astype('Int64')
    df = df.dropna(subset=['player_id']).copy()
    df['role'] = role
    return df

bat = read_candidates('batting_auction_eligibility_audit.csv', 'batting')
bowl = read_candidates('bowling_auction_eligibility_audit.csv', 'bowling')

identities = pd.concat([bat[['player_id', 'player_name']],
                        bowl[['player_id', 'player_name']]], ignore_index=True)
identities = identities.drop_duplicates('player_id')

if REGISTRY.exists():
    previous = pd.read_csv(REGISTRY, dtype={'player_id': 'Int64'}).drop_duplicates('player_id')
    keep = [c for c in FIELDS if c in previous and c != 'player_name']
    registry = identities.merge(previous[keep], on='player_id', how='left', validate='one_to_one')
else:
    registry = identities.copy()

for field in FIELDS:
    if field not in registry:
        registry[field] = pd.NA
for field in ['indian_status', 'uncapped_status', 'unattached_status', 'registration_status']:
    registry[field] = registry[field].fillna('REVIEW').astype(str).str.strip().str.upper()
for field in ['evidence_url', 'verified_on', 'notes']:
    registry[field] = registry[field].fillna('')

registry = registry[FIELDS].sort_values('player_name')
registry.to_csv(REGISTRY, index=False)

# Verified means all three eligibility conditions have independently been checked.
# Registration may remain REVIEW before the IPL 2027 auction list is published.
verified_ids = registry.loc[
    registry[['indian_status', 'uncapped_status', 'unattached_status']].eq('YES').all(axis=1)
    & registry['evidence_url'].astype(str).str.strip().ne(''), 'player_id'
]
review_ids = registry.loc[
    ~registry[['indian_status', 'uncapped_status', 'unattached_status']].eq('NO').any(axis=1),
    'player_id'
]

for role, source in [('batting', bat), ('bowling', bowl)]:
    joined = source.merge(registry[FIELDS].drop(columns='player_name'),
                          on='player_id', how='left', validate='many_to_one')
    review = joined.loc[joined['player_id'].isin(review_ids)].copy()
    review = review.sort_values(['adjusted_score', 'player_name'], ascending=[False, True])
    review.insert(0, 'review_rank', range(1, len(review) + 1))
    review.to_csv(DATA / f'uncapped_indian_{role}_review.csv', index=False)

    verified = review.loc[review['player_id'].isin(verified_ids)].copy()
    verified = verified.drop(columns='review_rank')
    verified.insert(0, 'verified_rank', range(1, len(verified) + 1))
    verified.to_csv(DATA / f'uncapped_indian_{role}_verified.csv', index=False)

    cols = ['review_rank', 'player_name', 'adjusted_score',
            'indian_status', 'uncapped_status', 'unattached_status']
    print(f'\n=== {role.upper()} — REVIEW TOP 20 (NOT VERIFIED) ===')
    print(review[cols].head(20).round(2).to_string(index=False))
    print(f'Review pool: {len(review)} | Verified eligible: {len(verified)}')

print(f'\nEditable verification registry: {REGISTRY}')
print('Update eligibility to YES/NO only when supported by evidence.')
print('A missing IPL 2026 roster mapping is NOT proof of being unattached.')
print('Current pressure scores remain exploratory and are not official auction rankings.')
