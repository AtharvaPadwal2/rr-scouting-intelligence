"use client";

import { useEffect, useMemo, useState } from "react";
import {
  ResponsiveContainer, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
  Legend, Cell, LineChart, Line, ReferenceLine,
} from "recharts";
import {
  Activity, ArrowDownRight, ArrowUpRight, BarChart3, ChevronDown,
  Crosshair, Database, Download, Info, RefreshCw, Shield, Target, TrendingUp,
} from "lucide-react";
import styles from "./page.module.css";

type Row = Record<string, string>;
type Payload = {
  data: { gaps: Row[]; league: Row[]; matches: Row[]; bowling: Row[]; middle: Row[]; finishers: Row[] };
  missing: string[];
  generatedAt: string;
};
const RR = "Rajasthan Royals";
const PHASES = ["powerplay", "middle", "death"];
const prettyPhase = (x: string) => ({ powerplay: "Powerplay", middle: "Middle overs", death: "Death overs" }[x] || x);
const n = (x: unknown) => { const value = Number(x); return Number.isFinite(value) ? value : 0; };
const fmt = (x: number, digits = 2) => x.toFixed(digits);
const pct = (num: number, den: number) => den ? (100 * num / den) : 0;
const palette = { pink: "#F12B8D", violet: "#8467FF", blue: "#58B8F9", white: "#F9F7FF", muted: "#9A94B3", gold: "#F5C96B" };

function downloadCsv(filename: string, records: Row[]) {
  if (!records.length) return;
  const keys = Object.keys(records[0]);
  const quote = (v: unknown) => '"' + String(v ?? "").replaceAll('"', '""') + '"';
  const csv = [keys.map(quote).join(","), ...records.map(r => keys.map(k => quote(r[k])).join(","))].join("\r\n");
  const href = URL.createObjectURL(new Blob([csv], { type: "text/csv;charset=utf-8" }));
  const a = document.createElement("a"); a.href = href; a.download = filename; a.click(); URL.revokeObjectURL(href);
}

