"use client";

import { useState, useEffect } from "react";

interface Entry {
  ts: string;
  topic: string;
  payload: Record<string, unknown>;
}

export function TelemetryLog() {
  const [entries, setEntries] = useState<Entry[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    async function fetchLog() {
      try {
        const res = await fetch("/api/telemetry?limit=20");
        const data = await res.json();
        if (!cancelled) setEntries(data.entries ?? []);
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    fetchLog();
    const t = setInterval(fetchLog, 5000);
    return () => {
      cancelled = true;
      clearInterval(t);
    };
  }, []);

  return (
    <div className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-4">
      <h3 className="text-sm font-semibold uppercase tracking-wider text-zinc-400">
        Telemetry (IoT publish log)
      </h3>
      <p className="mt-1 text-xs text-zinc-500">
        Topic: /mars/greenhouse/zone1/sensors · last 20
      </p>
      <div className="mt-3 max-h-48 overflow-y-auto rounded border border-zinc-700 bg-black/30 p-2 font-mono text-xs">
        {loading ? (
          <p className="text-zinc-500">Loading…</p>
        ) : entries.length === 0 ? (
          <p className="text-zinc-500">No entries yet.</p>
        ) : (
          entries.map((e, i) => (
            <div key={i} className="border-b border-zinc-800 py-1 last:border-0">
              <span className="text-zinc-500">{e.ts}</span> {e.topic}
            </div>
          ))
        )}
      </div>
    </div>
  );
}
