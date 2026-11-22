import { useCallback, useEffect, useLayoutEffect, useRef, useState } from 'react'
import { ErrorNotice } from '../components/ErrorNotice'
import { call, toError, type LatexDoc, type LatexResult, type LatexStatus, type PdfInfo } from '../lib/bridge'
import { cls } from '../lib/cls'
import { CONVERT_EXTS, useToolRequest, useWorkspace } from '../lib/workspace'
import { PageThumb } from '../pdf/components'
import { CodeEditor, type CodeEditorHandle } from './CodeEditor'
import { relativeTexPath } from './paths'

const RECENT_KEY = 'toolbox.latexRecent'
const AUTO_KEY = 'toolbox.latexAuto'

const TEMPLATES: { id: string; label: string }[] = [
  { id: 'article', label: 'Article' },
  { id: 'report', label: 'Report (chapters)' },
  { id: 'beamer', label: 'Presentation (Beamer)' },
  { id: 'letter', label: 'Letter' },
]

const SNIPPETS: { label: string; text: string }[] = [
  { label: 'Section', text: '\\section{|}\n' },
  { label: 'Subsection', text: '\\subsection{|}\n' },
  { label: 'Bold', text: '\\textbf{|}' },
  { label: 'Italic', text: '\\textit{|}' },
  { label: 'Bulleted list', text: '\\begin{itemize}\n  \\item |\n\\end{itemize}\n' },
  { label: 'Numbered list', text: '\\begin{enumerate}\n  \\item |\n\\end{enumerate}\n' },
  { label: 'Inline math', text: '$|$' },
  { label: 'Equation', text: '\\begin{equation}\n  |\n\\end{equation}\n' },
  { label: 'Aligned equations', text: '\\begin{align}\n  a &= b + c \\\\\n  |\n\\end{align}\n' },
  { label: 'Fraction', text: '\\frac{|}{}' },
  { label: 'Table', text: '\\begin{table}[htbp]\n  \\centering\n  \\begin{tabular}{lll}\n    \\hline\n    A & B & C \\\\\n    \\hline\n    | &  &  \\\\\n    \\hline\n  \\end{tabular}\n  \\caption{}\n  \\label{tab:}\n\\end{table}\n' },
  { label: 'Footnote', text: '\\footnote{|}' },
  { label: 'Link', text: '\\href{https://|}{}' },
  { label: 'Page break', text: '\\newpage\n' },
]

function readRecent(): string[] {
  try {
    const v = JSON.parse(localStorage.getItem(RECENT_KEY) ?? '[]')
    return Array.isArray(v) ? v.filter((x) => typeof x === 'string') : []
  } catch {
    return []
  }
}

function pushRecent(path: string) {
  try {
    const list = [path, ...readRecent().filter((p) => p.toLowerCase() !== path.toLowerCase())].slice(0, 8)
    localStorage.setItem(RECENT_KEY, JSON.stringify(list))
  } catch {
    /* storage unavailable */
  }
}

function readAuto(): boolean {
  try {
    return localStorage.getItem(AUTO_KEY) !== '0'
  } catch {
    return true
  }
}

const fileName = (p: string) => p.split(/[\\/]/).pop() ?? p
const dirName = (p: string) => p.replace(/[\\/][^\\/]*$/, '')

/** Polls the LaTeX engine status until setup has finished. */
function useLatexStatus() {
  const [status, setStatus] = useState<LatexStatus | null>(null)
  const [tick, setTick] = useState(0)
  useEffect(() => {
    let active = true
    let timer = 0
    const poll = () => {
      call('latex_status').then(
        (s) => {
          if (!active) return
          setStatus(s)
          if (!['ready', 'error', 'missing'].includes(s.state)) timer = window.setTimeout(poll, 1000)
        },
        () => active && (timer = window.setTimeout(poll, 3000)),
      )
    }
    poll()
    return () => {
      active = false
      window.clearTimeout(timer)
    }
  }, [tick])
  const retry = useCallback(async () => {
    await call('components_retry')
    setTick((t) => t + 1)
  }, [])
  return { status, retry }
}

