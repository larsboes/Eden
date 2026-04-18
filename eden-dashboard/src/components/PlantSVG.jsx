// Each crop gets a completely different silhouette — no shared skeleton.

export default function PlantSVG({ crop = 'Soybean', bbch = 50, health = 90, stressed = false, width = 120, height = 160 }) {
  const g = Math.min(bbch / 89, 1) // growth 0-1
  const cx = width / 2
  const gy = height - 28 // ground Y
  const opacity = stressed ? 0.45 : 0.75 + (health / 100) * 0.25
  const uid = crop.slice(0, 3)

  const renderer = RENDERERS[crop] || RENDERERS.Soybean

  return (
    <svg width={width} height={height} viewBox={`0 0 ${width} ${height}`}>
      <defs>
        <radialGradient id={`soil-${uid}`} cx="50%" cy="30%" r="60%">
          <stop offset="0%" stopColor="#a0764a" stopOpacity="0.7" />
          <stop offset="80%" stopColor="#7c5a33" stopOpacity="0.8" />
          <stop offset="100%" stopColor="#5c3d1e" stopOpacity="0.5" />
        </radialGradient>
        <style>{`@keyframes sw{0%,100%{transform:rotate(0)}50%{transform:rotate(1.2deg)}}`}</style>
      </defs>

      {/* Soil */}
      <ellipse cx={cx} cy={gy + 5} rx={width * 0.35} ry={8} fill={`url(#soil-${uid})`} />

      {/* Plant */}
      <g style={{ transformOrigin: `${cx}px ${gy}px`, animation: stressed ? 'none' : 'sw 5s ease-in-out infinite' }} opacity={opacity}>
        {renderer({ cx, gy, g, bbch, health, stressed, width, uid })}
      </g>

      {/* Health dot */}
      <circle cx={cx} cy={gy} r={2.5} fill={health > 70 ? '#22c55e' : health > 40 ? '#f59e0b' : '#ef4444'} opacity={0.5}>
        <animate attributeName="opacity" values="0.25;0.55;0.25" dur="3s" repeatCount="indefinite" />
      </circle>

      {/* Stress ring */}
      {stressed && (
        <circle cx={cx} cy={gy - g * 50 - 15} r={8} fill="none" stroke="#ef4444" strokeWidth={0.8} strokeDasharray="2 3" opacity={0.4}>
          <animate attributeName="opacity" values="0.2;0.5;0.2" dur="2s" repeatCount="indefinite" />
        </circle>
      )}
    </svg>
  )
}

