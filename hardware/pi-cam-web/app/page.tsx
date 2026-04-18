"use client";

import { useState, useEffect, useCallback } from "react";
import { SensorCards } from "./components/SensorCards";
import { SensorTrends, type TrendPoint } from "./components/SensorTrends";
import { ControlPanel } from "./components/ControlPanel";
import { EarthLink } from "./components/EarthLink";
import { TelemetryLog } from "./components/TelemetryLog";

interface SensorResponse {
  reading: {
    zone_id: string;
    pressure_hpa: number | null;
    pressure_source?: string | null;
    temperature_c: number | null;
    temperature_source?: string | null;
    humidity_pct: number | null;
    humidity_source?: string | null;
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
  };
  relay: { fan: boolean; pump: boolean; leds: boolean; updated_at: string };
  source?: "real" | "mock";
  source_error?: string | null;
  sensors?: Record<string, unknown> | null;
}

export default function Home() {
  const [data, setData] = useState<SensorResponse | null>(null);
  const [history, setHistory] = useState<TrendPoint[]>([]);
  const [sensorsLoading, setSensorsLoading] = useState(true);
  const [controlLoading, setControlLoading] = useState(false);
  const [cameraSrc, setCameraSrc] = useState("/api/stream?ts=0");

  const fetchSensors = useCallback(async () => {
    try {
      const res = await fetch("/api/sensors");
      const json = await res.json();
      setData(json);
      const r = json?.reading;
      if (r && typeof r === "object") {
        const point: TrendPoint = {
          timestamp: typeof r.timestamp === "string" ? r.timestamp : new Date().toISOString(),
          temperature_c: typeof r.temperature_c === "number" ? r.temperature_c : null,
          humidity_pct: typeof r.humidity_pct === "number" ? r.humidity_pct : null,
          pressure_hpa: typeof r.pressure_hpa === "number" ? r.pressure_hpa : null,
          ambient_light_pct: typeof r.ambient_light_pct === "number" ? r.ambient_light_pct : null,
          water_level_pct: typeof r.water_level_pct === "number" ? r.water_level_pct : null,
          soil_moisture_pct: typeof r.soil_moisture_pct === "number" ? r.soil_moisture_pct : null,
        };
        setHistory((prev) => {
          const next = [...prev, point];
          return next.slice(-60);
        });
      }
    } catch {
      setData(null);
    } finally {
      setSensorsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchSensors();
    const t = setInterval(fetchSensors, 3000);
    return () => clearInterval(t);
  }, [fetchSensors]);

  useEffect(() => {
    const refresh = () => setCameraSrc(`/api/stream?ts=${Date.now()}`);
    refresh();
    const timer = setInterval(refresh, 3000);
    return () => clearInterval(timer);
  }, []);

  const handleToggle = useCallback(
    async (key: "fan" | "pump" | "leds", value: boolean) => {
      setControlLoading(true);
      try {
        const res = await fetch("/api/control", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ [key]: value }),
        });
        const relay = await res.json();
        setData((prev) => (prev ? { ...prev, relay } : null));
      } finally {
        setControlLoading(false);
      }
    },
    []
  );

  return (
    <main className="min-h-screen bg-zinc-950 px-4 py-6 text-zinc-100 md:px-8">
      <div className="mx-auto max-w-6xl space-y-8">
        <header className="border-b border-zinc-800 pb-4">
          <h1 className="text-3xl font-bold tracking-tight">
            AstroFarm — Martian Greenhouse
          </h1>
          <p className="mt-1 text-sm text-zinc-400">
            Syngenta x AWS START HACK 2026 · Autonomous AI agent · Zone 1 (Pi 5)
          </p>
        </header>

        <section>
          <div className="mb-3 flex items-center justify-between">
            <h2 className="text-lg font-semibold text-zinc-300">Sensors</h2>
            <p className="text-xs text-zinc-500">
              Source: {data?.source ?? "unknown"}
              {data?.source_error ? ` (${data.source_error})` : ""}
            </p>
          </div>
          <SensorCards
            reading={data?.reading ?? null}
            loading={sensorsLoading}
          />
        </section>

        <section>
          <h2 className="mb-3 text-lg font-semibold text-zinc-300">Sensor trends</h2>
          <SensorTrends history={history} />
        </section>

        <section>
          <h2 className="mb-3 text-lg font-semibold text-zinc-300">Control</h2>
          <ControlPanel
            relay={data?.relay ?? null}
            loading={controlLoading}
            onToggle={handleToggle}
          />
        </section>

        <section className="grid gap-6 md:grid-cols-2">
          <EarthLink />
          <TelemetryLog />
        </section>

        <section>
          <h2 className="mb-3 text-lg font-semibold text-zinc-300">Camera</h2>
          <div className="overflow-hidden rounded-2xl border border-zinc-800 bg-black shadow-xl">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src={cameraSrc}
              alt="Pi Camera — plant imaging"
              className="h-auto w-full"
            />
          </div>
          <p className="mt-2 text-xs text-zinc-500">
            Pi Camera snapshot every 3 seconds.
          </p>
        </section>
      </div>
    </main>
  );
}

