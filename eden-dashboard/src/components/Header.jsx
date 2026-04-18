import { useState, useEffect } from 'react'
import { useTheme } from '../hooks/useTheme'

export default function Header({ sol, dashboardState, onStateChange, demoRunning, view, onViewChange, apiConnected, sseConnected, mars, apiStatus }) {
  const anyConnected = apiConnected || sseConnected
  const { theme, toggle } = useTheme()
  const [time, setTime] = useState({ h: 14, m: 24, s: 9 })

  useEffect(() => {
    const iv = setInterval(() => {
      setTime(t => {
        let { h, m, s } = t
        s++
        if (s >= 60) { s = 0; m++ }
        if (m >= 60) { m = 0; h++ }
        if (h >= 24) h = 0
        return { h, m, s }
      })
    }, 1000)
    return () => clearInterval(iv)
  }, [])

  const pad = n => String(n).padStart(2, '0')

  const stateColors = {
    nominal: '#34d399',
    alert: '#e8913a',
    crisis: '#ef4444',
    recovery: '#60a5fa',
  }

  return (
    <div className="eden-header">
      {/* Left: Brand + View tabs */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
        <div style={{ display: 'flex', alignItems: 'baseline', gap: 10 }}>
          <span style={{
            fontFamily: 'var(--font-mono)',
            fontSize: 26,
            fontWeight: 700,
            color: '#e8913a',
            letterSpacing: 4,
          }}>
            EDEN
          </span>
          <span style={{ fontSize: 10, color: 'var(--fg-muted)', fontFamily: 'var(--font-mono)', letterSpacing: 1 }}>
            Sol {sol}
          </span>
          <span style={{ fontSize: 10, color: 'var(--fg-muted)', fontFamily: 'var(--font-mono)' }}>·</span>
          <span style={{ fontSize: 12, color: '#e8913a', fontFamily: 'var(--font-mono)', fontWeight: 500 }}>
            {pad(time.h)}:{pad(time.m)}:{pad(time.s)}
          </span>
          {mars && (
            <>
              <span style={{ fontSize: 10, color: 'var(--fg-muted)', fontFamily: 'var(--font-mono)' }}>·</span>
              <span style={{ fontSize: 10, color: '#63B3ED', fontFamily: 'var(--font-mono)' }}>
                {Math.round(mars.exterior_temp)}°C
              </span>
              <span style={{ fontSize: 10, color: mars.dust_opacity > 0.5 ? '#f59e0b' : 'var(--fg-muted)', fontFamily: 'var(--font-mono)' }}>
                τ{mars.dust_opacity?.toFixed(1)}
              </span>
              {mars.radiation_alert && (
                <span style={{
                  fontSize: 8, fontFamily: 'var(--font-mono)', fontWeight: 700,
                  color: '#ef4444', background: 'rgba(239,68,68,0.15)',
                  padding: '1px 5px', borderRadius: 3, letterSpacing: 0.5,
                }}>
                  RAD
                </span>
              )}
              {mars.storm_active && (
                <span style={{
                  fontSize: 8, fontFamily: 'var(--font-mono)', fontWeight: 700,
                  color: '#f59e0b', background: 'rgba(245,158,11,0.15)',
                  padding: '1px 5px', borderRadius: 3, letterSpacing: 0.5,
                }}>
                  STORM
                </span>
              )}
            </>
          )}
        </div>

        {/* View tabs */}
        <div className="view-tabs">
          <button
            className={`view-tab ${view === 'cluster' ? 'view-tab--active' : ''}`}
            onClick={() => onViewChange('cluster')}
          >
            Cluster
          </button>
          <button
            className={`view-tab ${view === 'dashboard' ? 'view-tab--active' : ''}`}
            onClick={() => onViewChange('dashboard')}
          >
            Dashboard
          </button>
          <button
            className={`view-tab ${view === 'lab' ? 'view-tab--active' : ''}`}
            onClick={() => onViewChange('lab')}
          >
            Lab
          </button>
        </div>
      </div>

      {/* Right: State switcher + theme toggle */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
        <div style={{ display: 'flex', gap: 4 }}>
          {Object.entries(stateColors).map(([key, color]) => (
            <button
              key={key}
              onClick={() => !demoRunning && onStateChange(key)}
              className="state-btn"
              style={{
                border: `1px solid ${dashboardState === key ? color + '66' : 'var(--border)'}`,
                background: dashboardState === key ? color + '15' : 'transparent',
                color: dashboardState === key ? color : 'var(--fg-muted)',
                opacity: demoRunning ? 0.5 : 1,
                cursor: demoRunning ? 'default' : 'pointer',
              }}
            >
              {key}
            </button>
          ))}
        </div>

        <span
          title={anyConnected
            ? `Backend connected — API: ${apiConnected ? 'OK' : 'off'}, SSE: ${sseConnected ? 'OK' : 'off'}, ${apiStatus?.model_tier || 'unknown'} model, ${apiStatus?.zones_count || 0} zones`
            : 'Backend offline — showing mock data. Start with: python -m eden'}
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: 5,
            fontSize: 10,
            fontFamily: 'var(--font-mono)',
            fontWeight: 700,
            color: anyConnected ? '#34d399' : '#f59e0b',
            padding: '3px 10px',
            borderRadius: 4,
            border: `1px solid ${anyConnected ? '#34d39940' : '#f59e0b40'}`,
            background: anyConnected ? '#34d39910' : '#f59e0b10',
            animation: anyConnected ? 'none' : 'pulse-mock 2s infinite',
          }}
        >
          <span style={{
            width: 7, height: 7, borderRadius: '50%',
            background: anyConnected ? '#34d399' : '#f59e0b',
            boxShadow: anyConnected ? '0 0 6px #34d399' : '0 0 6px #f59e0b',
          }} />
          {anyConnected ? 'LIVE' : 'MOCK'}
          {anyConnected && apiStatus?.model_tier && apiStatus.model_tier !== 'none' && (
            <span style={{ color: '#60a5fa', marginLeft: 2 }}>
              {apiStatus.model_tier}
            </span>
          )}
          {anyConnected && (
            <span style={{ fontWeight: 400, fontSize: 9 }}>
              <span style={{ color: apiConnected ? '#34d399' : '#ef4444' }}>API{apiConnected ? '✓' : '✗'}</span>
              {' '}
              <span style={{ color: sseConnected ? '#34d399' : '#ef4444' }}>SSE{sseConnected ? '✓' : '✗'}</span>
            </span>
          )}
        </span>

        <button className="theme-toggle" onClick={toggle} title={`Switch to ${theme === 'dark' ? 'light' : 'dark'} mode`}>
          {theme === 'dark' ? '☀️' : '🌙'}
        </button>
      </div>
    </div>
  )
}
