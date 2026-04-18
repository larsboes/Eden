import { execFile } from "node:child_process";
import { promisify } from "node:util";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

const execFileAsync = promisify(execFile);

export async function GET() {
  try {
    const { stdout } = await execFileAsync(
      "rpicam-jpeg",
      [
        "--nopreview",
        "--width",
        "1280",
        "--height",
        "720",
        "--quality",
        "90",
        "--timeout",
        "1",
        "-o",
        "-",
      ],
      { encoding: "buffer", maxBuffer: 10 * 1024 * 1024, timeout: 5000 },
    );

    return new Response(stdout as Buffer, {
      headers: {
        "Content-Type": "image/jpeg",
        "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0, no-transform",
        Pragma: "no-cache",
      },
    });
  } catch {
    return new Response("Camera snapshot failed", { status: 500 });
  }
}

