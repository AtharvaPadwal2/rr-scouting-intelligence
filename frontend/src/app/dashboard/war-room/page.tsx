
"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import {
  ResponsiveContainer, RadarChart, Radar,
  PolarGrid, PolarAngleAxis, PolarRadiusAxis,
  Tooltip, Legend, BarChart, Bar,
  XAxis, YAxis, CartesianGrid
} from "recharts";

type Role = "BATTER" | "BOWLER";
type Source = "ALL_SMAT" | "CURATED" | "AUCTION";
type AnyRow = Record<string, any>;

type Prospect = {
  key: string;
  id: string;
  name: string;
  team: string;
  source: Source;
  role: Role;
  score: number;
  matches: number;
  balls: number;
  runs: number;
  strikeRate: number | null;
  wickets: number;
  economy: number | null;
  wicketRate: number | null;
  age: number | null;
  verified: boolean;
  status: string;
};

type Pick = {
  key: string;
  name: string;
  role: Role;
  source: Source;
  score: number;
  status: string;
};

const PINK = "#F34B9B";
const BLUE = "#67B9FF";
const SAVE_KEY = "rr-war-room-expanded-v2";

const num = (v: unknown) => {
  if (v === null || v === undefined || v === "") return 0;
  const x = Number(v);
  return Number.isFinite(x) ? x : 0;
};

const text = (v: unknown) =>
  v === null || v === undefined ? "" : String(v);

function pct(value: number, values: number[], lower = false) {
  if (!values.length) return 50;
  const below = values.filter(v => v < value).length;
  const equal = values.filter(v => v === value).length;
  const result = 100 * (below + equal / 2) / values.length;
  return Math.round(lower ? 100 - result : result);
}

function ageOf(dob: string, asOf = "2026-11-10") {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(dob)) return null;
  const born = new Date(dob + "T00:00:00Z");
  const end = new Date(asOf + "T00:00:00Z");
  if (
    Number.isNaN(born.getTime()) ||
    born.toISOString().slice(0, 10) !== dob ||
    born > end
  ) return null;

  let age = end.getUTCFullYear() - born.getUTCFullYear();
  if (
    end.getUTCMonth() < born.getUTCMonth() ||
    (
      end.getUTCMonth() === born.getUTCMonth() &&
      end.getUTCDate() < born.getUTCDate()
    )
  ) age--;
  return age;
}

