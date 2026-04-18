import { useRef } from 'react'
import NeuralPathways from './NeuralPathways'

// Holographic / digital twin aesthetic overlay.
// Adds scanlines, grid, shimmer, and ambient neural pathways.
// Wraps pod cards in Lab view to visually distinguish them from Production.

let _idCounter = 0

export default function DigitalTwinOverlay({ children, active = true }) {
  const idRef = useRef(`dt-${_idCounter++}`)
  const id = idRef.current

  if (!active) return children

  return (
    <div style={{ position: 'relative', overflow: 'hidden' }}>
      {children}

      {/* Ambient neural pathways — AI always monitoring */}
      <div style={{
        position: 'absolute',
        top: '25%', left: '50%',
        transform: 'translateX(-50%)',
        width: 120, height: 140,
        pointerEvents: 'none', zIndex: 2,
      }}>
        <NeuralPathways ambient width={120} height={140} id={id} />
      </div>

      {/* Scanlines */}
      <div style={{
        position: 'absolute', inset: 0, pointerEvents: 'none', zIndex: 3,
        background: `repeating-linear-gradient(
          0deg,
          transparent,
          transparent 2px,
          rgba(167,139,250,0.015) 2px,
          rgba(167,139,250,0.015) 4px
        )`,
        mixBlendMode: 'screen',
      }} />

      {/* Grid pattern */}
      <div style={{
        position: 'absolute', inset: 0, pointerEvents: 'none', zIndex: 3,
        backgroundImage: `
          linear-gradient(rgba(167,139,250,0.04) 1px, transparent 1px),
          linear-gradient(90deg, rgba(167,139,250,0.04) 1px, transparent 1px)
        `,
        backgroundSize: '20px 20px',
      }} />

      {/* Holographic shimmer — sweeping light */}
      <div style={{
        position: 'absolute', inset: 0, pointerEvents: 'none', zIndex: 4,
        background: 'linear-gradient(105deg, transparent 40%, rgba(167,139,250,0.04) 45%, rgba(96,165,250,0.03) 50%, transparent 55%)',
        backgroundSize: '200% 100%',
        animation: 'dtShimmer 6s ease-in-out infinite',
      }} />

      {/* Top edge holographic line */}
      <div style={{
        position: 'absolute', top: 0, left: 0, right: 0, height: 1, zIndex: 5,
        pointerEvents: 'none',
        background: 'linear-gradient(90deg, transparent 10%, rgba(167,139,250,0.3) 30%, rgba(96,165,250,0.2) 70%, transparent 90%)',
        animation: 'dtEdgePulse 4s ease-in-out infinite',
      }} />

      {/* Corner markers — HUD-style */}
      {[
        { top: 4, left: 4 },
        { top: 4, right: 4 },
        { bottom: 4, left: 4 },
        { bottom: 4, right: 4 },
      ].map((pos, i) => (
        <div key={i} style={{
          position: 'absolute', ...pos, zIndex: 5, pointerEvents: 'none',
          width: 8, height: 8,
          borderTop: i < 2 ? '1px solid rgba(167,139,250,0.25)' : 'none',
          borderBottom: i >= 2 ? '1px solid rgba(167,139,250,0.25)' : 'none',
          borderLeft: i % 2 === 0 ? '1px solid rgba(167,139,250,0.25)' : 'none',
          borderRight: i % 2 === 1 ? '1px solid rgba(167,139,250,0.25)' : 'none',
        }} />
      ))}

      {/* VIRTUAL tag */}
      <div style={{
        position: 'absolute', top: 6, right: 10, zIndex: 6, pointerEvents: 'none',
        fontFamily: 'var(--font-mono)', fontSize: 7, fontWeight: 700,
        letterSpacing: 2, color: 'rgba(167,139,250,0.35)',
      }}>
        VIRTUAL
      </div>

      <style>{`
        @keyframes dtShimmer {
          0% { background-position: 200% 0; }
          100% { background-position: -200% 0; }
        }
        @keyframes dtEdgePulse {
          0%, 100% { opacity: 0.4; }
          50% { opacity: 1; }
        }
      `}</style>
    </div>
  )
}
