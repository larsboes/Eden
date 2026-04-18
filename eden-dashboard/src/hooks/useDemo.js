import { useState, useEffect, useCallback } from 'react'

const DEMO_SCRIPT = [
  { at: 0,  state: 'nominal',  log: 'nominal',   label: 'All systems nominal' },
  { at: 8,  state: 'alert',    log: 'cme',        label: 'CME detected — DONKI alert' },
  { at: 14, state: 'alert',    log: 'council',    label: 'Council debates strategies' },
  { at: 20, state: 'alert',    log: 'stockpile',  label: 'Pre-storm stockpiling' },
  { at: 28, state: 'crisis',   log: 'storm',      label: 'Storm hits — 30% solar' },
  { at: 35, state: 'recovery', log: 'recovery',   label: 'Storm clearing — recovery' },
  { at: 42, state: 'nominal',  log: 'nominal',    label: 'Back to nominal — loop restarts' },
]

export function useDemo() {
  const [state, setState] = useState('nominal')
  const [running, setRunning] = useState(false)
  const [elapsed, setElapsed] = useState(0)
  const [step, setStep] = useState(0)
  const [logKey, setLogKey] = useState('nominal')

  const loopDuration = DEMO_SCRIPT[DEMO_SCRIPT.length - 1].at
  const currentT = elapsed % loopDuration
  const currentStep = DEMO_SCRIPT[step]
  const isAlert = state === 'alert' || state === 'crisis'

  useEffect(() => {
    if (!running) return
    const iv = setInterval(() => {
      setElapsed(e => {
        const next = e + 1
        const t = next % loopDuration
        let current = DEMO_SCRIPT[0]
        for (const s of DEMO_SCRIPT) {
          if (t >= s.at) current = s
        }
        setState(current.state)
        setLogKey(current.log)
        setStep(DEMO_SCRIPT.indexOf(current))
        return next
      })
    }, 1000)
    return () => clearInterval(iv)
  }, [running, loopDuration])

  const start = useCallback(() => {
    setRunning(true)
    setElapsed(0)
    setStep(0)
    setState('nominal')
    setLogKey('nominal')
  }, [])

  const stop = useCallback(() => {
    setRunning(false)
    setState('nominal')
    setLogKey('nominal')
  }, [])

  const setManualState = useCallback((s) => {
    if (!running) {
      setState(s)
      setLogKey(s === 'nominal' ? 'nominal' : 'council')
    }
  }, [running])

  return {
    state, running, elapsed, step, logKey,
    loopDuration, currentT, currentStep, isAlert,
    start, stop, setManualState,
  }
}
