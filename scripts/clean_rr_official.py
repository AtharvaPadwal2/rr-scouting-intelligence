
from pathlib import Path
import json
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
OUT = ROOT / "data" / "processed" / "rr_official"
REPORT = ROOT / "data" / "reports" / "rr_official"

OUT.mkdir(parents=True, exist_ok=True)
REPORT.mkdir(parents=True, exist_ok=True)

FILES = [
    "ball_by_ball.csv",
    "matches.csv",
    "playing_eleven.csv",
    "competition_team_player_mapping.csv",
    "teams.csv",
    "competitions.csv",
]

print("\n=== RR OFFICIAL DATA CLEANING ===")

# ----------------------------------------
# 1. Load and validate input files
# ----------------------------------------
missing = [f for f in FILES if not (RAW / f).is_file()]

if missing:
    raise FileNotFoundError(
        f"Missing files in {RAW}: {missing}"
    )

data = {
    name: pd.read_csv(RAW / name, low_memory=False)
    for name in FILES
}

balls = data["ball_by_ball.csv"].copy()
matches = data["matches.csv"].copy()
players = data["competition_team_player_mapping.csv"].copy()
competitions = data["competitions.csv"].copy()
teams = data["teams.csv"].copy()
playing_xi = data["playing_eleven.csv"].copy()

required_ball_cols = [
    "match_id", "innings", "overid",
    "over_ball_num", "innings_ball_num",
    "batting_team_id", "bowling_team_id",
    "striker_id", "bowler_id", "runs",
    "extras_type", "extras1_runs",
    "extras_2_runs", "dismissal_type",
    "is_wicket",
]

for col in required_ball_cols:
    if col not in balls.columns:
        raise ValueError(f"Missing delivery column: {col}")

print("\n=== INPUT ROW COUNTS ===")
for name, df in data.items():
    print(f"{name}: {len(df):,}")

original_rows = len(balls)
exact_duplicates = int(balls.duplicated().sum())

# Save duplicate evidence rather than silently
# discarding records.
if exact_duplicates:
    balls[balls.duplicated(keep=False)].to_csv(
        REPORT / "exact_duplicate_deliveries.csv",
        index=False
    )
    balls = balls.drop_duplicates().copy()

# ----------------------------------------
# 2. Standardize IDs and dates
# ----------------------------------------
id_columns = [
    "match_id", "innings", "overid",
    "over_ball_num", "innings_ball_num",
    "batting_team_id", "bowling_team_id",
    "striker_id", "non_striker_id",
    "bowler_id", "dismissed_player_id",
]

for col in id_columns:
    if col in balls:
        balls[col] = pd.to_numeric(
            balls[col], errors="coerce"
        ).astype("Int64")

for col in ["runs", "extras_2_runs"]:
    balls[col] = pd.to_numeric(
        balls[col], errors="coerce"
    )

balls["delivery_ist_time"] = pd.to_datetime(
    balls["delivery_ist_time"],
    errors="coerce",
    utc=True
)

matches["match_date"] = pd.to_datetime(
    matches["match_date"], errors="coerce"
)

# ----------------------------------------
# 3. Normalize extras classifications
# ----------------------------------------
balls["extras_type_clean"] = (
    balls["extras_type"]
    .astype("string")
    .str.lower()
    .str.strip()
)

extras_map = {
    "wide": "wide",
    "overstep": "no_ball",
    "legbyes": "leg_byes",
    "byes": "byes",
    "other": "other",
    "penalty": "penalty",
}

balls["extras_category"] = (
    balls["extras_type_clean"]
    .map(extras_map)
    .fillna("none")
)

balls["is_wide"] = (
    balls["extras_category"] == "wide"
)

balls["is_no_ball"] = (
    balls["extras_category"] == "no_ball"
)

# This is provisional until delivery sequence
# and official scorecards are reconciled.
balls["legal_ball_candidate"] = ~(
    balls["is_wide"] | balls["is_no_ball"]
)

# extras1_runs is a category code, not
# a reliable numerical extras-run amount.
# Preserve original columns; do not sum it.
balls["extras_amount_verified"] = False

