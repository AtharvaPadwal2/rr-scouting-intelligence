"""Reproducible fictional T20 season records for local development."""
import argparse
from pathlib import Path
from random import Random

import pandas as pd

ROLES = ("Opener", "Finisher", "Wicketkeeper-batter", "Pace bowler",
         "Spin bowler", "All-rounder")
TEAMS = ("Pink Dunes", "Blue Harbors", "Silver Peaks", "Amber Falcons")
SEASONS = (2024, 2025, 2026)


def generate_players(seed: int = 42, players: int = 96) -> pd.DataFrame:
    """Return one row per fictional player and season, with seeded test defects."""
    if players < 1:
        raise ValueError("players must be positive")

    rng = Random(seed)
    rows = []
    for index in range(players):
        role = ROLES[index % len(ROLES)]
        age = rng.randint(16, 23)
        team = rng.choice(TEAMS)
        batting_style = rng.choice(("Right-hand bat", "Left-hand bat"))
        bowling_style = {
            "Pace bowler": "Right-arm pace", "Spin bowler": "Left-arm spin",
            "All-rounder": "Right-arm pace",
        }.get(role)
        batting_rate = rng.gauss(1.35 if role == "Finisher" else 1.18, 0.18)
        batting_trend = rng.uniform(-0.07, 0.12)
        bowling_economy = rng.uniform(6.4, 9.7)
        bowling_trend = rng.uniform(-0.55, 0.35)

        for offset, season in enumerate(SEASONS):
            matches = rng.randint(2, 14)
            innings = rng.randint(max(1, matches - 3), matches)
            tailender = role in ("Pace bowler", "Spin bowler")
            balls = innings * rng.randint(3, 9) if tailender else innings * rng.randint(10, 25)
            runs = max(0, round(balls * (batting_rate + offset * batting_trend)))
            dismissals = rng.randint(0, innings) if tailender else rng.randint(1, innings)
            legal_balls = rng.randint(8, 23) * matches if bowling_style else None
            rows.append({
                "source": "synthetic",
                "player_id": f"SYN-{index + 1:03}",
                "player_name": f"Fictional Prospect {index + 1:03}",
                "team": team,
                "season": season,
                "format": "T20",
                "competition": "Fictional Domestic T20 Cup",
                "age_at_season_end": age + offset,
                "role": role,
                "batting_style": batting_style,
                "bowling_style": bowling_style,
                "nationality": "Indian",
                "internationally_capped": False,
                "matches": matches,
                "batting_innings": innings,
                "balls_faced": balls,
                "runs": runs,
                "dismissals": dismissals,
                "legal_balls_bowled": legal_balls,
                "runs_conceded": (
                    round(legal_balls / 6 * (bowling_economy + offset * bowling_trend))
                    if legal_balls is not None else None
                ),
                "wickets": rng.randint(0, matches * 2) if legal_balls is not None else None,
            })

    frame = pd.DataFrame(rows).astype({
        "balls_faced": "Int64", "legal_balls_bowled": "Int64",
        "runs_conceded": "Int64", "wickets": "Int64",
    })
    frame.loc[0, "balls_faced"] = pd.NA
    frame.loc[1, "role"] = f"  {frame.loc[1, 'role'].lower()}  "
    frame.loc[2, "runs"] = -1
    return pd.concat([frame, frame.iloc[[0]]], ignore_index=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--players", type=int, default=96)
    parser.add_argument("--output", type=Path, default=Path("data/synthetic/players.csv"))
    args = parser.parse_args()
    if args.players < 1:
        parser.error("--players must be positive")

    frame = generate_players(seed=args.seed, players=args.players)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(args.output, index=False, mode="x")
    print(f"Wrote {len(frame)} rows to {args.output}")


if __name__ == "__main__":
    main()
