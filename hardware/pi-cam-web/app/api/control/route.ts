import { getRelayState, setRelayState } from "@/lib/control-state";

export const dynamic = "force-dynamic";

export async function GET() {
  return Response.json(getRelayState());
}

export async function POST(request: Request) {
  const body = await request.json().catch(() => ({}));
  const { fan, pump, leds } = body;
  const next: Partial<ReturnType<typeof getRelayState>> = {};
  if (typeof fan === "boolean") next.fan = fan;
  if (typeof pump === "boolean") next.pump = pump;
  if (typeof leds === "boolean") next.leds = leds;
  const state = setRelayState(next);
  return Response.json(state);
}
