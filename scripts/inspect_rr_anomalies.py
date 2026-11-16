
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]

DATA = ROOT / "data" / "processed" / "rr_official"
REPORT = ROOT / "data" / "reports" / "rr_official"

df = pd.read_csv(
    DATA / "deliveries_clean.csv",
    low_memory=False
)

cases = [
    (14130, 1, 14),
    (14130, 2, 14),
    (14164, 1, 14),
    (24353, 2, 18),
    (41509, 1, 12),
]

columns = [
    "match_id",
    "innings",
    "overid",
    "over_ball_num",
    "innings_ball_num",
    "runs",
    "extras_type",
    "extras1_runs",
    "extras_2_runs",
    "dismissal_type",
    "is_wicket",
]

available = [c for c in columns if c in df.columns]

print("\n=== EXCEPTIONAL OVERS ===")

for match_id, innings, over in cases:

    # Show the affected over and its neighboring overs.
    subset = df[
        (df["match_id"] == match_id)
        & (df["innings"] == innings)
        & df["overid"].between(over - 1, over + 1)
    ].copy()

    subset = subset.sort_values(
        ["overid", "innings_ball_num"],
        kind="stable"
    )

    print(
        f"\nMATCH {match_id} | "
        f"INNINGS {innings} | OVER {over}"
    )

    print(subset[available].to_string(index=False))

# Examine ambiguous 'other' events.
extra = (
    df["extras_type"]
    .astype("string")
    .str.lower()
    .str.strip()
)

other = df[extra.eq("other").fillna(False)].copy()

print("\n=== OTHER EXTRAS ===")
print("Total:", len(other))

print("\nSample events:")
print(other[available].head(20).to_string(index=False))

print("\n=== EXTRAS TYPE DISTRIBUTION ===")
print(extra.value_counts(dropna=False).to_string())

# Save affected events for detailed investigation.
parts = []

for match_id, innings, over in cases:
    selected = df[
        (df["match_id"] == match_id)
        & (df["innings"] == innings)
        & df["overid"].between(over - 1, over + 1)
    ]
    parts.append(selected)

exceptions = pd.concat(
    parts, ignore_index=True
).drop_duplicates()

REPORT.mkdir(parents=True, exist_ok=True)

exceptions.to_csv(
    REPORT / "anomaly_delivery_context.csv",
    index=False
)

other.to_csv(
    REPORT / "ambiguous_other_extras.csv",
    index=False
)

print("\nAnomaly inspection complete.")
