# RR Scouting Intelligence — Squad Gap Analytics Page

A standalone Next.js App Router page using live local CSV analysis exports. Styled in Rajasthan Royals-inspired pink/navy. No chart values are hardcoded; they are read from your processed files.

## Install in your EXISTING Next.js frontend

From `D:\rr-scouting-intelligence\frontend`:

```powershell
npm install recharts lucide-react csv-parse
```

Copy the supplied `app/rr-gap/` and `app/api/rr-gap/` folders into your frontend's `app/` directory.

If your project uses `src/app`, instead put them inside `frontend/src/app/`.

The API looks for `../data/processed` relative to the Next.js working directory by default. This matches:

```text
D:\rr-scouting-intelligence\
├── data\processed\
│   ├── rr_squad_gap_report.csv
│   ├── ipl_2026_team_phase_comparison.csv
│   ├── rr_2026_match_phase_analysis.csv
│   ├── rr_2026_bowler_phase_analysis.csv
│   ├── rr_2026_middle_win_loss.csv
│   └── rr_2026_death_batters.csv
└── frontend\
    └── app\...
```

If your folder layout differs, create `.env.local` inside `frontend`:

```env
RR_DATA_DIR=D:/rr-scouting-intelligence/data/processed
```

Then run:

```powershell
npm run dev
```

Visit http://localhost:3000/rr-gap (or whichever port your Next.js server uses).

## Features
- Season KPI strip showing RR match count, phase rank and death-overs conceding in losses.
- Batting versus conceded run-rate chart.
- RR versus IPL benchmark by phase (toggle batting/bowling).
- Win versus loss run rates and wickets by match phase.
- Player-level bowling splits (powerplay/middle/death) with sample-size threshold.
- Finisher strike-rate chart with win/loss filters.
- Interactive scouting requirement panels loaded from `rr_squad_gap_report.csv`.
- CSV export of the gap report and refresh action.
- Source-missing warnings and API error state.

## Important limitations
- Historical IPL 2026 figures are provisional until reconciled against external scorecards.
- Player run-conceded metric includes team extras (byes/leg-byes), so it is **not** official personal bowler economy.
- Win/loss sample sizes are not necessarily equal.
- The API serves local analysis data over HTTP: run locally and do **not** deploy publicly with confidential RR scouting files.
- If you re-run your Python analysis, click **Refresh data** on the page. If source schema changes, adjust the API/page accordingly.
