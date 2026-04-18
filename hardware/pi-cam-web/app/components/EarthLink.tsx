"use client";

import { useState } from "react";

interface Suggestion {
  id: string;
  timestamp: string;
  latency_min?: number;
  summary: string;
  actions: string[];
  raw: string;
}

export function EarthLink() {
  const [suggestion, setSuggestion] = useState<Suggestion | null>(null);
  const [loading, setLoading] = useState(false);
  const [simulate22, setSimulate22] = useState(false);

  const fetchSuggestion = async () => {
    setLoading(true);
    setSuggestion(null);
    try {
      const url = `/api/agent/suggestions${simulate22 ? "?latency=22" : ""}`;
      const res = await fetch(url);
      const data = await res.json();
      setSuggestion(data.suggestion);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-4">
      <h3 className="text-sm font-semibold uppercase tracking-wider text-zinc-400">
        Earth link (Bedrock agent — dummy)
      </h3>
      <p className="mt-1 text-xs text-zinc-500">
        AWS us-west-2 · 22-min one-way latency simulated when enabled
      </p>
      <div className="mt-3 flex flex-wrap items-center gap-2">
        <label className="flex items-center gap-2 text-sm text-zinc-400">
          <input
            type="checkbox"
            checked={simulate22}
            onChange={(e) => setSimulate22(e.target.checked)}
            className="rounded border-zinc-600"
          />
          Simulate 22 min latency
        </label>
        <button
          type="button"
          onClick={fetchSuggestion}
          disabled={loading}
          className="rounded-lg bg-violet-600 px-4 py-2 text-sm font-medium text-white hover:bg-violet-500 disabled:opacity-50"
        >
          {loading ? "Requesting…" : "Get suggestion"}
        </button>
      </div>
      {suggestion && (
        <div className="mt-4 rounded-lg border border-zinc-700 bg-zinc-800/50 p-3">
          {suggestion.latency_min != null && (
            <span className="mb-2 inline-block rounded bg-amber-500/20 px-2 py-0.5 text-xs text-amber-400">
              +{suggestion.latency_min} min Earth delay
            </span>
          )}
          <p className="font-medium text-zinc-200">{suggestion.summary}</p>
          <ul className="mt-2 list-inside list-disc text-sm text-zinc-400">
            {suggestion.actions.map((a, i) => (
              <li key={i}>{a}</li>
            ))}
          </ul>
          <p className="mt-2 text-xs text-zinc-500">{suggestion.raw}</p>
        </div>
      )}
    </div>
  );
}
