export default function MicroBar({ value, max = 100, color = '#e8913a', height = 6, warn, crit }) {
  let barColor = color
  const pct = (value / max) * 100
  if (crit && pct < crit) barColor = '#ef4444'
  else if (warn && pct < warn) barColor = '#f59e0b'

  return (
    <div style={{ width: '100%', height, background: 'var(--bg-3)', borderRadius: height / 2, overflow: 'hidden' }}>
      <div style={{
        width: `${Math.min(pct, 100)}%`,
        height: '100%',
        background: barColor,
        borderRadius: height / 2,
        transition: 'width 1s ease, background 0.5s',
      }} />
    </div>
  )
}
