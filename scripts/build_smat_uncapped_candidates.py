
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data/processed/smat_player_seasons.csv"
OUT = ROOT / "data/processed/rr_official"
OUT.mkdir(parents=True, exist_ok=True)

df = pd.read_csv(SOURCE, low_memory=False)

# Convert statistics to numeric.
numeric = [
    "matches", "batting_innings", "runs",
    "balls_faced", "dismissals",
    "legal_balls_bowled", "runs_conceded",
    "wickets", "age_at_season_end"
]

for col in numeric:
    df[col] = pd.to_numeric(
        df[col], errors="coerce"
    )

# Extract starting year: 2024/25 -> 2024.
df["season_year"] = pd.to_numeric(
    df["season"].astype(str).str.extract(
        r"(\d{4})"
    )[0],
    errors="coerce"
)

latest_year = int(df["season_year"].max())
recent_start = latest_year - 2

print("Latest SMAT season start:", latest_year)
print("Recent window:", recent_start, "to", latest_year)

recent = df[
    df["season_year"].between(
        recent_start, latest_year
    )
].copy()

# Do not silently treat missing statistics as zero.
stat_cols = [
    "matches", "batting_innings", "runs",
    "balls_faced", "dismissals",
    "legal_balls_bowled", "runs_conceded",
    "wickets"
]

missing_stats = recent[stat_cols].isna().sum()
print("\nMissing statistics by column:")
print(missing_stats.to_string())

recent = recent.dropna(
    subset=["player_id", "player_name"]
).copy()

# Aggregate player-team-season records.
# A player may have multiple team rows.
players = recent.groupby(
    "player_id", as_index=False
).agg(
    player_name=("player_name", "first"),
    teams=("team", lambda s: ", ".join(
        sorted(set(s.dropna().astype(str)))
    )),
    seasons=("season", lambda s: ", ".join(
        sorted(set(s.dropna().astype(str)))
    )),
    seasons_played=("season_year", "nunique"),
    last_season=("season_year", "max"),
    matches=("matches", "sum"),
    batting_innings=("batting_innings", "sum"),
    runs=("runs", "sum"),
    balls_faced=("balls_faced", "sum"),
    dismissals=("dismissals", "sum"),
    legal_balls_bowled=("legal_balls_bowled", "sum"),
    runs_conceded=("runs_conceded", "sum"),
    wickets=("wickets", "sum")
)

# Batting measures.
players["strike_rate"] = np.where(
    players["balls_faced"] > 0,
    100 * players["runs"] / players["balls_faced"],
    np.nan
)

players["batting_average"] = np.where(
    players["dismissals"] > 0,
    players["runs"] / players["dismissals"],
    np.nan
)

# Bowling measures.
players["economy"] = np.where(
    players["legal_balls_bowled"] > 0,
    6 * players["runs_conceded"]
    / players["legal_balls_bowled"],
    np.nan
)

players["wickets_per_24_balls"] = np.where(
    players["legal_balls_bowled"] > 0,
    24 * players["wickets"]
    / players["legal_balls_bowled"],
    np.nan
)

# Qualified recent performers.
bat = players[
    (players["balls_faced"] >= 100)
    & (players["batting_innings"] >= 5)
].copy()

bowl = players[
    (players["legal_balls_bowled"] >= 60)
    & (players["matches"] >= 5)
].copy()

# Smoothed scoring to reduce small-sample bias.
league_sr = (
    100 * bat["runs"].sum()
    / max(bat["balls_faced"].sum(), 1)
) if len(bat) else 0

league_econ = (
    6 * bowl["runs_conceded"].sum()
    / max(bowl["legal_balls_bowled"].sum(), 1)
) if len(bowl) else 0

league_wicket_rate = (
    24 * bowl["wickets"].sum()
    / max(bowl["legal_balls_bowled"].sum(), 1)
) if len(bowl) else 0