// ─── SOYBEAN: Dense bushy canopy, trifoliate clusters ───────────────────────
function renderSoybean({ cx, gy, g, bbch }) {
  const h = 25 + g * 50
  const top = gy - h
  return (
    <g>
      {/* Thick main stem */}
      <path d={`M${cx},${gy} C${cx + 2},${gy - h * 0.4} ${cx - 2},${gy - h * 0.7} ${cx},${top}`}
        stroke="#3e7d2a" strokeWidth={2.5 + g} fill="none" strokeLinecap="round" />

      {/* Side branches — short, dense, angled up */}
      {g > 0.15 && Array.from({ length: Math.min(Math.floor(g * 5) + 1, 5) }, (_, i) => {
        const y = gy - h * ((i + 1) / 6)
        const side = i % 2 === 0 ? -1 : 1
        const bLen = 10 + g * 8
        return (
          <g key={i}>
            <path d={`M${cx},${y} Q${cx + side * bLen * 0.5},${y - 4} ${cx + side * bLen},${y - 2}`}
              stroke="#3e7d2a" strokeWidth={1.2} fill="none" />
            {/* Trifoliate leaf cluster: 3 rounded leaves */}
            <g transform={`translate(${cx + side * bLen},${y - 2})`}>
              <ellipse cx={0} cy={-6} rx={5 + g * 3} ry={4 + g * 2} fill="#2d8a3e" opacity={0.85} />
              <ellipse cx={-5} cy={-2} rx={4 + g * 2.5} ry={3.5 + g * 1.5} fill="#3a9e4a" opacity={0.75} transform="rotate(-20)" />
              <ellipse cx={5} cy={-2} rx={4 + g * 2.5} ry={3.5 + g * 1.5} fill="#3a9e4a" opacity={0.75} transform="rotate(20)" />
              {/* Center vein */}
              <line x1={0} y1={-2} x2={0} y2={-8} stroke="#1e6b2d" strokeWidth={0.4} opacity={0.3} />
            </g>
          </g>
        )
      })}

      {/* Dense canopy cloud at top */}
      {g > 0.4 && (
        <g>
          <ellipse cx={cx} cy={top + 5} rx={14 + g * 10} ry={10 + g * 7} fill="#2d8a3e" opacity={0.3} />
          <ellipse cx={cx - 5} cy={top + 2} rx={8 + g * 5} ry={6 + g * 4} fill="#3a9e4a" opacity={0.25} />
          <ellipse cx={cx + 6} cy={top + 4} rx={7 + g * 4} ry={5 + g * 3} fill="#22803a" opacity={0.2} />
        </g>
      )}

      {/* Flowers BBCH 60-69 */}
      {bbch >= 60 && bbch < 70 && (
        <g>
          {[[-8, 5], [6, 2], [-2, -3]].map(([dx, dy], i) => (
            <g key={i}>
              {[0, 72, 144, 216, 288].map((a, j) => (
                <circle key={j} cx={cx + dx + Math.cos(a * Math.PI / 180) * 3} cy={top + dy + Math.sin(a * Math.PI / 180) * 3}
                  r={1.5} fill="white" opacity={0.7} />
              ))}
              <circle cx={cx + dx} cy={top + dy} r={1.5} fill="#fbbf24" opacity={0.9} />
            </g>
          ))}
        </g>
      )}

      {/* Pods BBCH 70+ */}
      {bbch >= 70 && [[-10, 8], [8, 4], [-3, -2], [11, 12]].slice(0, Math.floor((bbch - 70) / 5) + 1).map(([dx, dy], i) => (
        <g key={i} transform={`rotate(${15 + i * 15} ${cx + dx} ${top + dy})`}>
          <path d={`M${cx + dx},${top + dy - 5} Q${cx + dx + 2.5},${top + dy} ${cx + dx},${top + dy + 5} Q${cx + dx - 2.5},${top + dy} ${cx + dx},${top + dy - 5}`}
            fill="#7cb342" opacity={0.85} />
        </g>
      ))}
    </g>
  )
}

