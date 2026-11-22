import { useEffect, useRef, useState } from 'react'
import { APP_NAME, COPYRIGHT, TAGLINE } from '../brand'
import { call, type BridgeState, type OcrEngines, type SystemInfo } from '../lib/bridge'
import { latexSummary, useComponents } from '../lib/useComponents'

const OFFICE_NAMES: Record<string, string> = { word: 'Word', excel: 'Excel', powerpoint: 'PowerPoint' }

const LABEL: Record<BridgeState, string> = {
  connecting: 'Connecting…',
  connected: 'Ready',
  unavailable: 'No Python backend',
}

/** Connection dot in the top bar; opens a panel with the app, system and engine details. */
export function StatusPill({ bridge }: { bridge: BridgeState }) {
  const [open, setOpen] = useState(false)
  const root = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!open) return
    const onDown = (e: MouseEvent) => {
      if (!root.current?.contains(e.target as Node)) setOpen(false)
    }
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setOpen(false)
    }
    document.addEventListener('mousedown', onDown)
    document.addEventListener('keydown', onKey)
    return () => {
      document.removeEventListener('mousedown', onDown)
      document.removeEventListener('keydown', onKey)
    }
  }, [open])

  return (
    <div className="status-wrap" ref={root}>
      <button
        type="button"
        className={`bridge-status bridge-${bridge}`}
        aria-expanded={open}
        aria-haspopup="dialog"
        title={bridge === 'connected' ? 'Python connected: show details' : LABEL[bridge]}
        onClick={() => setOpen((o) => !o)}
      >
        <span className="dot" />
        <span className="bridge-label">{LABEL[bridge]}</span>
      </button>
      {open && <About bridge={bridge} />}
    </div>
  )
}

function About({ bridge }: { bridge: BridgeState }) {
  const [info, setInfo] = useState<SystemInfo | null>(null)
  const [latency, setLatency] = useState<number | null>(null)
  const [ocr, setOcr] = useState<OcrEngines | null>(null)
  const [office, setOffice] = useState<string | null>(null)
  const latex = useComponents()

  useEffect(() => {
    if (bridge !== 'connected') return
    let active = true
    ;(async () => {
      try {
        const sys = await call('get_system_info')
        const start = performance.now()
        await call('ping')
        if (!active) return
        setLatency(performance.now() - start)
        setInfo(sys)
      } catch {
        /* shown as dashes */
      }
    })()
    call('ocr_engines').then(
      (e) => active && setOcr(e),
      () => {},
    )
    call('conversion_engines').then(
      (e) => {
        if (!active) return
        const apps = Object.entries(e.office)
          .filter(([, ok]) => ok)
          .map(([k]) => OFFICE_NAMES[k] ?? k)
        setOffice(apps.length ? `Microsoft ${apps.join(', ')}` : e.libreoffice ? 'LibreOffice' : 'Not found')
      },
      () => {},
    )
    return () => {
      active = false
    }
  }, [bridge])

  const ocrText = ocr
    ? [ocr.tesseract.path && `Tesseract (${ocr.tesseract.languages.length} language${ocr.tesseract.languages.length === 1 ? '' : 's'})`, ocr.windows.languages.length && `Windows OCR (${ocr.windows.languages.join(', ')})`]
        .filter(Boolean)
        .join(' · ') || 'Not available'
    : '—'

  const rows: [string, string][] = [
    ['LaTeX', latex ? latexSummary(latex) : '—'],
    ['OCR', ocrText],
    ['Office conversion', office ?? '—'],
    ['Python', info ? `${info.python_implementation} ${info.python_version}` : '—'],
    ['System', info ? `${info.os} ${info.os_version} · ${info.machine} · ${info.cpu_count} cores` : '—'],
    ['Mode', info ? (info.frozen ? 'Packaged build' : 'Running from source') : '—'],
  ]

  return (
    <div className="popover about" role="dialog" aria-label={`About ${APP_NAME}`}>
      <div className="about-head">
        <img src="./favicon.svg" alt="" width={36} height={36} />
        <div>
          <strong>{info?.app_name ?? APP_NAME}</strong>
          <span className="small">{TAGLINE}</span>
          <span className="muted small">
            {info ? `Version ${info.app_version}` : ''}
            {latency !== null ? ` · bridge ${latency.toFixed(1)} ms` : ''}
          </span>
        </div>
      </div>
      <dl className="kv">
        {rows.map(([k, v]) => (
          <div key={k} className="kv-row">
            <dt>{k}</dt>
            <dd>{v}</dd>
          </div>
        ))}
      </dl>
      {latex?.state === 'error' && (
        <button type="button" className="btn btn-secondary btn-sm" onClick={() => void call('components_retry')}>
          Retry LaTeX setup
        </button>
      )}
      <footer className="about-legal small">
        <p className="muted">
          {COPYRIGHT}. {APP_NAME} is free software under the GNU GPL, version 3 or later, and comes with absolutely no warranty.
        </p>
        <p className="about-links">
          <button type="button" onClick={() => void call('open_link', 'website')}>
            Website
          </button>
          <button type="button" onClick={() => void call('open_link', 'docs')}>
            Help
          </button>
          <button type="button" onClick={() => void call('open_link', 'source')}>
            Source code
          </button>
          <button type="button" onClick={() => void call('open_link', 'license')}>
            License
          </button>
          <button type="button" onClick={() => void call('open_link', 'issues')}>
            Report a problem
          </button>
        </p>
      </footer>
    </div>
  )
}
