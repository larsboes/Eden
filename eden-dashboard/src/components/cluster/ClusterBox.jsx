import MicroBar from '../MicroBar'

const syncColors = {
  Synced:    '#34d399',
  Warning:   '#e8913a',
  OutOfSync: '#ef4444',
  Syncing:   '#60a5fa',
}

const healthLabels = {
  Healthy:      'Synced',
  'CME Incoming': 'Warning',
  Degraded:     'Degraded',
  Recovering:   'Recovering',
}

export default function ClusterBox({ cluster, sol, proposedCount = 0 }) {
  if (!cluster) return null

  const syncColor = syncColors[cluster.syncStatus] || '#34d399'
  const isCrisis = cluster.healthStatus === 'Degraded'
  const isAlert = cluster.healthStatus === 'CME Incoming'
  const isRecovery = cluster.healthStatus === 'Recovering'

  const healthPct = isCrisis ? 78 : isAlert ? 88 : isRecovery ? 91 : 92

  const statusLabel = healthLabels[cluster.healthStatus] || cluster.healthStatus

  const boxStyle = {
    width: 220,
    minHeight: 0,
    alignSelf: 'stretch',
    background: 'var(--bg-1)',
    border: `1px solid ${isCrisis ? 'rgba(239,68,68,0.25)' : isAlert ? 'rgba(232,145,58,0.2)' : 'var(--border)'}`,
    borderRadius: 'var(--radius-lg)',
    boxShadow: 'var(--card-shadow)',
    padding: '16px 14px',
    display: 'flex',
    flexDirection: 'column',
    gap: 12,
    transition: 'all 0.5s ease',
    flexShrink: 0,
  }

  const monoStyle = {
    fontFamily: 'var(--font-mono)',
  }

  const labelStyle = {
    ...monoStyle,
    fontSize: 10,
    fontWeight: 600,
    letterSpacing: 1,
    color: 'var(--fg-muted)',
    textTransform: 'uppercase',
  }

  const valueStyle = {
    ...monoStyle,
    fontSize: 13,
    fontWeight: 600,
    color: 'var(--fg-secondary)',
  }

  return (
    <div style={boxStyle}>
      {/* Cluster name + sync status */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span style={{
            ...monoStyle,
            fontSize: 18,
            fontWeight: 700,
            color: '#e8913a',
            letterSpacing: 2,
          }}>
            EDEN
          </span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <span style={{
            width: 8,
            height: 8,
            borderRadius: '50%',
            background: syncColor,
            boxShadow: `0 0 8px ${syncColor}`,
            display: 'inline-block',
            animation: isCrisis ? 'pulse 2s ease-in-out infinite' : 'none',
          }} />
          <span style={{
            ...monoStyle,
            fontSize: 10,
            fontWeight: 600,
            color: syncColor,
          }}>
            {statusLabel}
          </span>
        </div>
      </div>

      {/* Health bar */}
      <div>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: 4 }}>
          <span style={labelStyle}>Health</span>
          <span style={{ ...monoStyle, fontSize: 16, fontWeight: 700, color: syncColor }}>{healthPct}%</span>
        </div>
        <MicroBar value={healthPct} color={syncColor} height={4} />
      </div>

      {/* Divider */}
      <div style={{ height: 1, background: 'var(--border)' }} />

      {/* Node / Pod counts */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
        <div>
          <div style={labelStyle}>Nodes</div>
          <div style={valueStyle}>{cluster.nodes}</div>
        </div>
        <div>
          <div style={labelStyle}>Pods</div>
          <div style={valueStyle}>{cluster.activePods}/{cluster.pods}</div>
        </div>
      </div>

      {/* Flight Rules */}
      <div>
        <div style={labelStyle}>Flight Rules</div>
        <div style={valueStyle}>
          {cluster.flightRules} active
          {proposedCount > 0 && <span style={{ color: '#a855f7', fontSize: 11 }}> · {proposedCount} proposed</span>}
        </div>
      </div>

      {/* PDB Status */}
      <div>
        <div style={labelStyle}>PDB</div>
        <div style={valueStyle}>
          {cluster.pdb.currentUnavailable}/{cluster.pods} unav.
        </div>
        <div style={{ ...monoStyle, fontSize: 9, color: cluster.pdb.budget === 'OK' ? 'var(--fg-muted)' : '#ef4444' }}>
          Budget: {cluster.pdb.maxUnavailable} {cluster.pdb.budget === 'OK' ? '' : '- VIOLATED'}
        </div>
      </div>

      {/* DaemonSet */}
      <div>
        <div style={labelStyle}>DaemonSet</div>
        <div style={valueStyle}>{cluster.daemonSet.ready}/{cluster.daemonSet.desired} sensors</div>
      </div>

      {/* Reconcile age */}
      <div>
        <div style={labelStyle}>Reconcile</div>
        <div style={valueStyle}>{cluster.reconciledAt}</div>
      </div>

      {/* Divider */}
      <div style={{ height: 1, background: 'var(--border)' }} />

      {/* Crisis info */}
      {(isCrisis || isAlert) && (
        <div style={{
          padding: '8px 10px',
          background: isCrisis ? 'rgba(239,68,68,0.06)' : 'rgba(232,145,58,0.06)',
          borderRadius: 'var(--radius-sm)',
          border: `1px solid ${isCrisis ? 'rgba(239,68,68,0.15)' : 'rgba(232,145,58,0.12)'}`,
        }}>
          {isCrisis && (
            <>
              <div style={{ ...monoStyle, fontSize: 10, fontWeight: 700, color: '#ef4444', marginBottom: 4 }}>
                CME Active
              </div>
              <div style={{ ...monoStyle, fontSize: 9, color: 'var(--fg-secondary)', marginBottom: 2 }}>
                NetworkPolicy: {cluster.networkPolicy}
              </div>
            </>
          )}
          {cluster.strategy && (
            <div style={{ ...monoStyle, fontSize: 9, color: 'var(--fg-secondary)', marginBottom: 2 }}>
              Strategy: {cluster.strategy}
            </div>
          )}
          {isCrisis && (
            <div style={{ ...monoStyle, fontSize: 8, color: 'var(--fg-muted)', marginTop: 4, lineHeight: 1.4 }}>
              AdmissionCtrl:{'\n'}FR-CME-001 ADMITTED{'\n'}FR-CME-002 ADMITTED
            </div>
          )}
        </div>
      )}

      {/* Sol counter at bottom */}
      <div style={{ marginTop: 'auto', textAlign: 'center' }}>
        <div style={labelStyle}>Mission</div>
        <div style={{ display: 'flex', alignItems: 'baseline', justifyContent: 'center', gap: 4, marginTop: 2 }}>
          <span style={{ ...monoStyle, fontSize: 14, fontWeight: 700, color: 'var(--fg)' }}>Sol {sol}</span>
          <span style={{ ...monoStyle, fontSize: 10, color: 'var(--fg-muted)' }}>/450</span>
        </div>
        <MicroBar value={sol} max={450} color="#e8913a" height={3} />
      </div>
    </div>
  )
}