// ─── LENTIL: Wispy, many tiny leaflets, tendrils, airy ─────────────────────
function renderLentil({ cx, gy, g, bbch }) {
  const h = 20 + g * 45
  const top = gy - h
  const numStems = g > 0.3 ? 3 : g > 0.1 ? 2 : 1
  return (
    <g>
      {/* Multiple thin stems fanning out */}
      {Array.from({ length: numStems }, (_, s) => {
        const spread = (s - (numStems - 1) / 2) * 8
        const stemTop = top + Math.abs(spread) * 0.5
        return (
          <g key={s}>
            <path d={`M${cx},${gy} Q${cx + spread * 0.3},${gy - h * 0.5} ${cx + spread},${stemTop}`}
              stroke="#4a7a3a" strokeWidth={1.2} fill="none" strokeLinecap="round" />

            {/* Tiny paired leaflets along each stem */}
            {g > 0.15 && Array.from({ length: Math.min(Math.floor(g * 6), 6) }, (_, i) => {
              const t = (i + 1) / 7
              const y = gy - h * t + Math.abs(spread) * t * 0.5
              const x = cx + spread * t
              const leafS = 2.5 + g * 2
              return (
                <g key={i}>
                  <ellipse cx={x - 4} cy={y} rx={leafS} ry={leafS * 0.5} fill="#4a9e5c" opacity={0.7} transform={`rotate(-15 ${x - 4} ${y})`} />
                  <ellipse cx={x + 4} cy={y} rx={leafS} ry={leafS * 0.5} fill="#4a9e5c" opacity={0.7} transform={`rotate(15 ${x + 4} ${y})`} />
                </g>
              )
            })}

            {/* Curling tendril at tip */}
            {g > 0.3 && (
              <path d={`M${cx + spread},${stemTop} Q${cx + spread + 5},${stemTop - 4} ${cx + spread + 3},${stemTop - 8} Q${cx + spread + 1},${stemTop - 10} ${cx + spread + 4},${stemTop - 12}`}
                stroke="#6aae6a" strokeWidth={0.6} fill="none" opacity={0.5} />
            )}
          </g>
        )
      })}

      {/* Flowers — tiny, delicate */}
      {bbch >= 60 && bbch < 70 && (
        <g>
          {[[-4, 3], [3, 0], [0, -5]].map(([dx, dy], i) => (
            <circle key={i} cx={cx + dx} cy={top + dy} r={2} fill="#c8b4e8" opacity={0.7} />
          ))}
        </g>
      )}

      {/* Tiny flat pods */}
      {bbch >= 70 && [[-6, 5], [5, 2], [-1, -3]].slice(0, Math.floor((bbch - 70) / 6) + 1).map(([dx, dy], i) => (
        <ellipse key={i} cx={cx + dx} cy={top + dy} rx={4} ry={2} fill="#8bc34a" opacity={0.8}
          transform={`rotate(${20 + i * 25} ${cx + dx} ${top + dy})`} />
      ))}
    </g>
  )
}

// ─── POTATO: Low, spreading, large dark leaves, tubers below ────────────────
function renderPotato({ cx, gy, g, bbch }) {
  const h = 18 + g * 38
  const top = gy - h
  return (
    <g>
      {/* Thick chunky stem */}
      <path d={`M${cx},${gy} C${cx + 3},${gy - h * 0.3} ${cx - 2},${gy - h * 0.6} ${cx + 1},${top}`}
        stroke="#5a8a3a" strokeWidth={3 + g * 1.5} fill="none" strokeLinecap="round" />

      {/* Large compound leaves — spread wide and droop */}
      {g > 0.12 && Array.from({ length: Math.min(Math.floor(g * 4) + 1, 4) }, (_, i) => {
        const y = gy - h * ((i + 1) / 5)
        const side = i % 2 === 0 ? -1 : 1
        const leafW = 12 + g * 10
        const leafH = 8 + g * 6
        return (
          <g key={i}>
            {/* Branch */}
            <path d={`M${cx},${y} Q${cx + side * leafW * 0.4},${y + 2} ${cx + side * leafW},${y + 5}`}
              stroke="#4a7a3a" strokeWidth={1.5} fill="none" />
            {/* Main large leaf — wide, irregular */}
            <path d={`M${cx + side * leafW},${y + 5}
              C${cx + side * (leafW + 6)},${y - leafH * 0.3} ${cx + side * (leafW - 2)},${y - leafH} ${cx + side * leafW * 0.6},${y - leafH * 0.5}
              C${cx + side * leafW * 0.4},${y - leafH * 0.2} ${cx + side * leafW * 0.5},${y + 3} ${cx + side * leafW},${y + 5}`}
              fill="#2e7d32" opacity={0.8} />
            {/* Side leaflet */}
            <ellipse cx={cx + side * leafW * 0.6} cy={y + 1} rx={5 + g * 3} ry={3.5 + g * 2}
              fill="#388e3c" opacity={0.6} transform={`rotate(${side * -10} ${cx + side * leafW * 0.6} ${y + 1})`} />
          </g>
        )
      })}

      {/* Small white/purple flowers BBCH 60-69 */}
      {bbch >= 60 && bbch < 70 && (
        <g>
          {[[-3, 0], [5, 3]].map(([dx, dy], i) => (
            <g key={i}>
              {[0, 72, 144, 216, 288].map((a, j) => (
                <circle key={j} cx={cx + dx + Math.cos(a * Math.PI / 180) * 3.5} cy={top + dy + Math.sin(a * Math.PI / 180) * 3.5}
                  r={2} fill="#e8d0f0" opacity={0.7} />
              ))}
              <circle cx={cx + dx} cy={top + dy} r={2} fill="#f9c74f" opacity={0.8} />
            </g>
          ))}
        </g>
      )}

      {/* Tubers underground */}
      {bbch > 35 && [[-13, 9], [10, 13], [0, 17], [-7, 15]].slice(0, Math.min(Math.floor((bbch - 35) / 12) + 1, 4)).map(([dx, dy], i) => (
        <g key={i}>
          <ellipse cx={cx + dx} cy={gy + dy} rx={6 + g * 3} ry={4.5 + g * 2}
            fill="#c49a5a" opacity={0.8} transform={`rotate(${i * 20 - 10} ${cx + dx} ${gy + dy})`} />
          <ellipse cx={cx + dx} cy={gy + dy} rx={5 + g * 2} ry={3.5 + g * 1.5}
            fill="#d4aa6a" opacity={0.4} transform={`rotate(${i * 20 - 10} ${cx + dx} ${gy + dy})`} />
          {/* Eyes */}
          <circle cx={cx + dx + 2} cy={gy + dy - 1.5} r={0.7} fill="#8a6a3a" opacity={0.4} />
          <circle cx={cx + dx - 2} cy={gy + dy + 1} r={0.5} fill="#8a6a3a" opacity={0.35} />
        </g>
      ))}
    </g>
  )
}

