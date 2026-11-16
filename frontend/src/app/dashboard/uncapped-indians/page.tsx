
"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
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

type Player = {
  player_id: string;
  display_name: string;
  teams?: string;
  seasons?: string;
  scouting_score: number;
  matches?: number;
  runs?: number;
  balls_faced?: number;
  strike_rate?: number;
  wickets?: number;
  legal_balls_bowled?: number;
  economy?: number;
  age?: number | null;
  nationality_check?: string;
  uncapped_check?: string;
  ipl_contract_check?: string;
  verified_eligible?: boolean;
  auction_2026_status?: string;
};

type Dataset = {
  metadata: {
    asOf: string;
    dataCoverage: string;
  };
  batters: Player[];
  bowlers: Player[];
};

type Role = "BATTER" | "BOWLER";

const PINK = "#F34B9B";
const BLUE = "#5789ED";

function number(value: unknown): number {
  const n = Number(value);
  return Number.isFinite(n) ? n : 0;
}

function percentile(values: number[], value: number): number {
  if (!values.length) return 0;
  return Math.round(
    (values.filter((v) => v <= value).length / values.length) * 100
  );
}

function ageLabel(p: Player) {
  return p.age == null ? "Age unverified" : `${p.age} years`;
}

export default function UncappedIndiansPage() {
  const [data, setData] = useState<Dataset | null>(null);
  const [error, setError] = useState("");
  const [role, setRole] = useState<Role>("BATTER");
  const [minAge, setMinAge] = useState(18);
  const [maxAge, setMaxAge] = useState(25);
  const [includeUnknown, setIncludeUnknown] = useState(true);
  const [verifiedOnly, setVerifiedOnly] = useState(false);
  const [search, setSearch] = useState("");
  const [selectedId, setSelectedId] = useState("");

  useEffect(() => {
    fetch("/data/uncapped-overview.json", { cache: "no-store" })
      .then((res) => {
        if (!res.ok) {
          throw new Error(`Data request failed: ${res.status}`);
        }
        return res.json();
      })
      .then((result: Dataset) => setData(result))
      .catch((err) => setError(String(err)));
  }, []);

  const allPlayers = useMemo(() => {
    const pool = role === "BATTER" ? data?.batters : data?.bowlers;
    return [...(pool ?? [])].sort(
      (a, b) => number(b.scouting_score) - number(a.scouting_score)
    );
  }, [data, role]);

  const filteredPlayers = useMemo(() => {
    return allPlayers.filter((p) => {
      const matchesSearch = (
        `${p.display_name} ${p.teams ?? ""}`
      ).toLowerCase().includes(search.toLowerCase());

      const matchesAge =
        p.age == null
          ? includeUnknown
          : p.age >= minAge && p.age <= maxAge;

      const matchesVerification =
        !verifiedOnly || p.verified_eligible === true;

      return matchesSearch && matchesAge && matchesVerification;
    });
  }, [
    allPlayers,
    search,
    includeUnknown,
    minAge,
    maxAge,
    verifiedOnly,
  ]);

  const selectedPlayer =
    filteredPlayers.find((p) => p.player_id === selectedId) ??
    filteredPlayers[0] ??
    null;

  const chartData = filteredPlayers.slice(0, 10).map((p) => ({
    name: p.display_name.length > 17
      ? p.display_name.slice(0, 17) + "…"
      : p.display_name,
    score: number(p.scouting_score),
  }));

  // All radar axes are percentiles among the same-role
  // research pool. These measure domestic performance,
  // NOT verified pressure-specific performance.
  const radarData = useMemo(() => {
    if (!selectedPlayer) return [];

    const metrics =
      role === "BATTER"
        ? [
            { label: "Scouting", field: "scouting_score" },
            { label: "Strike rate", field: "strike_rate" },
            { label: "Run volume", field: "runs" },
            { label: "Matches", field: "matches" },
            { label: "Ball sample", field: "balls_faced" },
          ]
        : [
            { label: "Scouting", field: "scouting_score" },
            { label: "Wickets", field: "wickets" },
            { label: "Economy", field: "economy", invert: true },
            { label: "Matches", field: "matches" },
            { label: "Ball sample", field: "legal_balls_bowled" },
          ];

    return metrics.map((metric) => {
      const field = metric.field as keyof Player;

      const validValues = allPlayers
        .map((p) => p[field])
        .filter(
          (v): v is number =>
            typeof v === "number" && Number.isFinite(v)
        );

      const value = selectedPlayer[field];
      const raw =
        typeof value === "number" && Number.isFinite(value)
          ? value
          : null;

      let result =
        raw === null ? 0 : percentile(validValues, raw);

      if (metric.invert && raw !== null) {
        result = 100 - result;
      }

      return {
        metric: metric.label,
        value: result,
        average: 50,
      };
    });
  }, [allPlayers, selectedPlayer, role]);

  const eligibleCount = allPlayers.filter(
    (p) => p.verified_eligible === true
  ).length;

  const sourcedAgeCount = allPlayers.filter(
    (p) => p.age != null
  ).length;

  return (
    <main className="rr-uncapped">
      <style>{`
        .rr-uncapped {
          min-height: 100vh;
          padding: 34px clamp(16px, 4vw, 64px) 80px;
          color: #f6f8ff;
          font-family: Inter, system-ui, sans-serif;
          background:
            radial-gradient(circle at 85% 0%,
              rgba(243,75,155,.15), transparent 32%),
            radial-gradient(circle at 0% 45%,
              rgba(40,93,205,.17), transparent 36%),
            #080e1d;
        }
        .rr-uncapped * { box-sizing: border-box; }
        .rr-uncapped h1,.rr-uncapped h2,.rr-uncapped p {
          margin: 0;
        }
        .rr-uncapped .eyebrow {
          color: #f7a0ce;
          font-size: 12px;
          font-weight: 800;
          letter-spacing: .2em;
        }
        .rr-uncapped h1 {
          font-size: clamp(36px, 4.5vw, 66px);
          letter-spacing: -.05em;
          margin: 12px 0;
        }
        .rr-uncapped .pink { color: ${PINK}; }
        .rr-uncapped .muted {
          color: #9faecb;
          font-size: 13px;
          line-height: 1.7;
        }
        .rr-uncapped .nav {
          display: flex;
          gap: 20px;
          margin-bottom: 30px;
          flex-wrap: wrap;
        }
        .rr-uncapped .nav a {
          color: #a8b8d5;
          text-decoration: none;
          font-size: 13px;
        }
        .rr-uncapped .nav a:hover { color: ${PINK}; }
        .rr-uncapped .stats {
          display: grid;
          grid-template-columns: repeat(4, 1fr);
          gap: 14px;
          margin: 28px 0;
        }
        .rr-uncapped .stat,.rr-uncapped .panel {
          background: #111a31;
          border: 1px solid #293752;
          border-radius: 19px;
        }
        .rr-uncapped .stat { padding: 23px; }
        .rr-uncapped .stat span {
          color: #9aaac6;
          font-size: 12px;
        }
        .rr-uncapped .stat strong {
          display: block;
          font-size: 34px;
          margin-top: 9px;
        }
        .rr-uncapped .panel { padding: 24px; }
        .rr-uncapped .filters {
          display: grid;
          grid-template-columns: repeat(4, minmax(0, 1fr));
          gap: 20px;
          margin-bottom: 16px;
        }
        .rr-uncapped label {
          display: block;
          font-size: 12px;
          color: #a8b7d0;
          margin-bottom: 9px;
        }
        .rr-uncapped input,
        .rr-uncapped select {
          width: 100%;
          border: 1px solid #344360;
          border-radius: 11px;
          background: #1a2540;
          color: white;
          padding: 12px;
          font: inherit;
        }
        .rr-uncapped input[type=range] {
          accent-color: ${PINK};
          padding: 8px 0;
        }
        .rr-uncapped .toggles {
          display: flex;
          flex-wrap: wrap;
          gap: 22px;
          align-items: center;
          margin-top: 12px;
        }
        .rr-uncapped .toggles label {
          display: flex;
          align-items: center;
          gap: 9px;
          margin: 0;
        }
        .rr-uncapped .toggles input {
          width: auto;
          accent-color: ${PINK};
        }
        .rr-uncapped .grid {
          display: grid;
          grid-template-columns: 1fr 1fr;
          gap: 16px;
          margin-top: 20px;
        }
        .rr-uncapped .section-title {
          font-size: 22px;
          font-weight: 800;
          margin-bottom: 6px;
        }
        .rr-uncapped .leaderboard {
          max-height: 520px;
          overflow: auto;
          margin-top: 17px;
          display: flex;
          flex-direction: column;
          gap: 8px;
        }
        .rr-uncapped .player-btn {
          display: grid;
          grid-template-columns: 36px 1fr auto;
          gap: 12px;
          align-items: center;
          width: 100%;
          background: #19243e;
          border: 1px solid transparent;
          border-radius: 12px;
          color: #f6f8ff;
          padding: 13px;
          text-align: left;
          cursor: pointer;
        }
        .rr-uncapped .player-btn:hover,
        .rr-uncapped .player-btn.active {
          border-color: ${PINK};
          background: #29213e;
        }
        .rr-uncapped .rank {
          color: ${PINK};
          font-weight: 800;
        }
        .rr-uncapped .small {
          font-size: 11px;
          color: #9eaeca;
          margin-top: 4px;
        }
        .rr-uncapped .score {
          font-size: 18px;
          font-weight: 800;
        }
        .rr-uncapped .chart {
          height: 330px;
          width: 100%;
          margin-top: 15px;
        }
        .rr-uncapped .details {
          display: grid;
          grid-template-columns: repeat(3, 1fr);
          gap: 10px;
          margin-top: 18px;
        }
        .rr-uncapped .detail {
          border-radius: 12px;
          background: #1a2540;
          padding: 13px;
        }
        .rr-uncapped .detail small {
          color: #a2b1cc;
          display: block;
          margin-bottom: 8px;
        }
        .rr-uncapped .detail strong { font-size: 19px; }
        .rr-uncapped .notice {
          margin: 20px 0;
          padding: 14px;
          border: 1px solid #80602c;
          border-radius: 12px;
          background: #392d21;
          color: #f6dbad;
          font-size: 12px;
          line-height: 1.7;
        }
        @media(max-width:1000px) {
          .rr-uncapped .grid { grid-template-columns: 1fr; }
          .rr-uncapped .stats { grid-template-columns: repeat(2,1fr); }
          .rr-uncapped .filters { grid-template-columns: repeat(2,1fr); }
        }
        @media(max-width:560px) {
          .rr-uncapped .filters { grid-template-columns: 1fr; }
          .rr-uncapped .details { grid-template-columns: repeat(2,1fr); }
        }
      `}</style>

      <nav className="nav">
        <Link href="/">Home</Link>
        <Link href="/dashboard/pressure-intelligence">
          Pressure Intelligence
        </Link>
        <Link href="/dashboard/auction-scouting">
          Auction Scouting
        </Link>
      </nav>

      <div className="eyebrow">
        RR SCOUTING INTELLIGENCE / DASHBOARD 03
      </div>

      <h1>
        Uncapped <span className="pink">Indian Talent</span>
      </h1>

      <p className="muted">
        Discover domestic prospects using SMAT performance,
        age filters and verified eligibility evidence.
      </p>

      {error && (
        <div className="notice">
          Could not load dashboard data: {error}
        </div>
      )}

      {!data && !error && <p>Loading scouting data...</p>}

      {data && (
        <>
          <section className="stats">
            <div className="stat">
              <span>Batting reviews</span>
              <strong>{data.batters.length}</strong>
            </div>
            <div className="stat">
              <span>Bowling reviews</span>
              <strong>{data.bowlers.length}</strong>
            </div>
            <div className="stat">
              <span>Verified eligible / selected role</span>
              <strong>{eligibleCount}</strong>
            </div>
            <div className="stat">
              <span>Sourced DOB / selected role</span>
              <strong>{sourcedAgeCount}</strong>
            </div>
          </section>

          <div className="notice">
            These are historical SMAT research candidates.
            Unverified players are not confirmed uncapped or
            unattached. The dataset does not establish current
            form or 2027 auction availability.
          </div>

          <section className="panel">
            <h2 className="section-title">Filter prospects</h2>

            <div className="filters">
              <div>
                <label>Player category</label>
                <select
                  value={role}
                  onChange={(e) => {
                    setRole(e.target.value as Role);
                    setSelectedId("");
                  }}
                >
                  <option value="BATTER">Batters</option>
                  <option value="BOWLER">Bowlers</option>
                </select>
              </div>

              <div>
                <label>Minimum age: {minAge}</label>
                <input
                  type="range"
                  min={16}
                  max={40}
                  value={minAge}
                  onChange={(e) =>
                    setMinAge(
                      Math.min(Number(e.target.value), maxAge)
                    )
                  }
                />
              </div>

              <div>
                <label>Maximum age: {maxAge}</label>
                <input
                  type="range"
                  min={16}
                  max={40}
                  value={maxAge}
                  onChange={(e) =>
                    setMaxAge(
                      Math.max(Number(e.target.value), minAge)
                    )
                  }
                />
              </div>

              <div>
                <label>Search player or team</label>
                <input
                  placeholder="Search..."
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                />
              </div>
            </div>

            <div className="toggles">
              <label>
                <input
                  type="checkbox"
                  checked={includeUnknown}
                  onChange={(e) =>
                    setIncludeUnknown(e.target.checked)
                  }
                />
                Include players with unknown age
              </label>

              <label>
                <input
                  type="checkbox"
                  checked={verifiedOnly}
                  onChange={(e) =>
                    setVerifiedOnly(e.target.checked)
                  }
                />
                Verified eligible only
              </label>
            </div>

            <p className="muted" style={{ marginTop: 14 }}>
              {filteredPlayers.length} matching players.
              Ages calculated as of {data.metadata.asOf}.
              Age-unverified records can be included for research,
              but their ages cannot be assumed to match the range.
            </p>
          </section>

          <section className="grid">
            <div className="panel">
              <h2 className="section-title">Domestic leaderboard</h2>
              <p className="muted">
                Ranked by the existing SMAT scouting index.
              </p>

              {filteredPlayers.length > 0 ? (
                <>
                  <div className="chart">
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart
                        data={[...chartData].reverse()}
                        layout="vertical"
                        margin={{ left: 12, right: 20 }}
                      >
                        <CartesianGrid
                          stroke="#303d5a"
                          strokeDasharray="3 4"
                          horizontal={false}
                        />
                        <XAxis
                          type="number"
                          domain={[0, 100]}
                          stroke="#9eafcd"
                        />
                        <YAxis
                          type="category"
                          dataKey="name"
                          width={120}
                          stroke="#d5def2"
                          fontSize={11}
                        />
                        <Tooltip
                          contentStyle={{
                            background: "#16213b",
                            border: "1px solid #3b4e75",
                          }}
                        />
                        <Bar
                          dataKey="score"
                          fill={PINK}
                          radius={[0, 6, 6, 0]}
                        />
                      </BarChart>
                    </ResponsiveContainer>
                  </div>

                  <div className="leaderboard">
                    {filteredPlayers.map((p, i) => (
                      <button
                        key={`${p.player_id}-${i}`}
                        className={
                          "player-btn " +
                          (selectedPlayer?.player_id === p.player_id
                            ? "active"
                            : "")
                        }
                        onClick={() => setSelectedId(p.player_id)}
                      >
                        <span className="rank">#{i + 1}</span>

                        <span>
                          <strong>{p.display_name}</strong>
                          <div className="small">
                            {p.teams || "Domestic"} · {ageLabel(p)}
                          </div>
                        </span>

                        <span className="score">
                          {number(p.scouting_score).toFixed(2)}
                        </span>
                      </button>
                    ))}
                  </div>
                </>
              ) : (
                <div className="notice">
                  No players meet these filters.
                  The DOB registry may not yet contain sourced ages,
                  or no candidates have verified eligibility.
                </div>
              )}
            </div>

            <div className="panel">
              <h2 className="section-title">
                Player Scouting Radar
              </h2>
              <p className="muted">
                Same-role percentile comparison against the
                domestic review pool.
              </p>

              {selectedPlayer && (
                <>
                  <h2 style={{ marginTop: 20 }}>
                    {selectedPlayer.display_name}
                  </h2>
                  <p className="muted">
                    {selectedPlayer.teams || "Domestic"} ·{" "}
                    {ageLabel(selectedPlayer)}
                  </p>

                  <div className="chart">
                    <ResponsiveContainer width="100%" height="100%">
                      <RadarChart data={radarData} outerRadius="66%">
                        <PolarGrid stroke="#344563" />
                        <PolarAngleAxis
                          dataKey="metric"
                          stroke="#d0daef"
                          fontSize={11}
                        />
                        <PolarRadiusAxis
                          domain={[0, 100]}
                          tick={false}
                          axisLine={false}
                        />
                        <Radar
                          name="Player"
                          dataKey="value"
                          stroke={PINK}
                          fill={PINK}
                          fillOpacity={0.3}
                        />
                        <Radar
                          name="Median reference"
                          dataKey="average"
                          stroke={BLUE}
                          fill={BLUE}
                          fillOpacity={0.05}
                        />
                        <Tooltip />
                      </RadarChart>
                    </ResponsiveContainer>
                  </div>

                  <div className="details">
                    <div className="detail">
                      <small>SMAT scouting score</small>
                      <strong>
                        {number(selectedPlayer.scouting_score).toFixed(2)}
                      </strong>
                    </div>

                    <div className="detail">
                      <small>Matches recorded</small>
                      <strong>{selectedPlayer.matches ?? "—"}</strong>
                    </div>

                    <div className="detail">
                      <small>Age</small>
                      <strong>{ageLabel(selectedPlayer)}</strong>
                    </div>

                    {role === "BATTER" ? (
                      <>
                        <div className="detail">
                          <small>Runs</small>
                          <strong>{selectedPlayer.runs ?? "—"}</strong>
                        </div>
                        <div className="detail">
                          <small>Strike rate</small>
                          <strong>
                            {selectedPlayer.strike_rate?.toFixed(2) ?? "—"}
                          </strong>
                        </div>
                        <div className="detail">
                          <small>Balls faced</small>
                          <strong>
                            {selectedPlayer.balls_faced ?? "—"}
                          </strong>
                        </div>
                      </>
                    ) : (
                      <>
                        <div className="detail">
                          <small>Wickets</small>
                          <strong>
                            {selectedPlayer.wickets ?? "—"}
                          </strong>
                        </div>
                        <div className="detail">
                          <small>Economy</small>
                          <strong>
                            {selectedPlayer.economy?.toFixed(2) ?? "—"}
                          </strong>
                        </div>
                        <div className="detail">
                          <small>Legal balls</small>
                          <strong>
                            {selectedPlayer.legal_balls_bowled ?? "—"}
                          </strong>
                        </div>
                      </>
                    )}
                  </div>

                  <div className="notice">
                    Eligibility:{" "}
                    {selectedPlayer.verified_eligible
                      ? "Verified in local registry"
                      : "Not verified"}.
                    {" "}Domestic performance is not the same as
                    pressure-specific performance.
                  </div>
                </>
              )}
            </div>
          </section>
        </>
      )}
    </main>
  );
}
