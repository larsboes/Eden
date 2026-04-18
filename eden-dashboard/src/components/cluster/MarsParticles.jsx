import { useState, useEffect } from 'react'

// ── Dust particles — varied sizes, speeds, positions ────────────────────────
const PARTICLES = [
  // Large slow drifters
  { id: 0,  x: 5,   y: 12,  size: 4.0, dur: 32, delay: 0,   opacity: 0.15 },
  { id: 1,  x: 18,  y: 45,  size: 3.5, dur: 28, delay: 3,   opacity: 0.12 },
  { id: 2,  x: 38,  y: 72,  size: 5.0, dur: 35, delay: 1,   opacity: 0.10 },
  { id: 3,  x: 60,  y: 28,  size: 4.5, dur: 30, delay: 6,   opacity: 0.14 },
  { id: 4,  x: 82,  y: 55,  size: 3.8, dur: 26, delay: 2,   opacity: 0.11 },
  { id: 5,  x: 92,  y: 80,  size: 4.2, dur: 34, delay: 8,   opacity: 0.13 },
  // Medium particles
  { id: 6,  x: 10,  y: 60,  size: 2.5, dur: 22, delay: 0,   opacity: 0.18 },
  { id: 7,  x: 28,  y: 20,  size: 2.0, dur: 25, delay: 4,   opacity: 0.16 },
  { id: 8,  x: 48,  y: 85,  size: 2.8, dur: 20, delay: 2,   opacity: 0.14 },
  { id: 9,  x: 65,  y: 40,  size: 2.2, dur: 28, delay: 7,   opacity: 0.17 },
  { id: 10, x: 75,  y: 15,  size: 2.6, dur: 24, delay: 1,   opacity: 0.15 },
  { id: 11, x: 88,  y: 65,  size: 2.0, dur: 30, delay: 5,   opacity: 0.13 },
  // Fine dust — many small fast ones
  { id: 12, x: 3,   y: 35,  size: 1.5, dur: 18, delay: 0,   opacity: 0.20 },
  { id: 13, x: 15,  y: 78,  size: 1.2, dur: 16, delay: 3,   opacity: 0.18 },
  { id: 14, x: 32,  y: 50,  size: 1.8, dur: 20, delay: 1,   opacity: 0.15 },
  { id: 15, x: 42,  y: 10,  size: 1.0, dur: 14, delay: 6,   opacity: 0.22 },
  { id: 16, x: 55,  y: 90,  size: 1.4, dur: 19, delay: 2,   opacity: 0.16 },
  { id: 17, x: 70,  y: 52,  size: 1.6, dur: 17, delay: 4,   opacity: 0.19 },
  { id: 18, x: 85,  y: 30,  size: 1.3, dur: 15, delay: 0,   opacity: 0.21 },
  { id: 19, x: 95,  y: 70,  size: 1.1, dur: 22, delay: 8,   opacity: 0.17 },
  // Edge drifters — enter from sides
  { id: 20, x: -3,  y: 25,  size: 3.5, dur: 20, delay: 0,   opacity: 0.10 },
  { id: 21, x: 103, y: 60,  size: 3.0, dur: 22, delay: 4,   opacity: 0.08 },
  { id: 22, x: -2,  y: 75,  size: 2.8, dur: 18, delay: 7,   opacity: 0.09 },
  { id: 23, x: 104, y: 35,  size: 3.2, dur: 24, delay: 2,   opacity: 0.07 },
]

// ── Wind streaks — thin horizontal lines blown across ───────────────────────
const STREAKS = [
  { id: 0, y: 18, width: 120, dur: 12, delay: 0,  opacity: 0.04 },
  { id: 1, y: 35, width: 80,  dur: 16, delay: 3,  opacity: 0.03 },
  { id: 2, y: 52, width: 140, dur: 10, delay: 1,  opacity: 0.05 },
  { id: 3, y: 68, width: 100, dur: 14, delay: 5,  opacity: 0.04 },
  { id: 4, y: 82, width: 160, dur: 11, delay: 2,  opacity: 0.03 },
  { id: 5, y: 45, width: 90,  dur: 18, delay: 7,  opacity: 0.035 },
  { id: 6, y: 25, width: 110, dur: 13, delay: 4,  opacity: 0.04 },
  { id: 7, y: 72, width: 130, dur: 15, delay: 6,  opacity: 0.03 },
]

const STATE_CONFIG = {
  nominal:  { color: '180, 120, 60',   vignetteAlpha: 0.12, grainAlpha: 0.03, streakMult: 1.0 },
  alert:    { color: '200, 130, 50',   vignetteAlpha: 0.18, grainAlpha: 0.04, streakMult: 1.5 },
  crisis:   { color: '200, 80, 50',    vignetteAlpha: 0.25, grainAlpha: 0.06, streakMult: 2.0 },
  recovery: { color: '140, 160, 180',  vignetteAlpha: 0.10, grainAlpha: 0.02, streakMult: 0.8 },
}