// ─── WHEAT: Tall single stalk, long drooping blades, golden ear ─────────────
function renderWheat({ cx, gy, g, bbch }) {
  const h = 30 + g * 60
  const top = gy - h
  return (
    <g>
      {/* Thin tall stalk — very vertical */}
      <line x1={cx} y1={gy} x2={cx} y2={top} stroke="#8a9a3a" strokeWidth={1.8 + g * 0.5} strokeLinecap="round" />
      {/* Node bumps */}
      {g > 0.2 && Array.from({ length: Math.floor(g * 3) + 1 }, (_, i) => {
        const y = gy - h * ((i + 1) / 5)
        return <ellipse key={i} cx={cx} cy={y} rx={2.5} ry={1.2} fill="#7a8a2a" opacity={0.5} />
      })}

      {/* Long arching blade leaves — signature wheat look */}
      {g > 0.1 && Array.from({ length: Math.min(Math.floor(g * 4) + 1, 5) }, (_, i) => {
        const y = gy - h * ((i + 1) / 5.5)
        const side = i % 2 === 0 ? -1 : 1
        const bladeLen = 18 + g * 15
        const droop = 8 + i * 3
        return (
          <g key={i}>
            {/* Blade as filled shape — long, narrow, curving down */}
            <path d={`M${cx},${y} Q${cx + side * bladeLen * 0.4},${y - 3} ${cx + side * bladeLen},${y + droop}
              L${cx + side * bladeLen * 0.98},${y + droop + 0.5}
              Q${cx + side * bladeLen * 0.35},${y - 1} ${cx},${y + 1.5} Z`}
              fill="#7a9a38" opacity={0.7 - i * 0.06} />
          </g>
        )
      })}

      {/* Wheat ear — the golden head */}
      {bbch > 40 && (() => {
        const earH = 6 + g * 16
        const earW = 3 + g * 2.5
        return (
          <g>
            {/* Ear body */}
            <path d={`M${cx},${top} Q${cx + earW},${top - earH * 0.3} ${cx + earW * 0.5},${top - earH}
              Q${cx},${top - earH - 2} ${cx - earW * 0.5},${top - earH}
              Q${cx - earW},${top - earH * 0.3} ${cx},${top}`}
              fill="#e8b830" opacity={0.9} />
            {/* Grain rows */}
            {Array.from({ length: Math.min(Math.floor(g * 6), 6) }, (_, i) => {
              const ey = top - earH * ((i + 1) / 7)
              const ew = earW * (1 - Math.abs((i + 1) / 7 - 0.5) * 1.2)
              return (
                <g key={i}>
                  <line x1={cx - ew} y1={ey} x2={cx + ew} y2={ey} stroke="#c8982a" strokeWidth={0.4} opacity={0.4} />
                </g>
              )
            })}
            {/* Awns (whiskers) */}
            {g > 0.5 && Array.from({ length: 4 }, (_, i) => {
              const ay = top - earH * ((i + 1) / 5)
              const side = i % 2 === 0 ? -1 : 1
              return <line key={i} x1={cx + side * earW * 0.5} y1={ay} x2={cx + side * (earW + 8)} y2={ay - 6}
                stroke="#d8a820" strokeWidth={0.5} opacity={0.5} />
            })}
          </g>
        )
      })()}
    </g>
  )
}

