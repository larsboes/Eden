/**
 * Mock sensor readings used as fallback when real hardware path fails.
 */

const ZONE_ID = "zone1";

export interface SensorReading {
  zone_id: string;
  timestamp: string;
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
}

let seed = 0;
function seededNoise(t: number): number {
  const x = Math.sin(t * 12.9898 + seed) * 43758.5453;
  return x - Math.floor(x);
}

export function getMockReading(): SensorReading {
  const t = Date.now() / 60000;
  seed = (seed + 1) % 100;
  const ambientLightPct = 35 + seededNoise(t + 2) * 60;
  const waterLevelPct = 20 + seededNoise(t + 5) * 60;
  return {
    zone_id: ZONE_ID,
    timestamp: new Date().toISOString(),
    temperature_c: 24 + seededNoise(t) * 6 - 1,
    temperature_source: "mock",
    humidity_pct: 55 + seededNoise(t + 1) * 25,
    humidity_source: "mock",
    pressure_hpa: 1000 + seededNoise(t + 8) * 25,
    pressure_source: "mock",
    ambient_light_pct: ambientLightPct,
    water_level_pct: waterLevelPct,
    light_lux: ambientLightPct * 10,
    soil_moisture_pct: 40 + seededNoise(t + 3) * 35,
    light_raw: Math.round(5000 + seededNoise(t + 9) * 25000),
    light_voltage: 0.5 + seededNoise(t + 10) * 2.0,
    water_raw: Math.round(3000 + seededNoise(t + 11) * 12000),
    water_voltage: 0.1 + seededNoise(t + 12) * 1.2,
    soil_raw: Math.round(12000 + seededNoise(t + 13) * 15000),
    soil_voltage: 0.8 + seededNoise(t + 14) * 1.5,
    ph: 5.8 + seededNoise(t + 4) * 1.2,
    water_level_cm: waterLevelPct / 10,
  };
}

