import { useRef, useState, type CSSProperties, type DragEvent } from 'react'
import { DND_FILE } from '../browser/fileKinds'
import { ErrorNotice } from '../components/ErrorNotice'
import { ArrowDownIcon, ArrowUpIcon, CloseIcon, PlusIcon, RotateCcwIcon, RotateCwIcon } from '../components/icons'
import { call, toError, type ImagePdfOptions, type ImageThumb } from '../lib/bridge'
import { cls } from '../lib/cls'
import { dirname, samePath } from '../lib/format'
import { CONVERT_EXTS, extOf, useToolRequest, useWorkspace } from '../lib/workspace'
import { ResultCard } from '../pdf/components'
import { useSaveFlow } from '../pdf/useSaveFlow'
import { EmptyDrop, OutputChooser } from './shared'

interface Img extends ImageThumb {
  key: number
  rotate: number
}

const EXTS = CONVERT_EXTS['to-pdf-images'] ?? []
const DND_ITEM = 'application/x-toolbox-image-item'

/** Page sizes in points (portrait), matching the Python side. */
const PAGE: Record<Exclude<ImagePdfOptions['page_size'], 'fit'>, [number, number]> = {
  a4: [595.28, 841.89],
  letter: [612, 792],
  legal: [612, 1008],
  a3: [841.89, 1190.55],
  a5: [419.53, 595.28],
}
const MARGIN_PT = { none: 0, small: 28.35, large: 56.69 }
const MOCK = 64 // px, longest side of the page mock

