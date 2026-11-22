import { useRef, useState, type PointerEvent } from 'react'
import { ErrorNotice } from '../../components/ErrorNotice'
import { call, toError, type Margins, type PdfInfo, type PdfPageInfo } from '../../lib/bridge'
import { cls } from '../../lib/cls'
import { MM_PER_POINT } from '../../lib/format'
import { useToolRequest } from '../../lib/workspace'
import { DocGate, PagePreview, ResultCard } from '../components'
import { usePdfDoc } from '../context'
import { PageNav } from '../PageNav'
import { useSaveFlow } from '../useSaveFlow'

type Side = keyof Margins
type Scope = 'all' | 'current' | 'range'

const SIDES: Side[] = ['top', 'right', 'bottom', 'left']
const NONE: Margins = { top: 0, right: 0, bottom: 0, left: 0 }
const MIN_SIZE = 18 // points; matches the Python side

const HANDLES: { name: string; edges: Side[] }[] = [
  { name: 'n', edges: ['top'] },
  { name: 'e', edges: ['right'] },
  { name: 's', edges: ['bottom'] },
  { name: 'w', edges: ['left'] },
  { name: 'ne', edges: ['top', 'right'] },
  { name: 'se', edges: ['bottom', 'right'] },
  { name: 'sw', edges: ['bottom', 'left'] },
  { name: 'nw', edges: ['top', 'left'] },
]

const clamp = (v: number, lo: number, hi: number) => Math.min(hi, Math.max(lo, v))
const toMm = (pt: number) => Math.round(pt * MM_PER_POINT * 10) / 10

export function CropPdf() {
  const pdf = usePdfDoc()
  useToolRequest('pdf-crop', (path) => void pdf.open(path))
  return (
    <section className="tool tool-wide">
      <header className="tool-header">
        <h1>Crop</h1>
        <p>Trim page margins. Drag the box or its handles, draw a new box, type exact margins, or auto-detect the content.</p>
      </header>
      <DocGate>{(doc) => <CropBody key={`${doc.path}|${doc.mtime}`} doc={doc} />}</DocGate>
    </section>
  )
}

function CropBody({ doc }: { doc: PdfInfo }) {
  const pdf = usePdfDoc()
  const [margins, setMargins] = useState<Margins>(NONE)
  const [current, setCurrent] = useState(0)
  const [scope, setScope] = useState<Scope>('all')
  const [range, setRange] = useState('')
  const [detecting, setDetecting] = useState(false)
  const [error, setError] = useState<Error | null>(null)
  const flow = useSaveFlow()
  const page = doc.pages[current]

  async function autoDetect() {
    setDetecting(true)
    setError(null)
    try {
      setMargins(await call('pdf_detect_margins', doc.path, current))
    } catch (err) {
      setError(toError(err))
    } finally {
      setDetecting(false)
    }
  }

  async function pagesToCrop(): Promise<number[] | null> {
    if (scope === 'all') return null
    if (scope === 'current') return [current]
    const [indexes] = await call('pdf_split_plan', doc.page_count, 'extract', range)
    return indexes
  }

  const width = page.width - margins.left - margins.right
  const height = page.height - margins.top - margins.bottom
  const cropped = SIDES.some((s) => margins[s] > 0)

  return (
    <div className="split-layout">
      <div className="split-main">
        <PagePreview
          file={doc}
          index={current}
          page={page}
          maxHeight={620}
          overlay={(scale) => <CropOverlay page={page} margins={margins} scale={scale} onChange={setMargins} />}
        />
        <PageNav index={current} count={doc.page_count} onChange={setCurrent} />
      </div>

      <aside className="side-panel">
        <h2 className="panel-title">Margins (mm)</h2>
        <div className="margin-grid">
          {SIDES.map((side) => (
            <label key={side} className={`margin-field m-${side}`}>
              <span>{side[0].toUpperCase() + side.slice(1)}</span>
              <input
                className="text-input num"
                type="number"
                min={0}
                step={0.5}
                value={toMm(margins[side])}
                onChange={(e) => {
                  const pt = Math.max(0, Number(e.target.value) / MM_PER_POINT)
                  if (Number.isFinite(pt)) setMargins((m) => ({ ...m, [side]: pt }))
                }}
              />
            </label>
          ))}
        </div>
        <div className="button-row">
          <button type="button" className="btn btn-secondary btn-sm" onClick={autoDetect} disabled={detecting}>
            {detecting ? 'Detecting…' : 'Auto-detect content'}
          </button>
          <button type="button" className="btn btn-ghost btn-sm" onClick={() => setMargins(NONE)} disabled={!cropped}>
            Reset
          </button>
        </div>
        <p className={cls('small', width < MIN_SIZE || height < MIN_SIZE ? 'field-error' : 'muted')}>
          Page {current + 1} becomes {toMm(width)} × {toMm(height)} mm
        </p>

        <h2 className="panel-title">Apply to</h2>
        <div className="radio-list" role="radiogroup">
          <label className="check">
            <input type="radio" checked={scope === 'all'} onChange={() => setScope('all')} /> All pages
          </label>
          <label className="check">
            <input type="radio" checked={scope === 'current'} onChange={() => setScope('current')} /> Only page {current + 1}
          </label>
          <label className="check">
            <input type="radio" checked={scope === 'range'} onChange={() => setScope('range')} /> Pages
            <input
              className="text-input grow"
              value={range}
              placeholder="e.g. 2-5, 8"
              spellCheck={false}
              onFocus={() => setScope('range')}
              onChange={(e) => setRange(e.target.value)}
            />
          </label>
        </div>
        <p className="muted small">The same margins are trimmed from each chosen page. Content outside the box is hidden, not deleted.</p>

        <ErrorNotice error={error} />
        <button
          type="button"
          className="btn btn-primary"
          disabled={flow.busy || !cropped || (scope === 'range' && !range.trim())}
          onClick={() =>
            flow.saveAs(doc.path, 'cropped', async (output) => call('pdf_crop', doc.path, output, margins, await pagesToCrop()))
          }
        >
          {flow.busy ? 'Saving…' : 'Save cropped PDF…'}
        </button>
        <ErrorNotice error={flow.error} />
        {flow.saved && <ResultCard files={flow.saved} onDismiss={flow.dismiss} onContinue={(f) => void pdf.open(f.path)} />}
      </aside>
    </div>
  )
}

