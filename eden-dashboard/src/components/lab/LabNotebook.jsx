import { useState, useEffect } from 'react'

// An animated notebook where the AI "writes" observations in real-time.
// Diagrams drawn, data points plotted, conclusions circled.
// Like watching a scientist's notebook fill itself in.

const ENTRIES = [
  { phase: 0.02, type: 'header', text: 'EDEN Lab — CME Response Analysis' },
  { phase: 0.05, type: 'note', text: 'Scenario: CME-2026-0124, v=1,243 km/s' },
  { phase: 0.08, type: 'note', text: 'Mars ETA: 50.7h — window for preparation' },
  { phase: 0.10, type: 'divider' },

  { phase: 0.12, type: 'label', text: 'KB QUERY RESULTS:' },
  { phase: 0.15, type: 'finding', text: 'Wheat @ BBCH 60-69: HIGH UV-B sensitivity' },
  { phase: 0.18, type: 'finding', text: 'Yield reduction: 15-40% without shielding' },
  { phase: 0.20, type: 'finding', text: 'Recommended: EC +0.3-0.5 pre-hardening' },
  { phase: 0.23, type: 'divider' },

  { phase: 0.25, type: 'label', text: 'PARAMETER SWEEP:' },
  { phase: 0.28, type: 'data', values: [
    { label: 'Optimal EC', value: '1.2 mS/cm' },
    { label: 'Optimal Light', value: '55%' },
    { label: 'Target pH', value: '6.0-6.3' },
  ]},
  { phase: 0.35, type: 'divider' },

  { phase: 0.38, type: 'label', text: 'MONTE CARLO (n=800):' },
  { phase: 0.42, type: 'chart', data: [
    { label: 'A', pct: 40, color: '#ef4444' },
    { label: 'B', pct: 12, color: '#f59e0b' },
    { label: 'C', pct: 3,  color: '#22c55e' },
  ]},
  { phase: 0.50, type: 'divider' },

  { phase: 0.55, type: 'label', text: 'KEY INSIGHT:' },
  { phase: 0.58, type: 'insight', text: 'Pre-storm EC hardening reduces radiation damage by 35%' },
  { phase: 0.62, type: 'insight', text: 'Water stockpile of 240L provides 3-sol buffer' },
  { phase: 0.68, type: 'divider' },

  { phase: 0.72, type: 'label', text: 'DECISION:' },
  { phase: 0.78, type: 'conclusion', text: 'Strategy C — Pre-emptive protocol' },
  { phase: 0.82, type: 'conclusion', text: 'Confidence: 87% | Recovery: 5 sols' },
  { phase: 0.88, type: 'stamp', text: 'APPROVED' },
]

export default function LabNotebook({ t, running, done }) {
  const [visibleCount, setVisibleCount] = useState(0)

  const progress = done ? 1 : t

  useEffect(() => {
    if (!running && !done) { setVisibleCount(0); return }
    let count = 0
    for (const entry of ENTRIES) {
      if (progress >= entry.phase) count++
    }
    setVisibleCount(count)
  }, [progress, running, done])

  if (!running && !done) {
    return (
      <div style={{
        padding: '10px 14px',
        background: 'var(--bg-2)', border: '1px solid var(--border)',
        borderRadius: 8, opacity: 0.5,
      }}>
        <div style={{
          fontFamily: 'var(--font-mono)', fontSize: 9, fontWeight: 700,
          color: 'var(--fg-muted)', letterSpacing: 1.5,
        }}>
          LAB NOTEBOOK — waiting for simulation
        </div>
      </div>
    )
  }

  return (
    <div style={{
      background: 'rgba(30,28,24,0.6)',
      border: '1px solid rgba(167,139,250,0.15)',
      borderRadius: 8, padding: '10px 14px',
      maxHeight: 320, overflowY: 'auto',
      position: 'relative',
    }}>
      {/* Header */}
      <div style={{
        display: 'flex', justifyContent: 'space-between', alignItems: 'center',
        marginBottom: 8,
      }}>
        <span style={{
          fontFamily: 'var(--font-mono)', fontSize: 9, fontWeight: 700,
          color: 'var(--fg-muted)', letterSpacing: 1.5,
        }}>
          LAB NOTEBOOK
        </span>
        {running && (
          <span style={{
            fontFamily: 'var(--font-mono)', fontSize: 8,
            color: '#a78bfa',
            animation: 'pulse 1.5s ease-in-out infinite',
          }}>
            writing...
          </span>
        )}
      </div>

      {/* Notebook lines background */}
      <div style={{
        position: 'absolute', inset: 0, pointerEvents: 'none',
        backgroundImage: 'repeating-linear-gradient(transparent, transparent 17px, rgba(167,139,250,0.04) 17px, rgba(167,139,250,0.04) 18px)',
        backgroundPosition: '0 40px',
      }} />

      {/* Entries */}
      <div style={{ position: 'relative', display: 'flex', flexDirection: 'column', gap: 3 }}>
        {ENTRIES.slice(0, visibleCount).map((entry, i) => (
          <NotebookEntry
            key={i}
            entry={entry}
            isNew={i === visibleCount - 1 && running}
          />
        ))}

        {/* Cursor blink */}
        {running && (
          <div style={{
            width: 6, height: 12,
            background: 'rgba(167,139,250,0.6)',
            borderRadius: 1,
            animation: 'blink 1s step-end infinite',
            marginTop: 2,
          }} />
        )}
      </div>

      <style>{`
        @keyframes blink {
          0%, 100% { opacity: 1; }
          50% { opacity: 0; }
        }
        @keyframes notebookSlide {
          from { opacity: 0; transform: translateY(4px); }
          to { opacity: 1; transform: translateY(0); }
        }
      `}</style>
    </div>
  )
}