bat["smoothed_sr"] = (
    bat["runs"] * 100 + 120 * league_sr
) / (bat["balls_faced"] + 120)

bowl["smoothed_economy"] = (
    6 * bowl["runs_conceded"]
    + 72 * league_econ
) / (bowl["legal_balls_bowled"] + 72)

bowl["smoothed_wickets_per_24"] = (
    24 * bowl["wickets"]
    + 72 * league_wicket_rate
) / (bowl["legal_balls_bowled"] + 72)

# Within-pool percentile ranks.
# These weights are provisional scouting heuristics.
bat["scouting_score"] = 100 * (
    0.60 * bat["smoothed_sr"].rank(pct=True)
    + 0.20 * bat["runs"].rank(pct=True)
    + 0.20 * bat["seasons_played"].rank(pct=True)
)

bowl["scouting_score"] = 100 * (
    0.50 * (
        1 - bowl["smoothed_economy"].rank(pct=True)
    )
    + 0.35 * bowl["smoothed_wickets_per_24"].rank(pct=True)
    + 0.15 * bowl["legal_balls_bowled"].rank(pct=True)
)

bat = bat.sort_values(
    ["scouting_score", "balls_faced"],
    ascending=False
).reset_index(drop=True)

bowl = bowl.sort_values(
    ["scouting_score", "legal_balls_bowled"],
    ascending=False
).reset_index(drop=True)

bat.insert(0, "rank", range(1, len(bat) + 1))
bowl.insert(0, "rank", range(1, len(bowl) + 1))

# Eligibility is intentionally unverified.
for table in (bat, bowl):
    table["indian_status"] = "REVIEW"
    table["uncapped_status"] = "REVIEW"
    table["unattached_status"] = "REVIEW"
    table["eligibility_status"] = "UNVERIFIED"

bat.to_csv(
    OUT / "smat_uncapped_batting_review.csv",
    index=False
)

bowl.to_csv(
    OUT / "smat_uncapped_bowling_review.csv",
    index=False
)

# Separate verification registry. Preserve prior edits.
registry_path = OUT / "smat_eligibility_registry.csv"

registry = pd.concat([
    bat[["player_id", "player_name"]],
    bowl[["player_id", "player_name"]]
]).drop_duplicates("player_id")

if registry_path.exists():
    old = pd.read_csv(registry_path, dtype={"player_id": str})
    registry["player_id"] = registry["player_id"].astype(str)

    preserved = [
        c for c in [
            "indian_status", "uncapped_status",
            "unattached_status", "evidence_url",
            "verification_note"
        ] if c in old.columns
    ]

    registry = registry.merge(
        old[["player_id"] + preserved].drop_duplicates(
            "player_id"
        ),
        on="player_id",
        how="left"
    )

for col in [
    "indian_status", "uncapped_status",
    "unattached_status"
]:
    if col not in registry:
        registry[col] = "REVIEW"
    else:
        registry[col] = registry[col].fillna("REVIEW")

for col in ["evidence_url", "verification_note"]:
    if col not in registry:
        registry[col] = ""

registry.to_csv(registry_path, index=False)

print("\n=== TOP 25 DOMESTIC BATTERS ===")
print(
    bat[[
        "rank", "player_name", "teams", "seasons",
        "matches", "runs", "balls_faced",
        "strike_rate", "scouting_score"
    ]].head(25).round(2).to_string(index=False)
)

print("\n=== TOP 25 DOMESTIC BOWLERS ===")
print(
    bowl[[
        "rank", "player_name", "teams", "seasons",
        "matches", "wickets", "legal_balls_bowled",
        "economy", "scouting_score"
    ]].head(25).round(2).to_string(index=False)
)

print("\n=== COVERAGE ===")
print("Recent player records:", len(players))
print("Qualified batters:", len(bat))
print("Qualified bowlers:", len(bowl))
print("Eligibility verified: 0 by this script")
print("Registry:", registry_path)
print("\nSMAT exploratory rankings generated.")
