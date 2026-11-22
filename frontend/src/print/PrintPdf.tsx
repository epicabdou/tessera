import { useEffect, useMemo, useState } from 'react'
import { ErrorNotice } from '../components/ErrorNotice'
import { JobProgressBar } from '../components/JobProgressBar'
import { call, toError, type PdfInfo, type PrinterInfo } from '../lib/bridge'
import { cls } from '../lib/cls'
import { useJob } from '../lib/useJob'
import { useToolRequest } from '../lib/workspace'
import { DocGate, PagePreview, ResultCard } from '../pdf/components'
import { usePdfDoc } from '../pdf/context'
import { PageNav } from '../pdf/PageNav'
import { useSaveFlow } from '../pdf/useSaveFlow'

type Layout = 'normal' | 'nup' | 'booklet'
type Duplex = 'none' | 'long' | 'short'

const SHEETS: { id: string; label: string; mm: [number, number] }[] = [
  { id: 'a4', label: 'A4', mm: [210, 297] },
  { id: 'a3', label: 'A3', mm: [297, 420] },
  { id: 'a5', label: 'A5', mm: [148, 210] },
  { id: 'letter', label: 'Letter', mm: [216, 279] },
  { id: 'legal', label: 'Legal', mm: [216, 356] },
  { id: 'tabloid', label: 'Tabloid', mm: [279, 432] },
]
const PER_SHEET = [2, 4, 6, 9, 16]

/** Driver paper id matching a sheet size (within 2 mm), if the printer has one. */
function paperFor(printer: PrinterInfo | undefined, sheet: string): number | null {
  const s = SHEETS.find((x) => x.id === sheet)
  if (!printer || !s) return null
  const [w, h] = s.mm
  return printer.papers.find((p) => Math.abs(Math.min(p.w_mm, p.h_mm) - w) <= 2 && Math.abs(Math.max(p.w_mm, p.h_mm) - h) <= 2)?.id ?? null
}

/** Printers that write a file instead of paper. */
function fileType(name: string): { label: string; extensions: string[] } | null {
  if (/print to pdf/i.test(name)) return { label: 'PDF', extensions: ['pdf'] }
  if (/xps/i.test(name)) return { label: 'XPS document', extensions: ['oxps', 'xps'] }
  return null
}

export function PrintPdf() {
  const pdf = usePdfDoc()
  useToolRequest('print-pdf', (path) => void pdf.open(path))
  return (
    <section className="tool tool-wide">
      <header className="tool-header">
        <h1>Advanced Print</h1>
        <p>Print with full control over the paper, two-sided printing, pages per sheet, booklets, crop marks and scaling. The preview shows the sheets as they will come out.</p>
      </header>
      <DocGate>{(doc) => <PrintBody key={`${doc.path}|${doc.mtime}`} doc={doc} />}</DocGate>
    </section>
  )
}

