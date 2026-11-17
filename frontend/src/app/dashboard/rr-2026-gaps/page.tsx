
"use client";

import Link from "next/link";
import { useState } from "react";
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  Cell,
  LineChart,
  Line,
  ReferenceLine,
} from "recharts";
import {
  ArrowRight,
  ArrowUpRight,
  ArrowDownRight,
  Activity,
  Target,
  Shield,
  Zap,
  Play,
  TrendingUp,
  AlertTriangle,
  Crosshair,
  BarChart3,
  Video,
  CheckCircle2,
  ChevronRight,
  Trophy,
} from "lucide-react";

const PINK = "#F11975";
const GOLD = "#F7C86C";
const GREEN = "#50E3BC";
const BLUE = "#72A9FF";
const MUTED = "#9BAEC8";

const batting = [
  { phase: "Powerplay", rr: 11.67, league: 10.10 },
  { phase: "Middle", rr: 9.59, league: 9.31 },
  { phase: "Death", rr: 10.34, league: 10.79 },
];

// Powerplay bowling uses the earlier squad-gap report.
// Another aggregation produced 10.18; see the data note.
const bowling = [
  { phase: "Powerplay", rr: 10.43, league: 10.10 },
  { phase: "Middle", rr: 9.59, league: 9.31 },
  { phase: "Death", rr: 10.69, league: 10.79 },
];

const outcomes = [
  {
    phase: "Powerplay",
    batWin: 12.26,
    batLoss: 10.90,
    bowlWin: 9.57,
    bowlLoss: 11.52,
  },
  {
    phase: "Middle",
    batWin: 10.14,
    batLoss: 8.94,
    bowlWin: 9.42,
    bowlLoss: 9.81,
  },
  {
    phase: "Death",
    batWin: 10.67,
    batLoss: 10.00,
    bowlWin: 9.32,
    bowlLoss: 12.36,
  },
];

const requirements = [
  {
    id: "01",
    code: "RR-G01",
    title: "Powerplay Pacer",
    priority: "HIGH",
    role: "Indian fast bowler",
    description:
      "A wicket-taking new-ball bowler who can control scoring in the opening six overs.",
    evidence: "11.52 economy in losses vs 9.57 in wins.",
    accent: GOLD,
    icon: Zap,
  },
  {
    id: "02",
    code: "RR-G02",
    title: "Death-Overs Specialist",
    priority: "HIGH",
    role: "Indian fast bowler",
    description:
      "A reliable death-overs option with yorkers, cutters, slower balls and control under pressure.",
    evidence: "12.36 economy in losses vs 9.32 in wins.",
    accent: PINK,
    icon: Target,
  },
  {
    id: "03",
    code: "RR-G03",
    title: "Explosive Finisher",
    priority: "HIGH",
    role: "Finisher / all-rounder",
    description:
      "A late-innings power hitter, ideally with the ability to contribute one or two overs.",
    evidence: "Death batting 10.34 vs league 10.79.",
    accent: GREEN,
    icon: TrendingUp,
  },
  {
    id: "04",
    code: "RR-G04",
    title: "Middle-Overs Wicket-Taker",
    priority: "MEDIUM",
    role: "Attacking spinner / bowler",
    description:
      "A partnership-breaking option capable of applying pressure through overs 7–15.",
    evidence: "Middle bowling 9.59 vs league 9.31.",
    accent: BLUE,
    icon: Crosshair,
  },
];

const panel =
  "rounded-2xl border border-[#263C59] bg-[#101F35]";

const tooltipStyle = {
  backgroundColor: "#081526",
  border: "1px solid #35516F",
  borderRadius: 12,
  color: "#FFFFFF",
  fontSize: 12,
};

function SectionHeading({
  number,
  eyebrow,
  title,
  description,
}: {
  number: string;
  eyebrow: string;
  title: string;
  description?: string;
}) {
  return (
    <div className="mb-6 flex items-start gap-4">
      <span className="mt-1 text-sm font-black text-[#F11975]">
        {number}
      </span>
      <div>
        <p className="text-[10px] font-bold uppercase tracking-[0.25em] text-[#F7C86C]">
          {eyebrow}
        </p>
        <h2 className="mt-1 text-2xl font-black tracking-tight text-white md:text-3xl">
          {title}
        </h2>
        {description && (
          <p className="mt-2 max-w-3xl text-sm leading-6 text-[#9BAEC8]">
            {description}
          </p>
        )}
      </div>
    </div>
  );
}

