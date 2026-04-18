import { useState } from 'react'

export default function Panel({ title, icon, color = '#e8913a', defaultOpen = true, badge, collapsible = true, children }) {
  const [open, setOpen] = useState(defaultOpen)

  return (
    <div className="eden-card" style={{ overflow: 'hidden' }}>
      {collapsible ? (
        <button
          onClick={() => setOpen(!open)}
          style={{
            width: '100%',
            display: 'flex',
            alignItems: 'center',
            gap: 8,
            padding: '10px 14px',
            background: 'none',
            border: 'none',
            borderBottom: open ? '1px solid var(--border)' : 'none',
            cursor: 'pointer',
            color: 'inherit',
            fontFamily: 'inherit',
            transition: 'border-color 0.3s',
          }}
        >
          <PanelHeader icon={icon} title={title} color={color} badge={badge} />
          <span style={{
            marginLeft: badge ? 8 : 'auto',
            fontSize: 10,
            color: 'var(--fg-muted)',
            transition: 'transform 0.2s',
            transform: open ? 'rotate(0)' : 'rotate(-90deg)',
            display: 'inline-block',
          }}>▼</span>
        </button>
      ) : (
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: 8,
          padding: '10px 14px',
          borderBottom: '1px solid var(--border)',
        }}>
          <PanelHeader icon={icon} title={title} color={color} badge={badge} />
        </div>
      )}
      {open && (
        <div style={{ padding: 14 }}>
          {children}
        </div>
      )}
    </div>
  )
}

function PanelHeader({ icon, title, color, badge }) {
  return (
    <>
      <span style={{ fontSize: 14 }}>{icon}</span>
      <span style={{
        fontFamily: 'var(--font-mono)',
        fontSize: 10,
        fontWeight: 700,
        letterSpacing: 2,
        textTransform: 'uppercase',
        color,
      }}>{title}</span>
      {badge && (
        <span style={{
          marginLeft: 'auto',
          fontFamily: 'var(--font-mono)',
          fontSize: 10,
          fontWeight: 600,
          padding: '2px 8px',
          borderRadius: 3,
          background: `${color}22`,
          color,
        }}>{badge}</span>
      )}
    </>
  )
}
