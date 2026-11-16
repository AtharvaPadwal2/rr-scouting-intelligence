
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "processed" / "rr_official"

states = pd.read_csv(
    DATA / "match_states_preliminary.csv", low_memory=False
)
matches = pd.read_csv(
    DATA / "matches_clean.csv", low_memory=False
)
roster = pd.read_csv(
    DATA / "ipl_2026_roster_proxy.csv", low_memory=False
)
players = pd.read_csv(
    DATA / "players_clean.csv", low_memory=False
)

# Build unique player identity registry.
names = (
    players[["player_id", "player_name"]]
    .dropna(subset=["player_id"])
    .drop_duplicates("player_id")
)

roster = (
    roster.drop(columns=["player_name"], errors="ignore")
    .merge(names, on="player_id", how="left")
    [["player_id", "player_name", "ipl_2026_team"]]
    .drop_duplicates("player_id")
)

# Attach competition metadata.
meta = matches[
    ["match_id", "comp_name", "match_format"]
].drop_duplicates("match_id")

states = states.drop(
    columns=["comp_name", "match_format"], errors="ignore"
).merge(meta, on="match_id", how="left", validate="many_to_one")

states = states.loc[
    states["pressure_eligible"].astype(str).str.lower().eq("true")
    & states["structural_pressure_level"].isin(["High", "Extreme"])
].copy()

states["competition_group"] = np.select(
    [
        states["comp_name"].fillna("").str.match(
            r"^IPL 20\d{2}$", case=False
        ),
        states["match_format"].fillna("").str.upper().eq("T20I")
    ],
    ["IPL", "T20I"],
    default="OTHER_T20"
)

states["runs"] = pd.to_numeric(
    states["runs"], errors="coerce"
).fillna(0)

extras = states["extras_type"].fillna("").str.lower()
states["bat_ball"] = ~extras.eq("wide")
states["legal_ball"] = ~extras.isin(
    ["wide", "overstep", "other"]
)

dismissal = (
    states["dismissal_type"].fillna("")
    .astype(str).str.lower()
    .str.replace(r"[\s_-]+", "", regex=True)
)

states["bowler_wicket"] = (
    dismissal.ne("")
    & ~dismissal.isin([
        "runout", "retiredout", "retiredhurt",
        "obstructingthefield"
    ])
)

# Benchmarks are competition + phase specific.
def calculate(kind, ipl_only=False):
    df = states.copy()

    if ipl_only:
        df = df[df["competition_group"].eq("IPL")].copy()

    if kind == "bat":
        df = df[df["bat_ball"]].copy()
        id_col = "striker_id"

        reference = df.groupby(
            ["competition_group", "pressure_phase"]
        )["runs"].mean().rename("expected_rate")

        df = df.join(
            reference,
            on=["competition_group", "pressure_phase"]
        )
        df["impact"] = df["runs"] - df["expected_rate"]

        output = df.groupby(id_col).agg(
            balls=("bat_ball", "sum"),
            matches=("match_id", "nunique"),
            runs=("runs", "sum"),
            impact=("impact", "sum")
        ).reset_index().rename(columns={id_col: "player_id"})

        output["raw_impact"] = (
            100 * output["impact"] / output["balls"]
        )

    else:
        df = df[df["legal_ball"]].copy()
        id_col = "bowler_id"

        reference = df.groupby(
            ["competition_group", "pressure_phase"]
        ).agg(
            expected_runs=("runs", "mean"),
            expected_wickets=("bowler_wicket", "mean")
        )

        df = df.join(
            reference,
            on=["competition_group", "pressure_phase"]
        )

        df["runs_prevented"] = (
            df["expected_runs"] - df["runs"]
        )
        df["wicket_impact"] = (
            df["bowler_wicket"].astype(int)
            - df["expected_wickets"]
        )

        output = df.groupby(id_col).agg(
            balls=("legal_ball", "sum"),
            matches=("match_id", "nunique"),
            wickets=("bowler_wicket", "sum"),
            runs_prevented=("runs_prevented", "sum"),
            wicket_impact=("wicket_impact", "sum")
        ).reset_index().rename(columns={id_col: "player_id"})

        output["raw_impact"] = (
            6 * output["runs_prevented"] / output["balls"]
            + 10 * output["wicket_impact"] / output["balls"]
        )

    # Same shrinkage rule as the earlier model.
    output["reliability"] = (
        output["balls"] / (output["balls"] + 120)
        * np.minimum(output["matches"] / 10, 1)
    )

    output["adjusted_score"] = (
        output["raw_impact"] * output["reliability"]
    )

    output = output.merge(
        roster, on="player_id", how="inner",
        validate="many_to_one"
    )

    output = output.loc[
        (output["balls"] >= 30)
        & (output["matches"] >= 3)
    ].copy()

    output = output.sort_values(
        ["adjusted_score", "balls"],
        ascending=[False, False]
    ).reset_index(drop=True)

    output["rank"] = np.arange(1, len(output) + 1)
    return output


for kind, label in [("bat", "batting"), ("bowl", "bowling")]:
    all_t20 = calculate(kind, ipl_only=False)
    ipl = calculate(kind, ipl_only=True)

    all_t20.to_csv(
        DATA / f"{label}_competition_normalized.csv",
        index=False
    )

    ipl.to_csv(
        DATA / f"{label}_ipl_only_rankings.csv",
        index=False
    )

    comparison = all_t20[[
        "player_id", "player_name", "ipl_2026_team",
        "rank", "balls", "adjusted_score"
    ]].rename(columns={
        "rank": "all_t20_rank",
        "balls": "all_t20_balls",
        "adjusted_score": "all_t20_score"
    })

    comparison = comparison.merge(
        ipl[[
            "player_id", "rank", "balls", "adjusted_score"
        ]].rename(columns={
            "rank": "ipl_rank",
            "balls": "ipl_balls",
            "adjusted_score": "ipl_score"
        }),
        on="player_id", how="left"
    )

    comparison["rank_change"] = (
        comparison["all_t20_rank"] - comparison["ipl_rank"]
    )

    comparison.to_csv(
        DATA / f"{label}_ipl_vs_all_t20.csv",
        index=False
    )

    print(f"\n=== {label.upper()}: IPL-ONLY TOP 20 ===")
    print(
        ipl[[
            "rank", "player_name", "ipl_2026_team",
            "matches", "balls", "adjusted_score"
        ]].head(20).round(2).to_string(index=False)
    )

    print(f"\n=== {label.upper()}: ALL-T20 TOP 10 COMPARISON ===")
    print(
        comparison[[
            "player_name", "all_t20_rank",
            "ipl_rank", "rank_change",
            "all_t20_balls", "ipl_balls"
        ]].head(10).to_string(index=False)
    )

    print(
        f"\nQualified {label}:",
        f"all T20={len(all_t20)}, IPL-only={len(ipl)}"
    )

print("\nCompetition-adjusted outputs saved.")
print("CAUTION: Structural-pressure proxy; not final rankings.")