# 'runs' is preserved as source-reported runs.
# Do not assume it represents complete team runs.
balls["source_runs"] = balls["runs"]

# ----------------------------------------
# 4. Correct wicket classification
# ----------------------------------------
dismissal = (
    balls["dismissal_type"]
    .astype("string")
    .str.lower()
    .str.strip()
    .str.replace(" ", "", regex=False)
)

non_bowler_dismissals = {
    "runout",
    "retireout",
    "retiredout",
    "obstructingthefield",
    "obstractingthefield",
    "retiredhurt",
}

balls["is_team_wicket"] = (
    dismissal.notna()
    & ~dismissal.isin({"retiredhurt"})
)

balls["is_bowler_wicket"] = (
    dismissal.notna()
    & ~dismissal.isin(non_bowler_dismissals)
)

balls["wicket_flag_mismatch"] = (
    balls["is_wicket"]
    .astype("string").str.lower().eq("true")
    != dismissal.notna()
)

# ----------------------------------------
# 5. Classify batting phases
# ----------------------------------------
# Official overid starts at 1, not 0.
def classify_phase(over):
    if pd.isna(over):
        return "unknown"
    if 1 <= over <= 6:
        return "powerplay"
    if 7 <= over <= 15:
        return "middle"
    if 16 <= over <= 20:
        return "death"
    return "outside_regulation"

balls["phase"] = balls["overid"].map(
    classify_phase
)

# ----------------------------------------
# 6. Validate delivery identifiers
# ----------------------------------------
delivery_key = [
    "match_id", "innings", "innings_ball_num"
]

duplicate_keys = balls.duplicated(
    subset=delivery_key, keep=False
)

balls["flag_duplicate_delivery_key"] = (
    duplicate_keys
)

missing_key = balls[delivery_key].isna().any(axis=1)

balls["flag_missing_delivery_key"] = missing_key

# Keep original order information.
balls = balls.sort_values(
    delivery_key,
    kind="stable",
    na_position="last"
).reset_index(drop=True)

# ----------------------------------------
# 7. Link matches and competitions
# ----------------------------------------
if matches["match_id"].duplicated().any():
    raise ValueError(
        "Duplicate match_id values in matches.csv"
    )

if competitions["comp_id"].duplicated().any():
    raise ValueError(
        "Duplicate comp_id values in competitions.csv"
    )

matches = matches.merge(
    competitions[
        ["comp_id", "comp_name",
         "match_format", "season"]
    ],
    on="comp_id",
    how="left",
    validate="many_to_one"
)

balls = balls.merge(
    matches[
        ["match_id", "comp_id", "match_date",
         "comp_name", "match_format", "season",
         "home_team_id", "away_team_id",
         "win_team_id", "revised_target",
         "first_inn_revised_overs",
         "second_inn_revised_overs"]
    ],
    on="match_id",
    how="left",
    validate="many_to_one",
    indicator=True
)

balls["flag_unknown_match"] = (
    balls["_merge"] != "both"
)

balls.drop(columns="_merge", inplace=True)

balls["flag_team_mismatch"] = ~(
    (
        (balls["batting_team_id"] == balls["home_team_id"])
        & (balls["bowling_team_id"] == balls["away_team_id"])
    )
    | (
        (balls["batting_team_id"] == balls["away_team_id"])
        & (balls["bowling_team_id"] == balls["home_team_id"])
    )
)

# ----------------------------------------
# 8. Normalize player mapping
# ----------------------------------------
player_records = players[
    ["player_id", "player_name"]
].dropna(subset=["player_id"]).copy()

# Retain identity conflicts for manual review.
conflicts = (
    player_records.groupby("player_id")["player_name"]
    .nunique(dropna=True)
)

conflicting_ids = conflicts[conflicts > 1].index

player_records[
    player_records["player_id"].isin(conflicting_ids)
].to_csv(
    REPORT / "player_identity_conflicts.csv",
    index=False
)

player_registry = (
    player_records
    .drop_duplicates(subset=["player_id"])
    .sort_values("player_id")
)

# Playing XI reference integrity checks.
known_matches = set(matches["match_id"])
xi_unknown_matches = int(
    (~playing_xi["match_id"].isin(known_matches)).sum()
)

