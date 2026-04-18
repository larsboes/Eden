import { getRecentTelemetry } from "@/lib/telemetry-log";

export const dynamic = "force-dynamic";

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const limit = Math.min(Number(searchParams.get("limit")) || 50, 200);
  const entries = getRecentTelemetry(limit);
  return Response.json({ entries });
}