function PrintBody({ doc }: { doc: PdfInfo }) {
  const flow = useSaveFlow()
  const job = useJob()
  const [printers, setPrinters] = useState<PrinterInfo[] | null>(null)
  const [printer, setPrinter] = useState('')
  const [copies, setCopies] = useState(1)
  const [collate, setCollate] = useState(true)
  const [pages, setPages] = useState('')
  const [reverse, setReverse] = useState(false)
  const [duplex, setDuplex] = useState<Duplex>('none')
  const [color, setColor] = useState(true)
  const [sheet, setSheet] = useState('auto')
  const [orientation, setOrientation] = useState<'auto' | 'portrait' | 'landscape'>('auto')
  const [scale, setScale] = useState<'fit' | 'actual' | 'custom'>('fit')
  const [percent, setPercent] = useState(100)
  const [layout, setLayout] = useState<Layout>('normal')
  const [perSheet, setPerSheet] = useState(2)
  const [frame, setFrame] = useState(false)
  const [marks, setMarks] = useState(false)
  const [bleed, setBleed] = useState(3)
  const [preview, setPreview] = useState<(PdfInfo & { sheets: number; source_pages: number }) | null>(null)
  const [previewError, setPreviewError] = useState<Error | null>(null)
  const [sheetIndex, setSheetIndex] = useState(0)
  const [error, setError] = useState<Error | null>(null)
  const [sent, setSent] = useState<string | null>(null)

  // Slow (network) printers report their capabilities late: ask again until all have.
  useEffect(() => {
    let active = true
    let timer = 0
    let attempts = 0
    const load = () => {
      call('printers').then(
        (list) => {
          if (!active) return
          setPrinters(list)
          setPrinter((name) => name || ((list.find((p) => p.default) ?? list[0])?.name ?? ''))
          if (list.some((p) => !p.ready) && ++attempts < 20) timer = window.setTimeout(load, 4000)
        },
        (err) => active && setError(toError(err)),
      )
    }
    load()
    return () => {
      active = false
      window.clearTimeout(timer)
    }
  }, [])

  const current = printers?.find((p) => p.name === printer)
  const canDuplex = !!current?.duplex
  const canColor = current ? current.color : true

  // Layout options (what the preview and the printer both use).
  const layoutOptions = useMemo(
    () => ({ pages, reverse, layout, per_sheet: perSheet, frame, sheet, orientation, marks, bleed_mm: marks ? bleed : 0 }),
    [pages, reverse, layout, perSheet, frame, sheet, orientation, marks, bleed],
  )
  const layoutKey = JSON.stringify(layoutOptions)

  useEffect(() => {
    let active = true
    const t = window.setTimeout(() => {
      call('print_preview', doc.path, JSON.parse(layoutKey)).then(
        (info) => {
          if (!active) return
          setPreview(info)
          setPreviewError(null)
          setSheetIndex((i) => Math.min(i, info.page_count - 1))
        },
        (err) => active && setPreviewError(toError(err)),
      )
    }, 300)
    return () => {
      active = false
      window.clearTimeout(t)
    }
  }, [layoutKey, doc.path])

  const options = {
    ...layoutOptions,
    copies,
    collate,
    duplex: canDuplex ? duplex : 'none',
    color: canColor && color,
    paper_id: paperFor(current, sheet),
    scale: scale === 'custom' ? percent : scale,
    auto_rotate: true,
  }

  const sheets = preview?.sheets ?? 0
  const paper = options.duplex === 'none' ? sheets : Math.ceil(sheets / 2)

  async function print() {
    setSent(null)
    setError(null)
    try {
      const type = fileType(printer)
      let output_file: string | undefined
      if (type) {
        const suggested = await call('frompdf_suggest', doc.path, type.extensions[0])
        const chosen = await call('save_file_dialog', suggested, type.label, type.extensions)
        if (!chosen) return
        output_file = chosen
      }
      const r = await job.run((id) => call('print_pdf', doc.path, printer, { ...options, output_file }, id))
      setSent(`Sent ${r.sheets} sheet${r.sheets === 1 ? '' : 's'}${r.copies > 1 ? ` × ${r.copies} copies` : ''} to ${r.printer}.`)
    } catch (err) {
      setError(toError(err))
    }
  }

  return (
    <div className="split-layout print-layout">
      <div className="split-main">
        {preview ? (
          <>
            <div className="sheet-stage">
              <PagePreview file={preview} index={sheetIndex} page={preview.pages[sheetIndex]} maxHeight={640} />
            </div>
            <PageNav index={sheetIndex} count={preview.page_count} onChange={setSheetIndex} />
            <p className="small muted center">
              {preview.source_pages} page{preview.source_pages === 1 ? '' : 's'} on {sheets} sheet side{sheets === 1 ? '' : 's'}
              {options.duplex !== 'none' && ` · ${paper} sheet${paper === 1 ? '' : 's'} of paper, two-sided`}
              {copies > 1 && ` · ${copies} copies`}
            </p>
          </>
        ) : (
          !previewError && <p className="muted">Preparing the preview…</p>
        )}
        <ErrorNotice error={previewError} />
      </div>
      <aside className="side-panel print-panel">
        <h2 className="panel-title">Printer</h2>
        <select className="text-input" value={printer} onChange={(e) => setPrinter(e.target.value)} disabled={!printers}>
          {!printers && <option>Looking for printers…</option>}
          {printers?.map((p) => (
            <option key={p.name} value={p.name}>
              {p.name}
              {p.default ? ' (default)' : ''}
              {p.ready ? '' : ' (checking…)'}
            </option>
          ))}
        </select>
        {printers?.length === 0 && <p className="small field-error">No printers are installed.</p>}
        {current && !current.ready && <p className="small muted">Asking this printer what it supports (two-sided, colour, paper)…</p>}
        <div className="field-grid">
          <label>
            Copies
            <input className="text-input num" type="number" min={1} max={999} value={copies} onChange={(e) => setCopies(Math.max(1, Math.min(999, Number(e.target.value) || 1)))} />
          </label>
          <label className="check">
            <input type="checkbox" checked={collate} disabled={copies < 2} onChange={(e) => setCollate(e.target.checked)} /> Collate
          </label>
          <label>
            Two-sided
            <select className="text-input" value={canDuplex ? duplex : 'none'} disabled={!canDuplex} onChange={(e) => setDuplex(e.target.value as Duplex)}>
              <option value="none">{canDuplex ? 'One-sided' : 'Not supported'}</option>
              <option value="long">Flip on long edge</option>
              <option value="short">Flip on short edge</option>
            </select>
          </label>
          <label>
            Colour
            <select className="text-input" value={canColor && color ? 'color' : 'gray'} disabled={!canColor} onChange={(e) => setColor(e.target.value === 'color')}>
              <option value="color">Colour</option>
              <option value="gray">Greyscale</option>
            </select>
          </label>
        </div>

        <h2 className="panel-title">Pages</h2>
        <div className="field-grid">
          <label>
            Page range
            <input className="text-input" value={pages} placeholder={`All ${doc.page_count}`} onChange={(e) => setPages(e.target.value)} spellCheck={false} />
          </label>
          <label className="check">
            <input type="checkbox" checked={reverse} onChange={(e) => setReverse(e.target.checked)} /> Reverse order
          </label>
        </div>

        <h2 className="panel-title">Layout</h2>
        <div className="segmented" role="radiogroup">
          {(
            [
              ['normal', 'One per sheet'],
              ['nup', 'Several per sheet'],
              ['booklet', 'Booklet'],
            ] as const
          ).map(([id, label]) => (
            <button
              key={id}
              type="button"
              role="radio"
              aria-checked={layout === id}
              className={cls('segment', layout === id && 'is-on')}
              onClick={() => {
                setLayout(id)
                if (id === 'booklet' && canDuplex) setDuplex('short')
              }}
            >
              {label}
            </button>
          ))}
        </div>
        {layout === 'nup' && (
          <div className="field-grid">
            <label>
              Pages per sheet
              <select className="text-input" value={perSheet} onChange={(e) => setPerSheet(Number(e.target.value))}>
                {PER_SHEET.map((n) => (
                  <option key={n} value={n}>
                    {n}
                  </option>
                ))}
              </select>
            </label>
            <label className="check">
              <input type="checkbox" checked={frame} onChange={(e) => setFrame(e.target.checked)} /> Page borders
            </label>
          </div>
        )}
        {layout === 'booklet' && (
          <p className="small muted">
            Pages are reordered two per sheet so the printout folds into a booklet. Print two-sided, flipping on the short edge{canDuplex ? '' : ' (this printer prints one side: feed the stack back in for the second side)'}.
          </p>
        )}
        <div className="field-grid">
          <label>
            Paper
            <select className="text-input" value={sheet} onChange={(e) => setSheet(e.target.value)}>
              <option value="auto">Same as the document</option>
              {SHEETS.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.label}
                </option>
              ))}
            </select>
          </label>
          <label>
            Orientation
            <select className="text-input" value={orientation} disabled={layout !== 'nup'} onChange={(e) => setOrientation(e.target.value as typeof orientation)}>
              <option value="auto">Automatic</option>
              <option value="portrait">Portrait</option>
              <option value="landscape">Landscape</option>
            </select>
          </label>
          <label>
            Scale
            <select className="text-input" value={scale} onChange={(e) => setScale(e.target.value as typeof scale)}>
              <option value="fit">Fit to printable area</option>
              <option value="actual">Actual size</option>
              <option value="custom">Custom…</option>
            </select>
          </label>
          {scale === 'custom' && (
            <label>
              Percent
              <input className="text-input num" type="number" min={10} max={400} value={percent} onChange={(e) => setPercent(Math.max(10, Math.min(400, Number(e.target.value) || 100)))} />
            </label>
          )}
        </div>

        <h2 className="panel-title">Press marks</h2>
        <label className="check">
          <input type="checkbox" checked={marks} disabled={layout !== 'normal'} onChange={(e) => setMarks(e.target.checked)} /> Crop marks
          {layout !== 'normal' && <span className="muted small"> (one page per sheet only)</span>}
        </label>
        {marks && layout === 'normal' && (
          <label className="range-field">
            Bleed ({bleed} mm)
            <input type="range" min={0} max={10} step={0.5} value={bleed} onChange={(e) => setBleed(Number(e.target.value))} />
          </label>
        )}

        <ErrorNotice error={error} />
        <JobProgressBar busy={job.busy} progress={job.progress} label="Preparing pages…" />
        <div className="button-row">
          <button type="button" className="btn btn-primary" disabled={job.busy || !printer || !preview} onClick={print}>
            {job.busy ? 'Printing…' : 'Print'}
          </button>
          <button
            type="button"
            className="btn btn-secondary"
            disabled={flow.busy || !preview}
            onClick={() => flow.saveAs(doc.path, 'print', (out) => call('print_save_pdf', doc.path, out, layoutOptions))}
          >
            Save layout as PDF…
          </button>
        </div>
        {sent && <p className="small">{sent}</p>}
        <ErrorNotice error={flow.error} />
        {flow.saved && <ResultCard files={flow.saved} onDismiss={flow.dismiss} />}
      </aside>
    </div>
  )
}
