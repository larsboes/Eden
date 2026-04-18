"use client";

interface RelayState {
  fan: boolean;
  pump: boolean;
  leds: boolean;
  updated_at: string;
}

interface ControlPanelProps {
  relay: RelayState | null;
  loading: boolean;
  onToggle: (key: "fan" | "pump" | "leds", value: boolean) => void;
}

const items: Array<{ key: "fan" | "pump" | "leds"; label: string; desc: string }> = [
  { key: "fan", label: "Fan", desc: "Temp > 28°C" },
  { key: "pump", label: "Pump", desc: "Moisture < 30%" },
  { key: "leds", label: "LEDs", desc: "Light < 500 lux" },
];

export function ControlPanel({ relay, loading, onToggle }: ControlPanelProps) {
  return (
    <div className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-4">
      <h3 className="text-sm font-semibold uppercase tracking-wider text-zinc-400">
        Relays (autonomy rules)
      </h3>
      <div className="mt-3 flex flex-wrap gap-3">
        {items.map(({ key, label, desc }) => {
          const on = relay ? relay[key] : false;
          return (
            <div key={key} className="flex items-center gap-2">
              <button
                type="button"
                disabled={loading}
                onClick={() => onToggle(key, !on)}
                className={`rounded-lg px-4 py-2 text-sm font-medium transition-colors ${
                  on
                    ? "bg-emerald-600 text-white hover:bg-emerald-500"
                    : "bg-zinc-700 text-zinc-300 hover:bg-zinc-600"
                }`}
              >
                {label}: {on ? "ON" : "OFF"}
              </button>
              <span className="text-xs text-zinc-500">{desc}</span>
            </div>
          );
        })}
      </div>
      {relay?.updated_at && (
        <p className="mt-2 text-xs text-zinc-500">Updated {new Date(relay.updated_at).toLocaleTimeString()}</p>
      )}
    </div>
  );
}