function NotebookEntry({ entry, isNew }) {
  const anim = isNew ? 'notebookSlide 0.3s ease both' : 'none'

  if (entry.type === 'divider') {
    return (
      <div style={{
        height: 1, margin: '3px 0',
        background: 'rgba(167,139,250,0.08)',
        animation: anim,
      }} />
    )
  }

  if (entry.type === 'header') {
    return (
      <div style={{
        fontFamily: 'var(--font-mono)', fontSize: 10, fontWeight: 700,
        color: '#a78bfa', letterSpacing: 1,
        borderBottom: '1px solid rgba(167,139,250,0.15)',
        paddingBottom: 4, marginBottom: 2,
        animation: anim,
      }}>
        {entry.text}
      </div>
    )
  }

  if (entry.type === 'label') {
    return (
      <div style={{
        fontFamily: 'var(--font-mono)', fontSize: 8, fontWeight: 700,
        color: 'var(--fg-muted)', letterSpacing: 1.5,
        marginTop: 2, animation: anim,
      }}>
        {entry.text}
      </div>
    )
  }

  if (entry.type === 'note') {
    return (
      <div style={{
        fontFamily: 'var(--font-mono)', fontSize: 9,
        color: 'var(--fg-secondary)', lineHeight: 1.5,
        animation: anim,
      }}>
        {entry.text}
      </div>
    )
  }

  if (entry.type === 'finding') {
    return (
      <div style={{
        fontFamily: 'var(--font-mono)', fontSize: 9,
        color: '#60a5fa', lineHeight: 1.5,
        paddingLeft: 8,
        borderLeft: '2px solid rgba(96,165,250,0.2)',
        animation: anim,
      }}>
        {entry.text}
      </div>
    )
  }

  if (entry.type === 'data') {
    return (
      <div style={{
        display: 'flex', gap: 12, animation: anim,
        padding: '4px 0',
      }}>
        {entry.values.map((v, i) => (
          <div key={i} style={{
            fontFamily: 'var(--font-mono)', fontSize: 8, lineHeight: 1.6,
          }}>
            <span style={{ color: 'var(--fg-muted)' }}>{v.label}: </span>
            <span style={{ color: '#22c55e', fontWeight: 700 }}>{v.value}</span>
          </div>
        ))}
      </div>
    )
  }

  if (entry.type === 'chart') {
    return (
      <div style={{
        display: 'flex', gap: 8, alignItems: 'flex-end',
        padding: '4px 0', animation: anim,
      }}>
        {entry.data.map((d, i) => (
          <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
            <div style={{
              width: Math.max(8, d.pct * 1.5), height: 8,
              background: d.color, borderRadius: 2, opacity: 0.7,
              transition: 'width 0.5s',
            }} />
            <span style={{
              fontFamily: 'var(--font-mono)', fontSize: 8, fontWeight: 700,
              color: d.color,
            }}>
              {d.label}: {d.pct}%
            </span>
          </div>
        ))}
      </div>
    )
  }

  if (entry.type === 'insight') {
    return (
      <div style={{
        fontFamily: 'var(--font-mono)', fontSize: 9, fontWeight: 600,
        color: '#e8913a', lineHeight: 1.5,
        paddingLeft: 8,
        borderLeft: '2px solid rgba(232,145,58,0.3)',
        animation: anim,
      }}>
        {entry.text}
      </div>
    )
  }

  if (entry.type === 'conclusion') {
    return (
      <div style={{
        fontFamily: 'var(--font-mono)', fontSize: 10, fontWeight: 700,
        color: '#22c55e', lineHeight: 1.6,
        padding: '2px 8px',
        background: 'rgba(34,211,153,0.06)',
        borderRadius: 4,
        animation: anim,
      }}>
        {entry.text}
      </div>
    )
  }

  if (entry.type === 'stamp') {
    return (
      <div style={{
        display: 'inline-block', marginTop: 4,
        fontFamily: 'var(--font-mono)', fontSize: 12, fontWeight: 700,
        color: '#22c55e', letterSpacing: 3,
        border: '2px solid rgba(34,211,153,0.4)',
        borderRadius: 4, padding: '2px 12px',
        transform: 'rotate(-3deg)',
        animation: anim,
      }}>
        {entry.text}
      </div>
    )
  }

  return null
}
