
from pathlib import Path
import json
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "outputs"
DASHBOARD = ROOT / "frontend/public/data/scouting_scores.json"

regional = pd.read_csv(
    OUT / "regional_verified_evidence.csv"
)

with DASHBOARD.open(encoding="utf-8") as f:
    data = json.load(f)

def clean(value):
    if pd.isna(value):
        return None
    if hasattr(value, "item"):
        return value.item()
    return value

for player in data["players"]:
    rows = regional[
        regional["player"] == player["name"]
    ]

    player["regionalEvidence"] = []

    for _, row in rows.iterrows():
        player["regionalEvidence"].append({
            "competition": row["competition"],
            "format": row["format"],
            "matches": clean(row["matches"]),
            "runs": clean(row["runs"]),
            "balls": clean(row["balls"]),
            "wickets": clean(row["wickets"]),
            "economy": clean(row["economy"]),
            "strikeRate": clean(row["strike_rate"]),
            "evidenceType": row["evidence_type"],
            "source": clean(row["source"]),
        })

    player["regionalEvidenceStatus"] = (
        "AGGREGATE_EVIDENCE_AVAILABLE"
        if player["regionalEvidence"]
        else "NOT_IN_REGIONAL_IMPORT"
    )

data["version"] = "0.4-HITL-regional-evidence"

with DASHBOARD.open("w", encoding="utf-8") as f:
    json.dump(data, f, indent=2, allow_nan=False)

print("\n=== DASHBOARD EVIDENCE UPDATE ===")
print("Players:", len(data["players"]))
print(
    "With regional evidence:",
    sum(bool(p["regionalEvidence"]) for p in data["players"])
)
print("Saved:", DASHBOARD)