function MetricCard({
  label,
  value,
  unit,
  detail,
  positive,
  icon: Icon,
}: {
  label: string;
  value: string;
  unit: string;
  detail: string;
  positive: boolean;
  icon: React.ElementType;
}) {
  const color = positive ? GREEN : PINK;

  return (
    <div className={`${panel} relative overflow-hidden p-5`}>
      <div
        className="absolute left-0 top-0 h-1 w-full"
        style={{ backgroundColor: color }}
      />
      <div className="flex items-center justify-between gap-2">
        <span className="text-[10px] font-bold uppercase tracking-widest text-[#9BAEC8]">
          {label}
        </span>
        <Icon size={19} style={{ color }} />
      </div>

      <div className="mt-5 flex items-baseline gap-2">
        <span className="text-4xl font-black tabular-nums text-white">
          {value}
        </span>
        <span className="text-xs text-[#8398B5]">{unit}</span>
      </div>

      <div className="mt-4 flex items-center gap-2 text-xs">
        {positive ? (
          <CheckCircle2 size={15} color={GREEN} />
        ) : (
          <AlertTriangle size={15} color={PINK} />
        )}
        <span className="text-[#BDCCDD]">{detail}</span>
      </div>
    </div>
  );
}

function PhaseChart({
  data,
  mode,
}: {
  data: typeof batting;
  mode: "batting" | "bowling";
}) {
  return (
    <div className={`${panel} p-5`}>
      <div className="mb-5">
        <h3 className="text-lg font-bold text-white">
          {mode === "batting"
            ? "Batting Phase Performance"
            : "Bowling Phase Performance"}
        </h3>
        <p className="mt-1 text-xs text-[#9BAEC8]">
          RR versus IPL league reference · runs per over
        </p>
      </div>

      <div className="h-[310px] w-full">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart
            data={data}
            margin={{ top: 15, right: 8, left: -20, bottom: 5 }}
            barGap={7}
          >
            <CartesianGrid
              stroke="#263C59"
              strokeDasharray="3 5"
              vertical={false}
            />
            <XAxis
              dataKey="phase"
              tick={{ fill: MUTED, fontSize: 11 }}
              axisLine={false}
              tickLine={false}
            />
            <YAxis
              domain={[0, 14]}
              tick={{ fill: MUTED, fontSize: 11 }}
              axisLine={false}
              tickLine={false}
            />
            <Tooltip
              contentStyle={tooltipStyle}
              formatter={(value) =>
                `${Number(value).toFixed(2)} runs/over`
              }
            />
            <Legend
              wrapperStyle={{ fontSize: 11, color: MUTED }}
            />
            <Bar
              dataKey="rr"
              name="Rajasthan Royals"
              fill={PINK}
              maxBarSize={45}
              radius={[6, 6, 0, 0]}
            />
            <Bar
              dataKey="league"
              name="League"
              fill={BLUE}
              maxBarSize={45}
              radius={[6, 6, 0, 0]}
            />
          </BarChart>
        </ResponsiveContainer>
      </div>

      <p className="mt-3 text-center text-xs text-[#9BAEC8]">
        {mode === "batting"
          ? "Higher scoring rate is better."
          : "Lower runs conceded per over is better."}
      </p>
    </div>
  );
}