export function LatexEditor() {
  const [doc, setDoc] = useState<(LatexDoc & { nonce: number }) | null>(null)
  const [error, setError] = useState<Error | null>(null)
  const { status, retry } = useLatexStatus()

  const load = useCallback(async (work: Promise<LatexDoc>) => {
    setError(null)
    try {
      const d = await work
      if (!d.untitled) pushRecent(d.path)
      setDoc((old) => ({ ...d, nonce: (old?.nonce ?? 0) + 1 }))
    } catch (err) {
      setError(toError(err))
    }
  }, [])
  const open = useCallback((path: string) => load(call('latex_read', path)), [load])
  const create = useCallback((template: string) => load(call('latex_new_document', template)), [load])
  const pick = useCallback(async () => {
    try {
      const [path] = await call('pick_files', 'LaTeX documents', ['tex'], false)
      if (path) await open(path)
    } catch (err) {
      setError(toError(err))
    }
  }, [open])
  useToolRequest('latex', (path) => void open(path))

  return (
    <section className="tool tool-full latex-tool">
      <EngineBanner status={status} retry={retry} />
      <ErrorNotice error={error} />
      {doc ? (
        <Workspace key={`${doc.path}|${doc.nonce}`} doc={doc} status={status} onNew={create} onOpen={pick} onReplace={(d) => setDoc((old) => ({ ...d, nonce: (old?.nonce ?? 0) + 1 }))} />
      ) : (
        <StartScreen onNew={create} onOpen={pick} onOpenPath={open} />
      )}
    </section>
  )
}

function EngineBanner({ status, retry }: { status: LatexStatus | null; retry: () => void }) {
  if (!status || status.state === 'ready') return null
  const pct = Math.round(status.progress * 100)
  const text: Record<LatexStatus['state'], string> = {
    unknown: 'Checking for a LaTeX engine…',
    missing: 'No LaTeX engine is installed yet.',
    downloading: `Downloading the LaTeX engine (Tectonic)… ${pct}%`,
    installing: 'Installing the LaTeX engine…',
    warming: 'Downloading the standard LaTeX packages (first run only, a few minutes)…',
    error: `LaTeX setup failed: ${status.error ?? 'unknown error'}`,
    ready: '',
  }
  const busy = ['downloading', 'installing', 'warming', 'unknown'].includes(status.state)
  return (
    <div className={cls('notice engine-banner', status.state === 'error' && 'notice-error')}>
      <span>{text[status.state]}</span>
      {busy && (
        <div className="job-track">
          <div className={cls('job-fill', status.state !== 'downloading' && 'is-indeterminate')} style={status.state === 'downloading' ? { width: `${pct}%` } : undefined} />
        </div>
      )}
      {(status.state === 'error' || status.state === 'missing') && (
        <button type="button" className="btn btn-secondary btn-sm" onClick={retry}>
          {status.state === 'error' ? 'Try again' : 'Install now'}
        </button>
      )}
    </div>
  )
}

function StartScreen({ onNew, onOpen, onOpenPath }: { onNew: (t: string) => void; onOpen: () => void; onOpenPath: (p: string) => void }) {
  const { selected } = useWorkspace()
  const recent = readRecent()
  const selectedTex = selected && !selected.is_dir && selected.path.toLowerCase().endsWith('.tex') ? selected : null
  return (
    <div className="latex-start">
      <header className="tool-header">
        <h1>LaTeX editor</h1>
        <p>Write LaTeX with highlighting and completion, and see the PDF update as you type. Errors link straight to the line.</p>
      </header>
      <h2 className="panel-title">New document</h2>
      <div className="template-grid">
        {TEMPLATES.map((t) => (
          <button key={t.id} type="button" className="card template-card" onClick={() => onNew(t.id)}>
            <span className="template-icon">{t.id === 'beamer' ? '▭' : t.id === 'letter' ? '✉' : '¶'}</span>
            <strong>{t.label}</strong>
          </button>
        ))}
      </div>
      <div className="button-row">
        <button type="button" className="btn btn-secondary" onClick={onOpen}>
          Open .tex file…
        </button>
        {selectedTex && (
          <button type="button" className="btn btn-ghost" onClick={() => onOpenPath(selectedTex.path)}>
            Open {selectedTex.name}
          </button>
        )}
      </div>
      {recent.length > 0 && (
        <>
          <h2 className="panel-title">Recent</h2>
          <ul className="recent-list">
            {recent.map((p) => (
              <li key={p}>
                <button type="button" className="link-btn" onClick={() => onOpenPath(p)} title={p}>
                  {fileName(p)}
                </button>
                <span className="muted small mono">{dirName(p)}</span>
              </li>
            ))}
          </ul>
        </>
      )}
    </div>
  )
}

