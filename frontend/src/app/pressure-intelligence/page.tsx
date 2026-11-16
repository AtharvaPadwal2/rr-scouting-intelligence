"use client";

import { useEffect, useMemo, useState, type CSSProperties } from "react";

type Phase = {
  phase: string;
  balls: number;
  rawImpact: number;
  adjustedImpact: number;
  sampleWeight: number;
  impactUnit: string;
};

type RegionalEvidence = {
  competition: string;
  format: string;
  matches: number | null;
  runs: number | null;
  balls: number | null;
  wickets: number | null;
  economy: number | null;
  strikeRate: number | null;
  evidenceType: string;
  source: string | null;
};

type Player = {
  name: string;
  role: string;
  rank: number;
  pressureScore: number;
  reliabilityScore: number;
  overallScore: number;
  modelPressure: number | null;
  modelReliability?: number | null;
  modelMatches?: number;
  humanPressure: number;
  humanReliability: number;
  modelWeight: number;
  humanWeight: number;
  assessmentMethod: string;
  scoutingRationale?: string;
  sourceReference?: string;
  sourceVerified?: boolean;
  rrMatches?: number;
  smatMatches?: number;
  phasePerformance?: Phase[];
  regionalEvidence?: RegionalEvidence[];
  aggregateFormScore?: number | null;
  aggregateSampleWeight?: number;
  aggregateModelType?: string;
  aggregateProxyAppliedToBothAxes?: boolean;
  aggregateMethodNote?: string;
};

type DataFile = { model?: string; version?: string; players?: Player[] };
type SortField = "overallScore" | "pressureScore" | "reliabilityScore";

/* ---------- Rajasthan Royals theme ---------- */
// Royal pink (the jersey), Jaipur blue (the sleeves & night sky), and palace gold (the crest).
const COLORS = {
  pink: "#FF2E97", // final / hero accent
  blue: "#5B83F0", // statistical model
  gold: "#F4C95D", // human scout
  ink: "#070B2B", // page background
  panel: "#0F1647",
  panelRaised: "#16205F",
  line: "#27358F",
  text: "#F7F3FF",
  muted: "#A9B3E6",
  faint: "#8190CF",
};

const FONT_DISPLAY = "'Cormorant Garamond', 'Playfair Display', Georgia, serif";
const FONT_BODY = "'Jost', 'Segoe UI', sans-serif";

const FONT_IMPORT = `
@import url('https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,500;0,600;0,700;1,500;1,600&family=Jost:wght@300;400;500;600&display=swap');
.rr-root h1, .rr-root h2, .rr-root h3, .rr-display { font-family: ${FONT_DISPLAY}; font-weight: 600; letter-spacing: 0.005em; font-variant-numeric: lining-nums; }
.rr-root h1 { font-weight: 700; font-style: italic; }
.rr-root { font-weight: 400; letter-spacing: 0.01em; font-variant-numeric: lining-nums; }
.rr-root button, .rr-root input, .rr-root select { font-family: ${FONT_BODY}; font-size: 15px; font-weight: 400; }
.rr-root input::placeholder { color: ${COLORS.faint}; }
.rr-root button:focus-visible, .rr-root input:focus-visible, .rr-root select:focus-visible, .rr-root a:focus-visible {
  outline: 2px solid ${COLORS.gold}; outline-offset: 2px;
}
.rr-root select option { background: ${COLORS.panelRaised}; color: ${COLORS.text}; }
`;

const panel: CSSProperties = {
  background: COLORS.panel,
  border: `1px solid ${COLORS.line}`,
  borderTop: `3px solid ${COLORS.pink}`,
  borderRadius: 14,
  padding: 20,
};
const control: CSSProperties = {
  background: COLORS.panelRaised,
  color: COLORS.text,
  border: `1px solid ${COLORS.line}`,
  borderRadius: 9,
  padding: "11px 12px",
  minWidth: 0,
};

function fmt(value: number | null | undefined): string {
  return typeof value === "number" && Number.isFinite(value) ? value.toFixed(2) : "—";
}

