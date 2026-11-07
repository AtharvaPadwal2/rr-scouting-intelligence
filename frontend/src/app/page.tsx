"use client";

import dynamic from "next/dynamic";
import { useEffect, useState } from "react";
import Image from "next/image";
import {
  Activity,
  ArrowDownUp,
  BarChart3,
  Database,
  Filter,
  Trophy,
  Users,
} from "lucide-react";
import type { EChartsOption } from "echarts";

const ReactECharts = dynamic(() => import("echarts-for-react"), {
  ssr: false,
  loading: () => (
    <div className="flex h-80 items-center justify-center text-sm text-slate-500">
      Loading chart…
    </div>
  ),
});

const PINK = "#EA1A85";
const BLUE = "#1A3789";
const COLORS = [PINK, BLUE, "#8B5CF6", "#0891B2", "#D97706", "#64748B"];
const API_URL = "http://127.0.0.1:8000";

type Metric =
  | "strikeRate"
  | "battingAverage"
  | "economy"
  | "bowlingAverage"
  | "bowlingStrikeRate"
  | "runs"
  | "wickets";

type Player = {
  recordKey: string;
  id: string;
  name: string;
  role: string;
  age: number | null;
  season: string;
  team: string;
competition: string;
matches: number | null;

  runs: number | null;
  balls: number | null;
  wickets: number | null;
  bowled: number | null;
  strikeRate: number | null;
  economy: number | null;
  battingAverage: number | null;
bowlingAverage: number | null;
bowlingStrikeRate: number | null;
};

type RankedPlayer = Player & { value: number };

type ApiRecord = {
  player_id: string | number | null;
  player_name: string | null;
  role: string | null;
  age_at_season_end: number | null;
  season: string | number | null;
  team?: string | null;
competition?: string | null;
matches?: number | null;
coverage_note?: string | null;
  runs?: number | null;
  balls_faced?: number | null;
  wickets?: number | null;
  legal_balls_bowled?: number | null;
  calculated_batting_strike_rate?: number | null;
  calculated_bowling_economy?: number | null;
  calculated_batting_average?: number | null;
calculated_bowling_average?: number | null;
calculated_bowling_strike_rate?: number | null;
};

type DatasetResponse = {
  filename: string;
  records: ApiRecord[];
};

const METRICS: Record<Metric, string> = {
  strikeRate: "Batting strike rate",
  battingAverage: "Batting average",
  economy: "Bowling economy",
  bowlingAverage: "Bowling average",
  bowlingStrikeRate: "Bowling strike rate",
  runs: "Runs",
  wickets: "Wickets",
};

const DESCRIPTIONS: Record<Metric, string> = {
  strikeRate: "Runs scored per 100 balls faced.",
  battingAverage: "Runs scored per dismissal. Higher is better.",
  economy: "Runs conceded per six legal balls. Lower is better.",
  bowlingAverage: "Runs conceded per wicket. Lower is better.",
  bowlingStrikeRate: "Legal balls bowled per wicket. Lower is better.",
  runs: "Total runs in each player-season record.",
  wickets: "Total wickets in each player-season record.",
};

