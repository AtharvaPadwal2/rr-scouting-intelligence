
import json
from pathlib import Path

import kagglehub
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "processed"
REPORTS = ROOT / "data" / "reports"

OUT.mkdir(parents=True, exist_ok=True)
REPORTS.mkdir(parents=True, exist_ok=True)

source = Path(kagglehub.dataset_download(
    "janvigoel19/ipl-2026-complete-ball-by-ball-dataset"
))

balls = pd.read_csv(source / "deliveries.csv", low_memory=False)
matches = pd.read_csv(source / "matches.csv", low_memory=False)

print("\n=== ORIGINAL DATA ===")
print("Delivery rows:", len(balls))
print("Matches:", len(matches))

# 1. Inspect duplicates before removing them.
multiplicity = (
    balls.fillna("__MISSING__")
    .value_counts(dropna=False)
)

print("\nDuplicate multiplicity:")
print(multiplicity.value_counts().sort_index())

duplicates_removed = int(balls.duplicated().sum())
balls = balls.drop_duplicates().copy()

# 2. Standardize franchise names.
team_names = {
    "rajasthanroyals": "Rajasthan Royals",
    "royalchallengersbengaluru": "Royal Challengers Bengaluru",
    "royalchallengersbangalore": "Royal Challengers Bengaluru",
    "mumbaiindians": "Mumbai Indians",
    "chennaisuperkings": "Chennai Super Kings",
    "kolkataknightriders": "Kolkata Knight Riders",
    "delhicapitals": "Delhi Capitals",
    "punjabkings": "Punjab Kings",
    "kingsxipunjab": "Punjab Kings",
    "gujarattitans": "Gujarat Titans",
    "lucknowsupergiants": "Lucknow Super Giants",
    "sunrisershyderabad": "Sunrisers Hyderabad",
}

def normalize_team(value):
    if pd.isna(value):
        return pd.NA
    cleaned = "".join(
        char for char in str(value).lower()
        if char.isalnum()
    )
    return team_names.get(cleaned, str(value).strip())

for col in ["batting_team", "bowling_team"]:
    balls[col] = balls[col].map(normalize_team)

for col in ["team1", "team2", "winner", "toss_winner"]:
    matches[col] = matches[col].map(normalize_team)

# 3. Normalize dates and numeric values.
balls["date"] = pd.to_datetime(balls["date"], errors="coerce")
matches["date"] = pd.to_datetime(matches["date"], errors="coerce")

numeric = [
    "runs_batter", "runs_extras", "runs_total",
    "over", "ball_num", "inning"
]

for col in numeric:
    balls[col] = pd.to_numeric(balls[col], errors="coerce")

# 4. Validate run totals.
expected_total = balls["runs_batter"] + balls["runs_extras"]

bad_totals = (
    balls["runs_total"].isna()
    | expected_total.isna()
    | balls["runs_total"].ne(expected_total)
)

balls["flag_invalid_total"] = bad_totals

# 5. Identify delivery phases.
# Based on zero-indexed 'over' values.
def get_phase(over):
    if pd.isna(over):
        return "unknown"
    if 0 <= over <= 5:
        return "powerplay"
    if 6 <= over <= 14:
        return "middle"
    if 15 <= over <= 19:
        return "death"
    return "outside_regulation"

balls["phase"] = balls["over"].apply(get_phase)

# 6. Validate and join match metadata.
if matches["match_id"].duplicated().any():
    raise ValueError("Duplicate match IDs in matches.csv")

known_matches = set(matches["match_id"])
unmatched_ids = set(balls["match_id"]) - known_matches

metadata = matches[
    ["match_id", "team1", "team2", "winner",
     "city", "toss_winner", "toss_decision"]
].rename(columns={"winner": "match_winner"})

balls = balls.merge(
    metadata,
    on="match_id",
    how="left",
    validate="many_to_one",
    indicator=True
)

balls["flag_unmatched_match"] = balls["_merge"].ne("both")
balls = balls.drop(columns="_merge")

# 7. Check participating teams and innings.
balls["flag_team_mismatch"] = ~(
    (
        (balls["batting_team"] == balls["team1"])
        & (balls["bowling_team"] == balls["team2"])
    )
    | (
        (balls["batting_team"] == balls["team2"])
        & (balls["bowling_team"] == balls["team1"])
    )
)

balls["flag_invalid_over"] = ~balls["over"].between(0, 19)

# 8. Extract ALL RR match deliveries.
rr_matches = matches[
    matches["team1"].eq("Rajasthan Royals")
    | matches["team2"].eq("Rajasthan Royals")
].copy()

rr = balls[
    balls["match_id"].isin(rr_matches["match_id"])
].copy()

rr["rr_batting"] = rr["batting_team"].eq("Rajasthan Royals")
rr["rr_bowling"] = rr["bowling_team"].eq("Rajasthan Royals")

# 9. Keep RR batting and opposition batting separate.
rr["rr_perspective"] = rr["rr_batting"].map(
    {True: "batting", False: "bowling"}
)

# 10. Save the cleaned datasets.
balls.to_csv(OUT / "ipl_2026_clean.csv", index=False)
rr.to_csv(OUT / "rr_2026_deliveries.csv", index=False)
rr_matches.to_csv(OUT / "rr_2026_matches.csv", index=False)

# 11. Generate preliminary phase counts.
# Do not treat row count as legal-ball count yet.
phase_summary = (
    rr.groupby(
        ["match_id", "inning", "rr_perspective", "phase"],
        dropna=False
    )
    .agg(
        recorded_events=("match_id", "size"),
        runs=("runs_total", "sum"),
        batter_runs=("runs_batter", "sum"),
        extras=("runs_extras", "sum"),
        wicket_events=("is_wicket", "sum"),
        invalid_totals=("flag_invalid_total", "sum")
    )
    .reset_index()
)

phase_summary.to_csv(
    OUT / "rr_2026_phase_preliminary.csv",
    index=False
)

# 12. Data quality report.
report = {
    "original_delivery_rows": int(len(balls) + duplicates_removed),
    "exact_duplicates_removed": duplicates_removed,
    "unique_delivery_rows": int(len(balls)),
    "matches_in_metadata": int(len(matches)),
    "matches_with_deliveries": int(balls["match_id"].nunique()),
    "unmatched_match_ids": sorted(int(x) for x in unmatched_ids),
    "rr_matches_in_metadata": int(len(rr_matches)),
    "rr_matches_with_deliveries": int(rr["match_id"].nunique()),
    "rr_delivery_rows": int(len(rr)),
    "rr_batting_rows": int(rr["rr_batting"].sum()),
    "rr_bowling_rows": int(rr["rr_bowling"].sum()),
    "invalid_run_totals": int(bad_totals.sum()),
    "team_mismatch_rows": int(balls["flag_team_mismatch"].sum()),
    "invalid_over_rows": int(balls["flag_invalid_over"].sum()),
    "missing_match_winners": int(matches["winner"].isna().sum()),
    "rr_match_ids": sorted(rr_matches["match_id"].astype(int).tolist())
}

with open(REPORTS / "ipl_2026_quality.json", "w") as file:
    json.dump(report, file, indent=2)

print("\n=== CLEANING REPORT ===")
for key, value in report.items():
    print(f"{key}: {value}")

print("\n=== OUTPUT FILES ===")
for file in sorted(OUT.glob("*2026*")):
    print(file.name)

print("\nCleaning pipeline complete.")
