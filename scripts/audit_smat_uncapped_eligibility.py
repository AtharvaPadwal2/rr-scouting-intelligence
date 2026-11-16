from pathlib import Path
import re
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DIR = ROOT / 'data' / 'processed' / 'rr_official'
DIR.mkdir(parents=True, exist_ok=True)

# Verified identity aliases only. Extend manually when supported by evidence.
ALIASES = {
    'rk singh': 'Rinku Singh',
    'rm patidar': 'Rajat Patidar',
    'pp shaw': 'Prithvi Shaw',
    'am rahane': 'Ajinkya Rahane',
    'r parag': 'Riyan Parag',
    'n rana': 'Nitish Rana',
    'ss iyer': 'Shreyas Iyer',
    'p simran singh': 'Prabhsimran Singh',
    'ybk jaiswal': 'Yashasvi Jaiswal',
    'kh pandya': 'Krunal Pandya',
    'b kumar': 'Bhuvneshwar Kumar',
    'i sharma': 'Ishant Sharma',
    'jd unadkat': 'Jaydev Unadkat',
    'tu deshpande': 'Tushar Deshpande',
    'vg arora': 'Vaibhav Arora',
    'k kartikeya': 'Kumar Kartikeya',
    'sz mulani': 'Shams Mulani',
}

# IPL 2026 squad checks grounded in published roster lists, not in this SMAT file.
# This is an initial exclusion set, NOT an exhaustive current-contracted register.
KNOWN_2026_SQUAD = {
    'Rinku Singh','Rajat Patidar','Prithvi Shaw','Ajinkya Rahane',
    'Abhishek Sharma','Urvil Patel','Priyansh Arya','Riyan Parag',
    'Anuj Rawat','Sameer Rizvi','Nitish Rana','Shubman Gill',
    'Shreyas Iyer','Prabhsimran Singh','Tilak Varma','Yashasvi Jaiswal',
    'Krunal Pandya','Ravi Bishnoi','Bhuvneshwar Kumar','Suyash Sharma',
    'Ishant Sharma','Tushar Deshpande','Yash Thakur','Arjun Tendulkar',
    'Harpreet Brar','Vaibhav Arora','Jaydev Unadkat',
}

# These names require capped/retirement verification regardless of squad mapping.
KNOWN_CAPPED_REVIEW = {'Vijay Shankar', 'Shivam Dube', 'Ravichandran Ashwin'}

def norm(value):
    return re.sub(r'[^a-z0-9]+', ' ', str(value).casefold()).strip()

def load(name):
    path = DIR / name
    if not path.exists():
        raise FileNotFoundError(f'Missing {path}')
    df = pd.read_csv(path, dtype={'player_id': str}, low_memory=False)
    return df

bat = load('smat_uncapped_batting_review.csv')
bowl = load('smat_uncapped_bowling_review.csv')
roster = load('ipl_2026_roster_proxy.csv')

# Official domestic IDs are string hashes; official RR IDs are numeric.
# Never equate them directly; only supported name matches are used here.
if 'player_name' not in roster.columns:
    players = load('players_clean.csv')
    roster = roster.merge(
        players[['player_id', 'player_name']].drop_duplicates('player_id'),
        on='player_id', how='left', validate='many_to_one'
    )
roster_names = set(roster['player_name'].dropna().map(norm))
known_names = set(map(norm, KNOWN_2026_SQUAD))

registry_file = DIR / 'smat_eligibility_registry.csv'
registry = pd.read_csv(registry_file, dtype={'player_id': str}) if registry_file.exists() else pd.DataFrame()
prior = registry.set_index('player_id').to_dict('index') if 'player_id' in registry else {}

