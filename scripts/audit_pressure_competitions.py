
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "processed" / "rr_official"

states = pd.read_csv(
    DATA / "match_states_preliminary.csv",
    low_memory=False
)

matches = pd.read_csv(
    DATA / "matches_clean.csv",
    low_memory=False
)

bat = pd.read_csv(
    DATA / "pressure_batting_reliability.csv"
)

bowl = pd.read_csv(
    DATA / "pressure_bowling_reliability.csv"
)

states = states[
    states["pressure_eligible"]
    .astype(str).str.lower().eq("true")
].copy()

states = states[
    states["structural_pressure_level"].isin(
        ["High", "Extreme"]
    )
]

# Match metadata may already exist in states.
# Drop overlapping metadata before merging.
metadata = matches[
    ["match_id", "comp_name", "match_format", "season"]
].drop_duplicates("match_id")

states = states.drop(
    columns=["comp_name", "match_format", "season"],
    errors="ignore"
)

states = states.merge(
    metadata,
    on="match_id",
    how="left",
    validate="many_to_one"
)

print("\n=== COMPETITION COVERAGE ===")
print(
    states.groupby(
        ["comp_name", "match_format"],
        dropna=False
    ).agg(
        matches=("match_id", "nunique"),
        deliveries=("match_id", "size")
    ).sort_values(
        "deliveries", ascending=False
    ).head(30).to_string()
)

top_bat = bat.sort_values(
    "base_rank"
).head(10)["player_id"]

top_bowl = bowl.sort_values(
    "base_rank"
).head(10)["player_id"]

for title, id_col, player_ids in [
    ("TOP BATTERS", "striker_id", top_bat),
    ("TOP BOWLERS", "bowler_id", top_bowl)
]:
    subset = states[
        states[id_col].isin(player_ids)
    ].copy()

    result = subset.groupby(
        [id_col, "comp_name"],
        dropna=False
    ).agg(
        deliveries=("match_id", "size"),
        matches=("match_id", "nunique")
    ).reset_index()

    print(f"\n=== {title}: COMPETITION MIX ===")
    print(
        result.sort_values(
            [id_col, "deliveries"],
            ascending=[True, False]
        ).to_string(index=False)
    )

    result.to_csv(
        DATA / (
            "batting_competition_mix.csv"
            if id_col == "striker_id"
            else "bowling_competition_mix.csv"
        ),
        index=False
    )

print("\nCompetition audit complete.")
