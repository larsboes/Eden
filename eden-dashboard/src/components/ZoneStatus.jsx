import MicroBar from './MicroBar'

const statusColors = { nominal: '#34d399', watch: '#f59e0b', warning: '#f59e0b', critical: '#ef4444' }

export default function ZoneStatus({ zones }) {
  return (
    <div style={{ display: 'grid', gridTemplateColumns: `repeat(${zones.length}, 1fr)`, gap: 8 }}>
      {zones.map(z => (
        <div
          key={z.id}
          className="zone-card"
          style={{
            borderColor: z.status !== 'nominal' ? statusColors[z.status] + '33' : undefined,
          }}
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
              <span style={{ fontSize: 14 }}>{z.icon}</span>
              <span style={{ fontSize: 12, fontWeight: 600 }}>{z.name}</span>
            </div>
            <span style={{
              width: 7, height: 7, borderRadius: '50%',
              background: statusColors[z.status],
              boxShadow: `0 0 6px ${statusColors[z.status]}`,
              display: 'inline-block',
            }} />
          </div>

          <MicroBar value={z.health} color={statusColors[z.status]} height={4} />

          <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 6 }}>
            <span style={{ fontSize: 10, color: 'var(--fg-muted)', fontFamily: 'var(--font-mono)' }}>
              {z.health}% · BBCH {z.bbch}
            </span>
            <span style={{ fontSize: 10, color: 'var(--fg-muted)', fontFamily: 'var(--font-mono)' }}>
              {z.activePods}/{z.pods}
            </span>
          </div>

          {/* CSS-only tooltip — no React state, no re-renders on hover */}
          <div className="zone-tooltip">
            <div style={{ fontSize: 11, fontWeight: 600, marginBottom: 8, color: 'var(--fg)' }}>
              {z.icon} {z.name} — {z.crops.join(', ')}
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '4px 16px', fontSize: 10, fontFamily: 'var(--font-mono)' }}>
              <SensorRow label="Temp" value={`${z.temp}°C`} />
              <SensorRow label="Humidity" value={`${z.humidity}%`} />
              <SensorRow label="Light" value={`${z.light}%`} />
              <SensorRow label="CO2" value={`${z.co2} ppm`} />
              <SensorRow label="pH" value={z.ph} />
              <SensorRow label="VPD" value={`${z.vpd} kPa`} />
              <SensorRow label="EC" value={`${z.ec} mS/cm`} />
              <SensorRow label="Water" value={`${z.waterUsage} L/sol`} />
            </div>
            <div style={{ marginTop: 8, fontSize: 9, color: 'var(--fg-muted)', fontFamily: 'var(--font-mono)' }}>
              BBCH {z.bbch} — {z.bbchLabel}
            </div>
          </div>
        </div>
      ))}
    </div>
  )
}

function SensorRow({ label, value }) {
  return (
    <div style={{ display: 'flex', justifyContent: 'space-between' }}>
      <span style={{ color: 'var(--fg-muted)' }}>{label}</span>
      <span style={{ color: 'var(--fg-secondary)', fontWeight: 500 }}>{value}</span>
    </div>
  )
}
