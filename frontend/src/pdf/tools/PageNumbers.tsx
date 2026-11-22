import { useState, type CSSProperties } from 'react'
import { ErrorNotice } from '../../components/ErrorNotice'
import { call, type PdfInfo } from '../../lib/bridge'
import { cls } from '../../lib/cls'
import { MM_PER_POINT } from '../../lib/format'
import { useToolRequest } from '../../lib/workspace'
import { DocGate, PagePreview, ResultCard } from '../components'
import { usePdfDoc } from '../context'
import { PageNav } from '../PageNav'
import { useSaveFlow } from '../useSaveFlow'

const FORMATS = [
  { value: '{n}', label: '1' },
  { value: 'Page {n}', label: 'Page 1' },
  { value: 'Page {n} of {total}', label: 'Page 1 of 9' },
  { value: '{n} / {total}', label: '1 / 9' },
  { value: '- {n} -', label: '- 1 -' },
  { value: 'custom', label: 'Custom…' },
]

const COLORS = [
  { value: '#000000', label: 'Black' },
  { value: '#444444', label: 'Dark grey' },
  { value: '#888888', label: 'Grey' },
  { value: '#ffffff', label: 'White' },
]

const VERTICAL = ['top', 'bottom'] as const
const HORIZONTAL = ['left', 'center', 'right'] as const

export function PageNumbers() {
  const pdf = usePdfDoc()
  useToolRequest('pdf-numbers', (path) => void pdf.open(path))
  return (
    <section className="tool tool-wide">
      <header className="tool-header">
        <h1>Page numbers</h1>
        <p>Stamp page numbers on the document: choose where, in what format, and which pages.</p>
      </header>
      <DocGate>{(doc) => <NumbersBody key={`${doc.path}|${doc.mtime}`} doc={doc} />}</DocGate>
    </section>
  )
}