export function ImagesToPdf() {
  const { selected, openInTool } = useWorkspace()
  const [items, setItems] = useState<Img[]>([])
  const [options, setOptions] = useState<ImagePdfOptions>({ page_size: 'a4', orientation: 'auto', margin: 'small', fit: 'contain' })
  const [mode, setMode] = useState<'single' | 'each'>('single')
  const [folder, setFolder] = useState<string | null>(null)
  const [notice, setNotice] = useState<Error | null>(null)
  const [dropSlot, setDropSlot] = useState<number | null>(null)
  const listRef = useRef<HTMLOListElement>(null)
  const seq = useRef(1)
  const flow = useSaveFlow()

  async function add(paths: string[], at?: number) {
    const ok = paths.filter((p) => EXTS.includes(extOf(p)))
    setNotice(ok.length < paths.length ? new Error('Skipped files that aren’t supported images.') : null)
    if (!ok.length) return
    try {
      const thumbs = await call('image_thumbnails', ok, 160)
      const bad = thumbs.filter((t) => t.error)
      if (bad.length) setNotice(new Error(`Couldn't read ${bad.map((b) => b.name).join(', ')}`))
      setItems((list) => {
        const fresh = thumbs.filter((t) => !t.error && !list.some((i) => samePath(i.path, t.path))).map((t) => ({ ...t, key: seq.current++, rotate: 0 }))
        const slot = at ?? list.length
        return [...list.slice(0, slot), ...fresh, ...list.slice(slot)]
      })
    } catch (err) {
      setNotice(toError(err))
    }
  }

  useToolRequest('to-pdf-images', (path) => void add([path]))

  async function pick() {
    try {
      const paths = await call('pick_files', 'Images', EXTS, true)
      if (paths.length) await add(paths)
    } catch (err) {
      setNotice(toError(err))
    }
  }

  const update = (key: number, patch: Partial<Img>) => setItems((list) => list.map((i) => (i.key === key ? { ...i, ...patch } : i)))
  const move = (from: number, to: number) =>
    setItems((list) => {
      if (to < 0 || to >= list.length || from === to) return list
      const next = [...list]
      const [it] = next.splice(from, 1)
      next.splice(to, 0, it)
      return next
    })

  // --- drag & drop: images from the Explorer, and reordering ---------------------
  function slotAt(e: DragEvent) {
    for (const el of listRef.current?.querySelectorAll<HTMLElement>('[data-img-index]') ?? []) {
      const r = el.getBoundingClientRect()
      if (e.clientY < r.top + r.height / 2) return Number(el.dataset.imgIndex)
    }
    return items.length
  }
  const accepts = (e: DragEvent) => e.dataTransfer.types.includes(DND_FILE) || e.dataTransfer.types.includes(DND_ITEM)
  function onDrop(e: DragEvent) {
    if (!accepts(e)) return
    e.preventDefault()
    const slot = slotAt(e)
    setDropSlot(null)
    const key = e.dataTransfer.getData(DND_ITEM)
    if (key) {
      const from = items.findIndex((i) => String(i.key) === key)
      if (from !== -1) move(from, slot > from ? slot - 1 : slot)
    } else {
      void add([e.dataTransfer.getData(DND_FILE)], slot)
    }
  }

  function convert() {
    const payload = items.map((i) => ({ path: i.path, rotate: i.rotate }))
    if (mode === 'each') {
      return flow.runSave(() => call('images_to_pdfs', payload, folder, options))
    }
    const first = items[0].path
    const source = items.length === 1 ? first : `${dirname(first)}\\images`
    return flow.saveTo(
      () => call('suggest_pdf_path', source, 'images'),
      (output) => call('images_to_pdf', payload, output, options),
    )
  }

  const selectedImage = selected && !selected.is_dir && EXTS.includes(extOf(selected.path)) ? selected : null
  const pages = items.reduce((n, i) => n + (i.pages ?? 1), 0)
  const fitToImage = options.page_size === 'fit'

  return (
    <section className="tool">
      <header className="tool-header">
        <h1>JPG to PDF</h1>
        <p>Turn images into PDF pages. JPEGs are embedded untouched (no quality loss); PNG, GIF, BMP, TIFF and WebP are stored losslessly.</p>
      </header>

      <div className="button-row">
        <button type="button" className="btn btn-secondary" onClick={pick}>
          <PlusIcon size={15} /> Add images…
        </button>
        {selectedImage && (
          <button type="button" className="btn btn-secondary" onClick={() => add([selectedImage.path])}>
            Add {selectedImage.name}
          </button>
        )}
        {items.length > 1 && (
          <button
            type="button"
            className="btn btn-ghost btn-sm"
            onClick={() => setItems((l) => [...l].sort((a, b) => a.name.localeCompare(b.name, undefined, { numeric: true })))}
          >
            Sort A–Z
          </button>
        )}
        {items.length > 0 && (
          <button type="button" className="btn btn-ghost btn-sm" onClick={() => setItems([])}>
            Clear list
          </button>
        )}
      </div>

      <ErrorNotice error={notice} />

      <ol
        ref={listRef}
        className={cls('conv-list', 'img-list', dropSlot !== null && 'is-over')}
        onDragOver={(e) => {
          if (!accepts(e)) return
          e.preventDefault()
          setDropSlot(slotAt(e))
        }}
        onDragLeave={(e) => {
          if (!e.currentTarget.contains(e.relatedTarget as Node | null)) setDropSlot(null)
        }}
        onDrop={onDrop}
      >
        {items.length === 0 && (
          <li>
            <EmptyDrop icon={<PlusIcon size={26} />} over={dropSlot !== null}>
              Drag images here from the Explorer, or use Add images.
            </EmptyDrop>
          </li>
        )}
        {items.map((img, i) => (
          <li
            key={img.key}
            data-img-index={i}
            className={cls('conv-row', 'img-row', dropSlot === i && 'drop-before')}
            draggable
            onDragStart={(e) => {
              e.dataTransfer.setData(DND_ITEM, String(img.key))
              e.dataTransfer.effectAllowed = 'move'
            }}
          >
            <span className="merge-pos">{i + 1}</span>
            <PageMock img={img} options={options} />
            <div className="conv-meta">
              <strong title={img.path}>{img.name}</strong>
              <span className="muted small">
                {img.width} × {img.height} px{(img.pages ?? 1) > 1 ? ` · ${img.pages} pages` : ''}
                {img.rotate ? ` · turned ${img.rotate}°` : ''}
              </span>
            </div>
            <div className="row-actions">
              <button type="button" className="icon-btn" title="Rotate left" aria-label="Rotate left" onClick={() => update(img.key, { rotate: (img.rotate + 270) % 360 })}>
                <RotateCcwIcon size={14} />
              </button>
              <button type="button" className="icon-btn" title="Rotate right" aria-label="Rotate right" onClick={() => update(img.key, { rotate: (img.rotate + 90) % 360 })}>
                <RotateCwIcon size={14} />
              </button>
              <button type="button" className="icon-btn" title="Move up" aria-label="Move up" disabled={i === 0} onClick={() => move(i, i - 1)}>
                <ArrowUpIcon size={14} />
              </button>
              <button type="button" className="icon-btn" title="Move down" aria-label="Move down" disabled={i === items.length - 1} onClick={() => move(i, i + 1)}>
                <ArrowDownIcon size={14} />
              </button>
              <button type="button" className="icon-btn" title="Remove" aria-label="Remove" onClick={() => setItems((l) => l.filter((x) => x.key !== img.key))}>
                <CloseIcon size={14} />
              </button>
            </div>
          </li>
        ))}
        {dropSlot !== null && dropSlot === items.length && items.length > 0 && <li className="drop-end" aria-hidden="true" />}
      </ol>

      <div className="card conv-options">
        <h2 className="card-title">Page setup</h2>
        <div className="opt-grid">
          <label>
            Page size
            <select className="text-input" value={options.page_size} onChange={(e) => setOptions((o) => ({ ...o, page_size: e.target.value as ImagePdfOptions['page_size'] }))}>
              <option value="fit">Same as image</option>
              <option value="a4">A4</option>
              <option value="letter">Letter</option>
              <option value="legal">Legal</option>
              <option value="a3">A3</option>
              <option value="a5">A5</option>
            </select>
          </label>
          <label>
            Orientation
            <select
              className="text-input"
              value={options.orientation}
              disabled={fitToImage}
              onChange={(e) => setOptions((o) => ({ ...o, orientation: e.target.value as ImagePdfOptions['orientation'] }))}
            >
              <option value="auto">Match each image</option>
              <option value="portrait">Portrait</option>
              <option value="landscape">Landscape</option>
            </select>
          </label>
          <label>
            Margin
            <select className="text-input" value={options.margin} onChange={(e) => setOptions((o) => ({ ...o, margin: e.target.value as ImagePdfOptions['margin'] }))}>
              <option value="none">None</option>
              <option value="small">Small (10 mm)</option>
              <option value="large">Large (20 mm)</option>
            </select>
          </label>
          <label>
            Image
            <select
              className="text-input"
              value={options.fit}
              disabled={fitToImage}
              onChange={(e) => setOptions((o) => ({ ...o, fit: e.target.value as ImagePdfOptions['fit'] }))}
            >
              <option value="contain">Fit whole image</option>
              <option value="fill">Fill page (crop edges)</option>
            </select>
          </label>
        </div>
        <div className="output-chooser" role="radiogroup" aria-label="Output">
          <label className="check">
            <input type="radio" checked={mode === 'single'} onChange={() => setMode('single')} /> One PDF with all images
          </label>
          <label className="check">
            <input type="radio" checked={mode === 'each'} onChange={() => setMode('each')} /> One PDF per image
          </label>
        </div>
        {mode === 'each' && <OutputChooser folder={folder} onChange={setFolder} what="image" />}
      </div>

      <div className="action-bar">
        <span className="muted">
          {items.length} {items.length === 1 ? 'image' : 'images'} · {pages} {pages === 1 ? 'page' : 'pages'}
        </span>
        <button type="button" className="btn btn-primary" disabled={flow.busy || items.length === 0} onClick={convert}>
          {flow.busy ? 'Converting…' : mode === 'each' ? 'Convert each to PDF' : 'Convert and save…'}
        </button>
      </div>

      <ErrorNotice error={flow.error} />
      {flow.saved && <ResultCard files={flow.saved} onDismiss={flow.dismiss} onContinue={(f) => openInTool('pdf-pages', f.path)} />}
    </section>
  )
}

