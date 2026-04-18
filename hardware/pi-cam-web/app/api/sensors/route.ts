import { getMockReading } from "@/lib/mock-sensors";
import { applyThresholdRules } from "@/lib/control-state";
import { publishToIot } from "@/lib/iot-dummy";
import { getRealSensorSnapshot } from "@/lib/real-sensors";

export const dynamic = "force-dynamic";

export async function GET() {
  let reading = getMockReading();
  let source: "real" | "mock" = "mock";
  let sourceError: string | null = null;
  let sensors: Record<string, unknown> | null = null;

  try {
    const real = await getRealSensorSnapshot();
    reading = real.reading;
    sensors = real.sensors;
    source = "real";
  } catch (error) {
    sourceError = error instanceof Error ? error.message : String(error);
  }

  const relayState = applyThresholdRules(reading);
  publishToIot({
    ...reading,
    relay: relayState,
  });

  return Response.json({
    reading,
    relay: relayState,
    source,
    source_error: sourceError,
    sensors,
  });
}

