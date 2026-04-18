import MicroBar from '../MicroBar'

const M = { fontFamily: 'var(--font-mono)' }

const STATUS_COLORS = {
  nominal: '#34d399', degraded: '#ef4444', critical: '#ef4444',
  standby: '#6b7280', warning: '#f59e0b',
}

// Mars environment details for hover tooltip (dynamic from props)
function getMarsDetail(mars, crisis) {
  if (!mars) {
    return crisis
      ? { title: 'Mars Exterior', rows: [['Surface', '-63\u00B0C'], ['Irradiance', '250 W/m\u00B2 (CME)'], ['Dust \u03C4', '0.8 (storm)'], ['Pressure', '6.1 hPa'], ['Status', 'STORM ACTIVE']] }
      : { title: 'Mars Exterior', rows: [['Surface', '-63\u00B0C'], ['Irradiance', '590 W/m\u00B2'], ['Dust \u03C4', '0.3'], ['Pressure', '6.1 hPa'], ['Ls', '215\u00B0 (dust season)']] }
  }
  return {
    title: 'Mars Exterior',
    rows: [
      ['Surface', `${Math.round(mars.exterior_temp)}\u00B0C`],
      ['Dome', `${Math.round(mars.dome_temp)}\u00B0C`],
      ['Irradiance', `${Math.round(mars.solar_irradiance)} W/m\u00B2`],
      ['Dust \u03C4', `${mars.dust_opacity?.toFixed(2)}`],
      ['Pressure', `${mars.pressure_hpa?.toFixed(1)} hPa`],
    ],
  }
}

// Detailed info shown on hover for each resource node
const NODE_DETAILS = {
  nominal: {
    solar:      { title: 'Solar Array', rows: [['Output', '4.2 kW'], ['Panels', '12 x 350W'], ['Efficiency', '94%'], ['Dust Coverage', '< 2%'], ['Angle', 'Auto-tracking']] },
    power:      { title: 'Power Grid', rows: [['Capacity', '5.0 kW'], ['Load', '3.94 kW (78%)'], ['To Desal', '1.8 kW'], ['To Lights', '1.2 kW'], ['To Heating', '0.6 kW'], ['Reserve', '0.34 kW']] },
    desal:      { title: 'Desalination Unit', rows: [['Rate', '120 L/sol'], ['Source', 'Subsurface brine'], ['Efficiency', '92%'], ['Filter Status', 'Clean'], ['Next Maint.', 'Sol 280']] },
    irrigation: { title: 'Irrigation System', rows: [['Zones Active', '4/4'], ['Daily Use', '88.7 L/sol'], ['Recycling', '65% captured'], ['Method', 'Drip + NFT'], ['Net Consumption', '31 L/sol']] },
    harvest:    { title: 'Harvest Output', rows: [['Cycle', 'Steady-state'], ['Total Yield', '1,282 kg est.'], ['Fresh Food Days', '420/450'], ['Next Harvest', 'Spinach Sol 252'], ['Calories/day', '362 kcal/person']] },
    crew:       { title: 'Crew Nutrition (4)', rows: [['Vitamin C', '133% surplus'], ['Iron', '112% (low bioavail.)'], ['Protein', '32% (rations: 68%)'], ['O\u2082 Contrib.', '14.2% of crew need'], ['Morale', 'Fresh food 23% boost']] },
  },
  crisis: {
    solar:      { title: 'Solar Array', rows: [['Output', '1.26 kW (-70%)'], ['Panels', 'Radiation damage risk'], ['Efficiency', '30%'], ['CME Impact', 'UV-B elevated'], ['Shields', 'ACTIVE']] },
    power:      { title: 'Power Grid', rows: [['Capacity', '5.0 kW'], ['Load', '2.25 kW (45%)'], ['Priority', 'Shields > Desal > Heat'], ['Lights', 'Minimum survival'], ['Reserve', 'DEPLETING']] },
    desal:      { title: 'Desalination Unit', rows: [['Rate', '36 L/sol (-70%)'], ['Pre-stockpiled', '580L in 48h'], ['Autonomy', '7.2 sols'], ['Deficit', '-64 L/sol'], ['Status', 'DEGRADED']] },
    irrigation: { title: 'Irrigation System', rows: [['Zones Active', '3/4 (Vitamin reduced)'], ['Daily Use', 'Rationed'], ['Recycling', 'Sealed (Zebra)'], ['Zone Isolation', 'ACTIVE'], ['Reserve Draw', '-64 L/sol']] },
    harvest:    { title: 'Harvest Output', rows: [['Status', 'PAUSED'], ['Pre-harvested', 'Spinach 1.9kg'], ['At Risk', 'Wheat (BBCH 60)'], ['Protected', 'Soybean, Potato'], ['Recovery Est.', '5 sols post-storm']] },
    crew:       { title: 'Crew Nutrition (4)', rows: [['Vitamin C', '128% (buffer 58 sols)'], ['Iron', '108% (Spinach secured)'], ['Protein', '-8% (Petrov on rations)'], ['O\u2082 Contrib.', '11.8% (lights dimmed)'], ['Status', 'Rations supplementing']] },
  },
}

