
"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";

const sections = [
  {
    heading: "MISSION CONTROL",
    links: [
      {
        number: "01",
        label: "Command Center",
        href: "/dashboard",
        symbol: "◈",
      },
      {
        number: "02",
        label: "Pressure Intelligence",
        href: "/dashboard/pressure-intelligence",
        symbol: "◉",
      },
    ],
  },
  {
    heading: "PLAYER DISCOVERY",
    links: [
      {
        number: "03",
        label: "Auction Scouting",
        href: "/dashboard/auction-scouting",
        symbol: "◎",
      },
      {
        number: "04",
        label: "Domestic Talent",
        href: "/dashboard/uncapped-indians",
        symbol: "◇",
      },
    ],
  },
  {
    heading: "DECISION ENGINE",
    links: [
      {
        number: "05",
        label: "Scouting War Room",
        href: "/dashboard/war-room",
        symbol: "✳",
      },
      {
        number: "06",
        label: "Final Recommendations",
        href: "/dashboard/recommendations",
        symbol: "▣",
        upcoming: true,
      },
    ],
  },
];

export default function ScoutingSidebar() {
  const pathname = usePathname();
  const [open, setOpen] = useState(false);

  return (
    <>
      <button
        type="button"
        className="rr-mobile-trigger"
        onClick={() => setOpen(!open)}
        aria-label={open ? "Close navigation" : "Open navigation"}
        aria-expanded={open}
      >
        {open ? "✕" : "☰"}
        <span>RR INTELLIGENCE</span>
      </button>

      {open && (
        <button
          className="rr-sidebar-backdrop"
          aria-label="Close menu"
          onClick={() => setOpen(false)}
        />
      )}

      <aside
        className={`rr-sidebar ${open ? "rr-sidebar-open" : ""}`}
      >
        <Link
          className="rr-brand"
          href="/dashboard"
          onClick={() => setOpen(false)}
        >
          <div className="rr-brand-symbol">RR</div>

          <div>
            <strong>RR INTELLIGENCE</strong>
            <small>SCOUTING COMMAND CENTER</small>
          </div>
        </Link>

        <div className="rr-project-label">
          <span className="rr-live-dot" />
          SUPERR SELECTOR / SEASON 2
        </div>

        <div className="rr-sidebar-navigation">
          {sections.map((section) => (
            <div className="rr-nav-group" key={section.heading}>
              <p className="rr-nav-heading">{section.heading}</p>

              {section.links.map((item) => {
                const active = pathname === item.href;

                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    onClick={() => setOpen(false)}
                    className={
                      `rr-nav-link ${active ? "rr-nav-active" : ""}`
                    }
                    aria-current={active ? "page" : undefined}
                  >
                    <span className="rr-nav-symbol">
                      {item.symbol}
                    </span>

                    <span className="rr-nav-text">
                      {item.label}
                      {item.upcoming && (
                        <small>Coming next</small>
                      )}
                    </span>

                    <span className="rr-nav-number">
                      {item.number}
                    </span>
                  </Link>
                );
              })}
            </div>
          ))}
        </div>

        <div className="rr-sidebar-footer">
          <div className="rr-sidebar-footer-card">
            <span>THE MISSION</span>
            <strong>Find the next generation.</strong>
            <p>
              From evidence to scouting decisions.
            </p>
          </div>

          <div className="rr-footer-note">
            IPL 2027 <span>●</span> RAJASTHAN ROYALS
          </div>
        </div>
      </aside>
    </>
  );
}