/** A small picture of the PDF page this image will become. */
function PageMock({ img, options }: { img: Img; options: ImagePdfOptions }) {
  const turned = img.rotate % 180 !== 0
  const iw = turned ? (img.height ?? 1) : (img.width ?? 1)
  const ih = turned ? (img.width ?? 1) : (img.height ?? 1)
  const margin = MARGIN_PT[options.margin]
  let pw: number
  let ph: number
  if (options.page_size === 'fit') {
    const pt = 72 / 96
    pw = iw * pt + 2 * margin
    ph = ih * pt + 2 * margin
  } else {
    ;[pw, ph] = PAGE[options.page_size]
    const landscape = options.orientation === 'auto' ? iw > ih : options.orientation === 'landscape'
    if (landscape) [pw, ph] = [ph, pw]
  }
  const k = MOCK / Math.max(pw, ph)
  const boxW = (pw - 2 * margin) * k
  const boxH = (ph - 2 * margin) * k
  const fill = options.fit === 'fill' && options.page_size !== 'fit'
  const s = (fill ? Math.max : Math.min)(boxW / iw, boxH / ih)
  const dw = iw * s
  const dh = ih * s
  const imgStyle: CSSProperties = {
    width: turned ? dh : dw,
    height: turned ? dw : dh,
    transform: `translate(-50%, -50%) rotate(${img.rotate}deg)`,
  }
  return (
    <div className="page-mock-wrap">
      <div className="page-mock" style={{ width: pw * k, height: ph * k }}>
        <div className="page-mock-box" style={{ left: margin * k, top: margin * k, width: boxW, height: boxH }}>
          {img.data_url && <img src={img.data_url} alt="" draggable={false} style={imgStyle} />}
        </div>
      </div>
    </div>
  )
}
