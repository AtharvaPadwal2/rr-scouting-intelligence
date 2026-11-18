from pathlib import Path
from datetime import datetime
import json
import shutil
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs"
DATA = ROOT / "data/processed/rr_official"
OUT.mkdir(exist_ok=True)

HUMAN = OUT / "human_scouting_assessments_final.csv"

REMOVE = {
    "Tanush Kotian",
    "Chetan Sakariya",
    "Simarjeet Singh",
}

ADD = [
    "Avesh Khan",
    "Suyash Sharma",
    "Gurjapneet Singh",
]

BATTERS = [
    "Daryl Mitchell",
    "Shai Hope",
    "Naman Dhir",
    "Glenn Phillips",
    "Tilak Varma",
    "David Miller",
    "Harry Brook",
    "Jacob Bethell",
    "Ashutosh Sharma",
    "Shashank Singh",
]

BOWLERS = [
    "Josh Tongue",
    "Gerald Coetzee",
    "Shamar Springer",
    "Jamie Overton",
    "Umran Malik",
    "Mitchell Santner",
    "Harshit Rana",
    "Avesh Khan",
    "Suyash Sharma",
    "Gurjapneet Singh",
]

ALIASES = {
    "Tilak Varma": "Namboori Tilak Varma",
}

SOURCES = {
    "Batting": DATA / "pressure_batting_reliability.csv",
    "Bowling": DATA / "pressure_bowling_reliability.csv",
}

def weight_for(balls):
    if balls >= 600:
        return 0.70
    if balls >= 250:
        return 0.50
    if balls > 0:
        return 0.30
    return 0.0

def ask_rating(name, metric):
    while True:
        value = input(
            f"{name} - {metric} /5: "
        ).strip()
        try:
            number = float(value)
            if np.isfinite(number) and 0 <= number <= 5:
                return number
        except ValueError:
            pass
        print("Enter a number between 0 and 5.")

# Read existing human assessments
if not HUMAN.exists():
    raise SystemExit(f"Missing human CSV: {HUMAN}")

human = pd.read_csv(HUMAN)

required = {
    "name", "role",
    "human_pressure", "human_reliability",
    "evidence_notes", "source_reference",
}
if not required.issubset(human.columns):
    raise SystemExit("Human CSV has missing columns.")

human["name"] = human["name"].str.strip()
human = human[~human["name"].isin(REMOVE)].copy().reset_index(drop=True)

if human["name"].duplicated().any():
    raise SystemExit("Duplicate human assessments found.")

# Read official pressure model
models = {}

for role, path in SOURCES.items():
    model = pd.read_csv(path)

    model["base_adjusted_score"] = pd.to_numeric(
        model["base_adjusted_score"],
        errors="coerce"
    )
    model = model.dropna(
        subset=["base_adjusted_score"]
    ).copy()

    if model["player_id"].duplicated().any():
        raise SystemExit(
            f"Duplicate player IDs in {path.name}"
        )

    models[role] = model

# Check replacements before requesting ratings
print("\n=== NEW BOWLER MODEL COVERAGE ===")

bowling_model = models["Bowling"]

for name in ADD:
    match = bowling_model[
        bowling_model["player_name"]
        .astype(str).str.casefold()
        .eq(name.casefold())
    ]

    if len(match) != 1:
        raise SystemExit(
            f"{name}: No unique qualifying model record. "
            "Check official name or sample threshold."
        )

    row = match.iloc[0]
    print(
        f"{name:<20} "
        f"Rank={int(row['base_rank']):<5} "
        f"Balls={int(row['balls']):<5} "
        f"Matches={int(row['matches'])}"
    )

# Request analyst ratings without inventing values
for name in ADD:
    if name in human["name"].values:
        continue

    print(f"\n=== HUMAN REVIEW: {name} ===")

    hp = ask_rating(name, "Human Pressure")
    hr = ask_rating(name, "Human Reliability")

    human.loc[len(human)] = {
        "name": name,
        "role": "Bowling",
        "human_pressure": hp,
        "human_reliability": hr,
        "evidence_notes": "",
        "source_reference": "",
    }

# Validate exact final selection
expected = {
    "Batting": set(BATTERS),
    "Bowling": set(BOWLERS),
}

for role, names in expected.items():
    actual = set(
        human.loc[human["role"].eq(role), "name"]
    )
    if actual != names:
        raise SystemExit(
            f"{role} mismatch. "
            f"Missing: {sorted(names - actual)}; "
            f"Extra: {sorted(actual - names)}"
        )

if len(human) != 20 or human["name"].duplicated().any():
    raise SystemExit("Final shortlist validation failed.")

for col in ["human_pressure", "human_reliability"]:
    values = pd.to_numeric(human[col], errors="coerce")
    if not values.notna().all() or not values.between(0, 5).all():
        raise SystemExit(f"Invalid values in {col}")
    human[col] = values

# Score players using the existing hybrid approach
rankings = {"batting": [], "bowling": []}

