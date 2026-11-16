
from pathlib import Path
import json
import math
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "outputs"
DASH = ROOT / "frontend/public/data/scouting_scores.json"

# Additional source-verified records
NEW = [
    {
        "player": "Shubham Kumar Gupta",
        "competition": "Assam Premier League 2026",
        "format": "T20",
        "role": "bowling",
        "matches": 12,
        "runs": None,
        "balls": 240,
        "wickets": 21,
        "economy": 7.00,
        "source": "https://www.cricdat.com/cricket/series/assam-premier-league-2026/stats/bowling-top-wicket-takers/130127",
    },
    {
        "player": "Ishant Bharadwaj",
        "competition": "SMAT 2025",
        "format": "T20",
        "role": "bowling",
        "matches": 6,
        "runs": None,
        "balls": 132,
        "wickets": 8,
        "economy": 9.32,
        "source": "https://www.cricbuzz.com/player-match-performance/match/128776/player/1466256/bowling?inningsId=2",
    },
]

TARGETS = {
    "Tushar Raheja",
    "Yajas Sharma",
    "Aaryavir Sehwag",
    "Khilan Patel",
    "Mohit Ulva",
    "Shubham Kumar Gupta",
    "Ishant Bharadwaj",
}

path = OUT / "regional_verified_evidence.csv"
original = pd.read_csv(path)
extra = pd.DataFrame(NEW)

data = pd.concat([original, extra], ignore_index=True)
data = data.drop_duplicates(
    ["player", "competition"], keep="last"
)

# Preserve evidence provenance.
data["evidence_type"] = data["matches"].apply(
    lambda n: "SINGLE_MATCH"
    if n == 1 else "TOURNAMENT_AGGREGATE"
)
data["t20_model_eligible"] = False

for col in ["runs", "balls", "wickets", "economy", "matches"]:
    data[col] = pd.to_numeric(data[col], errors="coerce")

data["strike_rate"] = (
    100 * data["runs"] / data["balls"]
).round(2)

data.to_csv(path, index=False)

# Assumed reference points, not empirically fitted benchmarks.
# ODI and T20 are evaluated separately.
BASELINES = {
    ("T20", "batting"): (150.0, 25.0),
    ("ODI", "batting"): (85.0, 35.0),
    ("T20", "bowling"): (1.1, 8.0),
    ("ODI", "bowling"): (1.0, 5.5),
}

def form_score(row):
    fmt = row["format"]
    role = row["role"]
    matches = int(row["matches"])

    if matches <= 0:
        return None, 0.0

    reference = BASELINES.get((fmt, role))
    if reference is None:
        return None, 0.0

    volume_baseline, rate_baseline = reference

    if role == "batting":
        runs = row["runs"]
        balls = row["balls"]

        if pd.isna(runs) or pd.isna(balls) or balls <= 0:
            return None, 0.0

        sr = 100 * runs / balls
        runs_per_match = runs / matches

        # Rate and scoring volume both matter.
        performance = (
            0.55 * math.log(
                max(sr, 1) / volume_baseline
            )
            + 0.45 * math.log(
                max(runs_per_match, 1) / rate_baseline
            )
        )
    else:
        wickets = row["wickets"]
        economy = row["economy"]

        if pd.isna(wickets):
            return None, 0.0

        wickets_per_match = wickets / matches

        wicket_component = math.log(
            max(wickets_per_match, 0.01) / volume_baseline
        )

        if pd.notna(economy) and economy > 0:
            economy_component = math.log(
                rate_baseline / economy
            )
            performance = (
                0.60 * wicket_component
                + 0.40 * economy_component
            )
        else:
            # Wicket-only evaluation has reduced coverage.
            performance = wicket_component * 0.60

    # Low samples shrink toward neutral form (3/5).
    sample_weight = matches / (matches + 10)

    score = 3 + sample_weight * 1.5 * math.tanh(
        performance / 0.45
    )

    return round(max(0, min(5, score)), 2), round(
        sample_weight, 3
    )

rows = []

for _, row in data.iterrows():
    if row["player"] not in TARGETS:
        continue

    score, weight = form_score(row)

    rows.append({
        "player": row["player"],
        "competition": row["competition"],
        "format": row["format"],
        "matches": int(row["matches"]),
        "aggregate_form_score": score,
        "sample_weight": weight,
        "model_type": "AGGREGATE_FORM_PROXY",
        "pressure_model_validated": False,
        "reliability_model_validated": False,
        "source": row["source"],
    })

scores = pd.DataFrame(rows)
scores.to_csv(
    OUT / "remaining_seven_model.csv", index=False
)

with DASH.open(encoding="utf-8") as f:
    dashboard = json.load(f)

lookup = scores.set_index("player")
evidence_lookup = data.set_index("player")

def optional_number(value):
    return None if pd.isna(value) else float(value)

for player in dashboard["players"]:
    name = player["name"]

    if name not in TARGETS or name not in lookup.index:
        continue

    score = lookup.loc[name]
    evidence = evidence_lookup.loc[name]

    player["aggregateFormScore"] = optional_number(
        score["aggregate_form_score"]
    )
    player["aggregateSampleWeight"] = float(
        score["sample_weight"]
    )
    player["aggregateModelType"] = "AGGREGATE_FORM_PROXY"

    # Keep the previously calculated HITL pressure,
    # reliability and overall scores unchanged.
    player["regionalEvidence"] = [{
        "competition": str(evidence["competition"]),
        "format": str(evidence["format"]),
        "matches": int(evidence["matches"]),
        "runs": optional_number(evidence["runs"]),
        "balls": optional_number(evidence["balls"]),
        "wickets": optional_number(evidence["wickets"]),
        "economy": optional_number(evidence["economy"]),
        "strikeRate": optional_number(evidence["strike_rate"]),
        "evidenceType": str(evidence["evidence_type"]),
        "source": str(evidence["source"]),
    }]

dashboard["version"] = "0.5-HITL-aggregate-form"
dashboard["aggregateScoreMethod"] = (
    "Reference-based, sample-shrunk tournament form proxy"
)

with DASH.open("w", encoding="utf-8") as f:
    json.dump(dashboard, f, indent=2, allow_nan=False)

print("\n=== REMAINING SEVEN MODEL POINTS ===")
print(
    scores[[
        "player", "format", "matches",
        "aggregate_form_score", "sample_weight"
    ]].to_string(index=False)
)

print("\nModel form profiles:",
      scores["aggregate_form_score"].notna().sum())
print("Saved:", OUT / "remaining_seven_model.csv")
print("Dashboard JSON updated.")
