const statusColors = {
  nominal:  '#34d399',
  warning:  '#f59e0b',
  critical: '#ef4444',
}

export default function ConnectorLine({ status = 'nominal', animated = false, width = 48, height = 2 }) {
  const color = statusColors[status] || '#34d399'
  const svgHeight = Math.max(height + 8, 12)

  const animatedStyle = animated ? {
    animation: `connector-flow-${status} 1.5s linear infinite`,
  } : {}

  return (
    <svg
      width={width}
      height={svgHeight}
      viewBox={`0 0 ${width} ${svgHeight}`}
      style={{
        display: 'block',
        flexShrink: 0,
        overflow: 'visible',
      }}
    >
      <defs>
        <linearGradient id={`conn-grad-${status}`} x1="0" y1="0" x2="1" y2="0">
          <stop offset="0%" stopColor={color} stopOpacity="0.3" />
          <stop offset="50%" stopColor={color} stopOpacity="1" />
          <stop offset="100%" stopColor={color} stopOpacity="0.3" />
        </linearGradient>
        <style>{`
          @keyframes connector-flow-nominal {
            0% { stroke-dashoffset: 16; }
            100% { stroke-dashoffset: 0; }
          }
          @keyframes connector-flow-warning {
            0% { stroke-dashoffset: 16; }
            100% { stroke-dashoffset: 0; }
          }
          @keyframes connector-flow-critical {
            0% { stroke-dashoffset: 16; }
            100% { stroke-dashoffset: 0; }
          }
        `}</style>
      </defs>

      {/* Background track */}
      <line
        x1={0}
        y1={svgHeight / 2}
        x2={width}
        y2={svgHeight / 2}
        stroke={color}
        strokeWidth={1}
        strokeOpacity={0.15}
      />

      {/* Main connector line */}
      <line
        x1={0}
        y1={svgHeight / 2}
        x2={width}
        y2={svgHeight / 2}
        stroke={`url(#conn-grad-${status})`}
        strokeWidth={animated ? 2 : 1.5}
        strokeDasharray={animated ? '6 10' : 'none'}
        style={animatedStyle}
        strokeLinecap="round"
      />

      {/* Arrowhead at the end */}
      <polygon
        points={`${width - 6},${svgHeight / 2 - 3} ${width},${svgHeight / 2} ${width - 6},${svgHeight / 2 + 3}`}
        fill={color}
        opacity={0.7}
      />

      {/* Glow dot at start */}
      <circle
        cx={0}
        cy={svgHeight / 2}
        r={2.5}
        fill={color}
        opacity={0.5}
      />
    </svg>
  )
}
