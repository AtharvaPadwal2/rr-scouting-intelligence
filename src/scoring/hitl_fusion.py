
from pathlib import Path
import json
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "outputs"
SCORING = ROOT / "data/processed/scoring"
PUBLIC = ROOT / "frontend/public/data"

human = pd.read_csv(
    OUT / "human_scouting_assessments.csv"
)

model = pd.read_csv(
    SCORING / "combined_statistical_pri.csv"
)

human["name"] = human["name"].str.strip()
model["player"] = model["player"].str.strip()

if human["name"].duplicated().any():
    raise ValueError("Duplicate human assessment names")

if model["player"].duplicated().any():
    raise ValueError("Duplicate model player names")

if not human["human_pressure"].between(0, 5).all():
    raise ValueError("Invalid human pressure score")

if not human["human_reliability"].between(0, 5).all():
    raise ValueError("Invalid human reliability score")

merged = human.merge(
    model,
    left_on="name",
    right_on="player",
    how="left",
    validate="one_to_one",
)

def calculate(row):
    has_model = pd.notna(row["model_pressure"])

    if not has_model:
        weight = 0.0
        method = "ANALYST_ONLY"
    else:
        matches = int(row["matches"])

        if matches >= 30:
            weight = 0.70
        elif matches >= 15:
            weight = 0.60
        elif matches >= 5:
            weight = 0.40
        else:
            weight = 0.20

        method = "HUMAN_IN_THE_LOOP"

    hp = float(row["human_pressure"])
    hr = float(row["human_reliability"])

    if has_model:
        mp = float(row["model_pressure"])
        mr = float(row["model_reliability"])

        pressure = weight * mp + (1 - weight) * hp
        reliability = weight * mr + (1 - weight) * hr
    else:
        pressure = hp
        reliability = hr

    return pd.Series({
        "model_weight": weight,
        "human_weight": 1 - weight,
        "final_pressure": round(pressure, 2),
        "final_reliability": round(reliability, 2),
        "final_pri": round(pressure + reliability, 2),
        "assessment_method": method,
    })

scored = pd.concat(
    [merged, merged.apply(calculate, axis=1)],
    axis=1,
)

scored = scored.sort_values(
    "final_pri", ascending=False
).reset_index(drop=True)

scored["rank"] = scored.index + 1

scored.to_csv(
    OUT / "hitl_final_scores.csv",
    index=False
)

# Update the existing dashboard JSON, preserving phase metrics.
dashboard_path = PUBLIC / "scouting_scores.json"

with dashboard_path.open(encoding="utf-8") as f:
    dashboard = json.load(f)

lookup = scored.set_index("name")

for player in dashboard["players"]:
    row = lookup.loc[player["name"]]

    has_model = pd.notna(row["model_pressure"])

    player.update({
        "rank": int(row["rank"]),
        "pressureScore": float(row["final_pressure"]),
        "reliabilityScore": float(row["final_reliability"]),
        "overallScore": float(row["final_pri"]),
        "modelPressure": (
            float(row["model_pressure"])
            if has_model else None
        ),
        "modelReliability": (
            float(row["model_reliability"])
            if has_model else None
        ),
        "humanPressure": float(row["human_pressure"]),
        "humanReliability": float(row["human_reliability"]),
        "modelWeight": float(row["model_weight"]),
        "humanWeight": float(row["human_weight"]),
        "assessmentMethod": row["assessment_method"],
        "reliabilityMethod": (
            "HYBRID" if has_model else "ANALYST"
        ),
        "modelMatches": (
            int(row["matches"]) if has_model else 0
        ),
        "evidenceConfidence": (
            "MODEL_AND_ANALYST"
            if has_model else "ANALYST_ONLY"
        ),
        "scoutingRationale": (
            "" if pd.isna(row["evidence_notes"])
            else str(row["evidence_notes"])
        ),
        "sourceReference": (
            "" if pd.isna(row["source_reference"])
            else str(row["source_reference"])
        ),
        "sourceVerified": False,
    })

dashboard["players"].sort(
    key=lambda x: x["rank"]
)

dashboard["version"] = "0.3-HITL"
dashboard["model"] = "ROYAL EDGE Human-in-the-Loop PRI"
dashboard["scoresValidated"] = False

with dashboard_path.open("w", encoding="utf-8") as f:
    json.dump(dashboard, f, indent=2, allow_nan=False)

print("\n=== HITL FINAL SCORES ===")
print(
    scored[[
        "rank", "name", "final_pressure",
        "final_reliability", "final_pri",
        "model_weight", "assessment_method"
    ]].to_string(index=False)
)

print("\nTotal players:", len(scored))
print(
    "Model-supported:",
    scored["model_pressure"].notna().sum()
)
print("Saved: outputs/hitl_final_scores.csv")
print("Dashboard JSON updated.")
