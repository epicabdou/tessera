import { useState } from 'react'
import { ErrorNotice } from '../../components/ErrorNotice'
import { RotateCcwIcon, RotateCwIcon } from '../../components/icons'
import { call, type PdfInfo } from '../../lib/bridge'
import { cls } from '../../lib/cls'
import { useToolRequest } from '../../lib/workspace'
import { DocGate, PageThumb, ResultCard } from '../components'
import { usePdfDoc } from '../context'
import { useSaveFlow } from '../useSaveFlow'

export function RotatePdf() {
  const pdf = usePdfDoc()
  useToolRequest('pdf-rotate', (path) => void pdf.open(path))
  return (
    <section className="tool tool-wide">
      <header className="tool-header">
        <h1>Rotate PDF</h1>
        <p>Turn pages by 90°, 180° or 270°. Select pages first, or rotate the whole document.</p>
      </header>
      <DocGate>{(doc) => <RotateBody key={`${doc.path}|${doc.mtime}`} doc={doc} />}</DocGate>
    </section>
  )
}

function RotateBody({ doc }: { doc: PdfInfo }) {
  const pdf = usePdfDoc()
  const n = doc.page_count
  const [rotations, setRotations] = useState<number[]>(() => Array(n).fill(0))
  const [selection, setSelection] = useState<ReadonlySet<number>>(new Set())
  const flow = useSaveFlow()

  const rotate = (targets: Iterable<number>, delta: number) => {
    const set = new Set(targets)
    setRotations((r) => r.map((v, i) => (set.has(i) ? (v + delta + 360) % 360 : v)))
  }
  const all = () => doc.pages.map((_, i) => i)
  const targets = () => (selection.size ? [...selection] : all())
  const pick = (filter: (i: number) => boolean) => setSelection(new Set(all().filter(filter)))
  const toggle = (i: number) =>
    setSelection((s) => {
      const next = new Set(s)
      if (next.has(i)) next.delete(i)
      else next.add(i)
      return next
    })

  const changed = rotations.filter((v) => v).length
  const scope = selection.size ? `${selection.size} selected` : 'all pages'

  return (
    <>
      <div className="toolbar" role="toolbar" aria-label="Rotation">
        <span className="muted small">Select</span>
        <button type="button" className="btn btn-ghost btn-sm" onClick={() => pick(() => true)}>
          All
        </button>
        <button type="button" className="btn btn-ghost btn-sm" onClick={() => pick((i) => i % 2 === 0)}>
          Odd
        </button>
        <button type="button" className="btn btn-ghost btn-sm" onClick={() => pick((i) => i % 2 === 1)}>
          Even
        </button>
        <button type="button" className="btn btn-ghost btn-sm" disabled={!selection.size} onClick={() => setSelection(new Set())}>
          None
        </button>
        <span className="toolbar-sep" />
        <button type="button" className="btn btn-secondary btn-sm" onClick={() => rotate(targets(), -90)}>
          <RotateCcwIcon size={14} /> 90° left
        </button>
        <button type="button" className="btn btn-secondary btn-sm" onClick={() => rotate(targets(), 90)}>
          <RotateCwIcon size={14} /> 90° right
        </button>
        <button type="button" className="btn btn-secondary btn-sm" onClick={() => rotate(targets(), 180)}>
          180°
        </button>
        <span className="muted small">({scope})</span>
        <span className="toolbar-spacer" />
        <button type="button" className="btn btn-ghost btn-sm" disabled={!changed} onClick={() => setRotations(Array(n).fill(0))}>
          Reset
        </button>
      </div>

      <div className="page-grid">
        {doc.pages.map((page, i) => (
          <div
            key={i}
            className={cls('page-card', 'is-clickable', selection.has(i) && 'is-selected')}
            onClick={() => toggle(i)}
            role="button"
            tabIndex={0}
            aria-pressed={selection.has(i)}
            onKeyDown={(e) => (e.key === ' ' || e.key === 'Enter') && toggle(i)}
          >
            <PageThumb file={doc} index={i} page={page} rotate={rotations[i]} />
            <div className="card-tools" onClick={(e) => e.stopPropagation()}>
              <button type="button" title="Rotate left" aria-label={`Rotate page ${i + 1} left`} onClick={() => rotate([i], -90)}>
                <RotateCcwIcon size={13} />
              </button>
              <button type="button" title="Rotate right" aria-label={`Rotate page ${i + 1} right`} onClick={() => rotate([i], 90)}>
                <RotateCwIcon size={13} />
              </button>
            </div>
            <span className="page-label">
              {i + 1}
              {rotations[i] !== 0 && <span className="page-origin">+{rotations[i]}°</span>}
            </span>
          </div>
        ))}
      </div>

      <ErrorNotice error={flow.error} />
      {flow.saved && <ResultCard files={flow.saved} onDismiss={flow.dismiss} onContinue={(f) => void pdf.open(f.path)} />}

      <div className="action-bar">
        <span className="muted">{changed ? `${changed} of ${n} pages rotated` : 'No changes yet'}</span>
        <button
          type="button"
          className="btn btn-primary"
          disabled={flow.busy || !changed}
          onClick={() => flow.saveAs(doc.path, 'rotated', (output) => call('pdf_rotate', doc.path, output, rotations))}
        >
          {flow.busy ? 'Saving…' : 'Save rotated PDF…'}
        </button>
      </div>
    </>
  )
}
