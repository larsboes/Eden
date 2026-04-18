/**
 * Append-only telemetry log (file-based, no SQLite native dep).
 * Log path: .data/telemetry.jsonl (created in project root or cwd).
 */

import { appendFileSync, existsSync, mkdirSync, readFileSync } from "node:fs";
import { join } from "node:path";

const DATA_DIR = join(process.cwd(), ".data");
const LOG_PATH = join(DATA_DIR, "telemetry.jsonl");
const MAX_LINES_READ = 200;

export interface TelemetryEntry {
  ts: string;
  topic: string;
  payload: Record<string, unknown>;
}

function ensureDir(): void {
  if (!existsSync(DATA_DIR)) {
    mkdirSync(DATA_DIR, { recursive: true });
  }
}

export function appendTelemetry(topic: string, payload: Record<string, unknown>): void {
  ensureDir();
  const entry: TelemetryEntry = {
    ts: new Date().toISOString(),
    topic,
    payload,
  };
  appendFileSync(LOG_PATH, JSON.stringify(entry) + "\n");
}

export function getRecentTelemetry(limit: number = 50): TelemetryEntry[] {
  ensureDir();
  if (!existsSync(LOG_PATH)) return [];
  const raw = readFileSync(LOG_PATH, "utf-8");
  const lines = raw.trim().split("\n").filter(Boolean);
  const slice = lines.slice(-Math.min(limit, MAX_LINES_READ));
  return slice.map((line) => JSON.parse(line) as TelemetryEntry).reverse();
}
