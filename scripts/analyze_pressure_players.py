
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "processed" / "rr_official"

df = pd.read_csv(
    DATA / "match_states_preliminary.csv",
    low_memory=False
)

df = df[df["pressure_eligible"].astype(str).str.lower().eq("true")].copy()

extra = df["extras_type"].fillna("").astype(str).str.lower()
kind = df["dismissal_type"].fillna("").astype(str).str.lower()
kind = kind.str.replace(" ", "", regex=False)

df["wide"] = extra.eq("wide")
df["illegal"] = extra.isin(["wide", "overstep", "other"])
df["legal"] = ~df["illegal"]

df["high_pressure"] = df["structural_pressure_level"].isin(
    ["High", "Extreme"]
)

df["batting_ball"] = ~df["wide"]
df["boundary"] = df["runs"].isin([4, 6])

non_bowler = {
    "runout", "retiredout", "retireout",
    "retiredhurt", "obstructingthefield"
}
df["bowler_wicket"] = kind.ne("") & ~kind.isin(non_bowler)

# We use batter runs only for batting statistics.
# Bowling economy cannot be certified until
# extras-run accounting is resolved.
def batting_stats(data):
    return (
        data.groupby(
            ["striker_id", "high_pressure"]
        )
        .agg(
            matches=("match_id", "nunique"),
            runs=("runs", "sum"),
            balls=("batting_ball", "sum"),
            boundaries=("boundary", "sum")
        )
        .reset_index()
    )

def bowling_stats(data):
    return (
        data.groupby(
            ["bowler_id", "high_pressure"]
        )
        .agg(
            matches=("match_id", "nunique"),
            legal_balls=("legal", "sum"),
            batter_runs_conceded=("runs", "sum"),
            wickets=("bowler_wicket", "sum"),
            boundaries=("boundary", "sum")
        )
        .reset_index()
    )

bat = batting_stats(df)
bowl = bowling_stats(df)

bat["strike_rate"] = (
    100 * bat["runs"] / bat["balls"].replace(0, np.nan)
)
bat["boundary_pct"] = (
    100 * bat["boundaries"] / bat["balls"].replace(0, np.nan)
)

bowl["batter_runs_per_over"] = (
    6 * bowl["batter_runs_conceded"]
    / bowl["legal_balls"].replace(0, np.nan)
)
bowl["balls_per_wicket"] = (
    bowl["legal_balls"]
    / bowl["wickets"].replace(0, np.nan)
)

# Pivot into high-pressure and baseline samples.
def compare(data, id_col, value_cols):
    wide = data.pivot(
        index=id_col,
        columns="high_pressure",
        values=value_cols
    )

    wide.columns = [
        f"{metric}_{'high' if high else 'baseline'}"
        for metric, high in wide.columns
    ]
    return wide.reset_index()

bat_compare = compare(
    bat, "striker_id",
    ["runs", "balls", "strike_rate", "boundary_pct", "matches"]
)

bowl_compare = compare(
    bowl, "bowler_id",
    ["legal_balls", "wickets", "batter_runs_per_over",
     "balls_per_wicket", "matches"]
)

# Require meaningful exposure in BOTH groups.
bat_compare["sample_qualified"] = (
    (bat_compare["balls_high"] >= 30)
    & (bat_compare["balls_baseline"] >= 60)
)

bowl_compare["sample_qualified"] = (
    (bowl_compare["legal_balls_high"] >= 30)
    & (bowl_compare["legal_balls_baseline"] >= 60)
)

bat_compare["sr_change"] = (
    bat_compare["strike_rate_high"]
    - bat_compare["strike_rate_baseline"]
)

bowl_compare["run_rate_change"] = (
    bowl_compare["batter_runs_per_over_high"]
    - bowl_compare["batter_runs_per_over_baseline"]
)

# These are comparison tables, NOT definitive rankings.
bat_compare.to_csv(
    DATA / "pressure_batting_exploratory.csv", index=False
)
bowl_compare.to_csv(
    DATA / "pressure_bowling_exploratory.csv", index=False
)

print("\n=== BATTING: HIGH STRUCTURAL PRESSURE ===")
print(
    bat_compare[bat_compare["sample_qualified"]]
    .sort_values("strike_rate_high", ascending=False)
    .head(20)
    .round(2)
    .to_string(index=False)
)

print("\n=== BOWLING: HIGH STRUCTURAL PRESSURE ===")
print(
    bowl_compare[bowl_compare["sample_qualified"]]
    .sort_values("batter_runs_per_over_high")
    .head(20)
    .round(2)
    .to_string(index=False)
)

print("\n=== SAMPLE COVERAGE ===")
print("Qualified batters:", int(bat_compare["sample_qualified"].sum()))
print("Qualified bowlers:", int(bowl_compare["sample_qualified"].sum()))

print("\nExploratory analysis saved.")
print("These are NOT final pressure-performance rankings.")