// ─── TOMATO: Vine, thick stem, large jagged leaves, red fruits ──────────────
function renderTomato({ cx, gy, g, bbch }) {
  const h = 25 + g * 50
  const top = gy - h
  return (
    <g>
      {/* Thick hairy stem — slight zigzag */}
      <path d={`M${cx},${gy} C${cx - 3},${gy - h * 0.25} ${cx + 4},${gy - h * 0.5} ${cx - 1},${gy - h * 0.75} C${cx - 3},${gy - h * 0.85} ${cx + 1},${gy - h * 0.95} ${cx},${top}`}
        stroke="#4a8a2e" strokeWidth={2.5 + g} fill="none" strokeLinecap="round" />

      {/* Large serrated/jagged compound leaves */}
      {g > 0.12 && Array.from({ length: Math.min(Math.floor(g * 4) + 1, 4) }, (_, i) => {
        const y = gy - h * ((i + 1) / 5)
        const side = i % 2 === 0 ? -1 : 1
        const lw = 14 + g * 10
        const lh = 10 + g * 6
        return (
          <g key={i}>
            <path d={`M${cx},${y} Q${cx + side * lw * 0.3},${y + 2} ${cx + side * lw * 0.8},${y + 3}`}
              stroke="#3a7a2a" strokeWidth={1} fill="none" />
            {/* Main leaf — jagged edges via zigzag path */}
            <path d={`M${cx + side * lw * 0.3},${y + 3}
              L${cx + side * lw * 0.5},${y - lh * 0.3}
              L${cx + side * lw * 0.65},${y - lh * 0.1}
              L${cx + side * lw * 0.8},${y - lh * 0.5}
              L${cx + side * lw * 0.9},${y - lh * 0.2}
              L${cx + side * lw},${y - lh * 0.4}
              Q${cx + side * lw * 0.85},${y + lh * 0.2} ${cx + side * lw * 0.5},${y + lh * 0.15}
              Q${cx + side * lw * 0.3},${y + lh * 0.1} ${cx + side * lw * 0.3},${y + 3}`}
              fill="#2e7d32" opacity={0.75} />
            {/* Smaller leaflet */}
            <ellipse cx={cx + side * lw * 0.45} cy={y - 2} rx={4 + g * 2} ry={3 + g * 1.5}
              fill="#388e3c" opacity={0.5} transform={`rotate(${side * 15} ${cx + side * lw * 0.45} ${y - 2})`} />
          </g>
        )
      })}

      {/* Yellow flowers BBCH 60-69 */}
      {bbch >= 60 && bbch < 70 && (
        <g>
          {[[-6, 5], [5, 0], [-2, -8]].map(([dx, dy], i) => (
            <g key={i}>
              {[0, 60, 120, 180, 240, 300].map((a, j) => (
                <ellipse key={j}
                  cx={cx + dx + Math.cos(a * Math.PI / 180) * 3}
                  cy={top + dy + Math.sin(a * Math.PI / 180) * 3}
                  rx={2} ry={1} fill="#fdd835" opacity={0.8}
                  transform={`rotate(${a} ${cx + dx + Math.cos(a * Math.PI / 180) * 3} ${top + dy + Math.sin(a * Math.PI / 180) * 3})`} />
              ))}
            </g>
          ))}
        </g>
      )}

      {/* Red tomato fruits BBCH 70+ */}
      {bbch >= 70 && [[-10, 10], [9, 5], [-4, -5], [12, 15]].slice(0, Math.floor((bbch - 70) / 4) + 1).map(([dx, dy], i) => {
        const r = 4 + g * 3
        return (
          <g key={i}>
            <circle cx={cx + dx} cy={top + dy} r={r} fill="#e53935" opacity={0.9} />
            {/* Calyx star */}
            <path d={`M${cx + dx},${top + dy - r + 1} L${cx + dx - 2.5},${top + dy - r - 1} L${cx + dx},${top + dy - r + 0.5} L${cx + dx + 2.5},${top + dy - r - 1} Z`}
              fill="#4caf50" opacity={0.7} />
            {/* Shine */}
            <circle cx={cx + dx - r * 0.3} cy={top + dy - r * 0.3} r={r * 0.25} fill="white" opacity={0.3} />
          </g>
        )
      })}
    </g>
  )
}

