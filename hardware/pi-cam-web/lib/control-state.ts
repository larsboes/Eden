/**
 * In-memory relay state and threshold rules (autonomy logic).
 * Fan on if temp>28°C; pump if moisture<30%; LEDs on when light<500 lux.
 */

import type { SensorReading } from "./mock-sensors";

export interface RelayState {
  fan: boolean;
  pump: boolean;
  leds: boolean;
  updated_at: string;
}

let state: RelayState = {
  fan: false,
  pump: false,
  leds: false,
  updated_at: new Date().toISOString(),
};

export function getRelayState(): RelayState {
  return { ...state };
}

export function setRelayState(partial: Partial<RelayState>): RelayState {
  state = {
    ...state,
    ...partial,
    updated_at: new Date().toISOString(),
  };
  return getRelayState();
}

export function applyThresholdRules(reading: SensorReading): RelayState {
  state.fan = reading.temperature_c > 28;
  state.pump = reading.soil_moisture_pct < 30;
  state.leds = reading.light_lux < 500;
  state.updated_at = new Date().toISOString();
  return getRelayState();
}
