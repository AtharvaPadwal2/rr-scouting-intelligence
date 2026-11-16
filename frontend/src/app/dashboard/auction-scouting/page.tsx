"use client";

import { useEffect, useMemo, useState } from "react";
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  RadarChart,
  Radar,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
} from "recharts";

type Item = Record<string, unknown>;
type Data = {
  metadata?: Record<string, unknown>;
  batters?: Item[];
  bowlers?: Item[];
  uncappedBatters?: Item[];
  uncappedBowlers?: Item[];
};
type Pool = "auction" | "domestic";
type Role = "batters" | "bowlers";

const str = (v: unknown): string => v === null || v === undefined ? "" : String(v);
const num = (v: unknown): number | null => {
  if (v === null || v === undefined || v === "") return null;
  const n = Number(v);
  return Number.isFinite(n) ? n : null;
};
const score = (r: Item, pool: Pool) => num(r[pool === "auction" ? "adjusted_score" : "scouting_score"]);
const name = (r: Item) => str(r.resolved_name || r.candidate_name || r.player_name || r.registry_name || "Unnamed player");
const pct = (v: number) => Math.max(0, Math.min(100, v));
const format = (n: number | null, digits = 2) => n === null ? "—" : n.toFixed(digits);
const abbrev = (s: string) => s.length > 21 ? `${s.slice(0, 20)}…` : s;

function statusOf(row: Item): string {
  const v = str(row.screening_status || row.verification_status || row.eligibility_status).toUpperCase();
  if (["VERIFIED_ELIGIBLE", "VERIFIED_UNATTACHED"].includes(v)) return "VERIFIED";
  if (v.includes("EXCLUDE")) return "EXCLUDED";
  if (v.includes("REGISTRATION")) return "REGISTRATION CHECK";
  if (v.includes("PRIORITY")) return "PRIORITY REVIEW";
  return "NOT VERIFIED";
}