function CropOverlay({
  page,
  margins,
  scale,
  onChange,
}: {
  page: PdfPageInfo
  margins: Margins
  scale: number
  onChange: (m: Margins) => void
}) {
  const W = page.width
  const H = page.height
  const drag = useRef<{ mode: Side[] | 'move' | 'draw'; x0: number; y0: number; start: Margins; origin: { x: number; y: number } } | null>(null)

  function begin(e: PointerEvent, mode: Side[] | 'move' | 'draw') {
    e.stopPropagation()
    e.preventDefault()
    const layer = (e.currentTarget as HTMLElement).closest('.crop-layer') as HTMLElement
    layer.setPointerCapture(e.pointerId)
    const r = layer.getBoundingClientRect()
    drag.current = {
      mode,
      x0: e.clientX,
      y0: e.clientY,
      start: margins,
      origin: { x: (e.clientX - r.left) / scale, y: (e.clientY - r.top) / scale },
    }
  }

  function move(e: PointerEvent) {
    const d = drag.current
    if (!d) return
    const dx = (e.clientX - d.x0) / scale
    const dy = (e.clientY - d.y0) / scale
    const s = d.start
    let m: Margins
    if (d.mode === 'move') {
      const w = W - s.left - s.right
      const h = H - s.top - s.bottom
      const left = clamp(s.left + dx, 0, W - w)
      const top = clamp(s.top + dy, 0, H - h)
      m = { left, top, right: W - w - left, bottom: H - h - top }
    } else if (d.mode === 'draw') {
      const x1 = clamp(d.origin.x + dx, 0, W)
      const y1 = clamp(d.origin.y + dy, 0, H)
      if (Math.abs(x1 - d.origin.x) < MIN_SIZE || Math.abs(y1 - d.origin.y) < MIN_SIZE) return
      m = {
        left: Math.min(d.origin.x, x1),
        right: W - Math.max(d.origin.x, x1),
        top: Math.min(d.origin.y, y1),
        bottom: H - Math.max(d.origin.y, y1),
      }
    } else {
      m = { ...s }
      for (const edge of d.mode) {
        if (edge === 'left') m.left = clamp(s.left + dx, 0, W - s.right - MIN_SIZE)
        if (edge === 'right') m.right = clamp(s.right - dx, 0, W - s.left - MIN_SIZE)
        if (edge === 'top') m.top = clamp(s.top + dy, 0, H - s.bottom - MIN_SIZE)
        if (edge === 'bottom') m.bottom = clamp(s.bottom - dy, 0, H - s.top - MIN_SIZE)
      }
    }
    onChange(m)
  }

  const end = () => {
    drag.current = null
  }

  return (
    <div
      className="crop-layer"
      onPointerDown={(e) => begin(e, 'draw')}
      onPointerMove={move}
      onPointerUp={end}
      onPointerCancel={end}
    >
      <div
        className="crop-rect"
        style={{
          left: margins.left * scale,
          top: margins.top * scale,
          width: Math.max(0, W - margins.left - margins.right) * scale,
          height: Math.max(0, H - margins.top - margins.bottom) * scale,
        }}
        onPointerDown={(e) => begin(e, 'move')}
      >
        {HANDLES.map((h) => (
          <span key={h.name} className={`crop-handle h-${h.name}`} onPointerDown={(e) => begin(e, h.edges)} />
        ))}
      </div>
    </div>
  )
}