export default function ResourceFlow({ flow, dashboardState, mars }) {
  if (!flow) return null
  const crisis = dashboardState === 'crisis'
  const details = NODE_DETAILS[crisis ? 'crisis' : 'nominal']
  const marsDetail = getMarsDetail(mars, crisis)

  // Mars environment status
  const marsStatus = crisis ? 'critical'
    : mars?.storm_active ? 'critical'
    : mars?.radiation_alert ? 'warning'
    : mars?.dust_opacity > 0.5 ? 'warning'
    : 'nominal'

  const marsValue = mars
    ? `${Math.round(mars.solar_irradiance)} W/m\u00B2`
    : crisis ? '250 W/m\u00B2' : '590 W/m\u00B2'

  const marsSub = mars
    ? `${Math.round(mars.exterior_temp)}\u00B0C \u00B7 \u03C4${mars.dust_opacity?.toFixed(1)}`
    : crisis ? '-63\u00B0C \u00B7 \u03C40.8' : '-63\u00B0C \u00B7 \u03C40.3'

  return (
    <div style={{
      padding: '16px 4px',
      borderTop: `1px solid ${crisis ? 'rgba(239,68,68,0.2)' : 'var(--border)'}`,
      borderBottom: `1px solid ${crisis ? 'rgba(239,68,68,0.2)' : 'var(--border)'}`,
      transition: 'all 0.5s',
    }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 14 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span style={{ ...M, fontSize: 11, fontWeight: 700, color: '#06b6d4', letterSpacing: 1.5 }}>RESOURCE FLOW</span>
          {crisis && <Tag label="DEGRADED" color="#ef4444" />}
        </div>
        <div style={{ ...M, fontSize: 8, color: 'var(--fg-muted)', display: 'flex', gap: 10 }}>
          {flow.ingress?.sources?.map(s => <span key={s}>{s}</span>)}
        </div>
      </div>

      {/* Main pipeline */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
        {/* Row 1: Main chain */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 0 }}>
          <Node k="mars" label="Mars" value={marsValue} sub={marsSub} status={marsStatus} icon="MRS" detail={marsDetail} />
          <Connector crisis={crisis} />
          <Node k="solar" label="Solar" value={flow.solar.value} status={flow.solar.status} icon="SOL" detail={details.solar} />
          <Connector crisis={crisis} />
          <Node k="power" label="Power Grid" value={flow.power.value} status={flow.power.status} icon="PWR" detail={details.power} />
          <Connector crisis={crisis} />
          <Node k="desal" label="Desalination" value={flow.desal.value} status={flow.desal.status} icon="H2O" detail={details.desal} />
          <Connector crisis={crisis} />
          <Node k="irrigation" label="Irrigation" value={flow.irrigation.value} status={flow.irrigation.status} icon="IRG" detail={details.irrigation} />
          <Connector crisis={crisis} />
          <Node k="harvest" label="Harvest" value={flow.harvest.value} status={flow.harvest.status} icon="HRV" detail={details.harvest} />
          <Connector crisis={crisis} />
          <Node k="crew" label="Crew (4)" value={`C:${flow.crew.vitC} Fe:${flow.crew.iron}`} sub={`O\u2082:${flow.crew.o2}`} status={flow.crew.status} icon="CRW" detail={details.crew} />
        </div>

        {/* Row 2: Power distribution branch */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, paddingLeft: 100 }}>
          <span style={{ ...M, fontSize: 8, color: 'var(--fg-muted)', letterSpacing: 1 }}>PWR</span>
          <Branch label="Lights" value={flow.lights.status === 'degraded' ? 'Min' : 'On'} status={flow.lights.status} />
          <Branch label="Heating" value={flow.heating.value} status={flow.heating.status} />
          <Branch label="Shields" value={flow.shields.value} status={flow.shields.status} />
          <Branch label="Battery" value={flow.battery.value} status={flow.battery.status} />
        </div>
      </div>
    </div>
  )
}

