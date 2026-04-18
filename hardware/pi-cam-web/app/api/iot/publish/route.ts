import { publishToIot } from "@/lib/iot-dummy";

export const dynamic = "force-dynamic";

export async function POST(request: Request) {
  const payload = await request.json().catch(() => ({}));
  const result = publishToIot(typeof payload === "object" && payload !== null ? payload : { payload });
  return Response.json(result);
}