function DeltaRow({
  label,
  rr,
  league,
  battingMode,
}: {
  label: string;
  rr: number;
  league: number;
  battingMode: boolean;
}) {
  const delta = rr - league;
  const favorable = battingMode ? delta > 0 : delta < 0;
  const magnitude = Math.min(Math.abs(delta) / 2, 1) * 100;

  return (
    <div className="rounded-xl border border-[#29415C] bg-[#0C1A2D] p-4">
      <div className="flex items-center justify-between gap-3">
        <span className="text-sm font-bold text-white">{label}</span>
        <span
          className="text-sm font-black tabular-nums"
          style={{ color: favorable ? GREEN : PINK }}
        >
          {delta > 0 ? "+" : ""}
          {delta.toFixed(2)}
        </span>
      </div>

      <div className="mt-3 h-2 overflow-hidden rounded-full bg-[#243850]">
        <div
          className="h-full rounded-full"
          style={{
            width: `${Math.max(magnitude, 3)}%`,
            backgroundColor: favorable ? GREEN : PINK,
          }}
        />
      </div>

      <div className="mt-3 flex justify-between text-[11px] text-[#91A5C0]">
        <span>RR {rr.toFixed(2)}</span>
        <span>League {league.toFixed(2)}</span>
      </div>
    </div>
  );
}