export default function AuctionScoutingPage() {
  const [data, setData] = useState<Data | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [pool, setPool] = useState<Pool>("auction");
  const [role, setRole] = useState<Role>("batters");
  const [query, setQuery] = useState("");
  const [onlyVerified, setOnlyVerified] = useState(false);
  const [selectedId, setSelectedId] = useState("");

  useEffect(() => {
    let active = true;
    fetch("/data/auction-overview.json", { cache: "no-store" })
      .then(async r => {
        if (!r.ok) throw new Error(`HTTP ${r.status}: /data/auction-overview.json`);
        return (await r.json()) as Data;
      })
      .then(d => { if (active) { setData(d); setError(""); } })
      .catch(e => { if (active) setError(e instanceof Error ? e.message : "Could not load auction data"); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, []);

  const currentKey = pool === "auction" ? role : role === "batters" ? "uncappedBatters" : "uncappedBowlers";
  const rows = useMemo(() => {
    const items = data?.[currentKey] as Item[] | undefined;
    return [...(Array.isArray(items) ? items : [])].sort((a, b) => (score(b, pool) ?? -Infinity) - (score(a, pool) ?? -Infinity));
  }, [currentKey, data, pool]);

  const filtered = useMemo(() => rows.filter(r => {
    const textMatch = `${name(r)} ${str(r.teams)} ${str(r.screening_status)}`.toLowerCase().includes(query.trim().toLowerCase());
    return textMatch && (!onlyVerified || statusOf(r) === "VERIFIED");
  }), [rows, query, onlyVerified]);
  const identifier = (r: Item) => `${str(r.player_id)}-${name(r)}`;
  const selected = filtered.find(r => identifier(r) === selectedId) ?? filtered[0] ?? null;

  const scores = rows.map(r => score(r, pool)).filter((s): s is number => s !== null);
  const lo = scores.length ? Math.min(...scores) : 0;
  const hi = scores.length ? Math.max(...scores) : 1;
  const percentile = (n: number | null) => {
    if (n === null || !scores.length) return null;
    return pct(100 * scores.filter(x => x <= n).length / scores.length);
  };

  const sample = selected ? num(selected.balls ?? selected.balls_high ?? selected.legal_balls_bowled ?? selected.balls_faced) : null;
  const appearances = selected ? num(selected.matches ?? selected.matches_high) : null;
  const sampleValues = rows.map(r => num(r.balls ?? r.balls_high ?? r.legal_balls_bowled ?? r.balls_faced) ?? 0);
  const matchValues = rows.map(r => num(r.matches ?? r.matches_high) ?? 0);
  const maxSample = Math.max(1, ...sampleValues);
  const maxMatches = Math.max(1, ...matchValues);
  const impact = selected ? percentile(score(selected, pool)) : null;
  const radar = [
    { metric: "Score rank", value: impact },
    { metric: "Ball sample", value: sample === null ? null : pct(100 * sample / maxSample) },
    { metric: "Match sample", value: appearances === null ? null : pct(100 * appearances / maxMatches) },
    { metric: "Consistency", value: selected ? num(selected.positive_match_pct) : null },
    { metric: "Stability", value: selected ? num(selected.top_10_scenario_pct) : null },
  ];
  const knownRadar = radar.filter(r => r.value !== null) as {metric: string; value: number}[];
  const chartData = filtered.slice(0, 10).reverse().map(r => ({ name: abbrev(name(r)), score: score(r, pool) ?? 0 }));
  const verifiedCount = rows.filter(r => statusOf(r) === "VERIFIED").length;

  return (
    <main className="auction-page">
      <style>{`
      .auction-page{min-height:100vh;color:#f7f8ff;background:radial-gradient(ellipse at 83% 0%,rgba(246,66,150,.11),transparent 29%),radial-gradient(ellipse at 2% 36%,rgba(41,92,205,.17),transparent 28%),#080e1e;font-family:Inter,ui-sans-serif,system-ui,sans-serif;padding:34px clamp(18px,3.5vw,60px) 70px}
      .auction-page *{box-sizing:border-box}
      .auction-page h1,.auction-page h2,.auction-page h3,.auction-page p{margin:0}
      .auction-page a{color:#f9a9d2;text-decoration:none}
      .auction-page .eyebrow{font-size:12px;letter-spacing:.22em;text-transform:uppercase;color:#f19fc8;font-weight:750}
      .auction-page h1{font-size:clamp(35px,4.3vw,66px);letter-spacing:-.05em;line-height:1.13;margin:14px 0}
      .auction-page .pink{color:#fb4c9e}
      .auction-page .sub{color:#adbad3;line-height:1.65;max-width:790px}
      .auction-page .head{display:flex;align-items:flex-start;justify-content:space-between;gap:24px;margin-bottom:24px}
      .auction-page .warning{max-width:315px;padding:14px 16px;border:1px solid #8b6024;background:#3c2b20b0;color:#f8d7a1;border-radius:14px;font-size:12px;line-height:1.5}
      .auction-page .cards{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:13px;margin:28px 0}
      .auction-page .card,.auction-page .panel{border:1px solid #2a3653;background:#111a31;border-radius:19px}
      .auction-page .card{padding:22px}
      .auction-page .statlabel{font-size:11px;color:#9caac4;letter-spacing:.08em;text-transform:uppercase}
      .auction-page .statval{font-size:35px;letter-spacing:-.04em;font-weight:800;margin:8px 0 3px}
      .auction-page .muted{color:#9baac4;font-size:12px}
      .auction-page .tools{display:flex;align-items:center;gap:12px;flex-wrap:wrap;margin:24px 0}
      .auction-page button,.auction-page input{font:inherit}
      .auction-page button{cursor:pointer}
      .auction-page .pill{border:1px solid #364564;background:#15213a;color:#e6edff;border-radius:12px;padding:11px 17px;font-weight:680;font-size:13px}
      .auction-page .pill.active{background:#f7489e;border-color:#f7489e;color:#0a1020}
      .auction-page .search{margin-left:auto;background:#111a31;border:1px solid #364564;color:#fff;border-radius:12px;padding:12px 15px;width:min(300px,100%)}
      .auction-page .checkbox{display:flex;align-items:center;gap:7px;font-size:12px;color:#cbd4e8}
      .auction-page .mainGrid{display:grid;grid-template-columns:1.02fr .98fr;gap:16px;align-items:stretch}
      .auction-page .panel{padding:23px;min-width:0}
      .auction-page .ptitle{font-size:21px;font-weight:780;letter-spacing:-.025em}
      .auction-page .panelHead{display:flex;align-items:start;justify-content:space-between;gap:12px;margin-bottom:16px}
      .auction-page .chartWrap{width:100%;height:310px}
      .auction-page .leaderboard{display:flex;flex-direction:column;gap:8px;max-height:365px;overflow-y:auto;padding-right:3px}
      .auction-page .entry{width:100%;display:grid;grid-template-columns:35px minmax(0,1fr) 78px;align-items:center;text-align:left;background:#18223c;border:1px solid transparent;color:#eff2ff;padding:13px 12px;border-radius:12px;gap:10px}
      .auction-page .entry.selected{border-color:#f7489e;background:#282039}
      .auction-page .entry:hover{border-color:#87537a}
      .auction-page .rank{font-size:13px;color:#f79fca;font-weight:800}
      .auction-page .ename{font-weight:750;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-size:13px}
      .auction-page .esub{color:#9daac6;font-size:11px;margin-top:3px}
      .auction-page .escore{text-align:right;font-size:16px;font-weight:790}
      .auction-page .tag{font-size:10px;border:1px solid #72552e;background:#372a25;color:#f5cb8f;padding:4px 7px;border-radius:7px;white-space:nowrap}
      .auction-page .tag.verified{border-color:#31695b;background:#163f38;color:#96f0ca}
      .auction-page .playerName{font-size:27px;font-weight:800;letter-spacing:-.03em;margin:10px 0 5px}
      .auction-page .detailMetrics{display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin-top:16px}
      .auction-page .metric{padding:13px;background:#1a2440;border-radius:12px}
      .auction-page .metric b{display:block;font-size:20px;margin-top:7px}
      .auction-page .footnote{font-size:11px;color:#b4c1d7;line-height:1.65;margin-top:16px;border-top:1px solid #32405b;padding-top:13px}
      .auction-page .empty{color:#d6c4cc;padding:35px 5px;text-align:center}
      @media(max-width:1060px){.auction-page .cards{grid-template-columns:repeat(2,1fr)}.auction-page .mainGrid{grid-template-columns:1fr}.auction-page .head{flex-direction:column}.auction-page .search{margin-left:0}}
      @media(max-width:560px){.auction-page .cards{grid-template-columns:1fr 1fr}.auction-page .card{padding:15px}.auction-page .statval{font-size:27px}.auction-page .panel{padding:16px}.auction-page .detailMetrics{grid-template-columns:repeat(2,1fr)}.auction-page .search{width:100%}}
      `}</style>

      <header className="head">
        <div>
          <div className="eyebrow">RR SCOUTING INTELLIGENCE / DASHBOARD 02</div>
          <h1>Auction <span className="pink">Scouting</span></h1>
          <p className="sub">Find high-upside performers outside our historical IPL 2026 squad mapping. Explore batting, bowling and domestic scouting evidence without misrepresenting contract or uncapped eligibility.</p>
          <p className="muted" style={{marginTop:10}}><a href="/dashboard/pressure-intelligence">← Pressure Intelligence</a> &nbsp; • &nbsp; <a href="/">Home</a></p>
        </div>
        <aside className="warning"><strong>VERIFICATION REQUIRED</strong><br/>These are candidate review pools, <em>not</em> confirmed free agents or guaranteed IPL 2027 auction registrations. Indian domestic participation alone does not establish uncapped status.</aside>
      </header>

      {error ? <section className="panel" style={{color:"#ffb3b3"}}>Data load failed: {error}. Run <code>python scripts/export_auction_dashboard.py</code> from the project root and check <code>frontend/public/data/auction-overview.json</code>.</section> : null}
      {loading ? <section className="panel">Loading scouting data…</section> : null}
      {!loading && data && !error ? <>
        <section className="cards" aria-label="Scouting coverage">
          <div className="card"><div className="statlabel">Auction batting reviews</div><div className="statval">{data.batters?.length ?? 0}</div><div className="muted">Not in 2026 roster proxy</div></div>
          <div className="card"><div className="statlabel">Auction bowling reviews</div><div className="statval">{data.bowlers?.length ?? 0}</div><div className="muted">Status still to verify</div></div>
          <div className="card"><div className="statlabel">Domestic batting reviews</div><div className="statval">{data.uncappedBatters?.length ?? 0}</div><div className="muted">SMAT-derived candidates</div></div>
          <div className="card"><div className="statlabel">Domestic bowling reviews</div><div className="statval">{data.uncappedBowlers?.length ?? 0}</div><div className="muted">SMAT-derived candidates</div></div>
        </section>
        <section className="tools" aria-label="Scouting filters">
          <button className={`pill ${pool === "auction" ? "active" : ""}`} onClick={() => {setPool("auction");setSelectedId("")}}>Auction review pool</button>
          <button className={`pill ${pool === "domestic" ? "active" : ""}`} onClick={() => {setPool("domestic");setSelectedId("")}}>Uncapped Indian research</button>
          <button className={`pill ${role === "batters" ? "active" : ""}`} onClick={() => {setRole("batters");setSelectedId("")}}>Batters</button>
          <button className={`pill ${role === "bowlers" ? "active" : ""}`} onClick={() => {setRole("bowlers");setSelectedId("")}}>Bowlers</button>
          <label className="checkbox"><input type="checkbox" checked={onlyVerified} onChange={e => setOnlyVerified(e.target.checked)}/> Verified only</label>
          <input className="search" placeholder="Search player or team…" value={query} onChange={e=>setQuery(e.target.value)} />
        </section>
        <section className="mainGrid">
          <div className="panel">
            <div className="panelHead"><div><h2 className="ptitle">Candidate leaderboard</h2><p className="muted">{filtered.length} visible of {rows.length} • {pool === "auction" ? "Structural-pressure adjusted scores" : "Historical SMAT scouting index"}</p></div><span className="tag">{verifiedCount} verified in this pool</span></div>
            {filtered.length ? <>
              <div className="chartWrap">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={chartData} layout="vertical" margin={{left:15,right:26,top:6,bottom:5}}>
                    <CartesianGrid stroke="#2b3550" strokeDasharray="3 5" horizontal={false}/>
                    <XAxis type="number" stroke="#93a0bb" fontSize={11}/>
                    <YAxis type="category" dataKey="name" width={123} stroke="#c9d3e8" fontSize={11} tickLine={false}/>
                    <Tooltip cursor={{fill:"#202943"}} contentStyle={{background:"#17223c",border:"1px solid #405172",borderRadius:12,color:"#f9f9ff"}}/>
                    <Bar dataKey="score" name="Scouting score" fill="#f64b9c" radius={[0,6,6,0]} maxBarSize={19}/>
                  </BarChart>
                </ResponsiveContainer>
              </div>
              <div className="leaderboard">
                {filtered.slice(0,30).map((r,i) => <button key={`${identifier(r)}-${i}`} className={`entry ${selected && identifier(selected) === identifier(r) ? "selected" : ""}`} onClick={()=>setSelectedId(identifier(r))}>
                  <span className="rank">#{i+1}</span><span><div className="ename">{name(r)}</div><div className="esub">{pool === "domestic" ? str(r.teams || "Domestic") : statusOf(r)}</div></span><span className="escore">{format(score(r,pool))}</span>
                </button>)}
              </div>
            </> : <div className="empty">No players match these filters. A verified-only view will remain empty until current contract, identity and uncapped eligibility are documented.</div>}
          </div>
          <div className="panel">
            <div className="panelHead"><div><h2 className="ptitle">Candidate evidence radar</h2><p className="muted">Observed and sample-based axes only</p></div><span className="tag">PROVISIONAL</span></div>
            {selected ? <>
              <div className="playerName">{name(selected)}</div>
              <p className="muted">{pool === "domestic" ? str(selected.teams || "SMAT domestic player") : "Outside historical IPL 2026 roster mapping"} · {statusOf(selected)}</p>
              {knownRadar.length >= 3 ? <div className="chartWrap" style={{height:335,marginTop:8}}>
                <ResponsiveContainer width="100%" height="100%">
                  <RadarChart data={radar} outerRadius="70%">
                    <PolarGrid stroke="#3b4867"/>
                    <PolarAngleAxis dataKey="metric" tick={{fill:"#c8d3e9",fontSize:11}}/>
                    <PolarRadiusAxis domain={[0,100]} tick={{fill:"#92a1c0",fontSize:10}} axisLine={false}/>
                    <Radar dataKey="value" stroke="#ff54a6" fill="#ff54a6" fillOpacity={0.32} strokeWidth={2.5} connectNulls={false}/>
                  </RadarChart>
                </ResponsiveContainer>
              </div> : <div className="empty">Insufficient verified metrics for a five-axis radar. Showing available observations below instead.</div>}
              <div className="detailMetrics">
                <div className="metric"><span className="statlabel">Model score</span><b>{format(score(selected,pool))}</b></div>
                <div className="metric"><span className="statlabel">Matches in sample</span><b>{appearances ?? "—"}</b></div>
                <div className="metric"><span className="statlabel">Relevant balls</span><b>{sample ?? "—"}</b></div>
                <div className="metric"><span className="statlabel">Positive matches</span><b>{num(selected.positive_match_pct) === null ? "—" : `${format(num(selected.positive_match_pct),1)}%`}</b></div>
                <div className="metric"><span className="statlabel">Top 10 stability</span><b>{num(selected.top_10_scenario_pct) === null ? "—" : `${format(num(selected.top_10_scenario_pct),1)}%`}</b></div>
                <div className="metric"><span className="statlabel">Eligibility</span><b style={{fontSize:12}}>{statusOf(selected)}</b></div>
              </div>
              <p className="footnote">Radar axes are independent descriptors, not a validated pressure index. Score rank is the percentile among this filtered category’s source pool; sample axes are scaled against the largest sample in that pool. Missing consistency or stability values are not invented. Neither auction availability nor nationality is treated as a performance attribute. SMAT data has incomplete match coverage through 2024/25.</p>
            </> : <div className="empty">Select a candidate to inspect their evidence.</div>}
          </div>
        </section>
        <p className="footnote">Data source: locally generated <code>auction-overview.json</code>. Batters and bowlers have different score scales and should not be directly compared. This is a research dashboard; verify identity, official IPL uncapped classification, current contracts, and auction registration before presenting a player as available.</p>
      </> : null}
    </main>
  );
}