for role, key in [
    ("Batting", "batting"),
    ("Bowling", "bowling"),
]:
    model = models[role]

    distribution = np.sort(
        model["base_adjusted_score"]
        .to_numpy(dtype=float)
    )

    for _, h in human[human["role"].eq(role)].iterrows():
        name = h["name"]
        official_name = ALIASES.get(name, name)

        found = model[
            model["player_name"]
            .astype(str).str.casefold()
            .eq(official_name.casefold())
        ]

        if len(found) > 1:
            raise SystemExit(f"Ambiguous model name: {name}")

        hp = float(h["human_pressure"])
        hr = float(h["human_reliability"])

        if found.empty:
            if name in ADD:
                raise SystemExit(
                    f"New player has no model coverage: {name}"
                )

            # Existing missing-coverage cases are disclosed.
            balls = 0
            matches = 0
            model_pressure = None
            raw_impact = None
            overall_rank = None
            positive_pct = None
            stability_pct = None
            weight = 0.0
            method = "ANALYST_ONLY_NO_MODEL_COVERAGE"
            confidence = "NO_MODEL_COVERAGE"

        else:
            row = found.iloc[0]

            balls = int(row["balls"])
            matches = int(row["matches"])
            raw_impact = float(
                row["base_adjusted_score"]
            )

            percentile = (
                np.searchsorted(
                    distribution,
                    raw_impact,
                    side="right"
                ) / len(distribution)
            )

            model_pressure = float(5 * percentile)
            weight = weight_for(balls)

            overall_rank = int(row["base_rank"])

            positive_pct = (
                float(row["positive_match_pct"])
                if pd.notna(row["positive_match_pct"])
                else None
            )

            stability_pct = (
                float(row["top_10_scenario_pct"])
                if pd.notna(row["top_10_scenario_pct"])
                else None
            )

            method = "HYBRID_OFFICIAL_PRESSURE_MODEL"

            if balls < 60 or matches < 5:
                confidence = "LIMITED"
            elif balls < 150 or matches < 15:
                confidence = "MODERATE"
            else:
                confidence = "STRONG"

        final_pressure = (
            weight * model_pressure
            + (1 - weight) * hp
            if model_pressure is not None
            else hp
        )

        final_reliability = hr
        pri = final_pressure + final_reliability

        rankings[key].append({
            "name": name,
            "role": role,
            "officialPlayerName": official_name,
            "pressureScore": round(final_pressure, 3),
            "reliabilityScore": round(final_reliability, 3),
            "overallScore": round(pri, 3),
            "modelPressure": (
                round(model_pressure, 3)
                if model_pressure is not None else None
            ),
            "humanPressure": hp,
            "humanReliability": hr,
            "modelWeight": weight,
            "humanWeight": round(1 - weight, 2),
            "modelAdjustedImpact": (
                round(raw_impact, 4)
                if raw_impact is not None else None
            ),
            "officialPoolRank": overall_rank,
            "pressureBalls": balls,
            "pressureMatches": matches,
            "positiveMatchPct": positive_pct,
            "top10StabilityPct": stability_pct,
            "confidence": confidence,
            "assessmentMethod": method,
            "evidenceNotes": (
                str(h["evidence_notes"])
                if pd.notna(h["evidence_notes"]) else ""
            ),
            "sourceReference": (
                str(h["source_reference"])
                if pd.notna(h["source_reference"]) else ""
            ),
        })

    rankings[key].sort(
        key=lambda x: (
            -x["overallScore"],
            -x["pressureBalls"],
            x["name"]
        )
    )

    for i, player in enumerate(rankings[key], 1):
        player["rank"] = i

    assert len(rankings[key]) == 10

payload = {
    "model": "ROYAL EDGE HYBRID PRI",
    "version": "1.1-revised-shortlist",
    "scoresValidated": False,
    "methodology": {
        "pressureScale": [0, 5],
        "reliabilityScale": [0, 5],
        "priScale": [0, 10],
        "modelNormalization":
            "Role-specific percentile of provisional "
            "adjusted structural-pressure impact",
        "modelWeightsByPressureBalls": {
            "1-249": 0.30,
            "250-599": 0.50,
            "600+": 0.70,
        },
        "pressureFormula":
            "w * modelPressure + (1-w) * humanPressure",
        "reliabilityFormula": "humanReliability",
        "priFormula":
            "pressureScore + reliabilityScore",
        "limitations": [
            "Structural-pressure proxy is provisional",
            "Bowling extras accounting is not fully validated",
            "Analyst ratings are subjective assessments",
            "Ranks compare only the selected 10 per role",
            "PDF phase weights are not independently "
            "recomputed in this exporter",
        ],
    },
    "batting": rankings["batting"],
    "bowling": rankings["bowling"],
}

# Back up existing outputs before replacing them
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
backup_dir = OUT / "backups" / timestamp
backup_dir.mkdir(parents=True, exist_ok=True)

paths = [
    HUMAN,
    OUT / "final_royal_edge_pri.json",
    OUT / "final_royal_edge_pri.csv",
]

for path in paths:
    if path.exists():
        shutil.copy2(path, backup_dir / path.name)

# Write revised assessment file and rankings
human.to_csv(HUMAN, index=False)

json_path = OUT / "final_royal_edge_pri.json"
csv_path = OUT / "final_royal_edge_pri.csv"

json_path.write_text(
    json.dumps(
        payload,
        indent=2,
        ensure_ascii=False,
        allow_nan=False
    ),
    encoding="utf-8"
)

flat = pd.DataFrame(
    rankings["batting"] + rankings["bowling"]
)
flat.to_csv(csv_path, index=False)

for key in ["batting", "bowling"]:
    print(f"\n=== FINAL {key.upper()} PRI ===")
    print(
        pd.DataFrame(rankings[key])[
            [
                "rank",
                "name",
                "pressureScore",
                "reliabilityScore",
                "overallScore",
                "confidence",
            ]
        ].to_string(index=False)
    )

print("\nSUCCESS")
print("Players:", len(flat))
print("JSON:", json_path)
print("CSV:", csv_path)
print("Human review:", HUMAN)
print("Backup:", backup_dir)
