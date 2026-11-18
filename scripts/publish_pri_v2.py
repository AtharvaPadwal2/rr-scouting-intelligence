import json
from pathlib import Path

ROOT = Path.cwd()

source = ROOT / "outputs/final_royal_edge_pri_v2.json"
public = ROOT / "frontend/public/royal-edge-pri-v2.json"
page = ROOT / "frontend/src/app/pressure-intelligence/page.tsx"

data = json.loads(source.read_text(encoding="utf-8"))

batting = data["batting"]
bowling = data["bowling"]

assert len(batting) == 10
assert len(bowling) == 10

all_players = batting + bowling
assert len({p["name"] for p in all_players}) == 20

# Adapt the new PRI v2 schema to the existing
# selected-player dashboard's expected schema.
players = []

for role, group in [
    ("Batting", batting),
    ("Bowling", bowling),
]:
    for p in group:
        players.append({
            "name": p["name"],
            "role": role,
            "rank": p["rank"],

            "pressureScore": p["pressureScore"],
            "reliabilityScore": p["reliabilityScore"],
            "overallScore": p["overallScore"],

            "modelPressure": p["modelPressure"],
            "modelReliability": p["modelReliability"],

            "humanPressure": p["humanPressure"],
            "humanReliability": p["humanReliability"],

            "modelWeight": p["modelWeight"],
            "humanWeight": p["humanWeight"],

            "modelMatches": p["pressureMatches"],
            "pressureBalls": p["pressureBalls"],
            "positiveMatchPct": p["positiveMatchPct"],
            "top10StabilityPct": p["top10StabilityPct"],

            "assessmentMethod": p["assessmentMethod"],
            "scoutingRationale": p.get("evidenceNotes", ""),
            "sourceReference": p.get("sourceReference", ""),
            "sourceVerified": False,
            "confidence": p["confidence"],

            "phasePerformance": [],
            "regionalEvidence": [],
        })

payload = {
    "model": "ROYAL EDGE HYBRID PRI v2",
    "version": "2.0-statistical-reliability",
    "scoresValidated": False,
    "methodology": data["methodology"],
    "players": players,
}

# Use public root instead of public/data,
# because the repository ignores data/ directories.
public.write_text(
    json.dumps(payload, indent=2, ensure_ascii=False),
    encoding="utf-8"
)

# Change only the picks page's data source.
code = page.read_text(encoding="utf-8")

old_path = "/data/scouting_scores.json"
new_path = "/royal-edge-pri-v2.json"

if old_path in code:
    code = code.replace(old_path, new_path)
elif new_path not in code:
    raise RuntimeError("Expected fetch path not found")

# Correct misleading source-verification wording.
code = code.replace(
    '"Verified through online sources ( Cricbuzz, Crex, Cricinfo)"',
    '"Analyst evidence; independent verification pending"'
)

# Replace misleading historical match-count labels.
code = code.replace(
    'RR matches: {active.rrMatches ?? 0} · SMAT matches: {active.smatMatches ?? 0} · Scored model matches:{" "}',
    'Official pressure matches:{" "}'
)

code = code.replace(
    "<span><Dot color={COLORS.pink} />Final HITL</span>",
    "<span><Dot color={COLORS.pink} />Hybrid PRI v2</span>"
)

page.write_text(code, encoding="utf-8")

print("\nSUCCESS: PRI v2 dashboard connected")
print("Players:", len(players))
print("Batters:", len(batting))
print("Bowlers:", len(bowling))
print("JSON:", public)
print("Page:", page)