function Workspace({
  doc,
  status,
  onNew,
  onOpen,
  onReplace,
}: {
  doc: LatexDoc
  status: LatexStatus | null
  onNew: (t: string) => void
  onOpen: () => void
  onReplace: (d: LatexDoc) => void
}) {
  const { filesChanged } = useWorkspace()
  const editor = useRef<CodeEditorHandle>(null)
  const [text, setText] = useState(doc.text)
  const [savedText, setSavedText] = useState(doc.text)
  const { path, untitled } = doc
  const [auto, setAuto] = useState(readAuto)
  const [engine, setEngine] = useState('auto')
  const [compiling, setCompiling] = useState(false)
  const [queued, setQueued] = useState(false)
  const [result, setResult] = useState<LatexResult | null>(null)
  const [pdf, setPdf] = useState<PdfInfo | null>(null)
  const [error, setError] = useState<Error | null>(null)
  const [showLog, setShowLog] = useState(false)
  const latest = useRef(doc.text)
  const running = useRef(false)
  const dirty = text !== savedText
  const canCompile = !!status?.engine

  const save = useCallback(async (target = path) => {
    const current = latest.current
    await call('latex_save', target, current)
    setSavedText(current)
    return current
  }, [path])

  const compile = useCallback(async () => {
    if (running.current) {
      setQueued(true)
      return
    }
    running.current = true
    setCompiling(true)
    setError(null)
    try {
      await save()
      const r = await call('latex_compile', path, engine)
      setResult(r)
      if (r.ok && r.pdf) {
        setPdf(await call('pdf_info', r.pdf))
        filesChanged()
      }
    } catch (err) {
      setError(toError(err))
    } finally {
      running.current = false
      setCompiling(false)
    }
  }, [save, path, engine, filesChanged])

  // A change made while compiling triggers one more run afterwards.
  useEffect(() => {
    if (!compiling && queued) {
      setQueued(false)
      void compile()
    }
  }, [compiling, queued, compile])

  // First compile when the document opens (if an engine is ready).
  const compiledOnce = useRef(false)
  useEffect(() => {
    if (canCompile && !compiledOnce.current) {
      compiledOnce.current = true
      void compile()
    }
  }, [canCompile, compile])

  // Auto-compile after a pause in typing.
  useEffect(() => {
    if (!auto || !canCompile || text === savedText) return
    const t = window.setTimeout(() => void compile(), 1200)
    return () => window.clearTimeout(t)
    // compile is intentionally left out: re-running on its identity change would restart the timer.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [text, auto, canCompile])

  async function saveAs() {
    try {
      let suggested = path
      if (untitled) {
        const docs = (await call('get_locations')).find((l) => l.kind === 'documents')
        suggested = `${docs?.path ?? dirName(path)}\\document.tex`
      }
      const target = await call('save_file_dialog', suggested, 'LaTeX document', ['tex'])
      if (!target) return
      const current = latest.current
      await call('latex_save', target, current)
      pushRecent(target)
      filesChanged()
      onReplace({ path: target, text: current, untitled: false })
    } catch (err) {
      setError(toError(err))
    }
  }

  async function saveNow() {
    if (untitled) return saveAs()
    try {
      await save()
      filesChanged()
    } catch (err) {
      setError(toError(err))
    }
  }

  async function insertImage() {
    try {
      const [img] = await call('pick_files', 'Images', [...(CONVERT_EXTS['to-pdf-images'] ?? []), 'pdf', 'eps'], false)
      if (!img) return
      const rel = relativeTexPath(dirName(path), img)
      editor.current?.insert(`\\begin{figure}[htbp]\n  \\centering\n  \\includegraphics[width=0.8\\linewidth]{${rel}}\n  \\caption{|}\n  \\label{fig:}\n\\end{figure}\n`)
    } catch (err) {
      setError(toError(err))
    }
  }

  const errors = result?.messages.filter((m) => m.kind === 'error') ?? []
  const warnings = result?.messages.filter((m) => m.kind === 'warning') ?? []

  return (
    <>
      <div className="toolbar latex-toolbar" role="toolbar">
        <select className="text-input tb-select" value="" aria-label="New document" onChange={(e) => e.target.value && onNew(e.target.value)}>
          <option value="">New…</option>
          {TEMPLATES.map((t) => (
            <option key={t.id} value={t.id}>
              {t.label}
            </option>
          ))}
        </select>
        <button type="button" className="btn btn-ghost btn-sm" onClick={onOpen}>
          Open…
        </button>
        <button type="button" className="btn btn-ghost btn-sm" onClick={saveNow} title="Ctrl+S">
          Save{dirty ? ' •' : ''}
        </button>
        <button type="button" className="btn btn-ghost btn-sm" onClick={saveAs}>
          Save as…
        </button>
        <span className="tb-sep" />
        <select
          className="text-input tb-select"
          value=""
          aria-label="Insert"
          onChange={(e) => {
            const s = SNIPPETS[Number(e.target.value)]
            if (s) editor.current?.insert(s.text)
          }}
        >
          <option value="">Insert…</option>
          {SNIPPETS.map((s, i) => (
            <option key={s.label} value={i}>
              {s.label}
            </option>
          ))}
        </select>
        <button type="button" className="btn btn-ghost btn-sm" onClick={insertImage}>
          Image…
        </button>
        <span className="toolbar-spacer" />
        <span className="muted small doc-name" title={untitled ? 'Not saved to your files yet: use Save as… to keep it' : path}>
          {untitled ? 'Untitled' : fileName(path)}
        </span>
        <select className="text-input tb-select" value={engine} aria-label="Engine" onChange={(e) => setEngine(e.target.value)}>
          <option value="auto">Engine: automatic</option>
          {Object.entries(status?.engines ?? {})
            .filter(([, p]) => p)
            .map(([name]) => (
              <option key={name} value={name}>
                {name}
              </option>
            ))}
        </select>
        <label className="check small">
          <input
            type="checkbox"
            checked={auto}
            onChange={(e) => {
              setAuto(e.target.checked)
              try {
                localStorage.setItem(AUTO_KEY, e.target.checked ? '1' : '0')
              } catch {
                /* storage unavailable */
              }
            }}
          />
          Live
        </label>
        <button type="button" className="btn btn-primary btn-sm" onClick={() => void compile()} disabled={!canCompile} title="Ctrl+Enter">
          {compiling ? 'Compiling…' : 'Compile'}
        </button>
      </div>
      <ErrorNotice error={error} />
      <div className="latex-split">
        <div className="latex-left">
          <CodeEditor ref={editor} value={doc.text} onChange={(t) => {
              latest.current = t
              setText(t)
            }} onSave={() => void saveNow()} onCompile={() => void compile()} />
          <div className={cls('latex-problems', errors.length > 0 && 'has-errors')}>
            <div className="problems-head">
              <strong className="small">
                {result ? (result.ok ? `Compiled with ${result.engine} in ${result.seconds.toFixed(1)} s` : 'Compilation failed') : canCompile ? 'Not compiled yet' : 'Waiting for the LaTeX engine'}
              </strong>
              <span className="muted small">
                {errors.length} error{errors.length === 1 ? '' : 's'} · {warnings.length} warning{warnings.length === 1 ? '' : 's'}
              </span>
              <span className="toolbar-spacer" />
              {result && (
                <button type="button" className="btn btn-ghost btn-xs" onClick={() => setShowLog((v) => !v)}>
                  {showLog ? 'Hide log' : 'Show log'}
                </button>
              )}
            </div>
            {showLog && result ? (
              <pre className="latex-log">{result.log}</pre>
            ) : (
              <ul className="problem-list">
                {[...errors, ...warnings].map((m, i) => (
                  <li key={i}>
                    <button type="button" className={cls('problem', m.kind === 'error' ? 'is-error' : 'is-warning')} disabled={!m.line} onClick={() => m.line && editor.current?.goToLine(m.line)}>
                      <span className="problem-kind">{m.kind === 'error' ? '✕' : '!'}</span>
                      <span className="problem-msg">{m.message}</span>
                      {m.line && <span className="problem-line mono">{fileName(m.file)}:{m.line}</span>}
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>
        <div className="latex-right">
          {pdf ? (
            <>
              <div className="latex-pdf-bar">
                <span className="small muted">
                  {pdf.page_count} page{pdf.page_count === 1 ? '' : 's'}
                  {result && !result.ok ? ' · showing the last good version' : ''}
                </span>
                <span className="toolbar-spacer" />
                <button type="button" className="btn btn-ghost btn-xs" onClick={() => void call('open_path', pdf.path)}>
                  Open PDF
                </button>
                <button type="button" className="btn btn-ghost btn-xs" onClick={() => void call('reveal_path', pdf.path)}>
                  Show in folder
                </button>
              </div>
              <PdfPages pdf={pdf} />
            </>
          ) : (
            <div className="latex-empty muted">{compiling ? 'Compiling…' : canCompile ? 'The PDF appears here after compiling.' : 'The PDF appears here once LaTeX is set up.'}</div>
          )}
        </div>
      </div>
    </>
  )
}

/** All pages of a PDF, fitted to the column width (lazy). */
function PdfPages({ pdf }: { pdf: PdfInfo }) {
  const ref = useRef<HTMLDivElement>(null)
  const [width, setWidth] = useState(400)
  useLayoutEffect(() => {
    const el = ref.current
    if (!el) return
    const ro = new ResizeObserver(() => setWidth(el.clientWidth))
    ro.observe(el)
    return () => ro.disconnect()
  }, [])
  const fit = Math.max(120, width - 32)
  const renderWidth = Math.min(1600, Math.ceil((fit * Math.min(2, window.devicePixelRatio || 1)) / 200) * 200)
  return (
    <div ref={ref} className="latex-pages">
      {pdf.pages.map((p, i) => (
        <div key={i} className="latex-page">
          <PageThumb file={pdf} index={i} page={p} fitWidth={fit} renderWidth={renderWidth} />
        </div>
      ))}
    </div>
  )
}
