import { useState } from 'react'
import { ErrorNotice } from '../components/ErrorNotice'
import { RotateCcwIcon, RotateCwIcon } from '../components/icons'
import { call, toError, type ImageInfo, type ImageView, type SavedImage } from '../lib/bridge'
import { cls } from '../lib/cls'
import { useToolRequest } from '../lib/workspace'
import { useJob } from '../lib/useJob'
import { ResultCard } from '../pdf/components'
import { useSaveFlow } from '../pdf/useSaveFlow'
import { BatchRun, FormatSelect, ImageGate, ImageListView, ImageStage, QualityField } from './components'
import { useImageDoc, outputExt } from './context'
import { CropBox } from './CropBox'
import { useImageList, useImagePreview } from './hooks'
import { fitAspect } from './resize'

// --- Crop ---------------------------------------------------------------------------------

const ASPECTS: { id: string; label: string; ratio: number | null | 'original' }[] = [
  { id: 'free', label: 'Free', ratio: null },
  { id: 'original', label: 'Original', ratio: 'original' },
  { id: '1:1', label: '1:1', ratio: 1 },
  { id: '4:3', label: '4:3', ratio: 4 / 3 },
  { id: '3:4', label: '3:4', ratio: 3 / 4 },
  { id: '16:9', label: '16:9', ratio: 16 / 9 },
  { id: '9:16', label: '9:16', ratio: 9 / 16 },
  { id: '3:2', label: '3:2', ratio: 3 / 2 },
  { id: '2:3', label: '2:3', ratio: 2 / 3 },
  { id: '5:4', label: '5:4', ratio: 5 / 4 },
  { id: '4:5', label: '4:5', ratio: 4 / 5 },
]

export function CropImage() {
  const doc = useImageDoc()
  useToolRequest('img-crop', (path) => void doc.open(path))
  return (
    <section className="tool tool-wide">
      <header className="tool-header">
        <h1>Crop Image</h1>
        <p>Trim the edges or frame an exact aspect ratio. Drag the box or its corners, or draw a new one; type exact pixels if you need them.</p>
      </header>
      <ImageGate>{(image) => <CropBody key={`${image.path}|${image.mtime}`} image={image} />}</ImageGate>
    </section>
  )
}

