import { useEffect, useState } from 'react'
import { ErrorNotice } from '../components/ErrorNotice'
import { call, toError, type PdfHealth } from '../lib/bridge'
import { formatBytes } from '../lib/format'
import { useWorkspace } from '../lib/workspace'
import { ResultCard } from '../pdf/components'
import { useSaveFlow } from '../pdf/useSaveFlow'
import { PathGate } from './PathGate'

/** Backend method: "pypdf" | "pdfium", optionally with " (salvaged)" / " (rebuilt)". */
function describeMethod(method: string) {
  if (method.includes('rebuilt')) return 'Recovered by scanning the file and rebuilding the page list.'
  if (method.includes('salvaged')) return 'Recovered by scanning the file for surviving objects.'
  if (method.startsWith('pdfium')) return 'Rebuilt by the PDF renderer’s recovery mode.'
  return 'Rewritten with a fresh cross-reference table.'
}

export function RepairPdf() {
  return (
    <section className="tool">
      <header className="tool-header">
        <h1>Repair PDF</h1>
        <p>Check a PDF for structural damage and rebuild it so it opens again. The original file is never changed.</p>
      </header>
      <PathGate tool="repair-pdf">{(path) => <RepairBody path={path} />}</PathGate>
    </section>
  )
}

function RepairBody({ path }: { path: string }) {
  const { openInTool } = useWorkspace()
  const flow = useSaveFlow()
  const [health, setHealth] = useState<PdfHealth | null>(null)
  const [error, setError] = useState<Error | null>(null)
  const [method, setMethod] = useState<string | null>(null)

  useEffect(() => {
    call('pdf_analyze', path).then(setHealth, (err) => setError(toError(err)))
  }, [path])

  if (error) return <ErrorNotice error={error} />
  if (!health) return <p className="muted">Checking the file…</p>

  return (
    <>
      <div className={`card health-card ${health.healthy ? 'is-ok' : 'is-bad'}`}>
        <span className="health-icon">{health.healthy ? '✓' : '!'}</span>
        <div>
          <strong>{health.healthy ? 'No problems found' : `${health.issues.length} problem${health.issues.length === 1 ? '' : 's'} found`}</strong>
          <p className="small muted">
            {formatBytes(health.size)}
            {health.pages !== null ? ` · ${health.pages} readable page${health.pages === 1 ? '' : 's'}` : ' · pages unreadable'}
          </p>
          {health.issues.length > 0 && (
            <ul className="issue-list small">
              {health.issues.slice(0, 12).map((i, n) => (
                <li key={n}>{i}</li>
              ))}
              {health.issues.length > 12 && <li className="muted">…and {health.issues.length - 12} more</li>}
            </ul>
          )}
        </div>
      </div>
      {method && <p className="small">{describeMethod(method)}</p>}
      <ErrorNotice error={flow.error} />
      {flow.saved && <ResultCard files={flow.saved} onDismiss={flow.dismiss} onContinue={(f) => openInTool('edit-pdf', f.path)} />}
      <div className="action-bar">
        <span className="muted small">{health.healthy ? 'You can still rebuild it, for example to drop leftover data.' : ''}</span>
        <button
          type="button"
          className="btn btn-primary"
          disabled={flow.busy}
          onClick={async () => {
            setMethod(null)
            await flow.saveAs(path, 'repaired', async (out) => {
              const r = await call('pdf_repair', path, out)
              setMethod(r.method)
              return r
            })
          }}
        >
          {flow.busy ? 'Repairing…' : 'Repair and save…'}
        </button>
      </div>
    </>
  )
}