// Interactive service node with hover detail tooltip
function Node({ k, label, value, sub, status, icon, detail }) {
  const c = STATUS_COLORS[status] || '#34d399'
  const degraded = status === 'degraded' || status === 'critical'
  return (
    <div className="flow-node" style={{
      flex: '1 1 0', minWidth: 100, maxWidth: 180, position: 'relative',
      background: 'var(--bg-2)', border: `1px solid ${degraded ? c + '55' : 'var(--border)'}`,
      borderRadius: 10, padding: '12px 14px',
      display: 'flex', flexDirection: 'column', gap: 4,
      transition: 'all 0.25s ease', cursor: 'default',
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
        <span style={{
          ...M, fontSize: 8, fontWeight: 700, letterSpacing: 0.5,
          color: degraded ? c : 'var(--fg-muted)',
          background: degraded ? c + '15' : 'var(--bg-3)',
          padding: '2px 5px', borderRadius: 3,
        }}>{icon}</span>
        <span style={{ ...M, fontSize: 10, fontWeight: 600, color: 'var(--fg)', letterSpacing: 0.3 }}>{label}</span>
      </div>
      <div style={{ ...M, fontSize: 13, fontWeight: 700, color: degraded ? c : 'var(--fg-secondary)' }}>{value}</div>
      {sub && <div style={{ ...M, fontSize: 9, color: 'var(--fg-muted)' }}>{sub}</div>}
      <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
        <span style={{ width: 5, height: 5, borderRadius: '50%', background: c, boxShadow: `0 0 4px ${c}` }} />
        <span style={{ ...M, fontSize: 8, color: c, textTransform: 'uppercase' }}>{status}</span>
      </div>

      {/* Hover tooltip — CSS-only via .flow-node:hover */}
      {detail && (
        <div className="flow-node__tooltip">
          <div style={{ ...M, fontSize: 12, fontWeight: 700, color: 'var(--fg)', marginBottom: 10, letterSpacing: 0.5 }}>
            {detail.title}
          </div>
          {detail.rows.map(([label, val], i) => {
            const isAlert = val.includes('DEPLET') || val.includes('DEGRAD') || val.includes('PAUSED') || val.includes('-')
            return (
              <div key={i} style={{
                display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                padding: '4px 0', borderBottom: i < detail.rows.length - 1 ? '1px solid var(--border)' : 'none',
              }}>
                <span style={{ ...M, fontSize: 10, color: 'var(--fg-muted)' }}>{label}</span>
                <span style={{ ...M, fontSize: 10, fontWeight: 600, color: isAlert ? '#ef4444' : 'var(--fg-secondary)' }}>{val}</span>
              </div>
            )
          })}
          {/* Progress bar for nodes with percentage */}
          {status !== 'standby' && (
            <div style={{ marginTop: 6 }}>
              <MicroBar
                value={status === 'nominal' ? 90 : status === 'degraded' ? 30 : 60}
                color={c} height={3}
              />
            </div>
          )}
        </div>
      )}
    </div>
  )
}

function Branch({ label, value, status }) {
  const c = STATUS_COLORS[status] || 'var(--fg-muted)'
  const degraded = status === 'degraded' || status === 'critical'
  return (
    <div style={{
      padding: '6px 10px', background: 'var(--bg-2)',
      border: `1px solid ${degraded ? c + '44' : 'var(--border)'}`,
      borderRadius: 8, display: 'flex', alignItems: 'center', gap: 6, transition: 'all 0.25s ease',
    }}>
      <span style={{ width: 4, height: 4, borderRadius: '50%', background: c, boxShadow: `0 0 3px ${c}` }} />
      <span style={{ ...M, fontSize: 10, fontWeight: 600, color: 'var(--fg-secondary)' }}>{label}</span>
      <span style={{ ...M, fontSize: 10, fontWeight: 700, color: degraded ? c : 'var(--fg-muted)' }}>{value}</span>
    </div>
  )
}

function Connector({ crisis }) {
  const color = crisis ? 'rgba(239,68,68,0.35)' : 'rgba(52,211,153,0.25)'
  return (
    <div style={{ width: 20, flexShrink: 0, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
      <svg width="20" height="12" viewBox="0 0 20 12">
        <line x1="0" y1="6" x2="14" y2="6" stroke={color} strokeWidth="1.5" strokeDasharray={crisis ? '3 2' : 'none'} />
        <polygon points="14,3 20,6 14,9" fill={color} />
      </svg>
    </div>
  )
}

function Tag({ label, color }) {
  return (
    <span style={{
      ...M, fontSize: 8, fontWeight: 700, color,
      background: color + '14', border: `1px solid ${color}33`,
      borderRadius: 4, padding: '1px 6px', letterSpacing: 0.5,
    }}>{label}</span>
  )
}