function exportFile(
  filename: string, value: string, mime: string
) {
  const blob = new Blob([value], { type: mime });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

function csvCell(v: unknown) {
  let value = text(v);
  if (/^[=+\-@\t\r]/.test(value)) value = "'" + value;
  return `"${value.replace(/"/g, '""')}"`;
}

export default function WarRoom() {
  const [smat, setSmat] = useState<AnyRow | null>(null);
  const [curated, setCurated] = useState<AnyRow | null>(null);
  const [auction, setAuction] = useState<AnyRow | null>(null);
  const [error, setError] = useState("");

  const [source, setSource] = useState<Source>("ALL_SMAT");
  const [role, setRole] = useState<Role>("BATTER");
  const [season, setSeason] = useState("ALL");
  const [minBalls, setMinBalls] = useState(0);
  const [minMatches, setMinMatches] = useState(0);
  const [minAge, setMinAge] = useState(18);
  const [maxAge, setMaxAge] = useState(25);
  const [includeUnknown, setIncludeUnknown] = useState(true);
  const [verifiedOnly, setVerifiedOnly] = useState(false);
  const [search, setSearch] = useState("");

  const [playerA, setPlayerA] = useState("");
  const [playerB, setPlayerB] = useState("");
  const [picks, setPicks] = useState<Pick[]>([]);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    Promise.all([
      fetch("/data/smat-warroom.json", { cache: "no-store" }),
      fetch("/data/uncapped-overview.json", { cache: "no-store" }),
      fetch("/data/auction-overview.json", { cache: "no-store" })
    ])
      .then(async responses => {
        for (const res of responses) {
          if (!res.ok) {
            throw new Error(`Missing ${res.url}: ${res.status}`);
          }
        }
        return Promise.all(responses.map(r => r.json()));
      })
      .then(([s, c, a]) => {
        setSmat(s);
        setCurated(c);
        setAuction(a);
      })
      .catch(err => setError(String(err)));

    try {
      const saved = localStorage.getItem(SAVE_KEY);
      if (saved) {
        const parsed = JSON.parse(saved);
        if (Array.isArray(parsed)) {
          setPicks(parsed.filter(
            (p: AnyRow) =>
              p &&
              typeof p.key === "string" &&
              (p.role === "BATTER" || p.role === "BOWLER")
          ));
        }
      }
    } catch {
      // Ignore malformed local shortlist.
    }
    setReady(true);
  }, []);

  useEffect(() => {
    if (ready) {
      localStorage.setItem(SAVE_KEY, JSON.stringify(picks));
    }
  }, [picks, ready]);

  const allDomesticCount = useMemo(() => {
    if (!smat) return 0;
    return new Set(
      (smat.records ?? []).map((r: AnyRow) => text(r.player_id))
    ).size;
  }, [smat]);

  const pool = useMemo<Prospect[]>(() => {
    if (!smat || !curated || !auction) return [];

    const dobMap = new Map<string, AnyRow>();
    for (const item of smat.dob_registry ?? []) {
      dobMap.set(text(item.player_id), item);
    }

    const reviewMap = new Map<string, AnyRow>();
    for (const item of smat.eligibility_registry ?? []) {
      reviewMap.set(text(item.player_id), item);
    }

    const isVerified = (r?: AnyRow) => Boolean(
      r &&
      text(r.nationality_check).toUpperCase() === "YES" &&
      text(r.uncapped_check).toUpperCase() === "YES" &&
      ["NO", "UNATTACHED"].includes(
        text(r.ipl_contract_check).toUpperCase()
      ) &&
      /^https?:\/\//i.test(text(r.evidence_url))
    );

    if (source === "ALL_SMAT") {
      const rows = (smat.records ?? []).filter(
        (r: AnyRow) => season === "ALL" || r.season === season
      );

      const grouped = new Map<string, AnyRow>();

      for (const r of rows) {
        const id = text(r.player_id);
        if (!id) continue;

        if (!grouped.has(id)) {
          grouped.set(id, {
            player_id: id,
            player_name: text(r.player_name),
            teams: new Set<string>(),
            matches: 0, runs: 0, balls_faced: 0,
            legal_balls_bowled: 0, runs_conceded: 0,
            wickets: 0
          });
        }

        const g = grouped.get(id)!;
        if (r.team) g.teams.add(text(r.team));

        for (const field of [
          "matches", "runs", "balls_faced",
          "legal_balls_bowled", "runs_conceded",
          "wickets"
        ]) {
          g[field] += num(r[field]);
        }
      }

      const computed: Prospect[] = [...grouped.values()].map(g => {
        const id = text(g.player_id);
        const balls = role === "BATTER"
          ? g.balls_faced
          : g.legal_balls_bowled;

        const rate = role === "BATTER"
          ? 100 * (g.runs + 1.3 * 120) /
            (g.balls_faced + 120)
          : 6 * (g.runs_conceded + 1.4 * 72) /
            (g.legal_balls_bowled + 72);

        const review = reviewMap.get(id);
        const dob = dobMap.get(id);
        const sourcedDOB =
          /^https?:\/\//i.test(text(dob?.dob_source_url));

        return {
          key: `ALL_SMAT:${role}:${id}`,
          id,
          name: text(g.player_name),
          team: [...g.teams].join(", "),
          source,
          role,
          score: 0,
          matches: g.matches,
          balls,
          runs: g.runs,
          strikeRate: g.balls_faced
            ? 100 * g.runs / g.balls_faced : null,
          wickets: g.wickets,
          economy: g.legal_balls_bowled
            ? 6 * g.runs_conceded / g.legal_balls_bowled
            : null,
          wicketRate: g.legal_balls_bowled
            ? 24 * g.wickets / g.legal_balls_bowled
            : null,
          age: sourcedDOB
            ? ageOf(text(dob?.date_of_birth)) : null,
          verified: isVerified(review),
          status: isVerified(review)
            ? "Locally verified"
            : "Eligibility unverified",
          _rate: rate,
        } as Prospect;
      });

      // The scoring is exploratory, derived within the
      // chosen season and role pool.
      const rateValues = computed.map(
        (p: AnyRow) => num(p._rate)
      );

      const volumeValues = computed.map(p =>
        role === "BATTER" ? p.runs : p.wickets
      );

      return computed.map((p: AnyRow) => ({
        ...p,
        score: Math.round(100 * (
          role === "BATTER"
            ? (
              .65 * pct(p._rate, rateValues) / 100 +
              .35 * pct(p.runs, volumeValues) / 100
            )
            : (
              .5 * pct(p._rate, rateValues, true) / 100 +
              .5 * pct(p.wickets, volumeValues) / 100
            )
        ) * 100) / 100
      })).sort((a, b) => b.score - a.score);
    }

    const dataset = source === "CURATED" ? curated : auction;
    const rows = role === "BATTER"
      ? dataset.batters ?? []
      : dataset.bowlers ?? [];

    return rows.map((r: AnyRow, i: number) => {
      const id = text(r.player_id || i);
      const dob = dobMap.get(id);
      const sourced =
        /^https?:\/\//i.test(text(dob?.dob_source_url));

      const review = reviewMap.get(id);
      const eligible = source === "CURATED"
        ? isVerified(review)
        : false;

      return {
        key: `${source}:${role}:${id}`,
        id,
        name: text(
          r.display_name ||
          r.resolved_name ||
          r.player_name ||
          r.candidate_name
        ),
        team: text(r.teams || r.ipl_2026_team),
        source,
        role,
        score: num(
          source === "CURATED"
            ? r.scouting_score
            : r.adjusted_score
        ),
        matches: num(r.matches),
        balls: num(
          source === "CURATED"
            ? role === "BATTER"
              ? r.balls_faced : r.legal_balls_bowled
            : r.balls
        ),
        runs: num(r.runs),
        strikeRate: r.strike_rate == null
          ? null : num(r.strike_rate),
        wickets: num(r.wickets),
        economy: r.economy == null
          ? null : num(r.economy),
        wicketRate: null,
        age: sourced ? ageOf(text(dob?.date_of_birth)) : null,
        verified: eligible,
        status: eligible
          ? "Locally verified"
          : "Eligibility unverified",
      } as Prospect;
    }).sort((a: Prospect, b: Prospect) => b.score - a.score);
  }, [smat, curated, auction, source, role, season]);

  const filtered = useMemo(() => pool.filter(p => {
    const agePass = p.age == null
      ? includeUnknown
      : p.age >= minAge && p.age <= maxAge;

    return (
      p.balls >= minBalls &&
      p.matches >= minMatches &&
      agePass &&
      (!verifiedOnly || p.verified) &&
      `${p.name} ${p.team}`
        .toLowerCase().includes(search.toLowerCase())
    );
  }), [
    pool, minBalls, minMatches,
    minAge, maxAge, includeUnknown,
    verifiedOnly, search
  ]);

  const a = filtered.find(p => p.key === playerA) ?? filtered[0];
  const b = filtered.find(p =>
    p.key === playerB && p.key !== a?.key
  ) ?? filtered.find(p => p.key !== a?.key);

  const axes = role === "BATTER"
    ? [
      ["Scouting index", "score", false],
      ["Strike rate", "strikeRate", false],
      ["Runs", "runs", false],
      ["Ball sample", "balls", false],
      ["Matches", "matches", false]
    ] as const
    : [
      ["Scouting index", "score", false],
      ["Wicket rate", "wicketRate", false],
      ["Economy", "economy", true],
      ["Ball sample", "balls", false],
      ["Matches", "matches", false]
    ] as const;

  const radar = axes.map(([metric, field, invert]) => {
    const values = pool.map(p => p[field])
      .filter((v): v is number =>
        typeof v === "number" && Number.isFinite(v)
      );

    function position(p?: Prospect) {
      if (!p) return null;
      const v = p[field];
      if (typeof v !== "number" || !Number.isFinite(v))
        return null;
      return pct(v, values, invert);
    }

    return {
      metric,
      A: position(a),
      B: position(b)
    };
  });

  function addPick(p?: Prospect) {
    if (!p) return;
    if (picks.some(x => x.key === p.key)) return;
    if (picks.filter(x => x.role === p.role).length >= 10) {
      alert("All 10 slots for this role are already occupied.");
      return;
    }

    setPicks(old => [...old, {
      key: p.key,
      name: p.name,
      role: p.role,
      source: p.source,
      score: p.score,
      status: p.status
    }]);
  }

  function downloadCSV() {
    const headers = [
      "Role", "Player", "Source",
      "Scouting Score", "Eligibility"
    ];
    const rows = picks.map(p => [
      p.role, p.name, p.source, p.score, p.status
    ]);
    const content = [
      headers.map(csvCell).join(","),
      ...rows.map(r => r.map(csvCell).join(","))
    ].join("\r\n");

    exportFile(
      "rr-war-room-top20.csv",
      "\uFEFF" + content,
      "text/csv;charset=utf-8"
    );
  }

  const stats = [
    ["Domestic players", allDomesticCount],
    ["Players in current role pool", pool.length],
    ["Matching filters", filtered.length],
    ["Selected", `${picks.length} / 20`]
  ];

  return (
    <main className="war-v2">
      <style>{`
        .war-v2 {
          min-height:100vh;
          background:radial-gradient(circle at 80% 0%,#321a40,#090f20 45%);
          color:#f8f9ff;
          padding:32px clamp(16px,4vw,64px) 80px;
          font-family:Inter,system-ui,sans-serif;
        }
        .war-v2 * {box-sizing:border-box}
        .war-v2 h1,.war-v2 h2,.war-v2 p {margin:0}
        .war-v2 h1 {font-size:clamp(36px,5vw,66px);letter-spacing:-.05em}
        .war-v2 h2 {font-size:21px;margin-bottom:10px}
        .war-v2 .pink {color:${PINK}}
        .war-v2 .muted {color:#a4b4d0;font-size:13px;line-height:1.6}
        .war-v2 nav {display:flex;gap:18px;flex-wrap:wrap;margin-bottom:32px}
        .war-v2 nav a {color:#b7c5e0;text-decoration:none;font-size:13px}
        .war-v2 .stats {display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin:26px 0}
        .war-v2 .panel,.war-v2 .stat {
          background:#131e35;border:1px solid #2b3955;
          border-radius:18px;padding:22px;
        }
        .war-v2 .stat small {display:block;color:#9fafd0;margin-bottom:9px}
        .war-v2 .stat strong {font-size:28px}
        .war-v2 .filters {display:grid;grid-template-columns:repeat(4,1fr);gap:15px}
        .war-v2 label {display:block;color:#b6c4df;font-size:12px;margin-bottom:8px}
        .war-v2 input,.war-v2 select {
          width:100%;padding:11px;border-radius:10px;
          border:1px solid #3b4b69;background:#1c2944;color:white;
        }
        .war-v2 input[type=checkbox] {width:auto;accent-color:${PINK}}
        .war-v2 .checks {display:flex;gap:22px;flex-wrap:wrap;margin-top:18px}
        .war-v2 .checks label {display:flex;align-items:center;gap:9px}
        .war-v2 .split {display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-top:18px}
        .war-v2 .bar {height:340px}
        .war-v2 .roster {max-height:430px;overflow:auto;margin-top:14px}
        .war-v2 .player {
          display:flex;justify-content:space-between;align-items:center;
          gap:12px;background:#1d2a47;padding:12px;
          border:1px solid transparent;border-radius:12px;
          width:100%;text-align:left;color:white;margin-bottom:8px;
          cursor:pointer;
        }
        .war-v2 .player:hover {border-color:${PINK}}
        .war-v2 .player small {display:block;color:#9eafcd;margin-top:3px}
        .war-v2 .radar {height:340px}
        .war-v2 .profile {
          background:#1e2a46;border-radius:12px;padding:16px;
        }
        .war-v2 .btn {
          background:${PINK};border:0;border-radius:10px;
          color:#141527;font-weight:800;cursor:pointer;padding:11px 15px;
        }
        .war-v2 .btn:disabled {opacity:.4;cursor:not-allowed}
        .war-v2 .pick {
          display:flex;justify-content:space-between;align-items:center;
          gap:10px;padding:12px;background:#1c2945;
          border-radius:10px;margin-top:8px;
        }
        .war-v2 .notice {
          border:1px solid #77592e;background:#32291f;
          color:#f0d3a2;border-radius:12px;
          padding:13px;margin:18px 0;font-size:12px;
        }
        @media(max-width:1000px) {
          .war-v2 .filters {grid-template-columns:repeat(2,1fr)}
          .war-v2 .split {grid-template-columns:1fr}
        }
        @media(max-width:650px) {
          .war-v2 .stats,.war-v2 .filters {grid-template-columns:1fr 1fr}
        }
      `}</style>

      <nav>
        <Link href="/">Home</Link>
        <Link href="/dashboard/pressure-intelligence">
          Pressure Intelligence
        </Link>
        <Link href="/dashboard/auction-scouting">
          Auction Scouting
        </Link>
        <Link href="/dashboard/uncapped-indians">
          Uncapped Indians
        </Link>
      </nav>

      <div style={{color:PINK,fontSize:12,fontWeight:800,letterSpacing:3}}>
        RAJASTHAN ROYALS / SCOUTING LAB / 04
      </div>

      <h1>Scouting <span className="pink">War Room</span></h1>
      <p className="muted">
        Explore the complete SMAT database, compare prospects
        and construct your 10-batter and 10-bowler shortlist.
      </p>

      {error && <div className="notice">{error}</div>}

      <div className="stats">
        {stats.map(([label, value]) => (
          <div className="stat" key={label}>
            <small>{label}</small>
            <strong>{value}</strong>
          </div>
        ))}
      </div>

      <div className="notice">
        Historical SMAT coverage ends at 2024/25 and is incomplete.
        Missing ages and unverified eligibility are not assumed.
        This is a domestic performance index, not a validated
        match-pressure or auction-availability prediction.
      </div>

      <section className="panel">
        <h2>Scouting filters</h2>

        <div className="filters">
          <div>
            <label>Candidate pool</label>
            <select value={source} onChange={e => {
              setSource(e.target.value as Source);
              setPlayerA(""); setPlayerB("");
            }}>
              <option value="ALL_SMAT">All Domestic Players</option>
              <option value="CURATED">Curated Uncapped Reviews</option>
              <option value="AUCTION">Auction Reviews</option>
            </select>
          </div>

          <div>
            <label>Role</label>
            <select value={role} onChange={e => {
              setRole(e.target.value as Role);
              setPlayerA(""); setPlayerB("");
            }}>
              <option value="BATTER">Batters</option>
              <option value="BOWLER">Bowlers</option>
            </select>
          </div>

          <div>
            <label>Season</label>
            <select value={season} onChange={e => {
              setSeason(e.target.value);
              setPlayerA(""); setPlayerB("");
            }} disabled={source !== "ALL_SMAT"}>
              <option value="ALL">All seasons</option>
              {(smat?.seasons ?? []).map((y: string) => (
                <option key={y} value={y}>{y}</option>
              ))}
            </select>
          </div>

          <div>
            <label>Search player / team</label>
            <input value={search}
              onChange={e => setSearch(e.target.value)}
              placeholder="Search..." />
          </div>

          <div>
            <label>Minimum relevant balls</label>
            <input type="number" min={0} value={minBalls}
              onChange={e => setMinBalls(
                Math.max(0, num(e.target.value))
              )} />
          </div>

          <div>
            <label>Minimum matches</label>
            <input type="number" min={0} value={minMatches}
              onChange={e => setMinMatches(
                Math.max(0, num(e.target.value))
              )} />
          </div>

          <div>
            <label>Minimum age</label>
            <input type="number" min={15} max={50}
              value={minAge} onChange={e => setMinAge(
                Math.min(maxAge, Math.max(15, num(e.target.value)))
              )} />
          </div>

          <div>
            <label>Maximum age</label>
            <input type="number" min={15} max={50}
              value={maxAge} onChange={e => setMaxAge(
                Math.max(minAge, Math.min(50, num(e.target.value)))
              )} />
          </div>
        </div>

        <div className="checks">
          <label>
            <input type="checkbox"
              checked={includeUnknown}
              onChange={e => setIncludeUnknown(e.target.checked)} />
            Include unknown ages
          </label>

          <label>
            <input type="checkbox"
              checked={verifiedOnly}
              onChange={e => setVerifiedOnly(e.target.checked)} />
            Verified eligible only
          </label>
        </div>
      </section>

      <div className="split">
        <section className="panel">
          <h2>Player discovery</h2>
          <p className="muted">
            {filtered.length} players match your filters.
            Select a player to compare or add to your shortlist.
          </p>

          <div className="bar">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart layout="vertical"
                data={[...filtered.slice(0,10)].reverse()}
                margin={{left:12,right:15}}>
                <CartesianGrid stroke="#32415d"
                  strokeDasharray="3 4" horizontal={false}/>
                <XAxis type="number" domain={[0,100]}
                  stroke="#a7b9d5" />
                <YAxis type="category" dataKey="name"
                  width={112} stroke="#c1cde0" fontSize={10}/>
                <Tooltip contentStyle={{
                  background:"#182540",
                  border:"1px solid #415578"
                }}/>
                <Bar dataKey="score" fill={PINK}
                  radius={[0,6,6,0]}/>
              </BarChart>
            </ResponsiveContainer>
          </div>

          <div className="roster">
            {filtered.slice(0,100).map((p,i) => (
              <button className="player" key={p.key}
                onClick={() => {
                  setPlayerA(p.key);
                  if (playerB === p.key) setPlayerB("");
                }}>
                <span>
                  <strong>#{i+1} {p.name}</strong>
                  <small>
                    {p.team || "Domestic"} ·{" "}
                    {p.age ?? "Age unknown"}
                    {p.age == null ? "" : " years"}
                  </small>
                </span>
                <strong style={{color:PINK}}>
                  {p.score.toFixed(2)}
                </strong>
              </button>
            ))}
          </div>
        </section>

        <section className="panel">
          <h2>Head-to-head radar</h2>
          <p className="muted">
            Both players are scored against the same selected
            role and data-source population.
          </p>

          <div className="filters" style={{
            gridTemplateColumns:"1fr 1fr",marginTop:18
          }}>
            <div>
              <label>Player A</label>
              <select value={a?.key ?? ""}
                onChange={e => setPlayerA(e.target.value)}>
                {filtered.map(p => (
                  <option key={p.key} value={p.key}>
                    {p.name}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label>Player B</label>
              <select value={b?.key ?? ""}
                onChange={e => setPlayerB(e.target.value)}>
                {filtered.filter(p => p.key !== a?.key)
                  .map(p => (
                    <option key={p.key} value={p.key}>
                      {p.name}
                    </option>
                  ))}
              </select>
            </div>
          </div>

          <div className="radar">
            <ResponsiveContainer width="100%" height="100%">
              <RadarChart data={radar} outerRadius="66%">
                <PolarGrid stroke="#435270"/>
                <PolarAngleAxis dataKey="metric"
                  stroke="#d7e2f5" fontSize={11}/>
                <PolarRadiusAxis domain={[0,100]}
                  tick={false} axisLine={false}/>
                <Radar name={a?.name ?? "Player A"}
                  dataKey="A" stroke={PINK}
                  fill={PINK} fillOpacity={0.23}/>
                <Radar name={b?.name ?? "Player B"}
                  dataKey="B" stroke={BLUE}
                  fill={BLUE} fillOpacity={0.19}/>
                <Legend/>
                <Tooltip contentStyle={{
                  background:"#182540",
                  border:"1px solid #415578"
                }}/>
              </RadarChart>
            </ResponsiveContainer>
          </div>

          <div className="split" style={{marginTop:0}}>
            {[a,b].map((p,i) => (
              <div className="profile" key={i}>
                <h2 style={{fontSize:17}}>
                  {p?.name ?? "No player"}
                </h2>
                <p className="muted">
                  Score: {p?.score.toFixed(2) ?? "—"}
                </p>
                <p className="muted">
                  Matches: {p?.matches ?? "—"} ·
                  Balls: {p?.balls ?? "—"}
                </p>
                <p className="muted">
                  {p?.status ?? "Unverified"}
                </p>
                <button className="btn" style={{marginTop:12}}
                  onClick={() => addPick(p)}
                  disabled={
                    !p || picks.some(x => x.key === p.key)
                  }>
                  Add to Top 10
                </button>
              </div>
            ))}
          </div>
        </section>
      </div>

      <section className="panel" style={{marginTop:18}}>
        <h2>Final scouting shortlist</h2>
        <p className="muted">
          Select up to 10 batters and 10 bowlers.
          Choices are saved in this browser.
        </p>

        <div className="split">
          {(["BATTER","BOWLER"] as Role[]).map(r => (
            <div key={r}>
              <h2 style={{marginTop:20}}>
                {r === "BATTER" ? "Batters" : "Bowlers"}
                {" "}({picks.filter(p => p.role === r).length}/10)
              </h2>

              {picks.filter(p => p.role === r).map((p,i) => (
                <div className="pick" key={p.key}>
                  <div>
                    <strong>#{i+1} {p.name}</strong>
                    <p className="muted">
                      {p.source} · {p.status}
                    </p>
                  </div>
                  <button className="btn"
                    onClick={() => setPicks(
                      old => old.filter(x => x.key !== p.key)
                    )}>
                    Remove
                  </button>
                </div>
              ))}
            </div>
          ))}
        </div>

        <div style={{display:"flex",gap:12,marginTop:22,flexWrap:"wrap"}}>
          <button className="btn" onClick={downloadCSV}
            disabled={!picks.length}>
            Export CSV
          </button>
          <button className="btn" onClick={() => exportFile(
            "rr-war-room-top20.json",
            JSON.stringify(picks,null,2),
            "application/json"
          )} disabled={!picks.length}>
            Export JSON
          </button>
          <button className="btn" onClick={() => {
            if (confirm("Clear all shortlisted players?"))
              setPicks([]);
          }} disabled={!picks.length}>
            Clear shortlist
          </button>
        </div>
      </section>
    </main>
  );
}
