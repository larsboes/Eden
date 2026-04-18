import { useState, useEffect } from 'react'

export default function AlertBanner({ visible, etaHours = 50.7 }) {
  const [elapsed, setElapsed] = useState(0)

  useEffect(() => {
    if (!visible) return
    const iv = setInterval(() => setElapsed(e => e + 1), 1000)
    return () => clearInterval(iv)
  }, [visible])

  if (!visible) return null

  const totalSec = Math.max(0, etaHours * 3600 - elapsed)
  const h = Math.floor(totalSec / 3600)
  const m = Math.floor((totalSec % 3600) / 60)
  const s = Math.floor(totalSec % 60)
  const pad = n => String(n).padStart(2, '0')

  return (
    <div className="fade-in eden-card" style={{
      padding: '16px 24px',
      background: 'rgba(239,68,68,0.06)',
      borderColor: 'rgba(239,68,68,0.2)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      animation: 'pulse-border 2s infinite',
    }}>
      <div>
        <div style={{ fontSize: 12, fontWeight: 600, color: '#ef4444', fontFamily: 'var(--font-mono)' }}>CME-2026-0315</div>
        <div style={{ fontSize: 11, color: 'var(--fg-muted)', marginTop: 2 }}>1,247 km/s · DONKI Live</div>
      </div>

      <div style={{
        fontFamily: 'var(--font-mono)',
        fontSize: 40,
        fontWeight: 700,
        color: '#ef4444',
        letterSpacing: 4,
        textShadow: '0 0 30px rgba(239,68,68,0.2)',
      }}>
        {pad(h)}:{pad(m)}:{pad(s)}
      </div>

      <div style={{ textAlign: 'right', fontSize: 11, color: 'var(--fg-muted)', fontFamily: 'var(--font-mono)', lineHeight: 1.8 }}>
        <div>Wheat BBCH 61 — HIGH risk</div>
        <div style={{ color: '#34d399' }}>Strategy C active</div>
      </div>
    </div>
  )
}