# ----------------------------------------
# 9. Audit legal-ball candidates
# ----------------------------------------
overs = (
    balls.groupby(
        ["match_id", "innings", "overid"],
        dropna=False
    )
    .agg(
        events=("match_id", "size"),
        legal_candidates=("legal_ball_candidate", "sum"),
        wides=("is_wide", "sum"),
        no_balls=("is_no_ball", "sum"),
        wickets=("is_team_wicket", "sum")
    )
    .reset_index()
)

overs["flag_over_six_legal"] = (
    overs["legal_candidates"] > 6
)

overs["flag_zero_legal"] = (
    overs["legal_candidates"] == 0
)

# An incomplete last over may be legitimate.
last_over = (
    overs.groupby(["match_id", "innings"])["overid"]
    .max()
    .rename("last_over")
    .reset_index()
)

overs = overs.merge(
    last_over,
    on=["match_id", "innings"],
    validate="many_to_one"
)

overs["flag_incomplete_nonterminal"] = (
    (overs["overid"] < overs["last_over"])
    & (overs["legal_candidates"] < 6)
)

flagged = overs[
    overs[
        [
            "flag_over_six_legal",
            "flag_zero_legal",
            "flag_incomplete_nonterminal",
        ]
    ].any(axis=1)
].copy()

# ----------------------------------------
# 10. Save cleaned datasets
# ----------------------------------------
balls.to_csv(
    OUT / "deliveries_clean.csv", index=False
)

matches.to_csv(
    OUT / "matches_clean.csv", index=False
)

player_registry.to_csv(
    OUT / "players_clean.csv", index=False
)

overs.to_csv(
    OUT / "over_validation.csv", index=False
)

flagged.to_csv(
    REPORT / "flagged_overs.csv", index=False
)

# ----------------------------------------
# 11. Quality report
# ----------------------------------------
report = {
    "original_ball_rows": original_rows,
    "exact_duplicate_rows": exact_duplicates,
    "clean_ball_rows": int(len(balls)),
    "matches_in_metadata": int(len(matches)),
    "matches_with_deliveries": int(
        balls["match_id"].nunique()
    ),
    "matches_without_deliveries": int(
        len(set(matches["match_id"])
            - set(balls["match_id"]))
    ),
    "unique_players_in_mapping": int(
        player_registry["player_id"].nunique()
    ),
    "player_identity_conflicts": int(
        len(conflicting_ids)
    ),
    "unknown_playing_xi_match_rows":
        xi_unknown_matches,
    "duplicate_delivery_keys": int(
        duplicate_keys.sum()
    ),
    "missing_delivery_keys": int(
        missing_key.sum()
    ),
    "unknown_match_rows": int(
        balls["flag_unknown_match"].sum()
    ),
    "team_mismatch_rows": int(
        balls["flag_team_mismatch"].sum()
    ),
    "wicket_flag_mismatches": int(
        balls["wicket_flag_mismatch"].sum()
    ),
    "wide_events": int(
        balls["is_wide"].sum()
    ),
    "no_ball_events": int(
        balls["is_no_ball"].sum()
    ),
    "overs_over_six_legal": int(
        overs["flag_over_six_legal"].sum()
    ),
    "incomplete_nonterminal_overs": int(
        overs["flag_incomplete_nonterminal"].sum()
    ),
    "flagged_overs": int(len(flagged)),
    "extras_runs_reconstructed": False,
    "legal_delivery_status": "provisional",
}

with open(
    REPORT / "quality_report.json",
    "w",
    encoding="utf-8"
) as f:
    json.dump(report, f, indent=2)

print("\n=== RR DATA QUALITY REPORT ===")
for key, value in report.items():
    print(f"{key}: {value}")

print("\n=== OUTPUT FILES ===")
for file in sorted(OUT.glob("*.csv")):
    print(file.name)

print("\n=== STATUS ===")
if len(flagged):
    print(
        "Cleaning complete with flagged overs."
    )
    print(
        "Legal-ball and scoring validation still required."
    )
else:
    print("No over-count anomalies found.")

print("\nOfficial dataset cleaning complete.")