function nullableNumber(value: unknown): number | null {
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

function median(values: number[]): number | string {
  if (values.length === 0) return "—";

  const sorted = [...values].sort((a, b) => a - b);
  const middle = Math.floor(sorted.length / 2);

  return sorted.length % 2 === 1
    ? sorted[middle]
    : (sorted[middle - 1] + sorted[middle]) / 2;
}

function formatMetric(value: number, metric: Metric): string {
  return value.toFixed(metric === "runs" || metric === "wickets" ? 0 : 2);
}
function convertRecords(records: ApiRecord[]): Player[] {
  return records.map((record, index) => ({
    recordKey: `record-${index}`,
    id: String(record.player_id ?? ""),
    name: record.player_name?.trim() || "Unnamed player",
    role: record.role?.trim() || "Unknown",
    age: nullableNumber(record.age_at_season_end),
    season: String(record.season ?? "Unknown"),
    team: record.team?.trim() || "Unknown",
competition: record.competition?.trim() || "Unknown",
matches: nullableNumber(record.matches),
    runs: nullableNumber(record.runs),
    balls: nullableNumber(record.balls_faced),
    wickets: nullableNumber(record.wickets),
    bowled: nullableNumber(record.legal_balls_bowled),
    strikeRate: nullableNumber(record.calculated_batting_strike_rate),
    economy: nullableNumber(record.calculated_bowling_economy),
    battingAverage: nullableNumber(record.calculated_batting_average),
bowlingAverage: nullableNumber(record.calculated_bowling_average),
bowlingStrikeRate: nullableNumber(record.calculated_bowling_strike_rate),
  }));
}


export default function Home() {
  const [players, setPlayers] = useState<Player[]>([]);
  const [filename, setFilename] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);
const [uploadError, setUploadError] = useState<string | null>(null);
const [source, setSource] = useState<"demo" | "uploaded">("demo");

  const [season, setSeason] = useState("All");
  const [role, setRole] = useState("All");
  const [metric, setMetric] = useState<Metric>("strikeRate");
  const [ascending, setAscending] = useState(false);
  const [minimumBalls, setMinimumBalls] = useState(50);
  const [team, setTeam] = useState("All");
const [competition, setCompetition] = useState("All");
const [minimumMatches, setMinimumMatches] = useState(0);

  useEffect(() => {
    const controller = new AbortController();

    async function loadDataset() {
      try {
        const response = await fetch(`${API_URL}/api/demo`, {
          signal: controller.signal,
          cache: "no-store",
        });

        if (!response.ok) {
          throw new Error(`Python API returned HTTP ${response.status}.`);
        }

        const dataset: DatasetResponse = await response.json();

        if (!Array.isArray(dataset.records)) {
          throw new Error("Python returned an unexpected dataset response.");
        }

        const records = convertRecords(dataset.records);

        if (!controller.signal.aborted) {
          setPlayers(records);
          setFilename(dataset.filename);
          setError(null);
        }
      } catch (caught) {
        if (!controller.signal.aborted) {
          setError(
            caught instanceof Error
              ? caught.message
              : "Could not load the Python dataset."
          );
        }
      } finally {
        if (!controller.signal.aborted) {
          setLoading(false);
        }
      }
    }

    void loadDataset();
    return () => controller.abort();
  }, []);
async function uploadDataset(file: File) {
  setUploading(true);
  setUploadError(null);

  try {
    const formData = new FormData();
    formData.append("file", file);

    const response = await fetch(`${API_URL}/api/datasets/import`, {
      method: "POST",
      body: formData,
    });

    if (!response.ok) {
      const failure = await response.json().catch(() => null);
      throw new Error(
        typeof failure?.detail === "string"
          ? failure.detail
          : `Upload failed with HTTP ${response.status}.`
      );
    }

    const dataset: DatasetResponse = await response.json();

    if (!Array.isArray(dataset.records)) {
      throw new Error("Python returned an unexpected dataset response.");
    }

    const records = convertRecords(dataset.records);

    setPlayers(records);
    setFilename(dataset.filename);
    setSource("uploaded");
    setSeason("All");
    setRole("All");
    setMetric("strikeRate");
    setAscending(false);
    setMinimumBalls(50);
    setTeam("All");
setCompetition("All");
setMinimumMatches(0);
    setError(null);
  } catch (caught) {
    setUploadError(
      caught instanceof Error ? caught.message : "Could not upload this file."
    );
  } finally {
    setUploading(false);
  }
}
  const roles = [...new Set(players.map((player) => player.role))].sort();
  const seasons = [...new Set(players.map((player) => player.season))].sort(
    (a, b) => b.localeCompare(a, undefined, { numeric: true })
  );
const teams = [...new Set(players.map((player) => player.team))].sort();
const competitions = [
  ...new Set(players.map((player) => player.competition)),
].sort();
  const bowling = [
  "economy",
  "bowlingAverage",
  "bowlingStrikeRate",
  "wickets",
].includes(metric);

 const filtered = players.filter((player) => {
  const matchesSeason = season === "All" || player.season === season;
  const matchesRole = role === "All" || player.role === role;
  const matchesTeam = team === "All" || player.team === team;
  const matchesCompetition =
    competition === "All" || player.competition === competition;

  const hasEnoughMatches =
    minimumMatches === 0 ||
    (player.matches !== null && player.matches >= minimumMatches);

  const sample = bowling ? player.bowled : player.balls;
  const hasSample = sample !== null && sample >= minimumBalls;
  const hasBowling =
    !bowling || (player.bowled !== null && player.bowled > 0);

  return (
    matchesSeason &&
    matchesRole &&
    matchesTeam &&
    matchesCompetition &&
    hasEnoughMatches &&
    hasSample &&
    hasBowling
  );
});

  const ranked: RankedPlayer[] = filtered
    .flatMap((player) => {
      const value = player[metric];
      return value === null ? [] : [{ ...player, value }];
    })
    .sort((a, b) =>
      ascending ? a.value - b.value : b.value - a.value
    );

  const chartPlayers = ranked.slice(0, 12);

  const chart: EChartsOption = {
    color: [bowling ? BLUE : PINK],
    grid: { left: 235, right: 65, top: 15, bottom: 55 },
    tooltip: {
      trigger: "axis",
      axisPointer: { type: "shadow" },
      confine: true,
    },
    xAxis: {
      type: "value",
      min: 0,
      name: METRICS[metric],
      nameLocation: "middle",
      nameGap: 35,
      splitLine: { lineStyle: { color: "#EEF0F6" } },
    },
    yAxis: {
      type: "category",
      inverse: true,
      data: chartPlayers.map(
        (player) => `${player.name} · ${player.season}`
      ),
      axisLine: { show: false },
      axisTick: { show: false },
      axisLabel: { width: 215, overflow: "truncate" },
    },
    series: [
      {
        type: "bar",
        data: chartPlayers.map((player) => player.value),
        barMaxWidth: 24,
        itemStyle: { borderRadius: [0, 5, 5, 0] },
        label: {
          show: true,
          position: "right",
          color: "#172554",
          formatter: (params) =>
            typeof params.value === "number"
              ? formatMetric(params.value, metric)
              : "",
        },
      },
    ],
  };

  const donut: EChartsOption = {
    tooltip: {
      trigger: "item",
      formatter: "{b}: {c} records ({d}%)",
      confine: true,
    },
    legend: {
      type: "scroll",
      bottom: 0,
      icon: "circle",
      textStyle: { fontSize: 11 },
    },
    series: [
      {
        type: "pie",
        radius: ["48%", "70%"],
        center: ["50%", "43%"],
        label: { show: false },
        itemStyle: { borderColor: "#FFFFFF", borderWidth: 3 },
        data: roles
          .map((name, index) => ({
            name,
            value: ranked.filter((player) => player.role === name).length,
            itemStyle: { color: COLORS[index % COLORS.length] },
          }))
          .filter((entry) => entry.value > 0),
      },
    ],
  };

  const statistics = [
    {
      label: "Players in dataset",
      value: new Set(players.map((player) => player.id).filter(Boolean)).size,
      icon: Users,
    },
    {
      label: "Matching usable records",
      value: ranked.length,
      icon: Filter,
    },
    {
      label: "Seasons available",
      value: seasons.length,
      icon: Database,
    },
    {
      label: "Median age · matching records",
      value: median(
        ranked.flatMap((player) => player.age === null ? [] : [player.age])
      ),
      icon: Activity,
    },
  ];

  const inputClass =
    "mt-2 w-full rounded-xl border border-slate-200 bg-white px-3 py-2.5 text-sm text-slate-800 outline-none focus:border-pink-500 focus:ring-2 focus:ring-pink-100";

  return (
    <div className="rr-workspace min-h-screen font-sans text-[#101B42]">
     <aside className="rr-sidebar fixed inset-y-0 left-0 hidden w-60 flex-col px-5 py-8 text-white lg:flex">
        <div className="flex items-center gap-3">
          <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl bg-[#EA1A85]">
            <Trophy size={25} />
          </div>
          <div>
            <p className="text-xl font-black tracking-tight">RR SCOUTING</p>
            <p className="text-[10px] tracking-[0.22em] text-blue-200">
              INTELLIGENCE
            </p>
          </div>
        </div>

        <div className="mt-12">
          <p className="mb-4 px-3 text-[10px] font-semibold tracking-[0.2em] text-blue-200">
            WORKSPACE
          </p>
          <div
            aria-current="page"
            className="flex items-center gap-3 rounded-xl bg-[#EA1A85] px-4 py-3 text-sm font-semibold"
          >
            <BarChart3 size={19} />
            Performance Explorer
          </div>
          <p className="mt-5 px-3 text-xs leading-6 text-blue-100">
            Explore performance, compare samples, and identify players to
            investigate further.
          </p>
        </div>

        <div className="mt-auto rounded-xl border border-white/20 px-4 py-3 text-xs text-blue-100">
          <span
            className={`mr-2 inline-block h-2 w-2 rounded-full ${
              error
                ? "bg-red-400"
                : loading
                  ? "bg-amber-400"
                  : "bg-emerald-400"
            }`}
          />
          {error ? "Connection failed" : loading ? "Connecting…" : "Python connected"}
        </div>
      </aside>

      <main className="mx-auto max-w-[1800px] p-5 sm:p-8 lg:ml-60 lg:p-10">
       <header className="rr-hero">
  <div className="rr-hero-copy">
    <p className="rr-hero-kicker">
      RAJASTHAN ROYALS · SCOUTING WORKSPACE
    </p>

    <h1 className="rr-hero-title">
      Find the next
      <br />
      generation of Royals.
    </h1>

    <p className="rr-hero-description">
      Explore domestic performances, compare player samples,
      and discover prospects worth a closer look.
    </p>
  </div>

  <div className="flex flex-wrap items-center gap-3">
    <span className="rounded-full border border-white/25 bg-[#081536]/75 px-4 py-2 text-[10px] font-bold tracking-wide text-white backdrop-blur-sm">
      {source === "demo" ? "SYNTHETIC DEMO DATA" : "UPLOADED DATASET"}
    </span>

    <label
      className={`rr-upload rounded-xl bg-[#EA1A85] px-4 py-2.5 text-sm font-semibold text-white ${
        loading || uploading
          ? "cursor-wait opacity-60"
          : "cursor-pointer hover:bg-pink-700"
      }`}
    >
      {uploading ? "Processing file…" : "Upload CSV / XLSX"}

      <input
        type="file"
        accept=".csv,.xlsx"
        disabled={loading || uploading}
        className="sr-only"
        onChange={(event) => {
          const file = event.currentTarget.files?.[0];
          event.currentTarget.value = "";

          if (file) {
            void uploadDataset(file);
          }
        }}
      />
    </label>
  </div>
</header>
        {uploading && (
  <p role="status" className="mt-4 text-sm text-[#1A3789]">
    Python is reading, cleaning, and calculating metrics for your upload…
  </p>
)}

{uploadError && (
  <div
    role="alert"
    className="mt-4 rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-800"
  >
    {uploadError}
  </div>
)}

        {filename && (
          <p className="mt-4 text-xs text-slate-500">
            Source · {filename} · {players.length} cleaned records
          </p>
        )}

        <section className="mt-8 grid grid-cols-2 gap-4 xl:grid-cols-4">
          {statistics.map(({ label, value, icon: Icon }) => (
            <div
              key={label}
              className="rr-stat-card flex items-center gap-4 rounded-2xl border border-slate-200 bg-white p-5"
            >
              <div className="rounded-xl bg-pink-50 p-3 text-[#EA1A85]">
                <Icon size={22} />
              </div>
              <div>
                <p className="text-2xl font-black">
                  {loading || error ? "—" : value}
                </p>
                <p className="mt-1 text-xs text-slate-500">{label}</p>
              </div>
            </div>
          ))}
        </section>

        <fieldset
          disabled={loading || error !== null}
          aria-label="Performance filters"
          className="mt-6 grid min-w-0 gap-4 rounded-2xl border border-slate-200 bg-white p-5 disabled:opacity-60 sm:grid-cols-2 xl:grid-cols-4"
        >
          <label className="text-xs font-semibold text-slate-600">
            Season
            <select
              className={inputClass}
              value={season}
              onChange={(event) => setSeason(event.target.value)}
            >
              <option value="All">All seasons</option>
              {seasons.map((availableSeason) => (
                <option key={availableSeason} value={availableSeason}>
                  {availableSeason}
                </option>
              ))}
            </select>
          </label>

          <label className="text-xs font-semibold text-slate-600">
            Playing role
            <select
              className={inputClass}
              value={role}
              onChange={(event) => setRole(event.target.value)}
            >
              <option value="All">All roles</option>
              {roles.map((name) => (
                <option key={name} value={name}>{name}</option>
              ))}
            </select>
          </label>

          <label className="text-xs font-semibold text-slate-600">
            Performance metric
            <select
              className={inputClass}
              value={metric}
              onChange={(event) => {
                const nextMetric = event.target.value as Metric;
                setMetric(nextMetric);
                setAscending(
  ["economy", "bowlingAverage", "bowlingStrikeRate"].includes(nextMetric)
);
              }}
            >
              {Object.entries(METRICS).map(([value, label]) => (
                <option key={value} value={value}>{label}</option>
              ))}
            </select>
          </label>

          <label className="text-xs font-semibold text-slate-600">
            Ranking order
            <select
              className={inputClass}
              value={ascending ? "ascending" : "descending"}
              onChange={(event) =>
                setAscending(event.target.value === "ascending")
              }
            >
              <option value="descending">High to low</option>
              <option value="ascending">Low to high</option>
            </select>
          </label>

          <label className="text-xs font-semibold text-slate-600">
            Minimum balls {bowling ? "bowled" : "faced"}
            <select
              className={inputClass}
              value={minimumBalls}
              onChange={(event) => setMinimumBalls(Number(event.target.value))}
            >
              {[0, 50, 100, 200, 300].map((value) => (
                <option key={value} value={value}>{value}</option>
              ))}
            </select>
          </label>
          <label className="text-xs font-semibold text-slate-600">
  Competition
  <select
    className={inputClass}
    value={competition}
    onChange={(event) => setCompetition(event.target.value)}
  >
    <option value="All">All competitions</option>
    {competitions.map((name) => (
      <option key={name} value={name}>{name}</option>
    ))}
  </select>
</label>

<label className="text-xs font-semibold text-slate-600">
  Team
  <select
    className={inputClass}
    value={team}
    onChange={(event) => setTeam(event.target.value)}
  >
    <option value="All">All teams</option>
    {teams.map((name) => (
      <option key={name} value={name}>{name}</option>
    ))}
  </select>
</label>

<label className="text-xs font-semibold text-slate-600">
  Minimum available matches per player
  <select
    className={inputClass}
    value={minimumMatches}
    onChange={(event) => setMinimumMatches(Number(event.target.value))}
  >
    {[0, 2, 3, 5, 7, 10].map((value) => (
      <option key={value} value={value}>
        {value === 0 ? "Any sample size" : `${value}+ matches`}
      </option>
    ))}
  </select>
</label>
        </fieldset>

        {loading ? (
          <div
            role="status"
            className="mt-6 rounded-2xl border border-slate-200 bg-white p-12 text-center text-slate-500"
          >
            Loading cleaned records from Python…
          </div>
        ) : error ? (
          <div
            role="alert"
            className="mt-6 rounded-2xl border border-red-200 bg-red-50 p-6 text-red-800"
          >
            <p className="font-semibold">Could not load the dataset</p>
            <p className="mt-2 text-sm">{error}</p>
            <p className="mt-2 text-sm">
              Check that FastAPI is running at {API_URL}, then refresh.
            </p>
            <button
              type="button"
              onClick={() => window.location.reload()}
              className="mt-4 rounded-lg bg-red-800 px-4 py-2 text-sm font-semibold text-white"
            >
              Retry connection
            </button>
          </div>
        ) : ranked.length === 0 ? (
          <div className="mt-6 rounded-2xl border border-dashed border-slate-300 bg-white p-12 text-center text-slate-500">
            No usable records match these filters. Try a different role,
            season, or smaller minimum sample.
          </div>
        ) : (
          <>
            <section className="mt-6 grid gap-6 xl:grid-cols-3">
              <div className="rr-panel min-w-0 rounded-2xl border border-slate-200 bg-white p-5 xl:col-span-2">
                <h2 className="text-lg font-bold">{METRICS[metric]} rankings</h2>
                <p className="mt-1 text-xs text-slate-500">
                  {DESCRIPTIONS[metric]} Showing the first {chartPlayers.length}{" "}
                  records in the selected order.
                </p>
                <div className="overflow-x-auto">
                  <div className="min-w-[580px]">
                    <ReactECharts
                      option={chart}
                      notMerge
                      style={{
                        height: Math.max(320, chartPlayers.length * 36 + 70),
                      }}
                    />
                  </div>
                </div>
              </div>

              <div className="rr-panel min-w-0 rounded-2xl border border-slate-200 bg-white p-5">
                <h2 className="text-lg font-bold">Role distribution</h2>
                <p className="mt-1 text-xs text-slate-500">
                  All {ranked.length} matching usable player-season records
                </p>
                <ReactECharts
                  option={donut}
                  notMerge
                  style={{ height: 340 }}
                />
              </div>
            </section>

            <section className="mt-6 overflow-hidden rounded-2xl border border-slate-200 bg-white">
              <div className="flex items-center justify-between gap-4 p-5">
                <div>
                  <h2 className="text-lg font-bold">Player records</h2>
                  <p className="mt-1 text-xs text-slate-500">
                    Click the metric column to reverse the table and chart order.
                  </p>
                </div>
                <span className="rounded-full bg-blue-50 px-3 py-1 text-xs font-semibold text-[#1A3789]">
                  {ranked.length} records
                </span>
              </div>

              <div className="max-h-[600px] overflow-auto">
                <table className="w-full whitespace-nowrap text-left text-sm">
                  <thead className="sticky top-0 bg-slate-50 text-xs text-slate-500">
                    <tr>
                      <th scope="col" className="px-5 py-4">Player</th>
                      <th scope="col" className="px-5 py-4">Team</th>
<th scope="col" className="px-5 py-4">Available matches</th>
                      <th scope="col" className="px-5 py-4">Role</th>
                      <th scope="col" className="px-5 py-4">Age at season end</th>
                      <th scope="col" className="px-5 py-4">Season</th>
                      <th scope="col" className="px-5 py-4">
                        Balls {bowling ? "bowled" : "faced"}
                      </th>
                      <th
                        scope="col"
                        className="px-5 py-4"
                        aria-sort={ascending ? "ascending" : "descending"}
                      >
                        <button
                          type="button"
                          className="flex items-center gap-2 text-[#1A3789]"
                          onClick={() => setAscending((current) => !current)}
                        >
                          {METRICS[metric]}
                          <ArrowDownUp size={14} />
                        </button>
                      </th>
                    </tr>
                  </thead>

                  <tbody>
                    {ranked.map((player) => (
                      <tr
                        key={player.recordKey}
                        className="border-t border-slate-100 hover:bg-pink-50/40"
                      >
                        <td className="px-5 py-4 font-semibold">{player.name}</td>
                        <td className="px-5 py-4">{player.team}</td>
<td className="px-5 py-4">{player.matches ?? "—"}</td>
                        <td className="px-5 py-4 text-slate-500">{player.role}</td>
                        <td className="px-5 py-4">{player.age ?? "—"}</td>
                        <td className="px-5 py-4">{player.season}</td>
                        <td className="px-5 py-4">
                          {(bowling ? player.bowled : player.balls) ?? "—"}
                        </td>
                        <td className="px-5 py-4 font-bold text-[#EA1A85]">
                          {formatMetric(player.value, metric)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>
          </>
        )}

        <p className="mt-6 text-xs text-slate-500">
          {source === "demo"
  ? "Fictional Python-generated data."
  : "Totals from available uploaded matches only. Season coverage may be incomplete."}{" "}
Each row represents a player-team-season record. Rates are calculated
by Python.
        </p>
      </main>
    </div>
  );
}