"use client";

type TrendKey =
  | "temperature_c"
  | "humidity_pct"
  | "pressure_hpa"
  | "ambient_light_pct"
  | "water_level_pct"
  | "soil_moisture_pct";

export interface TrendPoint {
  timestamp: string;
  temperature_c: number | null;
  humidity_pct: number | null;
  pressure_hpa: number | null;
  ambient_light_pct: number | null;
  water_level_pct: number | null;
  soil_moisture_pct: number | null;
}

interface SensorTrendsProps {
  history: TrendPoint[];
}

const CHART_WIDTH = 320;
const CHART_HEIGHT = 120;
const PADDING_X = 8;
const PADDING_Y = 10;

const seriesConfig: Array<{
  key: TrendKey;
  label: string;
  unit: string;
  color: string;
}> = [
  { key: "temperature_c", label: "Air temperature", unit: "C", color: "#22d3ee" },
  { key: "humidity_pct", label: "Air humidity", unit: "%", color: "#60a5fa" },
  { key: "pressure_hpa", label: "Pressure", unit: "hPa", color: "#a78bfa" },
  { key: "ambient_light_pct", label: "Ambient light", unit: "%", color: "#facc15" },
  { key: "water_level_pct", label: "Water level", unit: "%", color: "#34d399" },
  { key: "soil_moisture_pct", label: "Soil moisture", unit: "%", color: "#f97316" },
];

function buildPath(history: TrendPoint[], key: TrendKey): { line: string; area: string; lastValue: number | null } {
  const values = history.map((p) => p[key]);
  const finiteValues = values.filter((v): v is number => v !== null && Number.isFinite(v));
  if (finiteValues.length < 2) {
    return { line: "", area: "", lastValue: finiteValues[finiteValues.length - 1] ?? null };
  }

  const min = Math.min(...finiteValues);
  const max = Math.max(...finiteValues);
  const range = Math.max(max - min, 0.001);
  const innerW = CHART_WIDTH - 2 * PADDING_X;
  const innerH = CHART_HEIGHT - 2 * PADDING_Y;

  const points: Array<[number, number]> = [];
  values.forEach((v, idx) => {
    if (v === null || !Number.isFinite(v)) return;
    const x = PADDING_X + (idx / Math.max(values.length - 1, 1)) * innerW;
    const norm = (v - min) / range;
    const y = PADDING_Y + (1 - norm) * innerH;
    points.push([x, y]);
  });

  if (points.length < 2) {
    return { line: "", area: "", lastValue: points.length ? finiteValues[finiteValues.length - 1] : null };
  }

  const line = points.map(([x, y], i) => `${i === 0 ? "M" : "L"}${x.toFixed(2)},${y.toFixed(2)}`).join(" ");
  const firstX = points[0][0];
  const lastX = points[points.length - 1][0];
  const bottom = (CHART_HEIGHT - PADDING_Y).toFixed(2);
  const area = `${line} L${lastX.toFixed(2)},${bottom} L${firstX.toFixed(2)},${bottom} Z`;

  return { line, area, lastValue: points.length ? finiteValues[finiteValues.length - 1] : null };
}

export function SensorTrends({ history }: SensorTrendsProps) {
  return (
    <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
      {seriesConfig.map((series) => {
        const path = buildPath(history, series.key);
        const latestLabel =
          path.lastValue == null ? "n/a" : `${path.lastValue.toFixed(series.key === "pressure_hpa" ? 1 : 1)} ${series.unit}`;
        const gradientId = `grad-${series.key}`;
        return (
          <div key={series.key} className="rounded-xl border border-zinc-800 bg-zinc-900/60 p-3 shadow-sm">
            <div className="mb-2 flex items-center justify-between">
              <p className="text-xs font-medium uppercase tracking-wider text-zinc-400">{series.label}</p>
              <p className="text-xs text-zinc-500">{latestLabel}</p>
            </div>
            <svg viewBox={`0 0 ${CHART_WIDTH} ${CHART_HEIGHT}`} className="h-28 w-full">
              <defs>
                <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor={series.color} stopOpacity="0.45" />
                  <stop offset="100%" stopColor={series.color} stopOpacity="0.02" />
                </linearGradient>
              </defs>
              <rect x="0" y="0" width={CHART_WIDTH} height={CHART_HEIGHT} fill="#0b1020" opacity="0.45" rx="8" />
              <path d={path.area} fill={`url(#${gradientId})`} />
              <path
                d={path.line}
                fill="none"
                stroke={series.color}
                strokeWidth="2.2"
                strokeLinecap="round"
                className="transition-all duration-700 ease-out"
              />
            </svg>
          </div>
        );
      })}
    </div>
  );
}

