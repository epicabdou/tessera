import { useEffect, useState } from 'react'
import { ErrorNotice } from '../components/ErrorNotice'
import { call, toError, type PdfInfo } from '../lib/bridge'
import { cls } from '../lib/cls'
import { CONVERT_EXTS, useToolRequest } from '../lib/workspace'
import { DocGate, PagePreview, ResultCard } from '../pdf/components'
import { usePdfDoc } from '../pdf/context'
import { PageNav } from '../pdf/PageNav'
import { useSaveFlow } from '../pdf/useSaveFlow'

const POSITIONS = ['top-left', 'top-center', 'top-right', 'middle-left', 'middle-center', 'middle-right', 'bottom-left', 'bottom-center', 'bottom-right']

export function Watermark() {
  const pdf = usePdfDoc()
  useToolRequest('watermark', (path) => void pdf.open(path))
  return (
    <section className="tool tool-wide">
      <header className="tool-header">
        <h1>Watermark</h1>
        <p>Stamp text or an image over (or under) the pages. The preview shows exactly what will be saved.</p>
      </header>
      <DocGate>{(doc) => <WatermarkBody key={`${doc.path}|${doc.mtime}`} doc={doc} />}</DocGate>
    </section>
  )
}

function WatermarkBody({ doc }: { doc: PdfInfo }) {
  const pdf = usePdfDoc()
  const flow = useSaveFlow()
  const [kind, setKind] = useState<'text' | 'image'>('text')
  const [text, setText] = useState('CONFIDENTIAL')
  const [family, setFamily] = useState('sans')
  const [bold, setBold] = useState(true)
  const [size, setSize] = useState(60)
  const [color, setColor] = useState('#d32f2f')
  const [opacity, setOpacity] = useState(25)
  const [rotation, setRotation] = useState(45)
  const [position, setPosition] = useState('middle-center')
  const [layer, setLayer] = useState<'over' | 'under'>('over')
  const [pages, setPages] = useState('')
  const [image, setImage] = useState<string | null>(null)
  const [scale, setScale] = useState(40)
  const [current, setCurrent] = useState(0)
  const [preview, setPreview] = useState<PdfInfo | null>(null)
  const [error, setError] = useState<Error | null>(null)

  const options = {
    kind,
    text,
    family,
    bold,
    size,
    color,
    opacity: opacity / 100,
    rotation,
    position,
    layer,
    pages,
    image: image ?? '',
    scale: scale / 100,
  }
  const key = JSON.stringify(options)
  const ready = kind === 'text' ? text.trim() !== '' : !!image

  // Render the real watermark on the current page (debounced) for an exact preview.
  useEffect(() => {
    if (!ready) return
    let active = true
    const t = window.setTimeout(() => {
      call('pdf_watermark_preview', doc.path, JSON.parse(key), current).then(
        (info) => {
          if (active) {
            setPreview(info)
            setError(null)
          }
        },
        (err) => active && setError(toError(err)),
      )
    }, 350)
    return () => {
      active = false
      window.clearTimeout(t)
    }
  }, [key, current, doc.path, ready])

  async function pickImage() {
    try {
      const [path] = await call('pick_files', 'Images', CONVERT_EXTS['to-pdf-images'] ?? [], false)
      if (path) setImage(path)
    } catch (err) {
      setError(toError(err))
    }
  }

  return (
    <div className="split-layout">
      <div className="split-main">
        {preview ? (
          <PagePreview file={preview} index={0} page={preview.pages[0]} maxHeight={700} />
        ) : (
          <PagePreview file={doc} index={current} page={doc.pages[current]} maxHeight={700} />
        )}
        <PageNav index={current} count={doc.page_count} onChange={setCurrent} />
      </div>
      <aside className="side-panel">
        <div className="segmented" role="radiogroup">
          {(['text', 'image'] as const).map((k) => (
            <button key={k} type="button" role="radio" aria-checked={kind === k} className={cls('segment', kind === k && 'is-on')} onClick={() => setKind(k)}>
              {k === 'text' ? 'Text' : 'Image'}
            </button>
          ))}
        </div>
        {kind === 'text' ? (
          <>
            <input className="text-input" value={text} onChange={(e) => setText(e.target.value)} aria-label="Watermark text" />
            <div className="field-grid">
              <label>
                Font
                <select className="text-input" value={family} onChange={(e) => setFamily(e.target.value)}>
                  <option value="sans">Arial</option>
                  <option value="serif">Times New Roman</option>
                  <option value="mono">Courier New</option>
                </select>
              </label>
              <label>
                Size (pt)
                <input className="text-input num" type="number" min={6} max={300} value={size} onChange={(e) => setSize(Number(e.target.value))} />
              </label>
              <label>
                Colour
                <input type="color" value={color} onChange={(e) => setColor(e.target.value)} />
              </label>
              <label className="check">
                <input type="checkbox" checked={bold} onChange={(e) => setBold(e.target.checked)} /> Bold
              </label>
            </div>
          </>
        ) : (
          <div className="button-row">
            <button type="button" className="btn btn-secondary btn-sm" onClick={pickImage}>
              {image ? 'Change image…' : 'Choose image…'}
            </button>
            {image && <span className="small mono">{image.split(/[\\/]/).pop()}</span>}
            <label className="range-field">
              Size ({scale}% of page width)
              <input type="range" min={5} max={100} value={scale} onChange={(e) => setScale(Number(e.target.value))} />
            </label>
          </div>
        )}
        <label className="range-field">
          Opacity ({opacity}%)
          <input type="range" min={5} max={100} value={opacity} onChange={(e) => setOpacity(Number(e.target.value))} />
        </label>
        <label className="range-field">
          Rotation ({rotation}°)
          <input type="range" min={-90} max={90} step={5} value={rotation} onChange={(e) => setRotation(Number(e.target.value))} />
        </label>
        <h2 className="panel-title">Position</h2>
        <div className="wm-grid">
          {POSITIONS.map((p) => (
            <button key={p} type="button" className={cls('pos-cell', position === p && 'is-on')} title={p.replace('-', ' ')} onClick={() => setPosition(p)}>
              <span className="pos-dot" />
            </button>
          ))}
        </div>
        <label className="check">
          <input type="checkbox" checked={position === 'tile'} onChange={(e) => setPosition(e.target.checked ? 'tile' : 'middle-center')} /> Repeat across the page (tile)
        </label>
        <div className="field-grid">
          <label>
            Layer
            <select className="text-input" value={layer} onChange={(e) => setLayer(e.target.value as 'over' | 'under')}>
              <option value="over">Over the content</option>
              <option value="under">Behind the content</option>
            </select>
          </label>
          <label>
            Pages
            <input className="text-input" value={pages} placeholder="All" onChange={(e) => setPages(e.target.value)} spellCheck={false} />
          </label>
        </div>
        <ErrorNotice error={error} />
        <button
          type="button"
          className="btn btn-primary"
          disabled={flow.busy || !ready}
          onClick={() => flow.saveAs(doc.path, 'watermarked', (out) => call('pdf_watermark', doc.path, out, options))}
        >
          {flow.busy ? 'Saving…' : 'Add watermark and save…'}
        </button>
        <ErrorNotice error={flow.error} />
        {flow.saved && <ResultCard files={flow.saved} onDismiss={flow.dismiss} onContinue={(f) => void pdf.open(f.path)} />}
      </aside>
    </div>
  )
}
