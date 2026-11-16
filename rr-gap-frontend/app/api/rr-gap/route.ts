import { NextResponse } from "next/server";
import { parse } from "csv-parse/sync";
import { readFile } from "node:fs/promises";
import path from "node:path";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

const DATA_DIR = process.env.RR_DATA_DIR || path.resolve(process.cwd(), "..", "data", "processed");
const SOURCES = {
  gaps: "rr_squad_gap_report.csv",
  league: "ipl_2026_team_phase_comparison.csv",
  matches: "rr_2026_match_phase_analysis.csv",
  bowling: "rr_2026_bowler_phase_analysis.csv",
  middle: "rr_2026_middle_win_loss.csv",
  finishers: "rr_2026_death_batters.csv",
} as const;

async function readCsv(filename: string) {
  const contents = await readFile(path.join(DATA_DIR, filename), "utf8");
  return parse(contents, { columns: true, skip_empty_lines: true, bom: true, trim: true }) as Record<string, string>[];
}

export async function GET() {
  const loaded = await Promise.allSettled(Object.entries(SOURCES).map(async ([key, file]) => [key, await readCsv(file)] as const));
  const data: Record<string, Record<string, string>[]> = {};
  const missing: string[] = [];
  loaded.forEach((entry, index) => {
    const [key, file] = Object.entries(SOURCES)[index];
    if (entry.status === "fulfilled") data[entry.value[0]] = entry.value[1];
    else {
      data[key] = [];
      missing.push(file);
    }
  });
  if (!data.gaps.length || !data.league.length || !data.matches.length) {
    return NextResponse.json({ error: "Core analysis CSV files could not be read.", dataDir: DATA_DIR, missing }, { status: 500 });
  }
  return NextResponse.json({ data, missing, generatedAt: new Date().toISOString() }, {
    headers: { "Cache-Control": "no-store" },
  });
}
