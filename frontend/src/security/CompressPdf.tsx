import { useState } from 'react'
import { ErrorNotice } from '../components/ErrorNotice'
import { JobProgressBar } from '../components/JobProgressBar'
import { call, type PdfInfo } from '../lib/bridge'
import { cls } from '../lib/cls'
import { formatBytes } from '../lib/format'
import { useJob } from '../lib/useJob'
import { useToolRequest } from '../lib/workspace'
import { DocGate, ResultCard } from '../pdf/components'
import { usePdfDoc } from '../pdf/context'
import { useSaveFlow } from '../pdf/useSaveFlow'

const LEVELS = [
  { id: 'low', label: 'Light', hint: 'Images up to 2400 px, high quality. Best for printing.' },
  { id: 'medium', label: 'Balanced', hint: 'Images up to 1600 px. Good on screen and for email.' },
  { id: 'high', label: 'Strong', hint: 'Images up to 1100 px, lower quality. Smallest file.' },
] as const

export function CompressPdf() {
  const pdf = usePdfDoc()
  useToolRequest('compress-pdf', (path) => void pdf.open(path))
  return (
    <section className="tool">
      <header className="tool-header">
        <h1>Compress PDF</h1>
        <p>Shrink a PDF by downsampling and re-encoding large images, merging duplicate resources and compressing the page content.</p>
      </header>
      <DocGate>{(doc) => <CompressBody key={`${doc.path}|${doc.mtime}`} doc={doc} />}</DocGate>
    </section>
  )
}

function CompressBody({ doc }: { doc: PdfInfo }) {
  const pdf = usePdfDoc()
  const flow = useSaveFlow()
  const job = useJob()
  const [level, setLevel] = useState<'low' | 'medium' | 'high'>('medium')
  const [strip, setStrip] = useState(false)
  const [summary, setSummary] = useState<{ before: number; after: number; images: number; optimal: boolean } | null>(null)
  const saving = summary ? 1 - summary.after / summary.before : 0

  return (
    <>
      <div className="level-cards" role="radiogroup">
        {LEVELS.map((l) => (
          <button key={l.id} type="button" role="radio" aria-checked={level === l.id} className={cls('card level-card', level === l.id && 'is-on')} onClick={() => setLevel(l.id)}>
            <strong>{l.label}</strong>
            <span className="muted small">{l.hint}</span>
          </button>
        ))}
      </div>
      <label className="check">
        <input type="checkbox" checked={strip} onChange={(e) => setStrip(e.target.checked)} /> Also remove metadata, thumbnails and embedded XMP
      </label>
      <div className="action-bar">
        <JobProgressBar busy={job.busy} progress={job.progress} label="Analysing…" />
        <button
          type="button"
          className="btn btn-primary"
          disabled={flow.busy || job.busy}
          onClick={async () => {
            setSummary(null)
            await flow.saveAs(doc.path, 'compressed', (out) =>
              job.run(async (id) => {
                const r = await call('pdf_compress', doc.path, out, level, strip, id)
                setSummary({ before: r.before, after: r.after, images: r.images_recompressed, optimal: !!r.already_optimal })
                return r
              }),
            )
          }}
        >
          {job.busy ? 'Compressing…' : 'Compress and save…'}
        </button>
      </div>
      {summary && (
        <div className="card compress-summary">
          <div className="size-bars">
            <div>
              <span className="muted small">Before</span>
              <strong>{formatBytes(summary.before)}</strong>
            </div>
            <div>
              <span className="muted small">After</span>
              <strong>{formatBytes(summary.after)}</strong>
            </div>
            <div>
              <span className="muted small">Saved</span>
              <strong>{summary.optimal ? '—' : `${Math.round(saving * 100)}%`}</strong>
            </div>
          </div>
          <div className="job-track">
            <div className="job-fill" style={{ width: `${Math.max(2, (summary.after / summary.before) * 100)}%` }} />
          </div>
          <p className="small muted">
            {summary.optimal
              ? 'This PDF is already well optimised; the copy is unchanged.'
              : `${summary.images} image${summary.images === 1 ? '' : 's'} re-encoded.`}
          </p>
        </div>
      )}
      <ErrorNotice error={flow.error} />
      {flow.saved && <ResultCard files={flow.saved} onDismiss={flow.dismiss} onContinue={(f) => void pdf.open(f.path)} />}
    </>
  )
}