pool = pd.concat([bat[['player_id','player_name']], bowl[['player_id','player_name']]], ignore_index=True).drop_duplicates('player_id')
records = []
for p in pool.itertuples(index=False):
    pid, raw_name = str(p.player_id), str(p.player_name)
    resolved = ALIASES.get(norm(raw_name), raw_name)
    in_2026_mapping = norm(resolved) in roster_names
    in_published_2026 = norm(resolved) in known_names
    reason = ('Matched historical IPL 2026 roster mapping' if in_2026_mapping else
              'Found in published IPL 2026 squad; check subsequent releases/trades' if in_published_2026 else
              'No 2026 roster match; absence does not establish free-agent status')
    old = prior.get(pid, {})
    # No automatic designation of free agent or uncapped.
    indian = str(old.get('indian_status', 'REVIEW')).upper().strip()
    uncapped = str(old.get('uncapped_status', 'REVIEW')).upper().strip()
    unattached = str(old.get('unattached_status', 'REVIEW')).upper().strip()
    evidence_url = str(old.get('evidence_url', '')).strip()
    note = str(old.get('verification_note', '')).strip()
    if in_2026_mapping or in_published_2026:
        status = 'EXCLUDE_PENDING_UPDATED_CONTRACT_CHECK'
    elif indian == uncapped == unattached == 'YES' and evidence_url not in ('', 'nan'):
        status = 'VERIFIED_ELIGIBLE_BY_MANUAL_REVIEW'
    else:
        status = 'REVIEW'
    if resolved in KNOWN_CAPPED_REVIEW and status == 'REVIEW':
        reason += '; check historical caps and applicable 2027 IPL classification'
    records.append({
        'player_id': pid, 'smat_name': raw_name, 'resolved_name': resolved,
        'ipl_2026_roster_match': in_2026_mapping,
        'published_2026_squad_match': in_published_2026,
        'indian_status': indian if indian in {'YES','NO','REVIEW'} else 'REVIEW',
        'uncapped_status': uncapped if uncapped in {'YES','NO','REVIEW'} else 'REVIEW',
        'unattached_status': unattached if unattached in {'YES','NO','REVIEW'} else 'REVIEW',
        'evidence_url': '' if evidence_url == 'nan' else evidence_url,
        'verification_note': '' if note == 'nan' else note,
        'reason': reason, 'screening_status': status,
    })

audit = pd.DataFrame(records)
audit_path = DIR / 'smat_uncapped_identity_audit.csv'
audit.to_csv(audit_path, index=False)

# Save registry using original column names so the earlier script continues working.
new_registry = audit.rename(columns={'smat_name':'player_name'})[
    ['player_id','player_name','resolved_name','indian_status','uncapped_status',
     'unattached_status','evidence_url','verification_note']
]
new_registry.to_csv(registry_file, index=False)

for role, frame in [('batting', bat), ('bowling', bowl)]:
    result = frame.drop(columns=['indian_status','uncapped_status','unattached_status','eligibility_status'], errors='ignore').merge(
        audit[['player_id','resolved_name','screening_status','reason']],
        on='player_id', how='left', validate='many_to_one'
    )
    review = result[result['screening_status'] == 'REVIEW'].sort_values('scouting_score', ascending=False)
    verified = result[result['screening_status'] == 'VERIFIED_ELIGIBLE_BY_MANUAL_REVIEW'].sort_values('scouting_score', ascending=False)
    result.to_csv(DIR / f'smat_{role}_eligibility_audit.csv', index=False)
    review.to_csv(DIR / f'smat_{role}_manual_review.csv', index=False)
    verified.to_csv(DIR / f'smat_{role}_verified.csv', index=False)
    print(f'\n=== {role.upper()} — NEEDS CONTRACT/CAP VERIFICATION ===')
    print(review[['resolved_name','teams','scouting_score']].head(20).round(2).to_string(index=False))
    print(f'Full pool: {len(result)} | Need review: {len(review)} | Manually verified: {len(verified)}')

print('Do not label REVIEW players as uncapped or unattached.')
print('2026 squad membership is an exclusion proxy; use newer transfers/releases for final status.')
