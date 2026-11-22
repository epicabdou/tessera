import { useEffect, useMemo, useState } from 'react'
import { ErrorNotice } from '../../components/ErrorNotice'
import { call, toError, type PdfInfo, type SplitMode } from '../../lib/bridge'
import { cls } from '../../lib/cls'
import { dirname, formatRanges } from '../../lib/format'
import { useToolRequest } from '../../lib/workspace'
import { DocGate, PageThumb, ResultCard } from '../components'
import { usePdfDoc } from '../context'
import { useSaveFlow } from '../useSaveFlow'

type Mode = 'ranges' | 'every' | 'extract'

const MODES: { id: Mode; label: string; hint: string }[] = [
  { id: 'ranges', label: 'By ranges', hint: 'Each range becomes its own file, e.g. 1-3, 4-8, 9-' },
  { id: 'every', label: 'Every N pages', hint: 'Cut the document into files of N pages each' },
  { id: 'extract', label: 'Extract pages', hint: 'Pick pages (click them, or type 1-3, 7) to copy into a new file' },
]

const groupColor = (g: number) => `hsl(${(g * 137.5 + 28) % 360} 70% 52%)`

export function SplitPdf() {
  const pdf = usePdfDoc()
  useToolRequest('pdf-split', (path) => void pdf.open(path))
  return (
    <section className="tool tool-wide">
      <header className="tool-header">
        <h1>Split PDF</h1>
        <p>Divide a PDF into separate files, or pull out specific pages.</p>
      </header>
      <DocGate>{(doc) => <SplitBody key={`${doc.path}|${doc.mtime}`} doc={doc} />}</DocGate>
    </section>
  )
}

function SplitBody({ doc }: { doc: PdfInfo }) {
  const pdf = usePdfDoc()
  const n = doc.page_count
  const half = Math.ceil(n / 2)
  const span = (a: number, b: number) => (a === b ? `${a}` : `${a}-${b}`)
  const [mode, setMode] = useState<Mode>('ranges')
  const [ranges, setRanges] = useState(n > 1 ? `${span(1, half)}, ${span(half + 1, n)}` : '1')
  const [every, setEvery] = useState('1')
  const [extract, setExtract] = useState('')
  const [separate, setSeparate] = useState(false)
  const [plan, setPlan] = useState<number[][]>([])
  const [planError, setPlanError] = useState<string | null>(null)
  const flow = useSaveFlow()

  const apiMode: SplitMode = mode === 'extract' ? (separate ? 'extract_each' : 'extract') : mode
  const value = mode === 'ranges' ? ranges : mode === 'every' ? every : extract

  // The plan comes from Python, so the preview matches exactly what will be written.
  useEffect(() => {
    let active = true
    const t = window.setTimeout(() => {
      if (!value.trim()) {
        setPlan([])
        setPlanError(null)
        return
      }
      call('pdf_split_plan', n, apiMode, value).then(
        (groups) => {
          if (!active) return
          setPlan(groups.filter((g) => g.length))
          setPlanError(null)
        },
        (err) => {
          if (!active) return
          setPlan([])
          setPlanError(toError(err).message)
        },
      )
    }, 150)
    return () => {
      active = false
      window.clearTimeout(t)
    }
  }, [n, apiMode, value])

  const groupOf = useMemo(() => {
    const map = new Map<number, number>()
    plan.forEach((group, g) => group.forEach((i) => map.has(i) || map.set(i, g)))
    return map
  }, [plan])

  function togglePage(i: number) {
    const chosen = new Set(plan.flat())
    if (chosen.has(i)) chosen.delete(i)
    else chosen.add(i)
    setExtract(formatRanges(chosen))
  }

  const files = plan.length
  const hint = MODES.find((m) => m.id === mode)!.hint

  return (
    <>
      <div className="options-row">
        <div className="segmented" role="radiogroup" aria-label="Split mode">
          {MODES.map((m) => (
            <button
              key={m.id}
              type="button"
              role="radio"
              aria-checked={mode === m.id}
              className={cls('segment', mode === m.id && 'is-on')}
              onClick={() => setMode(m.id)}
            >
              {m.label}
            </button>
          ))}
        </div>

        {mode === 'ranges' && (
          <input
            className="text-input grow"
            value={ranges}
            onChange={(e) => setRanges(e.target.value)}
            aria-label="Page ranges"
            spellCheck={false}
          />
        )}
        {mode === 'every' && (
          <label className="inline-field">
            Pages per file
            <input
              className="text-input num"
              type="number"
              min={1}
              max={n}
              value={every}
              onChange={(e) => setEvery(e.target.value)}
            />
          </label>
        )}
        {mode === 'extract' && (
          <>
            <input
              className="text-input grow"
              value={extract}
              placeholder="Click pages below, or type e.g. 1-3, 7"
              onChange={(e) => setExtract(e.target.value)}
              aria-label="Pages to extract"
              spellCheck={false}
            />
            <label className="check">
              <input type="checkbox" checked={separate} onChange={(e) => setSeparate(e.target.checked)} />
              One file per page
            </label>
          </>
        )}
      </div>
      <p className={cls('small', planError ? 'field-error' : 'muted')}>{planError ?? hint}</p>

      <div className="page-grid">
        {doc.pages.map((page, i) => {
          const g = groupOf.get(i)
          const clickable = mode === 'extract'
          return (
            <div
              key={i}
              className={cls('page-card', g === undefined && 'is-excluded', clickable && 'is-clickable', clickable && g !== undefined && 'is-selected')}
              onClick={clickable ? () => togglePage(i) : undefined}
              role={clickable ? 'button' : undefined}
              aria-pressed={clickable ? g !== undefined : undefined}
              tabIndex={clickable ? 0 : undefined}
              onKeyDown={clickable ? (e) => (e.key === ' ' || e.key === 'Enter') && togglePage(i) : undefined}
            >
              <PageThumb file={doc} index={i} page={page} />
              <span className="page-label">{i + 1}</span>
              {g !== undefined && (mode !== 'extract' || separate) && (
                <span className="group-badge" style={{ background: groupColor(g) }} title={`File ${g + 1}`}>
                  {g + 1}
                </span>
              )}
            </div>
          )
        })}
      </div>

      <ErrorNotice error={flow.error} />
      {flow.saved && <ResultCard files={flow.saved} onDismiss={flow.dismiss} onContinue={(f) => void pdf.open(f.path)} />}

      <div className="action-bar">
        <span className="muted">
          {files === 0 ? 'No pages selected' : `Creates ${files} ${files === 1 ? 'file' : 'files'}`}
        </span>
        <button
          type="button"
          className="btn btn-primary"
          disabled={flow.busy || files === 0 || !!planError}
          onClick={() =>
            flow.saveToFolder(dirname(doc.path), async (folder) => (await call('pdf_split', doc.path, folder, apiMode, value)).files)
          }
        >
          {flow.busy ? 'Splitting…' : 'Split and save to folder…'}
        </button>
      </div>
    </>
  )
}
