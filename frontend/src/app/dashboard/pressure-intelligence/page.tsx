"use client";

import { useEffect, useMemo, useState } from "react";
import {
  ResponsiveContainer, RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis,
  Radar, BarChart, Bar, CartesianGrid, XAxis, YAxis, Tooltip, Cell,
} from "recharts";

type Axis = { axis: string; value: number };
type Player = {
  id: string; name: string; team: string; role: "batting" | "bowling";
  rank: number; adjustedScore: number; balls: number; matches: number;
  positiveMatchPct: number; top10StabilityPct: number;
  iplEvidencePct: number | null; radar: Axis[];
};
type Dashboard = {
  meta: { title: string; methodology: string; batters: number; bowlers: number; ipl2026MappedPlayers: number | null };
  batting: Player[]; bowling: Player[];
};

const pink = "#FF5DA8";
const cyan = "#70D9FF";
const panel = "rounded-2xl border border-white/10 bg-[#101931]/90 p-5 shadow-[0_12px_48px_rgba(0,0,0,.18)]";

export default function PressureOverviewPage() {
  const [data, setData] = useState<Dashboard | null>(null);
  const [error, setError] = useState("");
  const [role, setRole] = useState<"batting" | "bowling">("batting");
  const [selectedId, setSelectedId] = useState("");

  useEffect(() => {
    fetch("/data/pressure-overview.json", { cache: "no-store" })
      .then(async (res) => { if (!res.ok) throw new Error(`Data request failed (${res.status})`); return res.json(); })
      .then((json: Dashboard) => setData(json))
      .catch((err) => setError(err instanceof Error ? err.message : "Unable to load data"));
  }, []);

  const players = useMemo(() => data?.[role] ?? [], [data, role]);
  const selected = players.find((p) => p.id === selectedId) ?? players[0];
  const top = players.slice(0, 10);
  const max = Math.max(...top.map((p) => p.adjustedScore), 1);

  return (
    <main className="min-h-screen bg-[#070D1D] text-[#F6F8FF]">
      <div className="pointer-events-none fixed inset-0 bg-[radial-gradient(ellipse_at_85%_0%,rgba(255,63,158,.14),transparent_42%),radial-gradient(ellipse_at_0%_48%,rgba(36,119,226,.15),transparent_45%)]" />
      <div className="relative mx-auto max-w-[1540px] space-y-6 px-4 py-8 md:px-8">
        <header className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <div className="mb-3 inline-flex items-center gap-2 rounded-full border border-pink-400/30 bg-pink-400/10 px-3 py-1 text-xs font-semibold uppercase tracking-[.22em] text-pink-300">RR Scouting Intelligence / 01</div>
            <h1 className="text-3xl font-black tracking-tight md:text-5xl">Pressure <span className="text-[#FF5DA8]">Intelligence</span></h1>
            <p className="mt-3 max-w-3xl text-sm text-slate-300 md:text-base">Measure impact, repeatability and ranking robustness. Explore the evidence behind every shortlist decision.</p>
          </div>
          <div className="rounded-xl border border-amber-400/30 bg-amber-400/10 px-4 py-3 text-xs text-amber-100">PROVISIONAL MODEL<br/><span className="text-amber-200/80">Structural pressure · IPL 2026 roster proxy</span></div>
        </header>

        {error ? <div className="rounded-xl border border-red-400/40 bg-red-500/10 p-5 text-red-200">{error}. Run the Python export script and check the JSON file in frontend/public/data.</div> : null}
        {!data && !error ? <div className={panel}>Loading scouting data…</div> : null}
        {data && (
          <>
            <section className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
              {[
                { label: "2026 roster-mapped players", value: data.meta.ipl2026MappedPlayers ?? "—", foot: "Historical eligibility proxy" },
                { label: "Ranked batters", value: data.meta.batters, foot: "All-T20 structural pressure" },
                { label: "Ranked bowlers", value: data.meta.bowlers, foot: "All-T20 structural pressure" },
                { label: "Sensitivity experiments", value: "20", foot: "9 batting + 11 bowling" },
              ].map((stat) => (
                <div key={stat.label} className={panel}>
                  <p className="text-xs uppercase tracking-wider text-slate-400">{stat.label}</p>
                  <p className="mt-2 text-4xl font-black text-white">{stat.value}</p>
                  <p className="mt-2 text-xs text-[#9AB5D8]">{stat.foot}</p>
                </div>
              ))}
            </section>

            <div className="flex flex-wrap gap-2">
              {(["batting", "bowling"] as const).map((r) => (
                <button key={r} onClick={() => { setRole(r); setSelectedId(""); }} className={`rounded-full px-5 py-2 text-sm font-bold transition ${role === r ? "bg-[#FF5DA8] text-[#190B20]" : "border border-white/15 bg-white/5 text-slate-200 hover:bg-white/10"}`}>
                  {r === "batting" ? "Batters" : "Bowlers"}
                </button>
              ))}
              <span className="my-auto ml-auto text-xs text-slate-400">Select any player below to update the radar</span>
            </div>

            <section className="grid gap-5 xl:grid-cols-[1.03fr_0.97fr]">
              <div className={panel}>
                <div className="mb-5 flex items-start justify-between gap-3">
                  <div><h2 className="text-xl font-extrabold">Top 10 performers</h2><p className="mt-1 text-sm text-slate-400">Adjusted model score • same role only</p></div>
                  <span className="rounded-lg bg-pink-400/10 px-2 py-1 text-xs font-semibold text-pink-300">{role.toUpperCase()}</span>
                </div>
                <div className="h-[380px] w-full">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={[...top].reverse()} layout="vertical" margin={{ top: 0, right: 20, bottom: 0, left: 8 }}>
                      <CartesianGrid stroke="#273652" horizontal={false} strokeDasharray="3 5"/>
                      <XAxis type="number" domain={[0, Math.ceil(max * 1.1)]} tick={{ fill: "#9EAEC9", fontSize: 11 }} axisLine={false} tickLine={false} />
                      <YAxis dataKey="name" type="category" width={119} tick={{ fill: "#E5ECFF", fontSize: 11 }} axisLine={false} tickLine={false}/>
                      <Tooltip contentStyle={{ background: "#0D1630", border: "1px solid #364361", borderRadius: 12 }} formatter={(value) => [Number(value).toFixed(2), "Adjusted score"]}/>
                      <Bar dataKey="adjustedScore" radius={[0, 6, 6, 0]} onClick={(entry) => { if (entry && typeof entry === "object" && "id" in entry) setSelectedId(String(entry.id)); }}>
                        {[...top].reverse().map((p) => <Cell key={p.id} cursor="pointer" fill={selected?.id === p.id ? pink : "#477CE2"}/>) }
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </div>

              <div className={panel}>
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div><h2 className="text-xl font-extrabold">Player Reliability Radar</h2><p className="mt-1 text-sm text-slate-400">Five measured dimensions, normalized 0–100</p></div>
                  <select aria-label="Select player" value={selected?.id ?? ""} onChange={(e) => setSelectedId(e.target.value)} className="max-w-full rounded-lg border border-white/20 bg-[#182442] px-3 py-2 text-sm text-white outline-none focus:border-pink-400">
                    {players.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
                  </select>
                </div>
                {selected && <>
                  <div className="mt-4 flex items-baseline justify-between gap-3"><div><p className="text-xl font-black">{selected.name}</p><p className="text-xs text-slate-400">{selected.team} · 2026 roster mapping</p></div><div className="text-right"><p className="text-xl font-bold text-pink-300">#{selected.rank}</p><p className="text-xs text-slate-400">Model rank</p></div></div>
                  <div className="h-[330px] w-full">
                    <ResponsiveContainer width="100%" height="100%">
                      <RadarChart data={selected.radar} outerRadius="68%">
                        <PolarGrid stroke="#395071"/>
                        <PolarAngleAxis dataKey="axis" tick={{ fill: "#CED9F1", fontSize: 11 }}/>
                        <PolarRadiusAxis domain={[0, 100]} tickCount={5} tick={{ fill: "#8194B6", fontSize: 9 }} axisLine={false}/>
                        <Radar dataKey="value" name={selected.name} stroke={pink} fill={pink} fillOpacity={0.3} strokeWidth={2}/>
                        <Tooltip contentStyle={{ background: "#0D1630", border: "1px solid #364361", borderRadius: 12 }}/>
                      </RadarChart>
                    </ResponsiveContainer>
                  </div>
                  <div className="grid grid-cols-3 gap-2 text-center">
                    <Metric label="Deliveries" value={selected.balls.toLocaleString()}/>
                    <Metric label="Positive matches" value={`${selected.positiveMatchPct.toFixed(1)}%`}/>
                    <Metric label="Top-10 stability" value={`${selected.top10StabilityPct.toFixed(1)}%`}/>
                  </div>
                </>}
              </div>
            </section>

            <section className={panel}>
              <div className="mb-4"><h2 className="text-xl font-extrabold">Scouting Leaderboard</h2><p className="mt-1 text-sm text-slate-400">Top 20. Click a row to inspect its radar profile.</p></div>
              <div className="overflow-x-auto"><table className="w-full min-w-[760px] text-left text-sm"><thead><tr className="border-b border-white/10 text-xs uppercase tracking-wider text-slate-400"><th className="pb-3">Rank</th><th className="pb-3">Player</th><th className="pb-3">Team (2026)</th><th className="pb-3 text-right">Score</th><th className="pb-3 text-right">Balls</th><th className="pb-3 text-right">Positive %</th><th className="pb-3 text-right">Stability %</th></tr></thead><tbody>{players.slice(0, 20).map((p) => <tr key={p.id} onClick={() => { setSelectedId(p.id); window.scrollTo({top: 200, behavior: "smooth"}); }} className={`cursor-pointer border-b border-white/5 transition hover:bg-white/10 ${p.id === selected?.id ? "bg-pink-400/10" : ""}`}><td className="py-3 font-bold text-pink-300">#{p.rank}</td><td className="py-3 font-semibold">{p.name}</td><td className="py-3 text-slate-400">{p.team}</td><td className="py-3 text-right font-bold">{p.adjustedScore.toFixed(2)}</td><td className="py-3 text-right">{p.balls}</td><td className="py-3 text-right">{p.positiveMatchPct.toFixed(1)}</td><td className="py-3 text-right">{p.top10StabilityPct.toFixed(1)}</td></tr>)}</tbody></table></div>
            </section>

            <section className="rounded-2xl border border-sky-400/20 bg-sky-400/5 p-5 text-sm text-slate-300">
              <h2 className="mb-2 font-extrabold text-white">How to read the Radar</h2>
              <p><strong>Impact:</strong> percentile of adjusted score within the same role. <strong>Consistency:</strong> percentage of eligible matches with positive impact. <strong>Delivery confidence:</strong> 100 × balls/(balls + 120). <strong>Match breadth:</strong> percentage of 30-match reference reached, capped at 100. <strong>Rank stability:</strong> share of sensitivity scenarios placing the player in the Top 10. These are model-evidence dimensions, not independent real-world pressure measurements.</p>
              <p className="mt-3 text-xs text-amber-200">{data.meta.methodology} Historical IPL team mappings do not prove current contracts, free-agent status, or uncapped eligibility.</p>
            </section>
          </>
        )}
      </div>
    </main>
  );
}

function Metric({label,value}:{label:string;value:string}) {
  return <div className="rounded-xl border border-white/10 bg-white/5 px-2 py-3"><p className="text-xs text-slate-400">{label}</p><p className="mt-1 text-base font-bold">{value}</p></div>;
}
