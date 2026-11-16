
from pathlib import Path
import pandas as pd

PATH = Path(
    "data/processed/rr_official/"
    "match_states_preliminary.csv"
)

df = pd.read_csv(PATH, low_memory=False)

# Only deliveries where Yash was the striker.
# Non-striker appearances must not count as balls faced.
player = df.loc[
    df["striker_name"].astype(str)
    .str.strip().str.casefold().eq("yash dhull")
].copy()

print("\n=== YASH DHULL: MATCH-STATE AUDIT ===")
print("Striker delivery rows:", len(player))

if player.empty:
    raise SystemExit("No striker deliveries found.")

# Identify available columns before calculating pressure.
relevant_keywords = (
    "match", "date", "comp", "season",
    "ball", "run", "wicket", "phase",
    "pressure", "eligible", "four", "six",
    "quality", "legal", "flag"
)

columns = [
    c for c in player.columns
    if any(word in c.lower() for word in relevant_keywords)
]

print("\nRelevant columns:")
print(columns)

print("\n=== COMPETITION COVERAGE ===")

for col in ["comp_name", "season", "match_format"]:
    if col in player.columns:
        print(f"\n{col}:")
        print(player[col].value_counts(dropna=False).to_string())

print("\n=== MATCH COVERAGE ===")

match_col = next(
    (
        c for c in ["match_id", "matchid"]
        if c in player.columns
    ),
    None
)

if match_col:
    grouped = player.groupby(match_col, dropna=False)

    for match_id, rows in grouped:
        info = {
            "match_id": match_id,
            "date": (
                rows["match_date"].iloc[0]
                if "match_date" in rows.columns
                else "Unknown"
            ),
            "striker_delivery_rows": len(rows),
        }

        if "runs" in rows.columns:
            info["runs_column_sum"] = pd.to_numeric(
                rows["runs"], errors="coerce"
            ).sum()

        print(info)

print("\n=== PRESSURE CLASSIFICATION ===")

pressure_cols = [
    c for c in player.columns
    if "pressure" in c.lower()
    or "eligible" in c.lower()
]

for col in pressure_cols:
    print(f"\n{col}:")

    if pd.api.types.is_numeric_dtype(player[col]):
        print(player[col].describe().to_string())
    else:
        print(
            player[col]
            .value_counts(dropna=False)
            .head(15)
            .to_string()
        )

print("\n=== DELIVERY FLAGS ===")

for col in [
    "legal_ball_candidate",
    "is_four",
    "is_six",
    "is_team_wicket",
    "flag_unknown_match",
    "flag_team_mismatch",
]:
    if col in player.columns:
        print(f"\n{col}:")
        print(player[col].value_counts(dropna=False).to_string())

print("\n=== PHASE COVERAGE ===")

if "phase" in player.columns:
    print(player["phase"].value_counts(dropna=False))

print("\n=== AUDIT COMPLETE ===")
print(
    "Note: Delivery rows are not automatically legal balls. "
    "The runs column's meaning and pressure eligibility "
    "must be verified before computing a batting strike rate."
)
