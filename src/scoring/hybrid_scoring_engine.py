
from pathlib import Path
import json
import math
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "outputs"
SCORING = ROOT / "data/processed" / "scoring"
PUBLIC = ROOT / "frontend/public/data"

PUBLIC.mkdir(parents=True, exist_ok=True)

assessments = pd.read_csv(
    OUT / "human_scouting_assessments.csv"
)

dashboard_path = PUBLIC / "scouting_scores.json"
with dashboard_path.open(encoding="utf-8") as f:
    dashboard = json.load(f)

phase = pd.read_csv(
    SCORING / "bayesian_phase_adjusted.csv"
)

# Phase weights are initial scouting assumptions.
PHASE_WEIGHTS = {
    "Batting": {
        "powerplay": 0.15,
        "middle": 0.35,
        "death": 0.50,
    },
    "Bowling": {
        "powerplay": 0.30,
        "middle": 0.30,
        "death": 0.40,
    },
}

def clamp(value, low=0.0, high=5.0):
    return max(low, min(high, float(value)))


def model_pressure_score(records, role):
    """Return an exploratory phase-based proxy out of 5."""
    if records.empty:
        return None

    weights = PHASE_WEIGHTS[role]
    values = []
    total_weight = 0.0

    for _, row in records.iterrows():
        p = row["phase"]
        impact = row["adjusted_impact"]

        if p not in weights or pd.isna(impact):
            continue

        # Impact units differ by discipline.
        scale = 35.0 if role == "Batting" else 2.5

        normalized = 3.0 + 1.5 * math.tanh(
            float(impact) / scale
        )

        weight = weights[p]
        values.append(normalized * weight)
        total_weight += weight

    if total_weight == 0:
        return None

    return round(clamp(sum(values) / total_weight), 2)


def model_weight(total_balls):
    """Coverage-dependent model contribution."""
    if total_balls >= 600:
        return 0.70
    if total_balls >= 250:
        return 0.50
    if total_balls > 0:
        return 0.30
    return 0.0


assessments["name"] = assessments["name"].astype(str).str.strip()

if assessments["name"].duplicated().any():
    raise ValueError("Duplicate player names in assessment file")

assessment_lookup = assessments.set_index("name")
result = []

for player in dashboard["players"]:
    name = player["name"]
    role = player["role"]

    if name not in assessment_lookup.index:
        raise ValueError(f"Missing assessment: {name}")

    a = assessment_lookup.loc[name]

    if pd.isna(a["human_pressure"]) or pd.isna(a["human_reliability"]):
        raise ValueError(f"Missing human scores: {name}")

    human_pressure = clamp(a["human_pressure"])
    human_reliability = clamp(a["human_reliability"])

    records = phase[phase["player"] == name]
    total_balls = int(records["balls"].sum())

    calculated_pressure = model_pressure_score(
        records, role
    )

    weight = (
        model_weight(total_balls)
        if calculated_pressure is not None
        else 0.0
    )

    if calculated_pressure is None:
        pressure = human_pressure
        method = "ANALYST_ASSESSED"
    else:
        pressure = (
            weight * calculated_pressure
            + (1 - weight) * human_pressure
        )
        method = "HYBRID_PHASE_PROXY"

    reliability = human_reliability
    pressure = round(pressure, 2)
    reliability = round(reliability, 2)
    overall = round(pressure + reliability, 2)

    notes = (
        "" if pd.isna(a.get("evidence_notes"))
        else str(a["evidence_notes"])
    )

    source = (
        "" if pd.isna(a.get("source_reference"))
        else str(a["source_reference"])
    )

    player.update({
        "humanPressure": human_pressure,
        "humanReliability": human_reliability,
        "modelPressure": calculated_pressure,
        "pressureScore": pressure,
        "reliabilityScore": reliability,
        "overallScore": overall,
        "modelWeight": round(weight, 2),
        "humanWeight": round(1 - weight, 2),
        "assessmentMethod": method,
        "reliabilityMethod": "ANALYST_ASSESSED",
        "evidenceConfidence": (
            "PHASE_DATA_AVAILABLE"
            if calculated_pressure is not None
            else "ANALYST_EVIDENCE_ONLY"
        ),
        "scoutingRationale": notes,
        "sourceReference": source,
        "sourceVerified": False,
    })

    result.append(player)

# Ranking is descriptive, not an auction eligibility ranking.
result.sort(
    key=lambda p: p["overallScore"],
    reverse=True
)

for rank, player in enumerate(result, start=1):
    player["rank"] = rank

dashboard["version"] = "0.2-hybrid"
dashboard["model"] = "ROYAL EDGE Hybrid PRI"
dashboard["pressureMethod"] = "Hybrid phase proxy / analyst"
dashboard["reliabilityMethod"] = "Analyst assessment"
dashboard["scoresValidated"] = False
dashboard["players"] = result

with dashboard_path.open("w", encoding="utf-8") as f:
    json.dump(
        dashboard, f, indent=2, allow_nan=False
    )

pd.DataFrame(result).to_csv(
    OUT / "hybrid_player_scores.csv",
    index=False
)

print("\n=== ROYAL EDGE HYBRID PRI ===")

for p in result:
    print(
        f"{p['rank']:2}. {p['name']:<24} "
        f"P:{p['pressureScore']:.2f} "
        f"R:{p['reliabilityScore']:.2f} "
        f"PRI:{p['overallScore']:.2f} "
        f"{p['assessmentMethod']}"
    )

print("\nPlayers scored:", len(result))
print(
    "Hybrid model-supported:",
    sum(
        p["assessmentMethod"] == "HYBRID_PHASE_PROXY"
        for p in result
    )
)
print("Saved:", dashboard_path)