function OutcomesChart({
  mode,
}: {
  mode: "batting" | "bowling";
}) {
  const battingMode = mode === "batting";

  const data = outcomes.map((row) => ({
    phase: row.phase,
    wins: battingMode ? row.batWin : row.bowlWin,
    losses: battingMode ? row.batLoss : row.bowlLoss,
  }));

  return (
    <div className={`${panel} p-5`}>
      <h3 className="text-lg font-bold text-white">
        {battingMode ? "Batting" : "Bowling"} in Wins vs Losses
      </h3>
      <p className="mt-1 text-xs text-[#9BAEC8]">
        {battingMode
          ? "Runs scored per over"
          : "Runs conceded per over"}
      </p>

      <div className="mt-5 h-[290px] w-full">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart
            data={data}
            margin={{ top: 10, right: 15, left: -20, bottom: 5 }}
          >
            <CartesianGrid
              stroke="#263C59"
              strokeDasharray="3 5"
              vertical={false}
            />
            <XAxis
              dataKey="phase"
              tick={{ fill: MUTED, fontSize: 11 }}
              axisLine={false}
              tickLine={false}
            />
            <YAxis
              domain={[0, 14]}
              tick={{ fill: MUTED, fontSize: 11 }}
              axisLine={false}
              tickLine={false}
            />
            <Tooltip
              contentStyle={tooltipStyle}
              formatter={(value) =>
                `${Number(value).toFixed(2)} runs/over`
              }
            />
            <Legend wrapperStyle={{ fontSize: 11 }} />
            <Line
              type="monotone"
              dataKey="wins"
              name="RR Wins"
              stroke={GREEN}
              strokeWidth={3}
              dot={{ r: 5, fill: GREEN }}
              activeDot={{ r: 7 }}
            />
            <Line
              type="monotone"
              dataKey="losses"
              name="RR Losses"
              stroke={PINK}
              strokeWidth={3}
              dot={{ r: 5, fill: PINK }}
              activeDot={{ r: 7 }}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

function VideoPanel() {
  const [videoError, setVideoError] = useState(false);

  return (
    <div className={`${panel} overflow-hidden`}>
      <div className="relative aspect-video bg-[#060F1C]">
        {!videoError ? (
          <video
            className="h-full w-full object-contain"
            src="/media/rr-2026-analysis.mp4"
            poster="/media/rr-analysis-poster.jpg"
            controls
            playsInline
            preload="metadata"
            onError={() => setVideoError(true)}
          />
        ) : (
          <div className="flex h-full flex-col items-center justify-center gap-4 p-6 text-center">
            <div className="rounded-full border border-[#F11975]/40 bg-[#F11975]/10 p-6">
              <Play size={32} fill={PINK} color={PINK} />
            </div>
            <h3 className="text-xl font-black text-white">
              RR 2026 · The Season Breakdown
            </h3>
            <p className="max-w-sm text-sm text-[#9BAEC8]">
              Place your video at
              <code className="mt-2 block text-[#F7C86C]">
                public/media/rr-2026-analysis.mp4
              </code>
            </p>
          </div>
        )}

        <span className="absolute left-4 top-4 rounded-md border border-white/20 bg-[#071526]/90 px-3 py-1.5 text-[10px] font-bold tracking-widest text-white">
          VIDEO ANALYSIS
        </span>
      </div>

      <div className="flex flex-wrap items-center justify-between gap-3 p-5">
        <div>
          <h3 className="font-bold text-white">
            RR 2026: From Performance to Recruitment
          </h3>
          <p className="mt-1 text-xs text-[#9BAEC8]">
            Campaign review · Scouting insights · IPL 2027
          </p>
        </div>
        <Video size={22} color={PINK} />
      </div>
    </div>
  );
}

export default function RRCampaignDashboard() {
  const [activeTab, setActiveTab] = useState<
    "overview" | "batting" | "bowling" | "outcomes"
  >("overview");

  const tabs = [
    { id: "overview", label: "Overview" },
    { id: "batting", label: "Batting" },
    { id: "bowling", label: "Bowling" },
    { id: "outcomes", label: "Wins vs Losses" },
  ] as const;

  return (
    <main className="min-h-screen bg-[#071426] text-white">
      <div className="mx-auto max-w-[1600px] space-y-10 px-4 py-6 md:px-8 md:py-9">

        {/* HERO */}
        <header className="relative overflow-hidden rounded-3xl border border-[#34445E] bg-gradient-to-br from-[#172B49] via-[#101D35] to-[#070D20] p-6 md:p-10">
          <div className="pointer-events-none absolute -right-24 -top-32 h-[420px] w-[420px] rounded-full bg-[#F11975]/10 blur-[100px]" />

          <div className="relative z-10">
            <div className="mb-6 flex flex-wrap items-center gap-3">
              <span className="rounded-full border border-[#F11975]/40 bg-[#F11975]/10 px-4 py-2 text-[10px] font-extrabold uppercase tracking-widest text-[#FF85BA]">
                Rajasthan Royals · Scouting Intelligence
              </span>
              <span className="rounded-full border border-[#F7C86C]/30 px-3 py-2 text-[10px] font-bold text-[#F7C86C]">
                IPL 2027 · Recruitment Strategy
              </span>
            </div>

            <div className="grid gap-7 lg:grid-cols-[1fr_auto] lg:items-end">
              <div>
                <p className="text-xs font-bold uppercase tracking-[0.3em] text-[#F7C86C]">
                  2026 Campaign Intelligence
                </p>
                <h1 className="mt-3 max-w-4xl text-4xl font-black uppercase leading-[1.08] tracking-tight md:text-6xl">
                  Where We <span className="text-[#50E3BC]">Excelled.</span>
                  <br />
                  Where We <span className="text-[#F11975]">Struggled.</span>
                </h1>
                <p className="mt-5 max-w-2xl text-sm leading-7 text-[#B4C5D9] md:text-base">
                  An evidence-led analysis of Rajasthan Royals&apos;
                  2026 campaign, translating phase performance and
                  match outcomes into targeted scouting priorities.
                </p>
              </div>

              <Link
                href="/pressure-intelligence"
                className="group inline-flex items-center justify-center gap-3 rounded-xl bg-[#F11975] px-7 py-4 text-sm font-black text-white shadow-lg shadow-pink-950/30 transition hover:bg-[#FF4E9E]"
              >
                View My Picks
                <ArrowRight
                  size={19}
                  className="transition-transform group-hover:translate-x-1"
                />
              </Link>
            </div>
          </div>
        </header>

        {/* SCORECARD */}
        <section>
          <SectionHeading
            number="01"
            eyebrow="Campaign at a glance"
            title="The RR Performance Scorecard"
            description="Four signals that explain the foundation of our scouting strategy."
          />
          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
            <MetricCard
              label="Powerplay Batting"
              value="11.67"
              unit="runs/over"
              detail="+1.57 above league reference"
              positive
              icon={TrendingUp}
            />
            <MetricCard
              label="Middle Batting"
              value="9.59"
              unit="runs/over"
              detail="+0.28 above league reference"
              positive
              icon={Activity}
            />
            <MetricCard
              label="Death Bowling / Losses"
              value="12.36"
              unit="runs/over"
              detail="3.04 above RR wins"
              positive={false}
              icon={AlertTriangle}
            />
            <MetricCard
              label="Death Batting Gap"
              value="−0.45"
              unit="runs/over"
              detail="Below league reference"
              positive={false}
              icon={ArrowDownRight}
            />
          </div>
        </section>

        {/* VIDEO + NARRATIVE */}
        <section>
          <SectionHeading
            number="02"
            eyebrow="Visual scouting report"
            title="The Story Behind the Numbers"
            description="A video-led review of RR's strongest phases, pressure points and recruitment opportunities."
          />

          <div className="grid gap-5 xl:grid-cols-[1.45fr_0.85fr]">
            <VideoPanel />

            <div className={`${panel} flex flex-col justify-between p-6`}>
              <div>
                <p className="text-[10px] font-bold uppercase tracking-widest text-[#F7C86C]">
                  Executive Analysis
                </p>
                <h3 className="mt-3 text-2xl font-black leading-tight">
                  Strong starts.
                  <br />
                  <span className="text-[#F11975]">
                    Inconsistent finishes.
                  </span>
                </h3>
                <p className="mt-5 text-sm leading-7 text-[#AFC1D6]">
                  RR&apos;s powerplay batting delivered a clear
                  league-relative advantage. However, late-innings
                  scoring and the variation in death-over bowling
                  between wins and losses highlight the next areas
                  for squad improvement.
                </p>
              </div>

              <div className="mt-7 space-y-4 border-t border-[#30435C] pt-6">
                {[
                  ["01", "Protect our powerplay batting strength"],
                  ["02", "Improve death-over bowling reliability"],
                  ["03", "Recruit genuine finishing power"],
                  ["04", "Add middle-over wicket-taking options"],
                ].map(([n, text]) => (
                  <div key={n} className="flex items-center gap-3">
                    <span className="font-black text-[#F11975]">{n}</span>
                    <span className="text-sm text-[#D3DEEB]">{text}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </section>

        {/* PERFORMANCE ANALYTICS */}
        <section>
          <SectionHeading
            number="03"
            eyebrow="Ball-by-ball findings"
            title="Performance Across Innings Phases"
            description="Compare RR's scoring and run containment against the league, then examine differences between wins and losses."
          />

          <div className="mb-5 flex flex-wrap gap-2">
            {tabs.map((tab) => (
              <button
                key={tab.id}
                type="button"
                onClick={() => setActiveTab(tab.id)}
                className={`rounded-xl px-5 py-3 text-xs font-bold transition ${
                  activeTab === tab.id
                    ? "bg-[#F11975] text-white"
                    : "border border-[#30435C] bg-[#12233A] text-[#AFC1D6] hover:bg-[#1C3452]"
                }`}
              >
                {tab.label}
              </button>
            ))}
          </div>

          {(activeTab === "overview" || activeTab === "batting") && (
            <div className="mb-5 grid gap-5 xl:grid-cols-2">
              <PhaseChart data={batting} mode="batting" />

              <div className={`${panel} p-5`}>
                <h3 className="mb-2 text-lg font-bold">
                  Batting: Advantage or Deficit?
                </h3>
                <p className="mb-5 text-xs text-[#9BAEC8]">
                  RR minus league run rate · positive is favorable
                </p>
                <div className="space-y-3">
                  {batting.map((row) => (
                    <DeltaRow
                      key={row.phase}
                      label={row.phase}
                      rr={row.rr}
                      league={row.league}
                      battingMode
                    />
                  ))}
                </div>
              </div>
            </div>
          )}

          {(activeTab === "overview" || activeTab === "bowling") && (
            <div className="mb-5 grid gap-5 xl:grid-cols-2">
              <PhaseChart data={bowling} mode="bowling" />

              <div className={`${panel} p-5`}>
                <h3 className="mb-2 text-lg font-bold">
                  Bowling: Advantage or Deficit?
                </h3>
                <p className="mb-5 text-xs text-[#9BAEC8]">
                  RR minus league conceded rate · negative is favorable
                </p>
                <div className="space-y-3">
                  {bowling.map((row) => (
                    <DeltaRow
                      key={row.phase}
                      label={row.phase}
                      rr={row.rr}
                      league={row.league}
                      battingMode={false}
                    />
                  ))}
                </div>
              </div>
            </div>
          )}

          {(activeTab === "overview" || activeTab === "outcomes") && (
            <>
              <div className="mb-5 grid gap-5 xl:grid-cols-2">
                <OutcomesChart mode="batting" />
                <OutcomesChart mode="bowling" />
              </div>

              <div className="rounded-2xl border border-[#F11975]/35 bg-[#F11975]/10 p-6">
                <div className="flex items-start gap-4">
                  <AlertTriangle
                    size={24}
                    className="mt-1 shrink-0 text-[#FF6CAB]"
                  />
                  <div>
                    <h3 className="text-lg font-black">
                      The Critical Discovery: Death-Overs Reliability
                    </h3>
                    <p className="mt-3 text-sm leading-7 text-[#C4D2E2]">
                      RR conceded 9.32 runs per over in the death
                      phase during wins, compared with 12.36
                      during losses. That is a 3.04-run-per-over
                      difference, the largest bowling separation
                      across the three phases in this outcome split.
                      It supports prioritizing dependable
                      death-overs bowlers, without treating this
                      association as proof of causation.
                    </p>
                  </div>
                </div>
              </div>
            </>
          )}
        </section>

        {/* STRENGTHS / WEAKNESSES */}
        <section>
          <SectionHeading
            number="04"
            eyebrow="Squad diagnosis"
            title="Our Strengths vs Our Weaknesses"
            description="Which advantages should we preserve, and which gaps require auction investment?"
          />

          <div className="grid gap-5 lg:grid-cols-2">
            <div className="rounded-2xl border border-[#50E3BC]/30 bg-[#102A35] p-6">
              <div className="flex items-center gap-3">
                <CheckCircle2 size={24} color={GREEN} />
                <h3 className="text-xl font-black text-[#50E3BC]">
                  Competitive Strengths
                </h3>
              </div>

              <div className="mt-6 space-y-4">
                {[
                  {
                    title: "Explosive Powerplay Batting",
                    text: "11.67 RR run rate vs 10.10 league reference.",
                  },
                  {
                    title: "Productive Middle-Over Batting",
                    text: "9.59 RR run rate vs 9.31 league reference.",
                  },
                  {
                    title: "Better Scoring in Wins",
                    text: "RR's batting run rates were higher across all three phases in wins than losses.",
                  },
                ].map((item) => (
                  <div
                    key={item.title}
                    className="rounded-xl border border-[#315A5E] bg-[#0A202D] p-4"
                  >
                    <div className="flex items-center gap-2">
                      <CheckCircle2 size={15} color={GREEN} />
                      <h4 className="text-sm font-bold">{item.title}</h4>
                    </div>
                    <p className="mt-2 text-xs leading-6 text-[#B5C8D3]">
                      {item.text}
                    </p>
                  </div>
                ))}
              </div>
            </div>

            <div className="rounded-2xl border border-[#F11975]/30 bg-[#2B1830] p-6">
              <div className="flex items-center gap-3">
                <AlertTriangle size={24} color={PINK} />
                <h3 className="text-xl font-black text-[#FF72AE]">
                  Recruitment Gaps
                </h3>
              </div>

              <div className="mt-6 space-y-4">
                {[
                  {
                    title: "Inconsistent Death Bowling",
                    text: "12.36 conceded per over in losses vs 9.32 in wins.",
                  },
                  {
                    title: "Limited Death-Over Acceleration",
                    text: "10.34 RR run rate vs 10.79 league reference.",
                  },
                  {
                    title: "Middle-Overs Bowling Control",
                    text: "9.59 conceded per over vs 9.31 league reference.",
                  },
                  {
                    title: "Powerplay Bowling in Defeats",
                    text: "11.52 conceded per over in losses vs 9.57 in wins.",
                  },
                ].map((item) => (
                  <div
                    key={item.title}
                    className="rounded-xl border border-[#61334F] bg-[#241629] p-4"
                  >
                    <div className="flex items-center gap-2">
                      <ArrowDownRight size={16} color={PINK} />
                      <h4 className="text-sm font-bold">{item.title}</h4>
                    </div>
                    <p className="mt-2 text-xs leading-6 text-[#C9B5C6]">
                      {item.text}
                    </p>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </section>

        {/* RECRUITMENT */}
        <section>
          <SectionHeading
            number="05"
            eyebrow="IPL 2027 Auction Strategy"
            title="From Weaknesses to Recruitment"
            description="Four player profiles derived from our pre-dataset RR squad-gap research."
          />

          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
            {requirements.map((item) => {
              const Icon = item.icon;

              return (
                <div
                  key={item.code}
                  className={`${panel} group relative flex flex-col overflow-hidden p-5 transition hover:-translate-y-1 hover:border-[#F11975]/50`}
                >
                  <div
                    className="absolute left-0 top-0 h-1 w-full"
                    style={{ backgroundColor: item.accent }}
                  />

                  <div className="flex items-center justify-between gap-2">
                    <span className="text-xs font-bold text-[#859BB7]">
                      {item.code}
                    </span>
                    <span
                      className="rounded-md px-2 py-1 text-[10px] font-extrabold"
                      style={{
                        color: item.accent,
                        backgroundColor: `${item.accent}18`,
                      }}
                    >
                      {item.priority}
                    </span>
                  </div>

                  <div
                    className="mt-5 flex h-12 w-12 items-center justify-center rounded-xl"
                    style={{
                      backgroundColor: `${item.accent}18`,
                      color: item.accent,
                    }}
                  >
                    <Icon size={25} />
                  </div>

                  <h3 className="mt-5 text-lg font-black text-white">
                    {item.title}
                  </h3>
                  <p className="mt-1 text-xs font-bold text-[#F7C86C]">
                    {item.role}
                  </p>

                  <p className="mt-4 flex-1 text-xs leading-6 text-[#A8BBD2]">
                    {item.description}
                  </p>

                  <div className="mt-5 border-t border-[#30435C] pt-4">
                    <p className="text-[10px] font-bold uppercase tracking-wider text-[#819AB8]">
                      Evidence
                    </p>
                    <p className="mt-2 text-xs leading-5 text-white">
                      {item.evidence}
                    </p>
                  </div>
                </div>
              );
            })}
          </div>
        </section>

        {/* CTA */}
        <section className="relative overflow-hidden rounded-3xl border border-[#F11975]/40 bg-gradient-to-r from-[#42153C] via-[#291731] to-[#101B35] p-7 md:p-10">
          <div className="relative z-10 flex flex-col justify-between gap-7 lg:flex-row lg:items-center">
            <div className="max-w-3xl">
              <p className="text-xs font-bold uppercase tracking-[0.28em] text-[#F7C86C]">
                The Next Step · Player Intelligence
              </p>
              <h2 className="mt-3 text-3xl font-black md:text-4xl">
                We Identified the Gaps.
                <br />
                <span className="text-[#FF7AB4]">
                  Now Meet Our Picks.
                </span>
              </h2>
              <p className="mt-4 text-sm leading-7 text-[#C9BED3]">
                Explore our player scouting intelligence, pressure
                scores, reliability assessments and individual
                recruitment cases.
              </p>
            </div>

            <Link
              href="/dashboard/pressure-intelligence"
              className="group inline-flex shrink-0 items-center justify-center gap-3 rounded-xl bg-[#F11975] px-8 py-5 text-sm font-black text-white transition hover:bg-[#FF4E9E]"
            >
              View My Picks
              <ArrowRight
                size={20}
                className="transition-transform group-hover:translate-x-1"
              />
            </Link>
          </div>
        </section>

        {/* PROVENANCE */}
        <footer className="border-t border-[#263C59] pb-5 pt-6 text-xs leading-6 text-[#8198B4]">
          <p>
            RR Scouting Intelligence · Independent IPL 2026
            public-data research · Not officially endorsed.
          </p>
          <p className="mt-2">
            Phase rates and win/loss figures are historical
            analytical snapshots, not recalculations from the
            proprietary scouting pack. The powerplay bowling
            squad-gap report used 10.43 while an earlier
            aggregation produced 10.18; filters and denominators
            should be reconciled before final publication.
            Outcome differences describe associations, not
            independent causal effects.
          </p>
        </footer>
      </div>
    </main>
  );
}
