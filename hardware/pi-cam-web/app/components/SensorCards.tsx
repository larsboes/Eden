"use client";

interface Reading {
  temperature_c: number | null;
  temperature_source?: string | null;
  humidity_pct: number | null;
  humidity_source?: string | null;
  pressure_hpa: number | null;
  pressure_source?: string | null;
  ambient_light_pct: number | null;
  water_level_pct: number | null;
  light_lux: number | null;
  soil_moisture_pct: number | null;
  light_raw: number | null;
  light_voltage: number | null;
  water_raw: number | null;
  water_voltage: number | null;
  soil_raw: number | null;
  soil_voltage: number | null;
  ph: number | null;
  water_level_cm: number | null;
  timestamp: string;
}

interface SensorCardsProps {
  reading: Reading | null;
  loading: boolean;
}

const cards: Array<{
  key: keyof Reading;
  label: string;
  unit: string;
  ok: (v: number) => boolean;
  decimals?: number;
  detail?: (r: Reading) => string;
}> = [
  {
    key: "pressure_hpa",
    label: "Pressure",
    unit: " hPa",
    ok: (v) => v >= 950 && v <= 1050,
    decimals: 1,
    detail: (r) => (r.pressure_source ? `source: ${r.pressure_source}` : ""),
  },
  {
    key: "temperature_c",
    label: "Air temperature",
    unit: "°C",
    ok: (v) => v >= 18 && v <= 30,
    detail: (r) => (r.temperature_source ? `source: ${r.temperature_source}` : ""),
  },
  {
    key: "humidity_pct",
    label: "Air humidity",
    unit: "%",
    ok: (v) => v >= 35 && v <= 80,
    detail: (r) => (r.humidity_source ? `source: ${r.humidity_source}` : "unavailable"),
  },
  {
    key: "ambient_light_pct",
    label: "Ambient light",
    unit: "%",
    ok: (v) => v >= 20,
    detail: (r) =>
      r.light_raw != null && r.light_voltage != null ? `raw ${r.light_raw} · ${r.light_voltage.toFixed(3)}V` : "",
  },
  {
    key: "soil_moisture_pct",
    label: "Soil moisture",
    unit: "%",
    ok: (v) => v >= 30 && v <= 70,
    detail: (r) =>
      r.soil_raw != null && r.soil_voltage != null ? `raw ${r.soil_raw} · ${r.soil_voltage.toFixed(3)}V` : "",
  },
  {
    key: "water_level_pct",
    label: "Water level",
    unit: "%",
    ok: (v) => v >= 20,
    detail: (r) =>
      r.water_raw != null && r.water_voltage != null ? `raw ${r.water_raw} · ${r.water_voltage.toFixed(3)}V` : "",
  },
];

export function SensorCards({ reading, loading }: SensorCardsProps) {
  return (
    <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
      {cards.map(({ key, label, unit, ok, decimals, detail }) => {
        const value = reading ? (reading[key] as number | null) : null;
        const inRange = value !== null ? ok(value) : null;
        return (
          <div
            key={key}
            className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-4 shadow-sm"
          >
            <p className="text-xs font-medium uppercase tracking-wider text-zinc-500">
              {label}
            </p>
            {loading && value === null ? (
              <p className="mt-1 text-2xl text-zinc-500">—</p>
            ) : (
              <p className="mt-1 text-2xl font-semibold tabular-nums text-zinc-100">
                {value != null
                  ? `${Number(value).toFixed(decimals ?? 0)}${unit}`
                  : "—"}
              </p>
            )}
            {reading && detail && (
              <p className="mt-0.5 text-xs text-zinc-500">{detail(reading)}</p>
            )}
            {inRange !== null && (
              <p
                className={`mt-0.5 text-xs ${inRange ? "text-emerald-500" : "text-amber-500"}`}
              >
                {inRange ? "In range" : "Out of range"}
              </p>
            )}
          </div>
        );
      })}
    </div>
  );
}

