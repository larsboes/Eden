/**
 * EDEN Dashboard — beautiful structured logging via pino (browser).
 *
 * Enterprise-grade structured logging with styled console output.
 * Each module gets its own color-coded badge in the browser console.
 *
 * Usage:
 *   import { logger, apiLog, sseLog, stateLog } from '../lib/logger'
 *   apiLog.info({ msg: 'poll_success', latency_ms: 42, zones: 4 })
 *   sseLog.warn({ msg: 'reconnecting', attempt: 3 })
 */
import pino from 'pino'

const LOG_LEVEL = import.meta.env.VITE_LOG_LEVEL || (import.meta.env.DEV ? 'debug' : 'info')

// ── Beautiful styled console output ─────────────────────────────────────

const MODULE_STYLES = {
  api:   { badge: '🛰️  API', color: '#06b6d4', bg: '#083344' },
  sse:   { badge: '📡 SSE', color: '#a78bfa', bg: '#1e1b4b' },
  state: { badge: '🔄 STATE', color: '#f59e0b', bg: '#451a03' },
  ui:    { badge: '🖱️  UI', color: '#ec4899', bg: '#500724' },
  eden:  { badge: '🌱 EDEN', color: '#34d399', bg: '#022c22' },
}

const LEVEL_ICONS = {
  10: '🔬', // trace
  20: '🐛', // debug
  30: '🌱', // info
  40: '⚠️',  // warn
  50: '🔥', // error
  60: '💀', // fatal
}

const LEVEL_COLORS = {
  10: '#6b7280', // trace - gray
  20: '#8b5cf6', // debug - purple
  30: '#34d399', // info - green
  40: '#f59e0b', // warn - amber
  50: '#ef4444', // error - red
  60: '#dc2626', // fatal - bright red
}

/**
 * Custom pino browser write function — produces beautiful styled console output.
 *
 * Example output (in browser console):
 *   🛰️  API  [INFO] poll_success  latency_ms=12 zones=4
 *   📡 SSE  [WARN] reconnecting  attempt=3
 */
function edenWrite(o) {
  const level = o.level || 30
  const module = o.module || 'eden'
  const msg = o.msg || ''
  const style = MODULE_STYLES[module] || MODULE_STYLES.eden
  const icon = LEVEL_ICONS[level] || '📋'
  const levelColor = LEVEL_COLORS[level] || '#6b7280'

  // Extract payload (remove pino internals)
  const payload = { ...o }
  delete payload.level
  delete payload.time
  delete payload.msg
  delete payload.module
  delete payload.app
  delete payload.env

  // Build key=value string
  const kvParts = Object.entries(payload)
    .filter(([k]) => !k.startsWith('_'))
    .map(([k, v]) => `${k}=${typeof v === 'object' ? JSON.stringify(v) : v}`)
  const kvStr = kvParts.length ? '  ' + kvParts.join('  ') : ''

  // Level label
  const levelNames = { 10: 'TRACE', 20: 'DEBUG', 30: 'INFO', 40: 'WARN', 50: 'ERROR', 60: 'FATAL' }
  const levelName = levelNames[level] || 'LOG'

  // Styled console output with CSS
  const badgeCSS = `background:${style.bg};color:${style.color};padding:2px 6px;border-radius:3px;font-weight:bold;font-size:11px`
  const levelCSS = `color:${levelColor};font-weight:bold;font-size:11px`
  const msgCSS = `color:#e2e8f0;font-weight:600;font-size:11px`
  const kvCSS = `color:#94a3b8;font-size:11px`
  const timeCSS = `color:#475569;font-size:10px`

  const ts = new Date().toISOString().slice(11, 19)

  const consoleFn = level >= 50 ? console.error
    : level >= 40 ? console.warn
    : level >= 30 ? console.info
    : console.debug

  consoleFn(
    `%c${ts}%c %c${style.badge}%c %c${levelName}%c ${icon} %c${msg}%c${kvStr}`,
    timeCSS, '',
    badgeCSS, '',
    levelCSS, '',
    msgCSS,
    kvCSS,
  )

  // Also log the full object for expandable inspection in DevTools
  if (Object.keys(payload).length > 0 && level >= 40) {
    consoleFn('  ↳ details:', payload)
  }
}

/**
 * Root logger — all child loggers inherit from this.
 *
 * Browser mode: beautiful styled console output.
 * In production, also ships warn+ logs to backend via sendBeacon.
 */
export const logger = pino({
  level: LOG_LEVEL,
  browser: {
    asObject: true,
    write: {
      trace: edenWrite,
      debug: edenWrite,
      info: edenWrite,
      warn: edenWrite,
      error: edenWrite,
      fatal: edenWrite,
    },
    transmit: import.meta.env.PROD
      ? {
          level: 'warn',
          send(_level, logEvent) {
            const body = JSON.stringify(logEvent)
            const api = import.meta.env.VITE_EDEN_API || 'http://localhost:8000'
            navigator.sendBeacon?.(`${api}/api/logs`, body)
          },
        }
      : undefined,
  },
  base: {
    app: 'eden-dashboard',
    env: import.meta.env.MODE,
  },
})

// ── Child loggers (one per concern) ────────────────────────────────────

/** API polling lifecycle — connect, disconnect, latency, errors */
export const apiLog = logger.child({ module: 'api' })

/** SSE streaming — connection, reconnection, event dispatch */
export const sseLog = logger.child({ module: 'sse' })

/** Dashboard state machine — transitions, view changes */
export const stateLog = logger.child({ module: 'state' })

/** UI interactions — chaos injection, demo controls, escalations */
export const uiLog = logger.child({ module: 'ui' })

// ── Utility: performance timer ─────────────────────────────────────────

/**
 * Start a performance timer. Returns a function that logs elapsed time.
 *
 * Usage:
 *   const done = startTimer(apiLog, 'api_poll')
 *   await fetch(...)
 *   done({ zones: 4 })  // logs styled: 🛰️ API [INFO] api_poll  duration_ms=42 zones=4
 */
export function startTimer(childLogger, operation) {
  const start = performance.now()
  return (extra = {}) => {
    const duration_ms = Math.round(performance.now() - start)
    childLogger.info({ msg: operation, duration_ms, ...extra })
  }
}
