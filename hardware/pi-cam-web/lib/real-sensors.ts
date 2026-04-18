import type { SensorReading } from "./mock-sensors";

const FASTAPI_BASE_URL = process.env.SENSOR_API_BASE_URL ?? "http://127.0.0.1:8001";

export interface SensorSnapshot {
  reading: SensorReading;
  sensors: Record<string, unknown>;
}

function fromRecord(record: unknown): Record<string, unknown> {
  return typeof record === "object" && record !== null ? (record as Record<string, unknown>) : {};
}

function toNullableNumber(value: unknown): number | null {
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

function normalizeReading(readingLike: unknown): SensorReading {
  const r = fromRecord(readingLike);
  const ambientPct = toNullableNumber(r.ambient_light_pct) ?? 0;
  const waterPct = toNullableNumber(r.water_level_pct) ?? 0;

  return {
    zone_id: typeof r.zone_id === "string" ? r.zone_id : "zone1",
    timestamp: typeof r.timestamp === "string" ? r.timestamp : new Date().toISOString(),
    temperature_c: toNullableNumber(r.temperature_c),
    temperature_source: typeof r.temperature_source === "string" ? r.temperature_source : null,
    humidity_pct: toNullableNumber(r.humidity_pct),
    humidity_source: typeof r.humidity_source === "string" ? r.humidity_source : null,
    pressure_hpa: toNullableNumber(r.pressure_hpa),
    pressure_source: typeof r.pressure_source === "string" ? r.pressure_source : null,
    ambient_light_pct: toNullableNumber(r.ambient_light_pct),
    water_level_pct: toNullableNumber(r.water_level_pct),
    light_lux: toNullableNumber(r.light_lux) ?? ambientPct * 10,
    soil_moisture_pct: toNullableNumber(r.soil_moisture_pct),
    light_raw: toNullableNumber(r.light_raw),
    light_voltage: toNullableNumber(r.light_voltage),
    water_raw: toNullableNumber(r.water_raw),
    water_voltage: toNullableNumber(r.water_voltage),
    soil_raw: toNullableNumber(r.soil_raw),
    soil_voltage: toNullableNumber(r.soil_voltage),
    ph: toNullableNumber(r.ph) ?? 6.0,
    water_level_cm: toNullableNumber(r.water_level_cm) ?? waterPct / 10,
  };
}

export async function getRealSensorSnapshot(timeoutMs: number = 3000): Promise<SensorSnapshot> {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), timeoutMs);
  let response: Response;
  try {
    response = await fetch(`${FASTAPI_BASE_URL}/sensors`, {
      method: "GET",
      cache: "no-store",
      signal: controller.signal,
    });
  } finally {
    clearTimeout(timeout);
  }

  if (!response.ok) {
    throw new Error(`Sensor API error: ${response.status} ${response.statusText}`);
  }

  const parsed = (await response.json()) as { reading?: unknown; sensors?: Record<string, unknown> };
  return {
    reading: normalizeReading(parsed.reading),
    sensors: parsed.sensors ?? {},
  };
}

