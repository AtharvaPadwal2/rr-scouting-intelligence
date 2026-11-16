
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
DATA = ROOT / "data" / "processed" / "rr_official"

# Load official player registry.
players = pd.read_csv(
    RAW / "competition_team_player_mapping.csv",
    low_memory=False
)

registry = (
    players[["player_id", "player_name"]]
    .dropna(subset=["player_id"])
    .drop_duplicates(subset=["player_id"])
    .copy()
)

registry["player_id"] = pd.to_numeric(
    registry["player_id"], errors="coerce"
).astype("Int64")

# Load exploratory performance tables.
bat = pd.read_csv(
    DATA / "pressure_batting_exploratory.csv"
)

bowl = pd.read_csv(
    DATA / "pressure_bowling_exploratory.csv"
)

def attach_names(df, id_col):
    result = df.copy()

    result[id_col] = pd.to_numeric(
        result[id_col], errors="coerce"
    ).astype("Int64")

    result = result.merge(
        registry,
        left_on=id_col,
        right_on="player_id",
        how="left",
        validate="many_to_one"
    )

    result["player_name"] = (
        result["player_name"]
        .fillna("UNKNOWN PLAYER")
    )

    return result.drop(columns=["player_id"])

bat = attach_names(bat, "striker_id")
bowl = attach_names(bowl, "bowler_id")

# Rank only within qualified samples.
qualified_bat = bat[
    bat["sample_qualified"].astype(str).str.lower().eq("true")
].copy()

qualified_bowl = bowl[
    bowl["sample_qualified"].astype(str).str.lower().eq("true")
].copy()

# Display exploratory leaders, not final rankings.
bat_leaders = qualified_bat.sort_values(
    ["strike_rate_high", "balls_high"],
    ascending=[False, False]
).head(30)

bowl_leaders = qualified_bowl.sort_values(
    ["batter_runs_per_over_high", "legal_balls_high"],
    ascending=[True, False]
).head(30)

print("\n=== TOP 30 EXPLORATORY BATTERS ===")
print(
    bat_leaders[
        [
            "player_name",
            "striker_id",
            "matches_high",
            "balls_high",
            "strike_rate_high",
            "sr_change"
        ]
    ].round(2).to_string(index=False)
)

print("\n=== TOP 30 EXPLORATORY BOWLERS ===")
print(
    bowl_leaders[
        [
            "player_name",
            "bowler_id",
            "matches_high",
            "legal_balls_high",
            "wickets_high",
            "batter_runs_per_over_high",
            "run_rate_change"
        ]
    ].round(2).to_string(index=False)
)

# Check mapping coverage.
print("\n=== PLAYER IDENTITY COVERAGE ===")
print(
    "Batters without names:",
    int(bat["player_name"].eq("UNKNOWN PLAYER").sum())
)
print(
    "Bowlers without names:",
    int(bowl["player_name"].eq("UNKNOWN PLAYER").sum())
)

# Export complete named datasets.
bat.to_csv(
    DATA / "pressure_batting_named.csv",
    index=False
)

bowl.to_csv(
    DATA / "pressure_bowling_named.csv",
    index=False
)

print("\nNamed player tables saved.")
print("These are exploratory, not final rankings.")