function NumbersBody({ doc }: { doc: PdfInfo }) {
  const pdf = usePdfDoc()
  const n = doc.page_count
  const [position, setPosition] = useState('bottom-center')
  const [format, setFormat] = useState('{n}')
  const [custom, setCustom] = useState('Page {n}')
  const [start, setStart] = useState(1)
  const [firstPage, setFirstPage] = useState(1)
  const [lastPage, setLastPage] = useState(n)
  const [fontSize, setFontSize] = useState(11)
  const [marginMm, setMarginMm] = useState(12)
  const [color, setColor] = useState('#000000')
  const [mirror, setMirror] = useState(false)
  const [current, setCurrent] = useState(0)
  const flow = useSaveFlow()

  const template = format === 'custom' ? custom : format
  const total = start + (lastPage - firstPage)
  const problems = [
    !template.includes('{n}') && 'The format needs {n} where the number goes.',
    !(firstPage >= 1 && firstPage <= lastPage && lastPage <= n) && `Pages must be within 1–${n}, first ≤ last.`,
    !(fontSize >= 4 && fontSize <= 96) && 'Font size must be 4–96 pt.',
  ].filter(Boolean) as string[]

  const numberFor = (i: number) => (i + 1 >= firstPage && i + 1 <= lastPage ? start + (i - (firstPage - 1)) : null)
  const textFor = (i: number) => {
    const num = numberFor(i)
    return num === null ? null : template.replaceAll('{n}', String(num)).replaceAll('{total}', String(total))
  }

  const [vertical, horizontal] = position.split('-')
  const margin = marginMm / MM_PER_POINT

  function overlay(scale: number) {
    const text = textFor(current)
    if (text === null) return <span className="num-skip">Not numbered</span>
    let side = horizontal
    if (mirror && (current + 1) % 2 === 0 && side !== 'center') side = side === 'left' ? 'right' : 'left'
    const style: CSSProperties = { fontSize: fontSize * scale, color }
    // Approximate the PDF baseline/cap-height placement in CSS.
    if (vertical === 'top') style.top = (margin - fontSize * 0.21) * scale
    else style.bottom = (margin - fontSize * 0.21) * scale
    if (side === 'left') style.left = margin * scale
    else if (side === 'right') style.right = margin * scale
    else {
      style.left = '50%'
      style.transform = 'translateX(-50%)'
    }
    return (
      <span className={cls('num-preview', color.toLowerCase() === '#ffffff' && 'on-light')} style={style}>
        {text}
      </span>
    )
  }

  return (
    <div className="split-layout">
      <div className="split-main">
        <PagePreview file={doc} index={current} page={doc.pages[current]} maxHeight={620} overlay={overlay} />
        <PageNav index={current} count={n} onChange={setCurrent} />
      </div>

      <aside className="side-panel">
        <h2 className="panel-title">Position</h2>
        <div className="pos-picker" role="radiogroup" aria-label="Position">
          {VERTICAL.map((v) => (
            <div key={v} className="pos-row">
              {HORIZONTAL.map((h) => {
                const id = `${v}-${h}`
                return (
                  <button
                    key={id}
                    type="button"
                    role="radio"
                    aria-checked={position === id}
                    aria-label={`${v} ${h}`}
                    title={`${v} ${h}`}
                    className={cls('pos-cell', position === id && 'is-on')}
                    onClick={() => setPosition(id)}
                  >
                    <span className="pos-dot" />
                  </button>
                )
              })}
            </div>
          ))}
        </div>
        <label className="check">
          <input type="checkbox" checked={mirror} onChange={(e) => setMirror(e.target.checked)} />
          Mirror on even pages (double-sided)
        </label>

        <h2 className="panel-title">Format</h2>
        <select className="text-input" value={format} onChange={(e) => setFormat(e.target.value)} aria-label="Number format">
          {FORMATS.map((f) => (
            <option key={f.value} value={f.value}>
              {f.label}
            </option>
          ))}
        </select>
        {format === 'custom' && (
          <input
            className="text-input"
            value={custom}
            onChange={(e) => setCustom(e.target.value)}
            aria-label="Custom format"
            placeholder="e.g. Report – {n}/{total}"
            spellCheck={false}
          />
        )}
        <p className="muted small">Use {'{n}'} for the number and {'{total}'} for the last number.</p>

        <h2 className="panel-title">Pages</h2>
        <div className="field-grid">
          <label>
            Number pages
            <span className="inline-pair">
              <input className="text-input num" type="number" min={1} max={n} value={firstPage} onChange={(e) => setFirstPage(Number(e.target.value))} aria-label="First page" />
              to
              <input className="text-input num" type="number" min={1} max={n} value={lastPage} onChange={(e) => setLastPage(Number(e.target.value))} aria-label="Last page" />
            </span>
          </label>
          <label>
            First number
            <input className="text-input num" type="number" value={start} onChange={(e) => setStart(Number(e.target.value))} />
          </label>
        </div>

        <h2 className="panel-title">Style</h2>
        <div className="field-grid">
          <label>
            Size (pt)
            <input className="text-input num" type="number" min={4} max={96} value={fontSize} onChange={(e) => setFontSize(Number(e.target.value))} />
          </label>
          <label>
            Margin (mm)
            <input className="text-input num" type="number" min={0} step={0.5} value={marginMm} onChange={(e) => setMarginMm(Math.max(0, Number(e.target.value)))} />
          </label>
          <label>
            Colour
            <span className="inline-pair">
              <select className="text-input" value={COLORS.some((c) => c.value === color) ? color : ''} onChange={(e) => e.target.value && setColor(e.target.value)}>
                {COLORS.map((c) => (
                  <option key={c.value} value={c.value}>
                    {c.label}
                  </option>
                ))}
                <option value="">Custom</option>
              </select>
              <input type="color" value={color} onChange={(e) => setColor(e.target.value)} aria-label="Custom colour" />
            </span>
          </label>
        </div>

        {problems.map((p) => (
          <p key={p} className="field-error small">
            {p}
          </p>
        ))}
        <button
          type="button"
          className="btn btn-primary"
          disabled={flow.busy || problems.length > 0}
          onClick={() =>
            flow.saveAs(doc.path, 'numbered', (output) =>
              call('pdf_number_pages', doc.path, output, {
                position,
                template,
                start,
                first_page: firstPage,
                last_page: lastPage,
                font_size: fontSize,
                margin,
                color,
                mirror,
              }),
            )
          }
        >
          {flow.busy ? 'Saving…' : 'Add numbers and save…'}
        </button>
        <ErrorNotice error={flow.error} />
        {flow.saved && <ResultCard files={flow.saved} onDismiss={flow.dismiss} onContinue={(f) => void pdf.open(f.path)} />}
      </aside>
    </div>
  )
}
