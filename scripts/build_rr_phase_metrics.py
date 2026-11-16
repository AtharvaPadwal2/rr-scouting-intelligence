
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "processed"
REPORT = ROOT / "data" / "reports"
REPORT.mkdir(exist_ok=True, parents=True)

df = pd.read_csv(
    DATA / "rr_2026_deliveries.csv",
    low_memory=False
)

# Preserve the original recorded-event order.
df["delivery_order"] = range(len(df))

# Provisional interpretation from the extras audit.
df["is_wide"] = df["extras_detail"].notna()
df["is_no_ball"] = df["c1"].notna()

df["is_legal"] = ~(
    df["is_wide"] | df["is_no_ball"]
)

# An actual dismissal is not always credited to the bowler.
non_bowler_kinds = {
    "run out",
    "retired hurt",
    "retired out",
    "obstructing the field",
}

kind = df["wicket_kind"].fillna("").str.lower().str.strip()

df["team_wicket"] = (
    kind.ne("") & kind.ne("retired hurt")
)
df["bowler_wicket"] = (
    kind.ne("") & ~kind.isin(non_bowler_kinds)
)

df["boundary"] = df["runs_batter"].isin([4, 6])

# A batting-team dot event has zero total runs.
df["team_dot"] = df["is_legal"] & df["runs_total"].eq(0)

# Audit legal-ball counts per over.
overs = (
    df.groupby(["match_id", "inning", "over"])
    .agg(
        events=("match_id", "size"),
        legal_balls=("is_legal", "sum"),
        wides=("is_wide", "sum"),
        no_balls=("is_no_ball", "sum"),
    )
    .reset_index()
)

overs["invalid_over"] = overs["legal_balls"] > 6

# An over with fewer than six legal deliveries can
# be valid when an innings ends mid-over.
terminal = (
    df.groupby(["match_id", "inning"])["over"]
    .max()
    .rename("last_over")
    .reset_index()
)

overs = overs.merge(
    terminal, on=["match_id", "inning"]
)

overs["incomplete_nonterminal"] = (
    (overs["over"] < overs["last_over"])
    & (overs["legal_balls"] < 6)
)

overs.to_csv(
    REPORT / "rr_2026_legal_over_audit.csv",
    index=False
)

# Create team-by-phase statistics.
summary = (
    df.groupby(
        ["match_id", "inning", "batting_team",
         "bowling_team", "phase"],
        dropna=False
    )
    .agg(
        runs=("runs_total", "sum"),
        legal_balls=("is_legal", "sum"),
        recorded_events=("match_id", "size"),
        wickets=("team_wicket", "sum"),
        bowler_wickets=("bowler_wicket", "sum"),
        boundaries=("boundary", "sum"),
        dot_balls=("team_dot", "sum"),
        wides=("is_wide", "sum"),
        no_balls=("is_no_ball", "sum")
    )
    .reset_index()
)

summary["run_rate"] = (
    summary["runs"] * 6
    / summary["legal_balls"].replace(0, float("nan"))
)

summary["dot_ball_pct"] = (
    summary["dot_balls"] * 100
    / summary["legal_balls"].replace(0, float("nan"))
)

summary["boundary_pct"] = (
    summary["boundaries"] * 100
    / summary["legal_balls"].replace(0, float("nan"))
)

summary["rr_role"] = summary["batting_team"].apply(
    lambda x: "Batting" if x == "Rajasthan Royals"
    else "Bowling"
)

summary.to_csv(
    DATA / "rr_2026_phase_metrics.csv",
    index=False
)

overall = (
    summary.groupby(["rr_role", "phase"])
    [["runs", "legal_balls", "wickets", "boundaries", "dot_balls"]]
    .sum()
    .reset_index()
)

overall["run_rate"] = (
    overall["runs"] * 6 / overall["legal_balls"]
).round(2)

overall["dot_pct"] = (
    overall["dot_balls"] * 100 / overall["legal_balls"]
).round(2)

overall["boundary_pct"] = (
    overall["boundaries"] * 100 / overall["legal_balls"]
).round(2)

print("\n=== LEGAL DELIVERY VALIDATION ===")
print("Illegal deliveries:", int((~df["is_legal"]).sum()))
print("Overs exceeding six legal balls:",
      int(overs["invalid_over"].sum()))
print("Incomplete nonterminal overs:",
      int(overs["incomplete_nonterminal"].sum()))
print("Deliveries marked both wide and no-ball:",
      int((df["is_wide"] & df["is_no_ball"]).sum()))

print("\n=== RR PHASE PERFORMANCE ===")
print(overall.to_string(index=False))

print("\nSaved:")
print("rr_2026_phase_metrics.csv")
print("rr_2026_legal_over_audit.csv")

if (
    overs["invalid_over"].any()
    or overs["incomplete_nonterminal"].any()
):
    print("\nWARNING: Review flagged overs before using metrics.")
else:
    print("\nOver-count validation passed.")
