export default function EventStream({ events, maxVisible = 6 }) {
  if (!events || events.length === 0) return null

  const monoStyle = { fontFamily: 'var(--font-mono)' }

  const typeColor = (type) => type === 'Warning' ? '#f59e0b' : '#34d399'

  const hasWarnings = events.some((e) => e.type === 'Warning')

  return (
    <div style={{
      background: 'var(--bg-1)',
      border: `1px solid ${hasWarnings ? 'rgba(245,158,11,0.12)' : 'var(--border)'}`,
      borderRadius: 'var(--radius-lg)',
      boxShadow: 'var(--card-shadow)',
      padding: '18px 20px',
      display: 'flex',
      flexDirection: 'column',
      gap: 10,
      transition: 'all 0.5s ease',
    }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'baseline', gap: 8 }}>
        <span style={{
          ...monoStyle,
          fontSize: 12,
          fontWeight: 700,
          color: '#f59e0b',
          letterSpacing: 1.5,
        }}>
          EVENTS
        </span>
        <span style={{
          ...monoStyle,
          fontSize: 10,
          color: 'var(--fg-muted)',
          letterSpacing: 0.5,
        }}>
          kubectl get events
        </span>
      </div>

      {/* Column headers */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: '40px 60px 120px 110px 1fr',
        gap: 0,
        padding: '0 0 6px 0',
        borderBottom: '1px solid var(--border)',
      }}>
        {['AGE', 'TYPE', 'REASON', 'OBJECT', 'MESSAGE'].map((col) => (
          <span key={col} style={{
            ...monoStyle,
            fontSize: 9,
            fontWeight: 700,
            letterSpacing: 1,
            color: 'var(--fg-muted)',
            textTransform: 'uppercase',
            textAlign: col === 'AGE' ? 'right' : 'left',
            paddingRight: col === 'AGE' ? 4 : 0,
          }}>
            {col}
          </span>
        ))}
      </div>

      {/* Event rows (scrollable) */}
      <div style={{
        maxHeight: maxVisible * 24,
        overflowY: 'auto',
        display: 'flex',
        flexDirection: 'column',
        gap: 0,
      }}>
        {events.map((evt, i) => {
          const isWarning = evt.type === 'Warning'
          return (
            <div
              key={`${evt.reason}-${evt.age}-${i}`}
              style={{
                display: 'grid',
                gridTemplateColumns: '40px 60px 120px 110px 1fr',
                gap: 0,
                padding: '5px 0',
                background: isWarning ? 'rgba(245,158,11,0.04)' : 'transparent',
                borderRadius: 2,
                alignItems: 'baseline',
                transition: 'background 0.3s ease',
              }}
            >
              {/* AGE */}
              <span style={{
                ...monoStyle,
                fontSize: 11,
                color: 'var(--fg-muted)',
                textAlign: 'right',
                paddingRight: 4,
              }}>
                {evt.age}
              </span>

              {/* TYPE */}
              <span style={{
                ...monoStyle,
                fontSize: 11,
                fontWeight: 700,
                color: typeColor(evt.type),
              }}>
                {evt.type}
              </span>

              {/* REASON */}
              <span style={{
                ...monoStyle,
                fontSize: 11,
                fontWeight: 700,
                color: 'var(--fg)',
                letterSpacing: 0.3,
                overflow: 'hidden',
                textOverflow: 'ellipsis',
                whiteSpace: 'nowrap',
              }}>
                {evt.reason}
              </span>

              {/* OBJECT */}
              <span style={{
                ...monoStyle,
                fontSize: 11,
                color: 'var(--fg-muted)',
                overflow: 'hidden',
                textOverflow: 'ellipsis',
                whiteSpace: 'nowrap',
              }}>
                {evt.object}
              </span>

              {/* MESSAGE */}
              <span style={{
                ...monoStyle,
                fontSize: 11,
                color: 'var(--fg-secondary)',
                overflow: 'hidden',
                textOverflow: 'ellipsis',
                whiteSpace: 'nowrap',
              }}>
                {evt.message}
              </span>
            </div>
          )
        })}
      </div>
    </div>
  )
}
