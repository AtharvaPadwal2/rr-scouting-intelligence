
"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

type Counts = {
  battingReviews: number | null;
  bowlingReviews: number | null;
};

const rrNeeds = [
  {
    code: "RR-G01",
    title: "Indian Powerplay Pacer",
    severity: "HIGH PRIORITY",
    description:
      "Investigate early-overs run control, wicket-taking potential and consistency.",
  },
  {
    code: "RR-G02",
    title: "Death-Overs Specialist",
    severity: "HIGH PRIORITY",
    description:
      "Focus on execution under late-innings pressure, variation and run prevention.",
  },
  {
    code: "RR-G03",
    title: "Finishing All-Rounder",
    severity: "HIGH PRIORITY",
    description:
      "Identify domestic batters capable of accelerating late, with additional bowling value.",
  },
  {
    code: "RR-G04",
    title: "Middle-Overs Wicket-Taker",
    severity: "SECONDARY PRIORITY",
    description:
      "Evaluate wicket-taking ability, control and reliability through overs 7–15.",
  },
];

const journey = [
  {
    number: "01",
    title: "Measure Pressure",
    description:
      "Study player impact across our provisional match-state pressure categories.",
    href: "/dashboard/pressure-intelligence",
  },
  {
    number: "02",
    title: "Screen Prospects",
    description:
      "Explore auction review pools and separate eligibility from performance.",
    href: "/dashboard/auction-scouting",
  },
  {
    number: "03",
    title: "Discover Talent",
    description:
      "Search historical SMAT records, compare roles and evaluate samples.",
    href: "/dashboard/uncapped-indians",
  },
  {
    number: "04",
    title: "Make Decisions",
    description:
      "Compare players, build a provisional shortlist and export evidence.",
    href: "/dashboard/war-room",
  },
];

export default function CommandCenter() {
  const [counts, setCounts] = useState<Counts>({
    battingReviews: null,
    bowlingReviews: null,
  });

  useEffect(() => {
    fetch("/data/uncapped-overview.json")
      .then((res) => {
        if (!res.ok) throw new Error("No data");
        return res.json();
      })
      .then((data) => {
        setCounts({
          battingReviews: Array.isArray(data.batters)
            ? data.batters.length
            : null,
          bowlingReviews: Array.isArray(data.bowlers)
            ? data.bowlers.length
            : null,
        });
      })
      .catch(() => {
        // Keep unavailable values as N/A.
      });
  }, []);

  const metrics = [
    {
      label: "Official delivery records",
      value: "200,999",
      caption: "Initial dataset audit",
    },
    {
      label: "SMAT unique players",
      value: "1,489",
      caption: "Historical data coverage",
    },
    {
      label: "Domestic batting reviews",
      value: counts.battingReviews?.toLocaleString() ?? "N/A",
      caption: "Provisional review records",
    },
    {
      label: "Domestic bowling reviews",
      value: counts.bowlingReviews?.toLocaleString() ?? "N/A",
      caption: "Provisional review records",
    },
  ];

  return (
    <div className="rr-command">
      <div className="rr-eyebrow">
        RAJASTHAN ROYALS / SUPERR SELECTOR S2
      </div>

      <h1 className="rr-heading">
        Scouting <span>Intelligence.</span>
      </h1>

      <p className="rr-description">
        An evidence-led scouting research workspace for
        identifying domestic cricket talent, investigating
        squad gaps, evaluating player performance and
        supporting Rajasthan Royals' IPL 2027 decisions.
      </p>

      <Link
        className="rr-action"
        href="/dashboard/pressure-intelligence"
      >
        Start Scouting Analysis <span>↗</span>
      </Link>

      <div className="rr-kpis">
        {metrics.map((item) => (
          <div className="rr-kpi" key={item.label}>
            <div className="rr-kpi-label">
              {item.label}
            </div>

            <strong className="rr-kpi-value">
              {item.value}
            </strong>

            <div className="rr-kpi-caption">
              {item.caption}
            </div>
          </div>
        ))}
      </div>

      <h2 className="rr-section-title">
        Where does RR need reinforcement?
      </h2>

      <div className="rr-gap-grid">
        {rrNeeds.map((need) => (
          <div className="rr-panel" key={need.code}>
            <span className="rr-gap-label">
              {need.code} / SQUAD NEED
            </span>

            <h3 className="rr-gap-title">
              {need.title}
            </h3>

            <p className="rr-gap-desc">
              {need.description}
            </p>

            <span className="rr-gap-tag">
              {need.severity}
            </span>
          </div>
        ))}
      </div>

      <h2 className="rr-section-title">
        From evidence to selection
      </h2>

      <div className="rr-journey">
        {journey.map((step) => (
          <Link href={step.href} key={step.number}>
            <span className="rr-journey-number">
              STEP {step.number}
            </span>

            <span className="rr-journey-title">
              {step.title}
            </span>

            <span className="rr-journey-desc">
              {step.description}
            </span>
          </Link>
        ))}
      </div>

      <div className="rr-panel" style={{ marginTop: 24 }}>
        <div className="rr-eyebrow">
          OUR METHODOLOGY
        </div>

        <h2 style={{ margin: "15px 0" }}>
          Performance first. Evidence always.
        </h2>

        <p className="rr-description">
          The pressure model uses structural match-state
          proxies, not reconstructed real-time win
          probabilities. The SMAT database contains available
          historical matches and may be incomplete. Player
          age, international-cap status and IPL contract
          availability require independent verification before
          a final auction recommendation.
        </p>
      </div>
    </div>
  );
}
