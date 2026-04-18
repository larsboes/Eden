import PlantSVG from './PlantSVG'
import MicroBar from './MicroBar'

const statusColors = { nominal: '#34d399', watch: '#f59e0b', warning: '#f59e0b', critical: '#ef4444' }

export default function PodCard({ zone, dashboardState }) {
  const isStressed = dashboardState === 'crisis'
  const color = statusColors[zone.status] || '#34d399'

  return (
    <div className="pod-card">
      {/* Pod header */}
      <div className="pod-card__header">
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span style={{ fontSize: 16 }}>{zone.icon}</span>
          <div>
            <div style={{ fontSize: 13, fontWeight: 600 }}>{zone.name}</div>
            <div style={{ fontSize: 10, color: 'var(--fg-muted)', fontFamily: 'var(--font-mono)' }}>
              Node:{zone.name.toLowerCase()} · {zone.pods} pods
            </div>
          </div>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span style={{
            fontSize: 20, fontWeight: 700, fontFamily: 'var(--font-mono)',
            color,
          }}>{zone.health}%</span>
          <span style={{
            width: 8, height: 8, borderRadius: '50%',
            background: color,
            boxShadow: `0 0 8px ${color}`,
            display: 'inline-block',
          }} />
        </div>
      </div>

      {/* Pod body — plant visualization */}
      <div className="pod-card__body">
        {/* Glass dome effect */}
        <div className="pod-card__dome">
          {zone.cropDetails?.map((crop, i) => (
            <div key={i} style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', flex: 1 }}>
              <PlantSVG
                crop={crop.name}
                bbch={crop.bbch}
                health={crop.health}
                stressed={isStressed}
                width={100}
                height={140}
              />
              <div style={{ fontSize: 9, fontFamily: 'var(--font-mono)', color: 'var(--fg-muted)', marginTop: 4, textAlign: 'center' }}>
                {crop.name}
              </div>
            </div>
          )) || (
            <PlantSVG crop={zone.crops[0]} bbch={zone.bbch} health={zone.health} stressed={isStressed} width={120} height={140} />
          )}
        </div>

        {/* Environment readings */}
        <div className="pod-card__sensors">
          <SensorPill label="TEMP" value={`${zone.temp}°C`} />
          <SensorPill label="HUM" value={`${zone.humidity}%`} />
          <SensorPill label="CO2" value={`${zone.co2}`} />
          <SensorPill label="LIGHT" value={`${zone.light}%`} />
          <SensorPill label="pH" value={zone.ph} />
          <SensorPill label="EC" value={zone.ec} />
          <SensorPill label="VPD" value={zone.vpd} />
          <SensorPill label="H2O" value={`${zone.waterUsage}L`} />
        </div>
      </div>

      {/* Pod footer — BBCH + companion */}
      <div className="pod-card__footer">
        <div>
          <span style={{ fontFamily: 'var(--font-mono)', fontSize: 10, color: 'var(--amber)' }}>BBCH {zone.bbch}</span>
          <span style={{ fontSize: 10, color: 'var(--fg-muted)', marginLeft: 6 }}>{zone.bbchLabel}</span>
        </div>
        <MicroBar value={zone.health} color={color} height={3} />
        {zone.cropDetails?.[0]?.companion && (
          <div style={{ fontSize: 9, color: 'var(--fg-muted)', marginTop: 4, fontStyle: 'italic' }}>
            {zone.cropDetails[0].companion}
          </div>
        )}
      </div>
    </div>
  )
}

function SensorPill({ label, value }) {
  return (
    <div className="sensor-pill">
      <span className="sensor-pill__label">{label}</span>
      <span className="sensor-pill__value">{value}</span>
    </div>
  )
}
