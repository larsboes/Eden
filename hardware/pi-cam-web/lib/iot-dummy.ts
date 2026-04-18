/**
 * Dummy AWS IoT Core: "publish" = log telemetry and return success.
 * Topic pattern: /mars/greenhouse/zone1/sensors
 */

import { appendTelemetry } from "./telemetry-log";

const TOPIC = "/mars/greenhouse/zone1/sensors";

export interface PublishResult {
  ok: boolean;
  topic: string;
  simulated: true;
  message: string;
}

export function publishToIot(payload: Record<string, unknown>): PublishResult {
  appendTelemetry(TOPIC, payload);
  return {
    ok: true,
    topic: TOPIC,
    simulated: true,
    message: "Telemetry published (dummy AWS IoT Core us-west-2)",
  };
}