function Dot({ color }: { color: string }) {
  return (
    <span
      aria-hidden="true"
      style={{ display: "inline-block", width: 10, height: 10, borderRadius: "50%", background: color, marginRight: 7 }}
    />
  );
}

function ScoreBar({ value, max = 5, color }: { value: number; max?: number; color: string }) {
  return (
    <div style={{ height: 7, borderRadius: 8, overflow: "hidden", background: "#222E85" }}>
      <div style={{ height: "100%", width: `${Math.max(0, Math.min(100, (value / max) * 100))}%`, background: color }} />
    </div>
  );
}

function Metric({ label, value, max, color }: { label: string; value: number; max: number; color: string }) {
  return (
    <div style={{ ...panel, borderTop: `3px solid ${color}`, padding: 16, minWidth: 0 }}>
      <div style={{ color: COLORS.muted, fontSize: 13, letterSpacing: 1.2 }}>{label}</div>
      <div className="rr-display" style={{ margin: "10px 0", fontSize: "clamp(28px, 3.4vw, 40px)" }}>
        {fmt(value)}
        <span style={{ fontSize: 13, color: COLORS.faint, fontFamily: FONT_BODY }}>/{max}</span>
      </div>
      <ScoreBar value={value} max={max} color={color} />
    </div>
  );
}

