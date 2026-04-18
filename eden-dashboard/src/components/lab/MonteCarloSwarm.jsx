import { useRef, useEffect, useState, useCallback } from 'react'

// Each particle = one simulated future outcome
// They fall and cluster into loss zones, making the AI's exploration visible

export default function MonteCarloSwarm({ t, running, done }) {
  const canvasRef = useRef(null)
  const particlesRef = useRef([])
  const prevTRef = useRef(0)
  const [count, setCount] = useState(0)

  // Canvas resize handler
  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const resize = () => {
      const rect = canvas.getBoundingClientRect()
      canvas.width = rect.width * 2
      canvas.height = rect.height * 2
    }
    resize()
    window.addEventListener('resize', resize)
    return () => window.removeEventListener('resize', resize)
  }, [])

  // Reset state
  useEffect(() => {
    if (!running && !done) {
      particlesRef.current = []
      prevTRef.current = 0
      setCount(0)
      const canvas = canvasRef.current
      if (canvas) {
        const ctx = canvas.getContext('2d')
        ctx.clearRect(0, 0, canvas.width, canvas.height)
      }
    }
  }, [running, done])

  const draw = useCallback(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext('2d')
    const W = canvas.width
    const H = canvas.height
    const dpr = 2

    ctx.clearRect(0, 0, W, H)
    ctx.save()
    ctx.scale(dpr, dpr)

    const w = W / dpr
    const h = H / dpr

    // Zone backgrounds — subtle gradient zones
    const zones = [
      { start: 0, end: 0.16, color: 'rgba(34,197,94,0.04)' },
      { start: 0.16, end: 0.50, color: 'rgba(245,158,11,0.025)' },
      { start: 0.50, end: 1.0, color: 'rgba(239,68,68,0.03)' },
    ]
    zones.forEach(z => {
      ctx.fillStyle = z.color
      ctx.fillRect(z.start * w, 0, (z.end - z.start) * w, h)
    })

    // Zone dividers
    ctx.strokeStyle = 'rgba(255,255,255,0.04)'
    ctx.lineWidth = 0.5
    ;[0.16, 0.50].forEach(x => {
      ctx.beginPath()
      ctx.moveTo(x * w, 0)
      ctx.lineTo(x * w, h)
      ctx.stroke()
    })

    // Draw all particles
    const particles = particlesRef.current
    for (let i = 0; i < particles.length; i++) {
      const p = particles[i]
      ctx.beginPath()
      ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2)
      ctx.fillStyle = `rgba(${p.cr},${p.cg},${p.cb},${p.settled ? p.alpha * 0.85 : p.alpha})`
      ctx.fill()
      // Glow for settled particles
      if (p.settled) {
        ctx.beginPath()
        ctx.arc(p.x, p.y, p.r + 1, 0, Math.PI * 2)
        ctx.fillStyle = `rgba(${p.cr},${p.cg},${p.cb},${p.alpha * 0.12})`
        ctx.fill()
      }
    }

    ctx.restore()
  }, [])

  // Main animation: spawn + physics + draw
  useEffect(() => {
    if (!running && !done) return

    const canvas = canvasRef.current
    if (!canvas) return
    const W = canvas.width / 2
    const H = canvas.height / 2

    // Spawn particles based on progress delta
    const dt = t - prevTRef.current
    prevTRef.current = t

    if (running && dt > 0) {
      const spawnCount = Math.max(1, Math.floor(dt * 1400))

      for (let i = 0; i < spawnCount; i++) {
        // Each particle = one Monte Carlo simulation run
        // Randomly sample a strategy + noise
        const roll = Math.random()
        let loss, cr, cg, cb

        if (roll < 0.33) {
          // Strategy A outcomes: centered ~40%, spread 28-50%
          loss = 28 + Math.random() * 22
          cr = 239; cg = 68; cb = 68
        } else if (roll < 0.66) {
          // Strategy B outcomes: centered ~12%, spread 5-22%
          loss = 5 + Math.random() * 17
          cr = 245; cg = 158; cb = 11
        } else {
          // Strategy C outcomes: centered ~3%, spread 0.5-8%
          loss = 0.5 + Math.random() * 7.5
          cr = 34; cg = 197; cb = 94
        }

        // Map loss % to x position (0-50% range maps to full width)
        const xNorm = loss / 50
        const x = 8 + xNorm * (W - 16)

        // Settled particles stack from bottom with some jitter
        const settledCount = particlesRef.current.filter(
          p => p.settled && Math.abs(p.x - x) < 12
        ).length
        const stackHeight = Math.min(settledCount * 1.2, H * 0.7)
        const targetY = H - 6 - stackHeight - Math.random() * 4

        particlesRef.current.push({
          x: x + (Math.random() - 0.5) * 8,
          y: -4 - Math.random() * 30,
          targetY,
          vy: 2 + Math.random() * 3,
          vx: (Math.random() - 0.5) * 0.4,
          cr, cg, cb,
          r: 1.0 + Math.random() * 1.2,
          alpha: 0.3 + Math.random() * 0.5,
          settled: false,
        })
      }
    }

    // Physics step
    const particles = particlesRef.current
    for (let i = 0; i < particles.length; i++) {
      const p = particles[i]
      if (p.settled) continue
      p.y += p.vy
      p.x += p.vx
      p.vy += 0.08 // gravity
      if (p.y >= p.targetY) {
        p.y = p.targetY
        p.settled = true
      }
    }

    // Cap particle count for performance
    if (particles.length > 800) {
      particlesRef.current = particles.slice(-800)
    }

    draw()
    setCount(particlesRef.current.length)
  }, [t, running, done, draw])

  return (
    <div style={{ marginTop: 14 }}>
      {/* Header */}
      <div style={{
        display: 'flex', justifyContent: 'space-between', alignItems: 'center',
        marginBottom: 6,
      }}>
        <span style={{
          fontFamily: 'var(--font-mono)', fontSize: 9, fontWeight: 700,
          color: 'var(--fg-muted)', letterSpacing: 1.5,
        }}>
          MONTE CARLO OUTCOMES
        </span>
        {(running || done) && (
          <span style={{
            fontFamily: 'var(--font-mono)', fontSize: 9, fontWeight: 600,
            color: '#a78bfa',
            animation: running ? 'pulse 2s ease-in-out infinite' : 'none',
          }}>
            {count} simulations
          </span>
        )}
      </div>

      {/* Canvas */}
      <canvas
        ref={canvasRef}
        style={{
          width: '100%',
          height: 110,
          borderRadius: 6,
          background: 'var(--bg-2)',
          border: '1px solid var(--border)',
          display: 'block',
        }}
      />

      {/* Zone labels */}
      <div style={{
        display: 'flex', marginTop: 4, paddingLeft: 2, paddingRight: 2,
      }}>
        <div style={{ flex: '0 0 16%', textAlign: 'center' }}>
          <span style={{
            fontFamily: 'var(--font-mono)', fontSize: 7, fontWeight: 700,
            color: '#22c55e', letterSpacing: 0.5,
          }}>0-8% LOSS</span>
        </div>
        <div style={{ flex: '0 0 34%', textAlign: 'center' }}>
          <span style={{
            fontFamily: 'var(--font-mono)', fontSize: 7, fontWeight: 700,
            color: '#f59e0b', letterSpacing: 0.5,
          }}>8-25% LOSS</span>
        </div>
        <div style={{ flex: '0 0 50%', textAlign: 'center' }}>
          <span style={{
            fontFamily: 'var(--font-mono)', fontSize: 7, fontWeight: 700,
            color: '#ef4444', letterSpacing: 0.5,
          }}>25-50% LOSS</span>
        </div>
      </div>
    </div>
  )
}