function useDashboard() {
  const [payload, setPayload] = useState<Payload | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [revision, setRevision] = useState(0);
  useEffect(() => {
    const controller = new AbortController();
    setLoading(true); setError("");
    fetch("/api/rr-gap", { cache: "no-store", signal: controller.signal })
      .then(async response => { const body = await response.json(); if (!response.ok) throw new Error(`${body.error ?? "API failed"} ${body.missing?.join(", ") ?? ""}`); return body; })
      .then(data => setPayload(data))
      .catch(err => { if (err.name !== "AbortError") setError(err.message); })
      .finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [revision]);
  return { payload, error, loading, refresh: () => setRevision(v => v + 1) };
}

const tooltipStyle = { backgroundColor: "#18142D", border: "1px solid #38304F", borderRadius: 12, color: "#FFF", fontSize: 12 };
const axisTick = { fill: "#9A94B3", fontSize: 11 };
function GraphShell({ children, title, subtitle, action }: { children: React.ReactNode; title: string; subtitle: string; action?: React.ReactNode }) {
  return <section className={styles.graphCard}><div className={styles.graphTop}><div><h3>{title}</h3><p>{subtitle}</p></div>{action}</div>{children}</section>;
}

export default function RRGapPage() {
  const { payload, loading, error, refresh } = useDashboard();
  const [selectedRole, setSelectedRole] = useState("bowling");
  const [selectedPhase, setSelectedPhase] = useState("powerplay");
  const [playerPhase, setPlayerPhase] = useState("powerplay");
  const [focusedGap, setFocusedGap] = useState("RR-G01");
  const [resultFilter, setResultFilter] = useState("All");
  const data = payload?.data;

  const phaseData = useMemo(() => PHASES.map(phase => {
    const batting = data?.league.find(r => r.team === RR && r.discipline === "batting" && r.phase === phase);
    const bowling = data?.league.find(r => r.team === RR && r.discipline === "bowling" && r.phase === phase);
    return { phase: prettyPhase(phase), rawPhase: phase, battingRate: n(batting?.run_rate), concededRate: n(bowling?.run_rate), league: n(batting?.league_run_rate), battingRank: n(batting?.league_rank), bowlingRank: n(bowling?.league_rank) };
  }), [data]);

  const comparison = useMemo(() => PHASES.map(phase => {
    const row = data?.league.find(r => r.team === RR && r.discipline === selectedRole && r.phase === phase);
    return { phase: prettyPhase(phase), rr: n(row?.run_rate), league: n(row?.league_run_rate), rank: n(row?.league_rank), difference: n(row?.run_rate) - n(row?.league_run_rate) };
  }), [data, selectedRole]);

  const splits = useMemo(() => {
    return ["Win", "Loss"].map(result => {
      const rows = data?.matches.filter(r => r.result === result && r.rr_role === (selectedRole === "batting" ? "Batting" : "Bowling") && r.phase === selectedPhase) ?? [];
      const runs = rows.reduce((sum, r) => sum + n(r.runs), 0);
      const balls = rows.reduce((sum, r) => sum + n(r.balls), 0);
      return { result: result === "Win" ? "Wins" : "Losses", runRate: balls ? runs * 6 / balls : 0, wickets: rows.reduce((sum, r) => sum + n(r.wickets), 0), runs, balls, games: new Set(rows.map(r => r.match_id)).size };
    });
  }, [data, selectedRole, selectedPhase]);

  const players = useMemo(() => {
    const rows = (playerPhase === "middle" ? data?.middle : data?.bowling) ?? [];
    const grouped = new Map<string, { name: string; winsRuns: number; winsBalls: number; lossesRuns: number; lossesBalls: number; wickets: number }>();
    for (const row of rows) {
      if (playerPhase !== "middle" && row.phase !== playerPhase) continue;
      if (row.result !== "Win" && row.result !== "Loss") continue;
      const id = row.bowler;
      const x = grouped.get(id) ?? { name: id, winsRuns: 0, winsBalls: 0, lossesRuns: 0, lossesBalls: 0, wickets: 0 };
      const win = row.result === "Win";
      x[win ? "winsRuns" : "lossesRuns"] += n(row.team_runs_conceded ?? row.runs);
      x[win ? "winsBalls" : "lossesBalls"] += n(row.legal_balls ?? row.balls);
      x.wickets += n(row.wickets);
      grouped.set(id, x);
    }
    return [...grouped.values()].filter(x => x.winsBalls + x.lossesBalls >= 30).sort((a,b) => (b.winsBalls+b.lossesBalls)-(a.winsBalls+a.lossesBalls)).slice(0, 8).map(x => ({
      name: x.name, wins: x.winsBalls ? x.winsRuns * 6 / x.winsBalls : null,
      losses: x.lossesBalls ? x.lossesRuns * 6 / x.lossesBalls : null,
      balls: x.winsBalls + x.lossesBalls, wickets: x.wickets,
    }));
  }, [data, playerPhase]);

  const finishers = useMemo(() => {
    const grouped = new Map<string, { name: string; runs: number; balls: number; matches: number }>();
    for (const row of data?.finishers ?? []) {
      if (resultFilter !== "All" && row.result !== resultFilter) continue;
      const x = grouped.get(row.batter) ?? { name: row.batter, runs: 0, balls: 0, matches: 0 };
      x.runs += n(row.runs); x.balls += n(row.balls); x.matches += n(row.matches);
      grouped.set(row.batter, x);
    }
    return [...grouped.values()].filter(x => x.balls >= 10).map(x => ({ ...x, strikeRate: pct(x.runs, x.balls) })).sort((a, b) => b.runs - a.runs).slice(0, 8);
  }, [data, resultFilter]);

  const gaps = data?.gaps ?? [];
  const activeGap = gaps.find(g => g.gap_id === focusedGap) ?? gaps[0];
  const matchCount = new Set(data?.matches.map(row => row.match_id)).size;
  const rrPowerplay = phaseData[0]?.battingRate ?? 0;
  const weakness = phaseData[1]?.bowlingRank ?? 0;
  const deathLoss = (() => { const rows = data?.matches.filter(r => r.result === "Loss" && r.rr_role === "Bowling" && r.phase === "death") ?? []; const balls = rows.reduce((s,r)=>s+n(r.balls),0); return balls ? rows.reduce((s,r)=>s+n(r.runs),0)*6/balls : 0; })();

  if (loading && !payload) return <main className={styles.shell}><div className={styles.centerState}><RefreshCw className={styles.spin} size={30}/><h2>Loading scouting intelligence</h2><p>Reading local analysis files…</p></div></main>;
  if (error && !payload) return <main className={styles.shell}><div className={styles.centerState}><Database size={32}/><h2>Data source unavailable</h2><p>{error}</p><button className={styles.primaryButton} onClick={refresh}>Try again</button></div></main>;
  if (!data) return null;

  return <main className={styles.shell}>
    <div className={styles.content}>
      <header className={styles.header}>
        <div className={styles.brand}><span className={styles.brandIcon}><Shield size={20}/></span><div><strong>RR / SCOUTING INTELLIGENCE</strong><span>Performance Analysis • IPL 2026</span></div></div>
        <div className={styles.headerActions}><span className={styles.live}><span/> LOCAL DATA</span><button className={styles.ghostButton} onClick={refresh}><RefreshCw size={14}/> Refresh data</button></div>
      </header>

      <div className={styles.hero}>
        <div className={styles.heroKicker}><Crosshair size={15}/> RECRUITMENT STRATEGY / 2027</div>
        <div className={styles.heroTitleRow}><div><h1>Squad <em>Gap Analysis.</em></h1><p>Turning IPL 2026 performance patterns into targeted, evidence-led recruitment priorities.</p></div><button className={styles.primaryButton} onClick={() => downloadCsv("rr_squad_gap_report.csv", gaps)}><Download size={16}/> Export gaps</button></div>
        <div className={styles.heroLine}/>
        <div className={styles.kpis}>
          <div className={styles.kpi}><span>Matches evaluated</span><strong>{matchCount}</strong><small>RR games in dataset</small></div>
          <div className={styles.kpi}><span>Powerplay batting</span><strong>#{phaseData[0].battingRank}<small className={styles.outOf}> / 10</small></strong><small><ArrowUpRight size={12}/> {fmt(rrPowerplay)} runs / over</small></div>
          <div className={styles.kpi}><span>Middle bowling rank</span><strong>#{weakness}<small className={styles.outOf}> / 10</small></strong><small><ArrowDownRight size={12}/> Runs conceded benchmark</small></div>
          <div className={styles.kpi}><span>Death bowling in losses</span><strong>{fmt(deathLoss)}</strong><small>Runs conceded / over</small></div>
        </div>
      </div>

      <div className={styles.sectionHead}><div><span className={styles.sectionIndex}>01 / PERFORMANCE</span><h2>Where does RR gain or lose ground?</h2><p>Run rates, phase-wise differences and IPL-wide benchmarking</p></div><span className={styles.mutedTag}><Activity size={14}/> 2026 SEASON</span></div>
      <div className={styles.graphGrid}>
        <GraphShell title="Scoring vs conceding" subtitle="RR runs scored and conceded per six legal deliveries">
          <div className={styles.chart}><ResponsiveContainer width="100%" height="100%"><BarChart data={phaseData} margin={{top:12,right:8,left:-22,bottom:0}} barGap={5}><CartesianGrid stroke="#2C2543" vertical={false} strokeDasharray="3 5"/><XAxis dataKey="phase" tick={axisTick} axisLine={false} tickLine={false}/><YAxis tick={axisTick} axisLine={false} tickLine={false} domain={[0,14]}/><Tooltip contentStyle={tooltipStyle} formatter={(v:any)=>fmt(n(v))}/><Legend wrapperStyle={{fontSize:12}}/><Bar dataKey="battingRate" name="RR batting" fill={palette.pink} radius={[5,5,0,0]} maxBarSize={35}/><Bar dataKey="concededRate" name="RR conceded" fill={palette.blue} radius={[5,5,0,0]} maxBarSize={35}/></BarChart></ResponsiveContainer></div>
          <div className={styles.chartNote}><Info size={13}/> Lower conceded rate is better; higher batting rate is better.</div>
        </GraphShell>
        <GraphShell title="RR vs IPL benchmark" subtitle="Compare batting or bowling phase run rates" action={<select className={styles.select} value={selectedRole} onChange={e=>setSelectedRole(e.target.value)}><option value="batting">Batting</option><option value="bowling">Bowling</option></select>}>
          <div className={styles.chart}><ResponsiveContainer width="100%" height="100%"><BarChart data={comparison} margin={{top:12,right:8,left:-22,bottom:0}} barGap={5}><CartesianGrid stroke="#2C2543" vertical={false} strokeDasharray="3 5"/><XAxis dataKey="phase" tick={axisTick} axisLine={false} tickLine={false}/><YAxis tick={axisTick} axisLine={false} tickLine={false} domain={[0,14]}/><Tooltip contentStyle={tooltipStyle} formatter={(v:any)=>fmt(n(v))}/><Legend wrapperStyle={{fontSize:12}}/><Bar name="Rajasthan Royals" dataKey="rr" fill={palette.pink} radius={[5,5,0,0]} maxBarSize={35}/><Bar name="IPL average" dataKey="league" fill={palette.violet} radius={[5,5,0,0]} maxBarSize={35}/></BarChart></ResponsiveContainer></div>
          <div className={styles.rankStrip}>{comparison.map(x=><div key={x.phase}><span>{x.phase}</span><strong>#{x.rank}/10</strong></div>)}</div>
        </GraphShell>
      </div>

      <div className={styles.sectionHead}><div><span className={styles.sectionIndex}>02 / MATCH OUTCOMES</span><h2>What changed in wins versus losses?</h2><p>Results split by phase, with weighted averages based on legal deliveries</p></div><div className={styles.tabs}>{PHASES.map(p=><button key={p} onClick={()=>setSelectedPhase(p)} className={selectedPhase===p?styles.tabActive:styles.tab}>{prettyPhase(p)}</button>)}</div></div>
      <div className={styles.graphGrid}>
        <GraphShell title={`${prettyPhase(selectedPhase)}: wins vs losses`} subtitle={selectedRole === "bowling" ? "Runs conceded per six legal balls" : "Runs scored per six legal balls"}>
          <div className={styles.chart}><ResponsiveContainer width="100%" height="100%"><BarChart data={splits} margin={{top:12,right:8,left:-20,bottom:0}}><CartesianGrid stroke="#2C2543" vertical={false} strokeDasharray="3 5"/><XAxis dataKey="result" tick={axisTick} axisLine={false} tickLine={false}/><YAxis tick={axisTick} axisLine={false} tickLine={false}/><Tooltip contentStyle={tooltipStyle} formatter={(v:any)=>fmt(n(v))}/><Bar dataKey="runRate" name="Runs per over" radius={[7,7,0,0]} maxBarSize={90}>{splits.map((entry,index)=><Cell key={index} fill={index===0?palette.blue:palette.pink}/>)}</Bar></BarChart></ResponsiveContainer></div>
          <div className={styles.rankStrip}>{splits.map(s=><div key={s.result}><span>{s.result} ({s.games} games)</span><strong>{fmt(s.runRate)} RPO</strong></div>)}</div>
        </GraphShell>
        <GraphShell title="Wickets by match outcome" subtitle={`Total dismissals in ${prettyPhase(selectedPhase).toLowerCase()} (${selectedRole})`}>
          <div className={styles.chart}><ResponsiveContainer width="100%" height="100%"><BarChart data={splits} margin={{top:12,right:8,left:-20,bottom:0}}><CartesianGrid stroke="#2C2543" vertical={false} strokeDasharray="3 5"/><XAxis dataKey="result" tick={axisTick} axisLine={false} tickLine={false}/><YAxis tick={axisTick} axisLine={false} tickLine={false} allowDecimals={false}/><Tooltip contentStyle={tooltipStyle}/><Bar dataKey="wickets" name="Wickets" radius={[7,7,0,0]} maxBarSize={90}>{splits.map((_,index)=><Cell key={index} fill={index===0?palette.blue:palette.pink}/>)}</Bar></BarChart></ResponsiveContainer></div>
          <div className={styles.chartNote}><Info size={13}/> Total wickets depend on matches and phase deliveries; use rates for fairer comparisons.</div>
        </GraphShell>
      </div>

      <div className={styles.sectionHead}><div><span className={styles.sectionIndex}>03 / PLAYER DEEP DIVE</span><h2>Which players influence each phase?</h2><p>Phase-specific bowling patterns and finishing contributions</p></div></div>
      <div className={styles.graphGrid}>
        <GraphShell title="Bowlers: outcomes compared" subtitle="Runs conceded per six legal deliveries, grouped by results" action={<select className={styles.select} value={playerPhase} onChange={e=>setPlayerPhase(e.target.value)}>{PHASES.map(p=><option key={p} value={p}>{prettyPhase(p)}</option>)}</select>}>
          <div className={styles.chartTall}><ResponsiveContainer width="100%" height="100%"><BarChart data={players} layout="vertical" margin={{top:10,right:8,left:15,bottom:0}} barGap={2}><CartesianGrid stroke="#2C2543" horizontal={false} strokeDasharray="3 5"/><XAxis type="number" tick={axisTick} axisLine={false} tickLine={false}/><YAxis type="category" dataKey="name" width={105} tick={{fill: "#CFC8E5",fontSize:10}} axisLine={false} tickLine={false}/><Tooltip contentStyle={tooltipStyle} formatter={(v:any)=>v==null?"No sample":fmt(n(v))}/><Legend wrapperStyle={{fontSize:12}}/><Bar dataKey="wins" name="In wins" fill={palette.blue} radius={[0,4,4,0]} maxBarSize={12}/><Bar dataKey="losses" name="In losses" fill={palette.pink} radius={[0,4,4,0]} maxBarSize={12}/></BarChart></ResponsiveContainer></div>
          <div className={styles.chartNote}>Showing players with at least 30 legal deliveries in the selected phase. Missing bars mean no sample.</div>
        </GraphShell>
        <GraphShell title="Death-overs finishers" subtitle="Batting strike rate; minimum 10 balls in the selected results" action={<select className={styles.select} value={resultFilter} onChange={e=>setResultFilter(e.target.value)}><option value="All">All games</option><option value="Win">Wins only</option><option value="Loss">Losses only</option></select>}>
          <div className={styles.chartTall}><ResponsiveContainer width="100%" height="100%"><BarChart data={finishers} layout="vertical" margin={{top:10,right:10,left:15,bottom:0}}><CartesianGrid stroke="#2C2543" horizontal={false} strokeDasharray="3 5"/><XAxis type="number" tick={axisTick} axisLine={false} tickLine={false}/><YAxis type="category" dataKey="name" width={105} tick={{fill: "#CFC8E5",fontSize:10}} axisLine={false} tickLine={false}/><Tooltip contentStyle={tooltipStyle} formatter={(v:any)=>fmt(n(v))}/><Bar dataKey="strikeRate" name="Strike rate" fill={palette.pink} radius={[0,5,5,0]} maxBarSize={22}/></BarChart></ResponsiveContainer></div>
          <div className={styles.chartNote}>Strike rate = 100 × batter runs / balls faced; includes no-balls faced, excludes wides.</div>
        </GraphShell>
      </div>

      <div className={styles.sectionHead}><div><span className={styles.sectionIndex}>04 / RECRUITMENT BLUEPRINT</span><h2>From weakness to player profile.</h2><p>Analyst-defined priorities backed by phase rankings and match outcomes</p></div></div>
      <div className={styles.gapLayout}>
        <div className={styles.gapList}>{gaps.map(g=><button key={g.gap_id} className={`${styles.gapItem} ${activeGap?.gap_id===g.gap_id?styles.gapItemActive:""}`} onClick={()=>setFocusedGap(g.gap_id)}><span className={styles.gapId}>{g.gap_id}</span><span className={styles.gapName}>{g.role}<small>IPL phase rank #{g.ipl_rank}/10</small></span><span className={styles.priority}>{g.priority_label}</span><ChevronDown className={styles.rotatedIcon} size={15}/></button>)}</div>
        {activeGap && <div className={styles.gapDetail}><div className={styles.gapDetailHead}><div><span className={styles.sectionIndex}>SELECTED REQUIREMENT</span><h3>{activeGap.role}</h3></div><span className={styles.priority}>{activeGap.priority_label} priority</span></div><div className={styles.detailMetrics}><div><small>RR phase rank</small><strong>#{activeGap.ipl_rank}<span> / 10</span></strong></div><div><small>RR run rate</small><strong>{fmt(n(activeGap.rr_run_rate))}</strong></div><div><small>League benchmark</small><strong>{fmt(n(activeGap.league_run_rate))}</strong></div></div><div className={styles.detailSection}><span>REQUIRED ATTRIBUTES</span><p>{activeGap.desired_attributes}</p></div><div className={styles.detailSection}><span>DOMESTIC FILTERS</span><p>{activeGap.domestic_filters}</p></div><div className={styles.detailSection}><span>2026 HISTORICAL OPTIONS</span><p>{activeGap.existing_options}</p></div><div className={styles.disclaimer}><Info size={15}/> Priorities are analyst-assigned and provisional; 2027 roster availability, auction eligibility and independent scorecard validation remain outstanding.</div></div>}
      </div>

      {payload?.missing?.length ? <div className={styles.warning}><Info size={17}/> Optional analysis files missing: {payload.missing.join(", ")}. Some player charts may be empty.</div> : null}
      <footer className={styles.footer}><span><Target size={15}/> RR SCOUTING INTELLIGENCE • IPL 2027</span><span>Local-only prototype · Source: processed IPL 2026 analysis CSVs · Refreshed {payload?.generatedAt ? new Date(payload.generatedAt).toLocaleTimeString() : "—"}</span></footer>
    </div>
  </main>;
}
