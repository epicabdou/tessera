import { useEffect, useState } from 'react'
import { call, type LatexStatus } from './bridge'

const SETTLED = ['ready', 'error', 'missing']

/** State of the downloadable components (the LaTeX engine), polled while setup runs. */
export function useComponents(): LatexStatus | null {
  const [latex, setLatex] = useState<LatexStatus | null>(null)
  useEffect(() => {
    let active = true
    let timer = 0
    const poll = () => {
      call('components_status').then(
        (s) => {
          if (!active) return
          setLatex(s.latex)
          if (!SETTLED.includes(s.latex.state)) timer = window.setTimeout(poll, 1500)
        },
        () => {
          if (active) timer = window.setTimeout(poll, 4000)
        },
      )
    }
    poll()
    return () => {
      active = false
      window.clearTimeout(timer)
    }
  }, [])
  return latex
}

export function latexSummary(s: LatexStatus): string {
  switch (s.state) {
    case 'downloading':
      return `Downloading LaTeX engine… ${Math.round(s.progress * 100)}%`
    case 'installing':
      return 'Installing LaTeX engine…'
    case 'warming':
      return 'Fetching LaTeX packages…'
    case 'error':
      return 'LaTeX setup failed'
    case 'missing':
      return 'LaTeX not installed'
    case 'ready':
      return s.engine ? `LaTeX ready (${s.engine})` : 'LaTeX ready'
    default:
      return 'Checking LaTeX…'
  }
}
