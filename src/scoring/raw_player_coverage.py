
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "data" / "processed" / "rr_official"
OUTPUT = ROOT / "outputs"

OUTPUT.mkdir(parents=True, exist_ok=True)

coverage = pd.read_csv(
    OUTPUT / "player_coverage_audit.csv"
)

deliveries = pd.read_csv(
    BASE / "deliveries_clean.csv",
    low_memory=False
)

deliveries["match_id"] = pd.to_numeric(
    deliveries["match_id"], errors="coerce"
)

for col in ["striker_id", "bowler_id"]:
    deliveries[col] = pd.to_numeric(
        deliveries[col], errors="coerce"
    )

results = []

for _, player in coverage.iterrows():
    name = player["player"]
    pid = player["player_id"]

    if pd.isna(pid):
        results.append({
            "player": name,
            "player_id": None,
            "batting_matches": 0,
            "batting_rows": 0,
            "bowling_matches": 0,
            "bowling_rows": 0,
            "total_matches": 0,
            "status": "IDENTITY_UNRESOLVED"
        })
        continue

    batting = deliveries[
        deliveries["striker_id"] == pid
    ]

    bowling = deliveries[
        deliveries["bowler_id"] == pid
    ]

    all_matches = set(batting["match_id"].dropna())
    all_matches.update(bowling["match_id"].dropna())

    batting_matches = batting["match_id"].nunique()
    bowling_matches = bowling["match_id"].nunique()

    total_matches = len(all_matches)

    results.append({
        "player": name,
        "player_id": int(pid),
        "batting_matches": batting_matches,
        "batting_rows": len(batting),
        "bowling_matches": bowling_matches,
        "bowling_rows": len(bowling),
        "total_matches": total_matches,
        "status": (
            "RAW_DATA_FOUND"
            if total_matches > 0
            else "NO_RAW_DATA"
        )
    })

result = pd.DataFrame(results)

result.to_csv(
    OUTPUT / "raw_player_coverage.csv",
    index=False
)

print("\n=== RAW PLAYER COVERAGE ===")
print(result.to_string(index=False))

print("\n=== COVERAGE SUMMARY ===")
print(result["status"].value_counts())

print("\nSaved: outputs/raw_player_coverage.csv")
