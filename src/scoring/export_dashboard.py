
from pathlib import Path
import json
import math
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / "outputs"
SCORING = ROOT / "data/processed/scoring"
PUBLIC = ROOT / "frontend/public/data"
PUBLIC.mkdir(parents=True, exist_ok=True)

players = pd.read_csv(
    OUTPUT / "player_coverage_audit.csv"
)

raw = pd.read_csv(
    OUTPUT / "raw_player_coverage.csv"
)

smat = pd.read_csv(
    OUTPUT / "smat_player_coverage.csv"
)

phase = pd.read_csv(
    SCORING / "bayesian_phase_adjusted.csv"
)

profiles = []

for _, player in players.iterrows():
    name = player["player"]
    role = player["role"]

    rr = raw[raw["player"] == name]
    domestic = smat[smat["player"] == name]
    current = phase[phase["player"] == name]

    rr_matches = int(
        rr.iloc[0]["total_matches"]
    ) if not rr.empty else 0

    smat_matches = (
        int(max(
            domestic.iloc[0]["batting_matches"],
            domestic.iloc[0]["bowling_matches"]
        ))
        if not domestic.empty else 0
    )

    phase_data = []

    for _, record in current.iterrows():
        phase_data.append({
            "phase": record["phase"],
            "balls": int(record["balls"]),
            "rawImpact": round(
                float(record["raw_impact"]), 2
            ),
            "adjustedImpact": round(
                float(record["adjusted_impact"]), 2
            ),
            "sampleWeight": round(
                float(record["sample_weight"]), 3
            ),
            "impactUnit": record["impact_unit"],
        })

    profiles.append({
        "name": name,
        "role": role,
        "rrMatches": rr_matches,
        "smatMatches": smat_matches,
        "hasExternalPhaseData": bool(phase_data),
        "phasePerformance": phase_data,
        "pressureScore": None,
        "reliabilityScore": None,
        "overallScore": None,
        "scoreStatus": "PENDING_VALIDATION",
    })

destination = PUBLIC / "scouting_scores.json"

with destination.open("w", encoding="utf-8") as f:
    json.dump(
        {
            "model": "ROYAL EDGE PRI",
            "version": "0.1",
            "players": profiles
        },
        f,
        indent=2,
        allow_nan=False
    )

print("\n=== DASHBOARD EXPORT ===")
print("Total players:", len(profiles))
print(
    "With phase metrics:",
    sum(p["hasExternalPhaseData"] for p in profiles)
)
print("Saved:", destination)
