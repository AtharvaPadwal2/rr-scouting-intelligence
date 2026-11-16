
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "processed"
REPORTS = ROOT / "data" / "reports"
REPORTS.mkdir(parents=True, exist_ok=True)

RR = "Rajasthan Royals"

# Load previously computed and validated analysis.
league = pd.read_csv(
    DATA / "ipl_2026_team_phase_comparison.csv"
)

results = pd.read_csv(
    DATA / "rr_2026_match_phase_analysis.csv"
)

deliveries = pd.read_csv(
    DATA / "rr_2026_deliveries.csv",
    low_memory=False
)

# ----------------------------------------
# 1. Extract RR league rankings.
# ----------------------------------------
rr = league[league["team"] == RR].copy()

def league_metric(discipline, phase):
    row = rr[
        (rr["discipline"] == discipline)
        & (rr["phase"] == phase)
    ].iloc[0]

    return {
        "rank": int(row["league_rank"]),
        "rate": round(float(row["run_rate"]), 2),
        "league_rate": round(
            float(row["league_run_rate"]), 2
        )
    }

# ----------------------------------------
# 2. Calculate weighted win/loss rates.
# ----------------------------------------
def result_metric(result, role, phase):
    rows = results[
        (results["result"] == result)
        & (results["rr_role"] == role)
        & (results["phase"] == phase)
    ]

    balls = rows["balls"].sum()

    return {
        "rate": round(
            6 * rows["runs"].sum() / balls, 2
        ) if balls else None,
        "wickets": int(rows["wickets"].sum()),
        "balls": int(balls)
    }

# ----------------------------------------
# 3. Recruitment profiles.
#
# Review priorities are analyst-set.
# They are NOT ML-generated scores.
# ----------------------------------------
profiles = [
    {
        "gap_id": "RR-G01",
        "role": "Powerplay Indian Pacer",
        "discipline": "bowling",
        "phase": "powerplay",
        "priority": 5,
        "desired_attributes":
            "New-ball swing/seam; early wickets; "
            "low boundary concession; right/left-hand matchups",
        "domestic_filters":
            "SMAT powerplay wickets, economy, "
            "wickets per legal ball, sample size",
        "existing_options":
            "JC Archer; N Burger; Brijesh Sharma; "
            "TU Deshpande; Sandeep Sharma",
    },
    {
        "gap_id": "RR-G02",
        "role": "Death-Over Indian Pacer",
        "discipline": "bowling",
        "phase": "death",
        "priority": 5,
        "desired_attributes":
            "Yorkers; slower balls; boundary prevention; "
            "death-over wickets; repeatable execution",
        "domestic_filters":
            "SMAT death economy, boundary rate, "
            "wickets, phase workload, consistency",
        "existing_options":
            "JC Archer; Brijesh Sharma; "
            "TU Deshpande; N Burger",
    },
    {
        "gap_id": "RR-G03",
        "role": "Indian Finisher / All-Rounder",
        "discipline": "batting",
        "phase": "death",
        "priority": 4,
        "desired_attributes":
            "Death-over strike rate; boundary hitting; "
            "finishing consistency; optional bowling value",
        "domestic_filters":
            "SMAT death SR, boundary %, balls faced, "
            "dismissal rate; VHT finishing; bowling contribution",
        "existing_options":
            "D Ferreira; Dhruv Jurel; RA Jadeja; "
            "SO Hetmyer; SB Dubey",
    },
    {
        "gap_id": "RR-G04",
        "role": "Middle-Over Wicket-Taker",
        "discipline": "bowling",
        "phase": "middle",
        "priority": 3,
        "desired_attributes":
            "Wicket-taking threat; spin/seam variation; "
            "dot-ball pressure; suitable matchups",
        "domestic_filters":
            "SMAT middle-over bowling SR, economy, "
            "dot-ball %, opponent quality, sample size",
        "existing_options":
            "RA Jadeja; Ravi Bishnoi; Yash Raj Punja; "
            "Brijesh Sharma",
    },
]

# ----------------------------------------
# 4. Build evidence-backed gap report.
# ----------------------------------------
records = []

for profile in profiles:
    discipline = profile["discipline"]
    phase = profile["phase"]

    role = (
        "Batting" if discipline == "batting"
        else "Bowling"
    )

    lm = league_metric(discipline, phase)
    wins = result_metric("Win", role, phase)
    losses = result_metric("Loss", role, phase)

    record = {
        **profile,
        "ipl_rank": lm["rank"],
        "rr_run_rate": lm["rate"],
        "league_run_rate": lm["league_rate"],
        "rr_minus_league": round(
            lm["rate"] - lm["league_rate"], 2
        ),
        "run_rate_in_wins": wins["rate"],
        "run_rate_in_losses": losses["rate"],
        "wickets_in_wins": wins["wickets"],
        "wickets_in_losses": losses["wickets"],
        "legal_balls_in_wins": wins["balls"],
        "legal_balls_in_losses": losses["balls"],
        "priority_label": (
            "High" if profile["priority"] >= 4
            else "Medium"
        ),
        "evidence_status": "Provisional",
        "squad_status": "Requires IPL 2027 verification",
    }

    records.append(record)

gaps = pd.DataFrame(records).sort_values(
    ["priority", "ipl_rank"],
    ascending=[False, False]
)

# ----------------------------------------
# 5. Create historical squad evidence.
# ----------------------------------------
kind = (
    deliveries["wicket_kind"]
    .fillna("")
    .str.lower()
    .str.strip()
)

deliveries["legal"] = ~(
    deliveries["extras_detail"].notna()
    | deliveries["c1"].notna()
)

deliveries["bowler_wicket"] = (
    kind.ne("")
    & ~kind.isin([
        "run out", "retired hurt",
        "retired out", "obstructing the field"
    ])
)

historical = deliveries[
    deliveries["bowling_team"] == RR
].copy()

bowling_options = (
    historical.groupby(["bowler", "phase"])
    .agg(
        matches=("match_id", "nunique"),
        legal_balls=("legal", "sum"),
        team_runs_conceded=("runs_total", "sum"),
        wickets=("bowler_wicket", "sum")
    )
    .reset_index()
)

bowling_options["runs_per_over"] = (
    bowling_options["team_runs_conceded"] * 6
    / bowling_options["legal_balls"].replace(0, float("nan"))
).round(2)

bowling_options["sample_qualified"] = (
    bowling_options["legal_balls"] >= 60
)

bowling_options.to_csv(
    DATA / "rr_2026_existing_bowling_options.csv",
    index=False
)

# ----------------------------------------
# 6. Export scouting gap report.
# ----------------------------------------
gaps.to_csv(
    DATA / "rr_squad_gap_report.csv",
    index=False
)

print("\n=== RR 2027 SQUAD GAP REPORT ===")

print(
    gaps[
        [
            "gap_id", "role", "priority_label",
            "ipl_rank", "rr_run_rate",
            "league_run_rate",
            "run_rate_in_wins",
            "run_rate_in_losses",
        ]
    ].to_string(index=False)
)

print("\n=== OUTPUT FILES ===")
print("rr_squad_gap_report.csv")
print("rr_2026_existing_bowling_options.csv")

print("\nIMPORTANT:")
print("Player options are from IPL 2026 appearances.")
print("Retention and IPL 2027 auction eligibility remain unverified.")
