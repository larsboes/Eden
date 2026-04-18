import { getMockReading } from "@/lib/mock-sensors";
import { getRelayState } from "@/lib/control-state";
import { getAgentSuggestion } from "@/lib/agent-dummy";

export const dynamic = "force-dynamic";

const MARS_LATENCY_MS = 22 * 60 * 1000; // 22 minutes

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const simulateLatency = searchParams.get("latency") === "22";
  const reading = getMockReading();
  const relayState = getRelayState();
  const suggestion = await getAgentSuggestion(reading, relayState, {
    delayMs: simulateLatency ? MARS_LATENCY_MS : 0,
  });
  return Response.json({
    suggestion,
    reading_at: reading.timestamp,
  });
}
