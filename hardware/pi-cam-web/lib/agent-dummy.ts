/**
 * Dummy Bedrock agent: canned suggestions based on sensor snapshot.
 * Optional 22-minute latency simulation (delayMs).
 */

import type { SensorReading } from "./mock-sensors";
import type { RelayState } from "./control-state";

export interface AgentSuggestion {
  id: string;
  timestamp: string;
  latency_min?: number;
  summary: string;
  actions: string[];
  raw: string;
}

const SUGGESTIONS: Array<{
  condition: (r: SensorReading, s: RelayState) => boolean;
  summary: string;
  actions: string[];
}> = [
  {
    condition: (r) => r.temperature_c > 28,
    summary: "Temperature above 28°C — increase ventilation.",
    actions: ["Fan ON", "Consider shading during peak irradiance"],
  },
  {
    condition: (r) => r.soil_moisture_pct < 30,
    summary: "Soil moisture low — irrigation recommended.",
    actions: ["Pump ON", "Check water reservoir level"],
  },
  {
    condition: (r) => r.ph < 5.5,
    summary: "pH below 5.5 — nutrient uptake may be affected.",
    actions: ["Dose pH-up (dummy)", "Recheck in 6h"],
  },
  {
    condition: (r) => r.light_lux < 400,
    summary: "Light below 500 lux — supplemental lighting suggested.",
    actions: ["LEDs ON", "Monitor photoperiod"],
  },
  {
    condition: (r) => r.water_level_cm < 10,
    summary: "Water reservoir low — refill or reduce consumption.",
    actions: ["Alert crew", "Reduce pump runtime if needed"],
  },
  {
    condition: () => true,
    summary: "Conditions within nominal range. Continue monitoring.",
    actions: ["No change"],
  },
];

export async function getAgentSuggestion(
  reading: SensorReading,
  relayState: RelayState,
  options?: { delayMs?: number }
): Promise<AgentSuggestion> {
  const delayMs = options?.delayMs ?? 0;
  if (delayMs > 0) {
    await new Promise((r) => setTimeout(r, delayMs));
  }

  const match = SUGGESTIONS.find((s) => s.condition(reading, relayState)) ?? SUGGESTIONS[SUGGESTIONS.length - 1];
  const latencyMin = delayMs > 0 ? Math.round(delayMs / 60000) : undefined;

  return {
    id: `sug-${Date.now()}`,
    timestamp: new Date().toISOString(),
    latency_min: latencyMin,
    summary: match.summary,
    actions: match.actions,
    raw: `[Bedrock Agent - dummy] Analyzed greenhouse data for ${reading.zone_id}. ${match.summary}`,
  };
}