// ─── SPINACH: Low flat rosette, broad dark leaves, no visible stem ──────────
function renderSpinach({ cx, gy, g }) {
  const numLeaves = Math.min(Math.floor(g * 6) + 2, 8)
  const maxLen = 10 + g * 18
  return (
    <g>
      {/* Leaves radiate from center at ground level — flat, broad, dark */}
      {Array.from({ length: numLeaves }, (_, i) => {
        const angle = (i * (360 / numLeaves)) - 90
        const rad = (angle * Math.PI) / 180
        const len = maxLen * (0.7 + Math.sin(i * 1.5) * 0.3)
        const tipX = cx + Math.cos(rad) * len
        const tipY = gy - 8 - Math.sin(rad) * len * 0.35 - g * 6
        const ctrlX = cx + Math.cos(rad) * len * 0.5
        const ctrlY = gy - 8 - Math.sin(rad) * len * 0.25 - g * 4
        const w = 4 + g * 4

        // perpendicular offsets for leaf width
        const perpX = -Math.sin(rad) * w
        const perpY = Math.cos(rad) * w * 0.35

        return (
          <g key={i}>
            {/* Leaf blade — spoon-shaped */}
            <path d={`M${cx},${gy - 6}
              Q${ctrlX + perpX},${ctrlY + perpY} ${tipX},${tipY}
              Q${ctrlX - perpX},${ctrlY - perpY} ${cx},${gy - 6}`}
              fill={i % 2 === 0 ? '#1b5e20' : '#2e7d32'} opacity={0.8 - i * 0.03} />
            {/* Center vein */}
            <path d={`M${cx},${gy - 6} Q${ctrlX},${ctrlY} ${tipX},${tipY}`}
              stroke="#0d4a14" strokeWidth={0.5} fill="none" opacity={0.3} />
          </g>
        )
      })}

      {/* Center crown */}
      <circle cx={cx} cy={gy - 6 - g * 3} r={3 + g * 2} fill="#2e7d32" opacity={0.4} />
    </g>
  )
}

