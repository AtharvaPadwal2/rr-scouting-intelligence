
import itertools
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
df = pd.read_csv(
    ROOT / "data/processed/rr_2026_deliveries.csv",
    low_memory=False
)

extra_cols = ["extras_detail", "c1", "c2", "c3"]

# Inspect overs with extra deliveries.
groups = df.groupby(["match_id", "inning", "over"])
over_sizes = groups.size()

long_overs = over_sizes[over_sizes > 6]

print("\n=== LONG OVERS ===")
print("Total:", len(long_overs))

print("\n=== POSSIBLE ILLEGAL DELIVERY COLUMNS ===")

results = []

for count in range(1, len(extra_cols) + 1):
    for combination in itertools.combinations(extra_cols, count):

        matches = 0
        total = 0
        errors = 0

        for key, events in groups:
            if len(events) <= 6:
                continue

            expected_illegal = len(events) - 6

            marked = events[list(combination)].notna().any(axis=1)
            detected = int(marked.sum())

            total += 1
            errors += abs(detected - expected_illegal)

            if detected == expected_illegal:
                matches += 1

        results.append({
            "columns": " + ".join(combination),
            "matching_overs": matches,
            "total_overs": total,
            "absolute_error": errors
        })

ranking = pd.DataFrame(results).sort_values(
    ["matching_overs", "absolute_error"],
    ascending=[False, True]
)

print(ranking.head(15).to_string(index=False))

# Show complete delivery details for selected long overs.
print("\n=== SAMPLE LONG OVERS ===")

for key in list(long_overs.index)[:3]:
    match_id, inning, over = key

    selected = df[
        (df["match_id"] == match_id)
        & (df["inning"] == inning)
        & (df["over"] == over)
    ]

    columns = [
        "over_ball", "over_ball2", "ball_num",
        "batter", "runs_batter", "runs_extras",
        "extras_detail", "c1", "c2", "c3",
        "runs_total", "wicket_kind"
    ]

    print(f"\nMatch {match_id}, innings {inning}, over {over}")
    print(selected[columns].to_string(index=False))

# Wicket classification check.
dismissals = df["wicket_kind"].notna()

non_bowler_kinds = [
    "run out", "retired hurt", "retired out",
    "obstructing the field"
]

bowler_wickets = (
    dismissals
    & ~df["wicket_kind"].str.lower().isin(non_bowler_kinds)
)

print("\n=== WICKET CLASSIFICATION ===")
print("All dismissals:", int(dismissals.sum()))
print("Bowler-credit wickets:", int(bowler_wickets.sum()))
print("Non-bowler dismissals:", int(
    (dismissals & ~bowler_wickets).sum()
))

print("\nValidation inspection complete.")