export default function MarsParticles({ enabled, dashboardState }) {
  if (!enabled) return null

  const cfg = STATE_CONFIG[dashboardState] || STATE_CONFIG.nominal
  const c = cfg.color

  return (
    <div style={{
      position: 'fixed', inset: 0, pointerEvents: 'none', zIndex: 0, overflow: 'hidden',
    }}>
      {/* Layer 1: Vignette — warm edge glow */}
      <div style={{
        position: 'absolute', inset: 0,
        background: `radial-gradient(ellipse 80% 70% at 50% 50%, transparent 40%, rgba(${c}, ${cfg.vignetteAlpha}) 100%)`,
        transition: 'background 1s ease',
      }} />

      {/* Layer 2: Top atmospheric haze */}
      <div style={{
        position: 'absolute', top: 0, left: 0, right: 0, height: '30%',
        background: `linear-gradient(180deg, rgba(${c}, ${cfg.vignetteAlpha * 0.4}) 0%, transparent 100%)`,
        transition: 'background 1s ease',
      }} />

      {/* Layer 3: Dust particles */}
      {PARTICLES.map(p => (
        <div
          key={p.id}
          style={{
            position: 'absolute',
            left: `${p.x}%`,
            top: `${p.y}%`,
            width: p.size,
            height: p.size,
            borderRadius: '50%',
            background: `rgba(${c}, ${p.opacity})`,
            boxShadow: `0 0 ${p.size * 3}px rgba(${c}, ${p.opacity * 0.6})`,
            animation: `marsDrift${p.id % 6} ${p.dur}s ease-in-out ${p.delay}s infinite`,
          }}
        />
      ))}

      {/* Layer 4: Wind streaks */}
      {STREAKS.map(s => (
        <div
          key={`s${s.id}`}
          style={{
            position: 'absolute',
            top: `${s.y}%`,
            left: '-10%',
            width: `${s.width}px`,
            height: '1px',
            background: `linear-gradient(90deg, transparent, rgba(${c}, ${s.opacity * cfg.streakMult}), transparent)`,
            animation: `marsStreak ${s.dur}s linear ${s.delay}s infinite`,
            opacity: cfg.streakMult,
          }}
        />
      ))}

      {/* Layer 5: Noise grain — atmospheric dust */}
      <div style={{
        position: 'absolute', inset: 0,
        opacity: cfg.grainAlpha,
        backgroundImage: `url("data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)'/%3E%3C/svg%3E")`,
        backgroundSize: '180px 180px',
        mixBlendMode: 'overlay',
        animation: 'marsGrain 8s steps(4) infinite',
        transition: 'opacity 1s ease',
      }} />

      {/* Keyframes */}
      <style>{`
        @keyframes marsDrift0 {
          0%, 100% { transform: translate(0, 0) scale(1); opacity: 1; }
          25% { transform: translate(18px, -30px) scale(1.3); opacity: 0.5; }
          50% { transform: translate(-10px, -55px) scale(0.8); opacity: 0.9; }
          75% { transform: translate(22px, -20px) scale(1.15); opacity: 0.4; }
        }
        @keyframes marsDrift1 {
          0%, 100% { transform: translate(0, 0) scale(1); opacity: 1; }
          30% { transform: translate(-20px, -15px) scale(0.85); opacity: 0.6; }
          60% { transform: translate(14px, -40px) scale(1.4); opacity: 0.3; }
          85% { transform: translate(-8px, -60px) scale(1.0); opacity: 0.7; }
        }
        @keyframes marsDrift2 {
          0%, 100% { transform: translate(0, 0) scale(1); opacity: 1; }
          33% { transform: translate(25px, -35px) scale(1.2); opacity: 0.4; }
          66% { transform: translate(-15px, -50px) scale(0.7); opacity: 0.8; }
        }
        @keyframes marsDrift3 {
          0%, 100% { transform: translate(0, 0) scale(0.9); opacity: 0.7; }
          20% { transform: translate(-12px, 18px) scale(1.3); opacity: 0.3; }
          40% { transform: translate(22px, -28px) scale(0.85); opacity: 1; }
          60% { transform: translate(-8px, -45px) scale(1.15); opacity: 0.25; }
          80% { transform: translate(10px, -12px) scale(1.0); opacity: 0.6; }
        }
        @keyframes marsDrift4 {
          0%, 100% { transform: translate(0, 0) scale(1); opacity: 0.8; }
          25% { transform: translate(30px, -10px) scale(1.1); opacity: 0.5; }
          50% { transform: translate(15px, -45px) scale(0.9); opacity: 1; }
          75% { transform: translate(-10px, -25px) scale(1.2); opacity: 0.35; }
        }
        @keyframes marsDrift5 {
          0%, 100% { transform: translate(0, 0) scale(1); opacity: 0.6; }
          20% { transform: translate(-18px, -20px) scale(1.25); opacity: 1; }
          50% { transform: translate(8px, -50px) scale(0.75); opacity: 0.4; }
          80% { transform: translate(-25px, -15px) scale(1.1); opacity: 0.8; }
        }
        @keyframes marsStreak {
          0% { transform: translateX(-100%); }
          100% { transform: translateX(calc(100vw + 100%)); }
        }
        @keyframes marsGrain {
          0% { transform: translate(0, 0); }
          25% { transform: translate(-5%, -5%); }
          50% { transform: translate(5%, 3%); }
          75% { transform: translate(-3%, 5%); }
          100% { transform: translate(0, 0); }
        }
      `}</style>
    </div>
  )
}

// Toggle button
export function ParticleToggle({ enabled, onToggle }) {
  return (
    <button
      onClick={onToggle}
      title={enabled ? 'Disable Mars atmosphere' : 'Enable Mars atmosphere'}
      style={{
        width: 28,
        height: 28,
        borderRadius: 'var(--radius-sm)',
        border: `1px solid ${enabled ? 'rgba(180,120,60,0.3)' : 'var(--border)'}`,
        background: enabled ? 'rgba(180,120,60,0.08)' : 'var(--bg-2)',
        color: enabled ? '#c4784a' : 'var(--fg-muted)',
        cursor: 'pointer',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        fontSize: 13,
        transition: 'all 0.2s ease',
        flexShrink: 0,
      }}
    >
      {enabled ? '\u2728' : '\u2727'}
    </button>
  )
}
