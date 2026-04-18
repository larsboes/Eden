import { useState } from 'react'

const API_BASE = import.meta.env.VITE_EDEN_API || 'http://localhost:8000'

const urgencyColors = {
  critical: '#ef4444',
  high: '#f59e0b',
  medium: '#06b6d4',
  low: '#22c55e',
}

const urgencyLabels = {
  critical: 'CRITICAL',
  high: 'HIGH',
  medium: 'MEDIUM',
  low: 'LOW',
}

const categoryIcons = {
  hardware: '🔧',
  safety: '⚠️',
  biological: '🌱',
  resource: '💧',
}

export default function CrewEscalationBanner({ escalations, onUpdate }) {
  if (!escalations || escalations.length === 0) return null

  // Show only pending/acknowledged escalations
  const active = escalations.filter(
    (e) => e.status === 'pending' || e.status === 'acknowledged'
  )
  if (active.length === 0) return null

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
      {active.map((esc) => (
        <EscalationCard key={esc.escalation_id} escalation={esc} onUpdate={onUpdate} />
      ))}
    </div>
  )
}

function EscalationCard({ escalation, onUpdate }) {
  const [loading, setLoading] = useState(null)
  const color = urgencyColors[escalation.urgency] || '#f59e0b'
  const isPending = escalation.status === 'pending'

  const doAction = async (action) => {
    setLoading(action)
    try {
      await fetch(
        `${API_BASE}/api/escalations/${escalation.escalation_id}/${action}`,
        { method: 'POST' }
      )
      if (onUpdate) onUpdate(escalation.escalation_id, action)
    } catch {
      /* backend might be down */
    }
    setLoading(null)
  }

  return (
    <div
      className="fade-in eden-card"
      style={{
        padding: '14px 20px',
        background: `rgba(${color === '#ef4444' ? '239,68,68' : color === '#f59e0b' ? '245,158,11' : '6,182,212'},0.06)`,
        borderColor: `${color}33`,
        display: 'flex',
        alignItems: 'center',
        gap: 16,
        animation: isPending ? 'pulse-border 2s infinite' : 'none',
      }}
    >
      {/* Urgency badge */}
      <div
        style={{
          fontFamily: 'var(--font-mono)',
          fontSize: 11,
          fontWeight: 700,
          color: '#fff',
          background: color,
          padding: '3px 8px',
          borderRadius: 4,
          letterSpacing: 1,
          whiteSpace: 'nowrap',
        }}
      >
        {categoryIcons[escalation.category] || '🔴'}{' '}
        {urgencyLabels[escalation.urgency] || 'HIGH'}
      </div>

      {/* Task description */}
      <div style={{ flex: 1, minWidth: 0 }}>
        <div
          style={{
            fontSize: 13,
            fontWeight: 600,
            color: 'var(--fg)',
            lineHeight: 1.4,
          }}
        >
          {escalation.task}
        </div>
        <div
          style={{
            fontSize: 10,
            color: 'var(--fg-muted)',
            fontFamily: 'var(--font-mono)',
            marginTop: 2,
          }}
        >
          Zone: {escalation.zone_id} · Est. {escalation.estimated_minutes} min ·{' '}
          {escalation.status.toUpperCase()}
        </div>
      </div>

      {/* Action buttons */}
      <div style={{ display: 'flex', gap: 6 }}>
        {isPending && (
          <ActionBtn
            label="ACK"
            color="#60a5fa"
            loading={loading === 'acknowledge'}
            onClick={() => doAction('acknowledge')}
          />
        )}
        <ActionBtn
          label="RESOLVE"
          color="#34d399"
          loading={loading === 'resolve'}
          onClick={() => doAction('resolve')}
        />
        <ActionBtn
          label="DISMISS"
          color="var(--fg-muted)"
          loading={loading === 'dismiss'}
          onClick={() => doAction('dismiss')}
        />
      </div>
    </div>
  )
}

function ActionBtn({ label, color, loading, onClick }) {
  return (
    <button
      onClick={onClick}
      disabled={loading}
      style={{
        fontFamily: 'var(--font-mono)',
        fontSize: 9,
        fontWeight: 700,
        padding: '4px 10px',
        borderRadius: 4,
        border: `1px solid ${color}44`,
        background: loading ? `${color}22` : 'transparent',
        color: loading ? color : 'var(--fg-muted)',
        cursor: loading ? 'default' : 'pointer',
        letterSpacing: 0.5,
        transition: 'all 0.2s',
      }}
    >
      {loading ? '...' : label}
    </button>
  )
}