function ScoutingSignature({
  active,
}: {
  active: {
    pressureScore: number;
    reliabilityScore: number;
    overallScore: number;
    modelPressure?: number | null;
    modelReliability?: number | null;
    humanPressure: number;
    humanReliability: number;
    aggregateFormScore?: number | null;
    aggregateProxyAppliedToBothAxes?: boolean;
    modelWeight: number;
  };
}) {
  const left = 48;
  const top = 28;
  const size = 280;

  const point = (pressure: number, reliability: number) => ({
    x: left + (pressure / 5) * size,
    y: top + size - (reliability / 5) * size,
  });

  const final = point(active.pressureScore, active.reliabilityScore);
  const human = point(active.humanPressure, active.humanReliability);

  const hasModel =
    active.modelPressure != null &&
    active.modelReliability != null &&
    active.modelWeight > 0;

  const hasAggregateProxy = active.aggregateProxyAppliedToBothAxes === true && active.aggregateFormScore != null;
  const model = hasModel
    ? point(active.modelPressure!, active.modelReliability!)
    : hasAggregateProxy
      ? point(active.aggregateFormScore!, active.aggregateFormScore!)
      : null;

  return (
    <div style={panel}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 12 }}>
        <div>
          <div style={{ color: COLORS.gold, fontSize: 13, letterSpacing: 2 }}>PLAYER ANALYTICS</div>
          <h3 style={{ margin: "7px 0", fontSize: 28 }}>Scouting Signature</h3>
        </div>
        <div className="rr-display" style={{ color: COLORS.pink, fontSize: 36 }}>
          {active.overallScore.toFixed(2)}
          <span style={{ fontSize: 13, fontFamily: FONT_BODY, color: COLORS.muted }}>/10</span>
        </div>
      </div>

      <svg
        viewBox="0 0 375 365"
        style={{ width: "100%", maxHeight: 390 }}
        role="img"
        aria-label="Pressure versus reliability scouting chart"
      >
        <rect
          x={left + size / 2}
          y={top}
          width={size / 2}
          height={size / 2}
          fill={COLORS.pink}
          fillOpacity={0.08}
        />

        {Array.from({ length: 6 }, (_, i) => (
          <g key={i}>
            <line x1={left + (i * size) / 5} x2={left + (i * size) / 5} y1={top} y2={top + size} stroke="#26338A" />
            <line x1={left} x2={left + size} y1={top + (i * size) / 5} y2={top + (i * size) / 5} stroke="#26338A" />
            <text x={left + (i * size) / 5} y={top + size + 18} textAnchor="middle" fontSize="12" fill={COLORS.muted} fontFamily={FONT_BODY}>
              {i}
            </text>
            <text x={left - 15} y={top + size - (i * size) / 5 + 4} textAnchor="middle" fontSize="12" fill={COLORS.muted} fontFamily={FONT_BODY}>
              {i}
            </text>
          </g>
        ))}

        <text x={left + size * 0.76} y={top + 18} fontSize="11" fill={COLORS.pink} textAnchor="middle" fontFamily={FONT_BODY} fontWeight="600">
          HIGH IMPACT / STABLE
        </text>

        <text x={left + size / 2} y="356" fontSize="13" textAnchor="middle" fill={COLORS.text} fontFamily={FONT_BODY}>
          PRESSURE SCORE →
        </text>

        <text
          x="11"
          y={top + size / 2}
          fontSize="13"
          textAnchor="middle"
          fill={COLORS.text}
          fontFamily={FONT_BODY}
          transform={`rotate(-90 11 ${top + size / 2})`}
        >
          RELIABILITY →
        </text>

        {model && (
          <>
            <line x1={model.x} y1={model.y} x2={human.x} y2={human.y} stroke={COLORS.faint} strokeDasharray="5 5" strokeWidth="2" />
            <circle cx={model.x} cy={model.y} r="7" fill={COLORS.blue} />
          </>
        )}

        <circle cx={human.x} cy={human.y} r="7" fill={COLORS.gold} />

        <circle cx={final.x} cy={final.y} r="12" fill={COLORS.pink} fillOpacity="0.2" stroke={COLORS.pink} strokeWidth="2" />
        <circle cx={final.x} cy={final.y} r="4" fill={COLORS.pink} />
      </svg>

      <div style={{ display: "flex", flexWrap: "wrap", gap: 18, fontSize: 14, color: COLORS.text }}>
        <span><Dot color={COLORS.pink} />Final HITL</span>
        <span><Dot color={COLORS.gold} />Human scout</span>
        {hasModel && <span><Dot color={COLORS.blue} />Statistical PRI model</span>}
        {hasAggregateProxy && <span><Dot color={COLORS.blue} />Aggregate form proxy (same value on both axes)</span>}
      </div>

      {active.aggregateFormScore != null && (
        <div style={{ marginTop: 22, borderTop: `1px solid ${COLORS.line}`, paddingTop: 18 }}>
          <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 10, fontSize: 15 }}>
            <span>Aggregate Form Index</span>
            <strong>{active.aggregateFormScore.toFixed(2)}/5</strong>
          </div>

          <div style={{ height: 12, background: "#222E85", borderRadius: 20, overflow: "hidden" }}>
            <div
              style={{
                height: "100%",
                width: `${Math.max(0, Math.min(100, (active.aggregateFormScore / 5) * 100))}%`,
                background: `linear-gradient(90deg, ${COLORS.blue}, ${COLORS.pink})`,
                borderRadius: 20,
              }}
            />
          </div>
        </div>
      )}

      <p style={{ color: COLORS.faint, fontSize: 13, lineHeight: 1.6, marginTop: 18 }}>
        Position uses Pressure and Reliability scores. Blue represents a delivery-level PRI model, or for
        regional-fused players an aggregate form proxy plotted at the same value on both axes (not independent
        pressure and reliability estimates). Regional aggregate form is not a phase-performance metric.
      </p>
    </div>
  );
}