function CropBody({ image }: { image: ImageInfo }) {
  const doc = useImageDoc()
  const flow = useSaveFlow()
  const { url, error } = useImagePreview(image)
  const [aspectId, setAspectId] = useState('free')
  const [rect, setRect] = useState(() => ({ x: Math.round(image.width * 0.1), y: Math.round(image.height * 0.1), w: Math.round(image.width * 0.8), h: Math.round(image.height * 0.8) }))
  const [shape, setShape] = useState<'rect' | 'circle'>('rect')
  const [format, setFormat] = useState('keep')
  const [quality, setQuality] = useState(92)
  const preset = ASPECTS.find((a) => a.id === aspectId)!
  const aspect = shape === 'circle' && preset.ratio === null ? null : preset.ratio === 'original' ? image.width / image.height : preset.ratio

  function chooseAspect(id: string) {
    setAspectId(id)
    const p = ASPECTS.find((a) => a.id === id)!
    if (p.ratio !== null) setRect(fitAspect(image.width, image.height, p.ratio === 'original' ? image.width / image.height : p.ratio))
  }

  const setField = (key: 'x' | 'y' | 'w' | 'h', v: number) =>
    setRect((r) => {
      const next = { ...r, [key]: Math.max(0, v) }
      if (aspect && key === 'w') next.h = next.w / aspect
      if (aspect && key === 'h') next.w = next.h * aspect
      next.w = Math.min(next.w, image.width - next.x)
      next.h = Math.min(next.h, image.height - next.y)
      return next
    })

  const fmt = shape === 'circle' && (format === 'keep' ? !['png', 'webp', 'avif'].includes(outputExt(image.path, 'keep')) : format === 'jpg') ? 'png' : format
  const ext = outputExt(image.path, fmt)

  return (
    <div className="split-layout">
      <div className="split-main">
        <ImageStage src={url} width={image.width} height={image.height} overlay={(scale) => <CropBox width={image.width} height={image.height} scale={scale} rect={rect} aspect={aspect} round={shape === 'circle'} onChange={setRect} />} />
        <ErrorNotice error={error} />
      </div>
      <aside className="side-panel">
        <h2 className="panel-title">Aspect ratio</h2>
        <div className="aspect-grid">
          {ASPECTS.map((a) => (
            <button key={a.id} type="button" className={cls('chip-btn', aspectId === a.id && 'is-on')} onClick={() => chooseAspect(a.id)}>
              {a.label}
            </button>
          ))}
        </div>
        <h2 className="panel-title">Area (pixels)</h2>
        <div className="xywh">
          {(['x', 'y', 'w', 'h'] as const).map((k) => (
            <label key={k}>
              {k === 'w' ? 'Width' : k === 'h' ? 'Height' : k.toUpperCase()}
              <input className="text-input num" type="number" min={0} value={Math.round(rect[k])} onChange={(e) => setField(k, Number(e.target.value))} />
            </label>
          ))}
        </div>
        <h2 className="panel-title">Shape</h2>
        <div className="segmented">
          {(['rect', 'circle'] as const).map((s) => (
            <button key={s} type="button" className={cls('segment', shape === s && 'is-on')} onClick={() => setShape(s)}>
              {s === 'rect' ? 'Rectangle' : 'Circle / oval'}
            </button>
          ))}
        </div>
        {shape === 'circle' && <p className="muted small">Outside the circle becomes transparent, so it's saved as PNG unless you pick WebP or AVIF.</p>}
        <div className="field-stack">
          <FormatSelect value={format} onChange={setFormat} formats={['jpg', 'png', 'webp', 'avif']} />
          {!['png'].includes(ext) && <QualityField value={quality} onChange={setQuality} />}
        </div>
        <button
          type="button"
          className="btn btn-primary"
          disabled={flow.busy}
          onClick={() =>
            flow.saveTo(
              () => call('image_suggest', image.path, '_cropped', fmt === 'keep' ? 'keep' : fmt),
              (out) => call('image_crop', image.path, out, rect, { format: fmt, quality, shape }),
              { label: 'Image', extensions: [ext] },
            )
          }
        >
          {flow.busy ? 'Saving…' : 'Crop and save…'}
        </button>
        <ErrorNotice error={flow.error} />
        {flow.saved && <ResultCard files={flow.saved} onDismiss={flow.dismiss} onContinue={(f) => void doc.open(f.path)} />}
      </aside>
    </div>
  )
}

// --- Rotate -------------------------------------------------------------------------------

export function RotateImage() {
  const list = useImageList('img-rotate')
  const flow = useSaveFlow()
  const job = useJob()
  const [folder, setFolder] = useState<string | null>(null)
  const [format, setFormat] = useState('keep')
  const [quality, setQuality] = useState(95)

  const turn = (path: string, delta: number) => {
    const item = list.items.find((i) => i.path === path)
    list.update(path, { turns: (((item?.turns ?? 0) + delta) % 4 + 4) % 4 })
  }
  const all = (fn: (path: string) => void) => list.good.forEach((i) => fn(i.path))
  const flip = (path: string, key: 'flipH' | 'flipV') => list.update(path, { [key]: !list.items.find((i) => i.path === path)?.[key] })
  const changed = list.good.filter((i) => i.turns || i.flipH || i.flipV)

  return (
    <section className="tool">
      <header className="tool-header">
        <h1>Rotate Image</h1>
        <p>Turn images by 90°, 180° or 270°, or mirror them. Set each image on its own, or all at once.</p>
      </header>
      <div className="toolbar">
        <span className="muted small">All images:</span>
        <button type="button" className="btn btn-ghost btn-sm" onClick={() => all((p) => turn(p, -1))}>
          <RotateCcwIcon size={14} /> Left
        </button>
        <button type="button" className="btn btn-ghost btn-sm" onClick={() => all((p) => turn(p, 1))}>
          <RotateCwIcon size={14} /> Right
        </button>
        <button type="button" className="btn btn-ghost btn-sm" onClick={() => all((p) => turn(p, 2))}>
          180°
        </button>
        <button type="button" className="btn btn-ghost btn-sm" onClick={() => all((p) => flip(p, 'flipH'))}>
          Flip horizontally
        </button>
        <button type="button" className="btn btn-ghost btn-sm" onClick={() => all((p) => flip(p, 'flipV'))}>
          Flip vertically
        </button>
        <span className="toolbar-spacer" />
        <button type="button" className="btn btn-ghost btn-sm" onClick={() => all((p) => list.update(p, { turns: 0, flipH: false, flipV: false }))}>
          Reset
        </button>
      </div>
      <ImageListView
        list={list}
        thumbStyle={(i) => ({ transform: `scale(${i.flipH ? -1 : 1}, ${i.flipV ? -1 : 1}) rotate(${(i.turns ?? 0) * 90}deg)` })}
        extra={(i) => (
          <span className="row-actions">
            <button type="button" className="icon-btn" aria-label="Rotate left" title="Rotate left" onClick={(e) => (e.stopPropagation(), turn(i.path, -1))}>
              <RotateCcwIcon size={15} />
            </button>
            <button type="button" className="icon-btn" aria-label="Rotate right" title="Rotate right" onClick={(e) => (e.stopPropagation(), turn(i.path, 1))}>
              <RotateCwIcon size={15} />
            </button>
            <button type="button" className={cls('icon-btn', i.flipH && 'is-on')} aria-label="Flip horizontally" title="Flip horizontally" onClick={(e) => (e.stopPropagation(), flip(i.path, 'flipH'))}>
              ⇋
            </button>
            <button type="button" className={cls('icon-btn', i.flipV && 'is-on')} aria-label="Flip vertically" title="Flip vertically" onClick={(e) => (e.stopPropagation(), flip(i.path, 'flipV'))}>
              ⇵
            </button>
          </span>
        )}
      />
      <ErrorNotice error={list.error} />
      <div className="card conv-options">
        <div className="opt-grid">
          <FormatSelect value={format} onChange={setFormat} formats={['jpg', 'png', 'webp', 'avif']} />
          <QualityField value={quality} onChange={setQuality} />
        </div>
      </div>
      <BatchRun
        count={changed.length}
        label="Rotate and save"
        folder={folder}
        onFolder={setFolder}
        flow={flow}
        job={job}
        note={list.good.length > 0 && !changed.length ? <span className="muted small">Turn or flip at least one image.</span> : undefined}
        onRun={() =>
          flow.runSave(() =>
            job.run((id) =>
              call(
                'image_rotate',
                changed.map((i) => ({ path: i.path, turns: i.turns ?? 0, flip_h: !!i.flipH, flip_v: !!i.flipV })),
                folder,
                { format, quality },
                id,
              ),
            ),
          )
        }
      />
    </section>
  )
}

// --- HTML to image ------------------------------------------------------------------------

const VIEWPORTS = [
  { id: 1440, label: 'Desktop (1440 px)' },
  { id: 1280, label: 'Laptop (1280 px)' },
  { id: 768, label: 'Tablet (768 px)' },
  { id: 390, label: 'Phone (390 px)' },
  { id: 0, label: 'Custom…' },
]

export function HtmlToImage() {
  const flow = useSaveFlow()
  const [kind, setKind] = useState<'url' | 'file' | 'code'>('url')
  const [url, setUrl] = useState('')
  const [file, setFile] = useState<string | null>(null)
  const [code, setCode] = useState('<div style="padding:40px;font:600 42px Segoe UI;background:linear-gradient(135deg,#6a5cff,#22b5e6);color:white;border-radius:24px">Hello from Tessera</div>')
  const [viewport, setViewport] = useState(1280)
  const [custom, setCustom] = useState(1000)
  const [full, setFull] = useState(true)
  const [height, setHeight] = useState(800)
  const [scale, setScale] = useState(1)
  const [format, setFormat] = useState<'png' | 'jpg' | 'webp'>('png')
  const [quality, setQuality] = useState(90)
  const [transparent, setTransparent] = useState(false)
  const [wait, setWait] = useState(0)
  const [shot, setShot] = useState<ImageView | null>(null)
  const [error, setError] = useState<Error | null>(null)
  useToolRequest('html-to-image', (path) => {
    setKind('file')
    setFile(path)
  })

  const value = kind === 'url' ? url : kind === 'file' ? (file ?? '') : code
  const width = viewport || custom
  const ext = format === 'jpg' ? 'jpg' : format

  async function pickFile() {
    try {
      const [p] = await call('pick_files', 'HTML', ['html', 'htm', 'xhtml', 'svg'], false)
      if (p) setFile(p)
    } catch (err) {
      setError(toError(err))
    }
  }

  async function capture() {
    setShot(null)
    const res = await flow.saveTo(
      async () => (await call('suggest_pdf_path', kind === 'code' ? null : value, kind === 'code' ? 'snippet' : 'page')).replace(/\.pdf$/i, `.${ext}`),
      (out) =>
        call('html_to_image', kind, value, out, {
          width,
          height,
          full_page: full,
          scale,
          format,
          quality,
          transparent: transparent && format !== 'jpg',
          wait,
          scroll: true,
        }) as Promise<SavedImage>,
      { label: 'Image', extensions: [ext] },
    )
    if (res) {
      try {
        setShot(await call('image_preview', res.path, 1400))
      } catch {
        /* the file is saved; the preview is a nicety */
      }
    }
  }

  return (
    <section className="tool">
      <header className="tool-header">
        <h1>HTML to Image</h1>
        <p>Render a web page, an HTML file or a snippet of HTML/CSS into a PNG, JPG or WebP picture: the whole page or just the visible area, at the width of any screen.</p>
      </header>
      <div className="segmented" role="radiogroup">
        {(
          [
            ['url', 'Web page'],
            ['file', 'HTML file'],
            ['code', 'HTML code'],
          ] as const
        ).map(([id, label]) => (
          <button key={id} type="button" role="radio" aria-checked={kind === id} className={cls('segment', kind === id && 'is-on')} onClick={() => setKind(id)}>
            {label}
          </button>
        ))}
      </div>
      <div className="card conv-options">
        {kind === 'url' && <input className="text-input wide-input" value={url} placeholder="https://example.com" aria-label="Web address" onChange={(e) => setUrl(e.target.value)} spellCheck={false} />}
        {kind === 'file' && (
          <div className="button-row">
            <button type="button" className="btn btn-secondary btn-sm" onClick={pickFile}>
              {file ? 'Change…' : 'Choose an HTML file…'}
            </button>
            {file && <span className="mono small">{file}</span>}
          </div>
        )}
        {kind === 'code' && <textarea className="code-area" value={code} onChange={(e) => setCode(e.target.value)} spellCheck={false} aria-label="HTML code" />}
        <div className="opt-grid">
          <label>
            Screen width
            <select className="text-input" value={viewport} onChange={(e) => setViewport(Number(e.target.value))}>
              {VIEWPORTS.map((v) => (
                <option key={v.id} value={v.id}>
                  {v.label}
                </option>
              ))}
            </select>
          </label>
          {viewport === 0 && (
            <label>
              Width (px)
              <input className="text-input num" type="number" min={320} max={3840} value={custom} onChange={(e) => setCustom(Number(e.target.value))} />
            </label>
          )}
          <label>
            Capture
            <select className="text-input" value={full ? 'full' : 'view'} onChange={(e) => setFull(e.target.value === 'full')}>
              <option value="full">The whole page</option>
              <option value="view">The visible area only</option>
            </select>
          </label>
          {!full && (
            <label>
              Visible height (px)
              <input className="text-input num" type="number" min={200} max={4000} value={height} onChange={(e) => setHeight(Number(e.target.value))} />
            </label>
          )}
          <label>
            Sharpness
            <select className="text-input" value={scale} onChange={(e) => setScale(Number(e.target.value))}>
              <option value={1}>1× (standard)</option>
              <option value={2}>2× (retina)</option>
              <option value={3}>3×</option>
            </select>
          </label>
          <label>
            Format
            <select className="text-input" value={format} onChange={(e) => setFormat(e.target.value as typeof format)}>
              <option value="png">PNG</option>
              <option value="jpg">JPG</option>
              <option value="webp">WebP</option>
            </select>
          </label>
          {format !== 'png' && <QualityField value={quality} onChange={setQuality} />}
          <label>
            Wait after loading (s)
            <input className="text-input num" type="number" min={0} max={30} value={wait} onChange={(e) => setWait(Number(e.target.value))} />
          </label>
          {format !== 'jpg' && (
            <label className="check span-2">
              <input type="checkbox" checked={transparent} onChange={(e) => setTransparent(e.target.checked)} /> Transparent background (for snippets and pages without a background)
            </label>
          )}
        </div>
      </div>
      <ErrorNotice error={error} />
      <ErrorNotice error={flow.error} />
      {flow.saved && <ResultCard files={flow.saved} onDismiss={flow.dismiss} />}
      {shot && (
        <div className="card shot-card">
          <ImageStage src={shot.data_url} width={shot.width} height={shot.height} maxHeight={520} checker />
        </div>
      )}
      <div className="action-bar">
        <span className="muted small">
          {width}px wide{scale > 1 ? ` at ${scale}× → ${width * scale}px` : ''}
        </span>
        <button type="button" className="btn btn-primary" disabled={flow.busy || !value.trim()} onClick={capture}>
          {flow.busy ? 'Rendering…' : 'Capture and save…'}
        </button>
      </div>
    </section>
  )
}
