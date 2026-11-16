
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "outputs"
OUT.mkdir(exist_ok=True)

records = [
    {
        "player": "Tushar Raheja",
        "competition": "TNPL 2026",
        "format": "T20",
        "role": "batting",
        "matches": 8,
        "runs": 422,
        "balls": 222,
        "wickets": None,
        "economy": None,
        "source": "https://www.crictracker.com/t20/tnpl/stats/batting-most-runs/",
    },
    {
        "player": "Yajas Sharma",
        "competition": "DPL 2026",
        "format": "T20",
        "role": "batting",
        "matches": 10,
        "runs": 365,
        "balls": 180,
        "wickets": None,
        "economy": None,
        "source": "https://www.crictracker.com/delhi-premier-league-t20/stats/batting-most-runs/",
    },
    {
        "player": "Aaryavir Sehwag",
        "competition": "U19 Asia Cup 2026",
        "format": "ODI",
        "role": "batting",
        "matches": 5,
        "runs": 361,
        "balls": None,
        "wickets": None,
        "economy": None,
        "source": "https://www.bcci.tv/news/article/india-u19-clinch-asia-cup-after-heroic-last-ball-win-over-pakistan",
    },
    {
        "player": "Khilan Patel",
        "competition": "U19 World Cup 2026",
        "format": "ODI",
        "role": "bowling",
        "matches": 7,
        "runs": None,
        "balls": 332,
        "wickets": 9,
        "economy": 5.01,
        "source": "https://www.cricbuzz.com/player-match-performance/match/138653/player/1460816/bowling?inningsId=2",
    },
    {
        "player": "Mohit Ulva",
        "competition": "U19 Asia Cup Final 2026",
        "format": "ODI",
        "role": "batting",
        "matches": 1,
        "runs": 49,
        "balls": 26,
        "wickets": None,
        "economy": None,
        "source": "https://www.bcci.tv/news/article/india-u19-clinch-asia-cup-after-heroic-last-ball-win-over-pakistan",
    },
]

df = pd.DataFrame(records)

df["strike_rate"] = (
    100 * df["runs"] / df["balls"]
).round(2)

df["evidence_type"] = df["matches"].apply(
    lambda n: "SINGLE_MATCH"
    if n == 1 else "TOURNAMENT_AGGREGATE"
)

df["t20_model_eligible"] = False

df.to_csv(
    OUT / "regional_verified_evidence.csv",
    index=False
)

remaining = [
    "Shubham Kumar Gupta",
    "Ishant Bharadwaj",
]

pd.DataFrame({
    "player": remaining,
    "status": ["SOURCE_REQUIRED"] * 2,
}).to_csv(
    OUT / "regional_evidence_pending.csv",
    index=False
)

print("\n=== REGIONAL EVIDENCE IMPORT ===")
print(
    df[[
        "player", "competition", "format",
        "matches", "runs", "wickets", "strike_rate"
    ]].to_string(index=False)
)

print("\nVerified evidence records:", len(df))
print("Further verification required:", len(remaining))
