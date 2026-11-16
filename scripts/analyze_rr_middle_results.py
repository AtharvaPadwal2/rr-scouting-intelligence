
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "processed"

df = pd.read_csv(
    DATA / "rr_2026_deliveries.csv",
    low_memory=False
)

rr = df[
    (df["bowling_team"] == "Rajasthan Royals")
    & (df["phase"] == "middle")
].copy()

rr["result"] = rr["match_winner"].apply(
    lambda w: "Win" if w == "Rajasthan Royals"
    else "Loss" if pd.notna(w)
    else "No Result"
)

rr["legal"] = ~(
    rr["extras_detail"].notna()
    | rr["c1"].notna()
)

kind = rr["wicket_kind"].fillna("").str.lower().str.strip()

rr["bowler_wicket"] = (
    kind.ne("")
    & ~kind.isin([
        "run out", "retired out",
        "retired hurt", "obstructing the field"
    ])
)

rr["boundary"] = rr["runs_batter"].isin([4, 6])

stats = (
    rr.groupby(["bowler", "result"])
    .agg(
        matches=("match_id", "nunique"),
        balls=("legal", "sum"),
        runs=("runs_total", "sum"),
        wickets=("bowler_wicket", "sum"),
        boundaries=("boundary", "sum")
    )
    .reset_index()
)

stats["runs_per_over"] = (
    6 * stats["runs"]
    / stats["balls"].replace(0, float("nan"))
).round(2)

stats["balls_per_wicket"] = (
    stats["balls"]
    / stats["wickets"].replace(0, float("nan"))
).round(2)

stats.to_csv(
    DATA / "rr_2026_middle_win_loss.csv",
    index=False
)

qualified = stats.groupby("bowler")["balls"].sum()
qualified = qualified[qualified >= 60].index

print("\n=== MIDDLE BOWLING: WINS VS LOSSES ===")
print(
    stats[stats["bowler"].isin(qualified)]
    .sort_values(["bowler", "result"])
    .to_string(index=False)
)

print("\n=== ALL MIDDLE-OVER BOWLERS BY RESULT ===")
overall = stats.groupby("result")[
    ["runs", "balls", "wickets"]
].sum()

overall["runs_per_over"] = (
    6 * overall["runs"] / overall["balls"]
).round(2)

print(overall.to_string())