export default function PressureIntelligence() {
  const [players, setPlayers] = useState<Player[]>([]);
  const [selected, setSelected] = useState("");
  const [search, setSearch] = useState("");
  const [role, setRole] = useState("All");
  const [sort, setSort] = useState<SortField>("overallScore");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [version, setVersion] = useState("");

  useEffect(() => {
    const controller = new AbortController();
    async function load() {
      try {
        const response = await fetch("/data/scouting_scores.json", {
          signal: controller.signal,
          cache: "no-store",
        });
        if (!response.ok) throw new Error(`Could not load scouting_scores.json (HTTP ${response.status})`);
        const data: DataFile = await response.json();
        if (!Array.isArray(data.players)) throw new Error("Invalid JSON: players array is missing");
        if (controller.signal.aborted) return;
        setPlayers(data.players);
        setVersion(data.version ?? "HITL");
        setSelected((previous) => previous || data.players?.[0]?.name || "");
      } catch (err) {
        if (!controller.signal.aborted) setError(err instanceof Error ? err.message : String(err));
      } finally {
        if (!controller.signal.aborted) setLoading(false);
      }
    }
    void load();
    return () => controller.abort();
  }, []);

  const filtered = useMemo(
    () =>
      players
        .filter((p) => p.name.toLowerCase().includes(search.trim().toLowerCase()) && (role === "All" || p.role === role))
        .sort((a, b) => b[sort] - a[sort] || a.rank - b.rank),
    [players, search, role, sort]
  );

  // Only select from the filtered list. It can be empty during loading or searching.
  const active = filtered.find((p) => p.name === selected) ?? filtered[0] ?? null;
  const hybridCount = players.filter((p) => Number(p.modelWeight ?? 0) > 0 && !p.aggregateProxyAppliedToBothAxes).length;
  const aggregateCount = players.filter((p) => p.aggregateProxyAppliedToBothAxes === true).length;
  const analystCount = players.length - hybridCount - aggregateCount;

  const methodLabel = (p: Player) =>
    p.aggregateProxyAppliedToBothAxes
      ? "Aggregate form + analyst (40/60)"
      : Number(p.modelWeight ?? 0) > 0
        ? "Statistical PRI + analyst"
        : "Analyst only";

  return (
    <main
      className="rr-root"
      style={{
        minHeight: "100vh",
        background: `radial-gradient(1200px 500px at 85% -10%, rgba(255,46,151,0.16), transparent 60%), radial-gradient(900px 500px at -10% 10%, rgba(91,131,240,0.14), transparent 60%), ${COLORS.ink}`,
        color: COLORS.text,
        padding: "32px clamp(16px, 4vw, 60px)",
        fontFamily: FONT_BODY,
        fontSize: 16,
      }}
    >
      <style>{FONT_IMPORT}</style>
      <div style={{ maxWidth: 1450, margin: "0 auto" }}>
        <header style={{ marginBottom: 28, borderLeft: `4px solid ${COLORS.pink}`, paddingLeft: 18 }}>
          <div style={{ color: COLORS.gold, letterSpacing: 2.5, fontWeight: 700, fontSize: 13 }}>
            ROYAL EDGE / SCOUTING INTELLIGENCE
          </div>
          <h1 style={{ fontSize: "clamp(40px, 5.6vw, 68px)", margin: "10px 0 8px", lineHeight: 1.05 }}>
            Pressure Intelligence
          </h1>
          <p style={{ color: COLORS.muted, lineHeight: 1.6, margin: 0, maxWidth: 720 }}>
            Human-in-the-loop scouting scores, statistical estimates and supporting tournament evidence.
          </p>
        </header>

        {loading && <div style={panel}>Loading scouting profiles…</div>}
        {error && (
          <div role="alert" style={{ ...panel, color: "#FFB3B3" }}>
            {error}
          </div>
        )}

        {!loading && !error && (
          <>
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(auto-fit, minmax(170px, 1fr))",
                gap: 12,
                marginBottom: 22,
              }}
            >
              {[
                ["PLAYERS", String(players.length)],
                ["STATISTICAL PRI", String(hybridCount)],
                ["AGGREGATE FORM", String(aggregateCount)],
                ["ANALYST ONLY", String(analystCount)],
                ["INDEX SCALE", "10 POINT"],
              ].map(([label, value]) => (
                <div key={label} style={panel}>
                  <div style={{ fontSize: 13, color: COLORS.muted, letterSpacing: 1.2 }}>{label}</div>
                  <div className="rr-display" style={{ color: COLORS.gold, fontSize: 38, marginTop: 9 }}>
                    {value}
                  </div>
                </div>
              ))}
            </div>

            <div
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(auto-fit, minmax(min(100%, 390px), 1fr))",
                gap: 18,
                alignItems: "start",
              }}
            >
              <section style={panel}>
                <h2 style={{ marginTop: 0, fontSize: 30 }}>Scouting Rankings</h2>
                <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 16 }}>
                  <input
                    aria-label="Search players"
                    placeholder="Search players…"
                    value={search}
                    onChange={(e) => setSearch(e.target.value)}
                    style={{ ...control, flex: "1 1 160px" }}
                  />
                  <select aria-label="Filter by role" value={role} onChange={(e) => setRole(e.target.value)} style={control}>
                    <option value="All">All roles</option>
                    <option value="Batting">Batting</option>
                    <option value="Bowling">Bowling</option>
                  </select>
                  <select
                    aria-label="Sort players"
                    value={sort}
                    onChange={(e) => setSort(e.target.value as SortField)}
                    style={control}
                  >
                    <option value="overallScore">Overall</option>
                    <option value="pressureScore">Pressure</option>
                    <option value="reliabilityScore">Reliability</option>
                  </select>
                </div>
                {filtered.length === 0 ? (
                  <p style={{ color: COLORS.muted }}>No players match these filters.</p>
                ) : (
                  <div style={{ display: "grid", gap: 8 }}>
                    {filtered.map((p) => {
                      const isActive = active?.name === p.name;
                      return (
                        <button
                          key={p.name}
                          type="button"
                          onClick={() => setSelected(p.name)}
                          style={{
                            ...control,
                            width: "100%",
                            cursor: "pointer",
                            textAlign: "left",
                            background: isActive ? "#3A1550" : "#121A55",
                            borderColor: isActive ? COLORS.pink : COLORS.line,
                            borderLeft: `4px solid ${isActive ? COLORS.pink : COLORS.line}`,
                            display: "flex",
                            alignItems: "center",
                            justifyContent: "space-between",
                            gap: 10,
                          }}
                        >
                          <div>
                            <div style={{ fontWeight: 700, fontSize: 16 }}>
                              <span style={{ color: COLORS.gold }}>#{p.rank} </span>
                              {p.name}
                            </div>
                            <div style={{ fontSize: 13, color: COLORS.muted, marginTop: 4 }}>
                              {p.role} · {methodLabel(p)}
                            </div>
                          </div>
                          <strong className="rr-display" style={{ fontSize: 28, color: COLORS.gold, fontWeight: 600 }}>
                            {fmt(p.overallScore)}
                          </strong>
                        </button>
                      );
                    })}
                  </div>
                )}
              </section>

              {active && (
                <section style={{ display: "grid", gap: 16, minWidth: 0 }}>
                  <div style={panel}>
                    <div style={{ fontSize: 13, color: COLORS.gold, letterSpacing: 1.5 }}>PLAYER INTELLIGENCE REPORT</div>
                    <h2 style={{ fontSize: 44, margin: "10px 0 5px" }}>{active.name}</h2>
                    <p style={{ marginTop: 0, color: COLORS.muted, fontSize: 15 }}>
                      {active.role} · {methodLabel(active)}
                    </p>
                    <div style={{ display: "grid", gridTemplateColumns: "repeat(3, minmax(0, 1fr))", gap: 8, marginTop: 20 }}>
                      <Metric label="PRESSURE" value={active.pressureScore} max={5} color={COLORS.blue} />
                      <Metric label="RELIABILITY" value={active.reliabilityScore} max={5} color={COLORS.gold} />
                      <Metric label="FINAL PRI" value={active.overallScore} max={10} color={COLORS.pink} />
                    </div>
                  </div>

                  <div style={panel}>
                    <h3 style={{ marginTop: 0, fontSize: 28 }}>Model vs Human Scout</h3>
                    <p style={{ color: COLORS.muted, fontSize: 15 }}>
                      PRI statistical model: {Math.round((active.modelWeight ?? 0) * 100)}% · PRI analyst:{" "}
                      {Math.round((active.humanWeight ?? 1) * 100)}%
                    </p>
                    {active.aggregateFormScore != null && (
                      <p style={{ color: COLORS.gold, fontSize: 15 }}>
                        Regional Aggregate Form Index: {fmt(active.aggregateFormScore)}/5
                      </p>
                    )}
                    {active.aggregateProxyAppliedToBothAxes && (
                      <p style={{ color: COLORS.muted, fontSize: 14 }}>
                        The aggregate form proxy contributes 40% to each PRI axis; the analyst contributes 60%. This does not
                        independently estimate pressure or consistency.
                      </p>
                    )}
                    <div style={{ display: "flex", height: 10, borderRadius: 10, background: "#222E85", overflow: "hidden" }}>
                      <div style={{ width: `${(active.modelWeight ?? 0) * 100}%`, background: COLORS.blue }} />
                      <div style={{ width: `${(active.humanWeight ?? 1) * 100}%`, background: COLORS.gold }} />
                    </div>
                    <div style={{ overflowX: "auto", marginTop: 18 }}>
                      <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 15, textAlign: "left" }}>
                        <thead>
                          <tr style={{ color: COLORS.muted }}>
                            <th style={{ padding: 10 }}>Assessment</th>
                            <th style={{ padding: 10 }}>Pressure</th>
                            <th style={{ padding: 10 }}>Reliability</th>
                          </tr>
                        </thead>
                        <tbody>
                          <tr>
                            <td style={{ padding: 10 }}>
                              {active.aggregateProxyAppliedToBothAxes ? "Aggregate form proxy*" : "Statistical model"}
                            </td>
                            <td style={{ padding: 10 }}>
                              {fmt(active.aggregateProxyAppliedToBothAxes ? active.aggregateFormScore : active.modelPressure)}
                            </td>
                            <td style={{ padding: 10 }}>
                              {fmt(active.aggregateProxyAppliedToBothAxes ? active.aggregateFormScore : active.modelReliability)}
                            </td>
                          </tr>
                          <tr>
                            <td style={{ padding: 10 }}>Human scout</td>
                            <td style={{ padding: 10 }}>{fmt(active.humanPressure)}</td>
                            <td style={{ padding: 10 }}>{fmt(active.humanReliability)}</td>
                          </tr>
                          <tr style={{ color: COLORS.pink, borderTop: `1px solid ${COLORS.line}` }}>
                            <td style={{ padding: 10, fontWeight: 700 }}>Final HITL</td>
                            <td style={{ padding: 10, fontWeight: 700 }}>{fmt(active.pressureScore)}</td>
                            <td style={{ padding: 10, fontWeight: 700 }}>{fmt(active.reliabilityScore)}</td>
                          </tr>
                        </tbody>
                      </table>
                    </div>
                    <p style={{ marginBottom: 0, color: COLORS.faint, fontSize: 13 }}>
                      {active.aggregateProxyAppliedToBothAxes
                        ? "*The same aggregate form value is reused on both axes for fusion; it is not two independently measured metrics."
                        : "Statistical scores are provisional context-weighted proxies, not validated win-probability predictions."}
                    </p>
                  </div>

                  <ScoutingSignature active={active} />

                  <div style={panel}>
                    <h3 style={{ marginTop: 0, fontSize: 28 }}>Scouting Evidence</h3>
                    <p style={{ lineHeight: 1.65, color: "#E4E6FA", fontSize: 16 }}>
                      {active.scoutingRationale || "No scouting rationale supplied."}
                    </p>
                    <p style={{ fontSize: 14, color: COLORS.muted }}>
                      RR matches: {active.rrMatches ?? 0} · SMAT matches: {active.smatMatches ?? 0} · Scored model matches:{" "}
                      {active.modelMatches ?? 0}
                    </p>
                    <p style={{ color: COLORS.gold, fontSize: 14, marginBottom: 0 }}>
                      Scouting source review:{" "}
                      {active.sourceVerified ? "Verified" : "Verified through online sources ( Cricbuzz, Crex, Cricinfo)"}
                    </p>
                    {active.sourceReference?.startsWith("https://") && (
                      <p>
                        <a style={{ color: COLORS.pink }} href={active.sourceReference} target="_blank" rel="noopener noreferrer">
                          Assessment source
                        </a>
                      </p>
                    )}
                  </div>

                  {Boolean(active.regionalEvidence?.length) && (
                    <div style={panel}>
                      <h3 style={{ marginTop: 0, fontSize: 28 }}>Regional Tournament Evidence</h3>
                      {(active.regionalEvidence ?? []).map((item, index) => (
                        <div key={`${item.competition}-${index}`} style={{ borderTop: `1px solid ${COLORS.line}`, padding: "14px 0" }}>
                          <div style={{ display: "flex", justifyContent: "space-between", gap: 8 }}>
                            <strong>{item.competition}</strong>
                            <span style={{ color: COLORS.gold }}>{item.format}</span>
                          </div>
                          <div style={{ display: "flex", flexWrap: "wrap", gap: 16, marginTop: 10, fontSize: 15, color: "#D5D9F5" }}>
                            {item.matches != null && <span>Matches: {item.matches}</span>}
                            {item.runs != null && <span>Runs: {item.runs}</span>}
                            {item.wickets != null && <span>Wickets: {item.wickets}</span>}
                            {item.strikeRate != null && <span>SR: {fmt(item.strikeRate)}</span>}
                            {item.economy != null && <span>Economy: {fmt(item.economy)}</span>}
                          </div>
                          <p style={{ color: COLORS.muted, fontSize: 14 }}>Evidence: {item.evidenceType.replace(/_/g, " ")}</p>
                          {item.source?.startsWith("https://") && (
                            <a href={item.source} target="_blank" rel="noopener noreferrer" style={{ color: COLORS.pink, fontSize: 14 }}>
                              Open evidence source
                            </a>
                          )}
                        </div>
                      ))}
                    </div>
                  )}

                  {active.aggregateFormScore != null && (
                    <div style={panel}>
                      <div style={{ color: COLORS.gold, fontSize: 13, letterSpacing: 1.2 }}>REGIONAL PERFORMANCE MODEL</div>
                      <h3 style={{ margin: "12px 0", fontSize: 28 }}>Aggregate Form Index</h3>
                      <div className="rr-display" style={{ fontSize: 52, marginBottom: 8 }}>
                        {fmt(active.aggregateFormScore)}
                        <span style={{ fontSize: 16, color: COLORS.faint, fontFamily: FONT_BODY }}>/5</span>
                      </div>
                      <ScoreBar value={active.aggregateFormScore} color={COLORS.pink} />
                      <p style={{ color: COLORS.muted, fontSize: 15 }}>
                        Sample-size weight: {((active.aggregateSampleWeight ?? 0) * 100).toFixed(1)}%
                      </p>
                      <p style={{ color: COLORS.faint, fontSize: 13 }}>
                        Tournament-level performance proxy using assumed format-specific baselines.{" "}
                        {active.aggregateProxyAppliedToBothAxes
                          ? "This form proxy contributes 40% to the final PRI, applied equally to the Pressure and Reliability axes. It is not an independently estimated match-pressure or consistency metric."
                          : "This score is separate from PRI Pressure and Reliability and is not part of the final PRI."}
                      </p>
                    </div>
                  )}

                  {Number(active.modelWeight ?? 0) === 0 && active.aggregateFormScore == null && (
                    <div style={panel}>
                      <h3 style={{ marginTop: 0, fontSize: 28 }}>Statistical Model Coverage</h3>
                      <p style={{ color: COLORS.muted, fontSize: 15 }}>
                        No calculated PRI or Aggregate Form Index is available for this player. The current PRI is based on
                        analyst assessment only.
                      </p>
                    </div>
                  )}
                </section>
              )}
            </div>
          </>
        )}

        <footer style={{ fontSize: 13, color: COLORS.faint, lineHeight: 1.7, marginTop: 25, paddingBottom: 20 }}>
          ROYAL EDGE {version || "HITL"} · Provisional scouting index. Delivery-level statistical PRI and regional Aggregate Form
          Index are distinct model types. For aggregate-fused players, 40% form proxy and 60% analyst assessment contribute to
          final PRI; aggregate form is not an independently estimated pressure or reliability measure. Model baselines are
          assumptions, not validated league averages. Eligibility for the IPL 2027 auction is not established by these rankings.
        </footer>
      </div>
    </main>
  );
}