// ─── BASIL: Compact dome, square stem, opposite pairs of broad ovate leaves ─
function renderBasil({ cx, gy, g, bbch }) {
  const h = 18 + g * 40
  const top = gy - h
  return (
    <g>
      {/* Square-ish stem */}
      <path d={`M${cx},${gy} L${cx},${top}`} stroke="#4a8a3a" strokeWidth={2 + g * 0.8} strokeLinecap="round" />

      {/* Opposite leaf pairs — progressively larger toward middle */}
      {g > 0.1 && Array.from({ length: Math.min(Math.floor(g * 5) + 1, 5) }, (_, i) => {
        const y = gy - h * ((i + 1) / 6)
        const leafS = 5 + g * 7 - Math.abs(i - 2) * 2.5 // largest in middle
        return (
          <g key={i}>
            {[-1, 1].map(side => (
              <g key={side}>
                {/* Short petiole */}
                <line x1={cx} y1={y} x2={cx + side * (leafS + 3)} y2={y - 1} stroke="#3a7a2a" strokeWidth={0.8} />
                {/* Ovate leaf — wide rounded */}
                <path d={`M${cx + side * (leafS + 3)},${y - 1}
                  Q${cx + side * (leafS + 8)},${y - leafS * 0.7} ${cx + side * (leafS + 4)},${y - leafS * 1.2}
                  Q${cx + side * (leafS + 1)},${y - leafS * 1.4} ${cx + side * leafS * 0.7},${y - leafS * 0.8}
                  Q${cx + side * leafS * 0.4},${y - leafS * 0.2} ${cx + side * (leafS + 3)},${y - 1}`}
                  fill={i % 2 === 0 ? '#43a047' : '#388e3c'} opacity={0.8} />
                {/* Leaf vein */}
                <line x1={cx + side * (leafS + 3)} y1={y - 1} x2={cx + side * (leafS + 3)} y2={y - leafS * 1.1}
                  stroke="#2e7d32" strokeWidth={0.35} opacity={0.3} />
              </g>
            ))}
          </g>
        )
      })}

      {/* Flower spike at top BBCH 60+ */}
      {bbch >= 60 && (
        <g>
          {Array.from({ length: 3 }, (_, i) => (
            <g key={i}>
              <circle cx={cx - 2} cy={top - 2 - i * 4} r={1.5} fill="white" opacity={0.6} />
              <circle cx={cx + 2} cy={top - 2 - i * 4} r={1.5} fill="white" opacity={0.6} />
            </g>
          ))}
        </g>
      )}
    </g>
  )
}

// ─── MICROGREENS: Dense forest of tiny sprouts ──────────────────────────────
function renderMicrogreens({ cx, gy, g, width }) {
  const numSprouts = Math.min(Math.floor(g * 12) + 4, 16)
  const spread = width * 0.3
  // Use deterministic positions based on index
  return (
    <g>
      {Array.from({ length: numSprouts }, (_, i) => {
        const x = cx + (((i * 7 + 3) % 13) - 6) / 6 * spread
        const stemH = 8 + g * 20 + ((i * 3) % 7) * 2
        const lean = ((i * 5) % 9 - 4) * 1.5
        const topY = gy - stemH
        return (
          <g key={i}>
            {/* Thin stem */}
            <path d={`M${x},${gy - 2} Q${x + lean * 0.5},${gy - stemH * 0.5} ${x + lean},${topY}`}
              stroke="#81c784" strokeWidth={0.8 + g * 0.3} fill="none" strokeLinecap="round" />
            {/* Cotyledon pair — small round */}
            <ellipse cx={x + lean - 3} cy={topY} rx={2.5 + g * 1.5} ry={1.8 + g}
              fill={i % 3 === 0 ? '#a5d6a7' : i % 3 === 1 ? '#81c784' : '#66bb6a'} opacity={0.8}
              transform={`rotate(-25 ${x + lean - 3} ${topY})`} />
            <ellipse cx={x + lean + 3} cy={topY} rx={2.5 + g * 1.5} ry={1.8 + g}
              fill={i % 3 === 0 ? '#66bb6a' : i % 3 === 1 ? '#a5d6a7' : '#81c784'} opacity={0.8}
              transform={`rotate(25 ${x + lean + 3} ${topY})`} />
          </g>
        )
      })}
    </g>
  )
}

const RENDERERS = {
  Soybean: renderSoybean,
  Lentil: renderLentil,
  Potato: renderPotato,
  Wheat: renderWheat,
  Tomato: renderTomato,
  Spinach: renderSpinach,
  Basil: renderBasil,
  Microgreens: renderMicrogreens,
}
