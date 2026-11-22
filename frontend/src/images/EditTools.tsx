import { useCallback, useEffect, useMemo, useState } from 'react'
import { ErrorNotice } from '../components/ErrorNotice'
import { RedoIcon, RotateCcwIcon, RotateCwIcon, UndoIcon } from '../components/icons'
import { BoxLayer, type Rect } from '../editing/BoxLayer'
import { call, toError, type ImageInfo } from '../lib/bridge'
import { cls } from '../lib/cls'
import { useJob } from '../lib/useJob'
import { IMAGE_EXTS, useToolRequest } from '../lib/workspace'
import { ResultCard } from '../pdf/components'
import { useHistory } from '../pdf/useHistory'
import { useSaveFlow } from '../pdf/useSaveFlow'
import { BatchRun, FormatSelect, ImageGate, ImageListView, ImageStage, QualityField } from './components'
import { outputExt, useImageDoc } from './context'
import { DrawLayer } from './DrawLayer'
import { useImageList, useRendered } from './hooks'
import { layerContent, measureText, transformLayers, type Layer, type LayerKind, type ViewOp } from './layers'

// --- Photo editor -------------------------------------------------------------------------

const FILTERS = ['none', 'vivid', 'warm', 'cool', 'mono', 'noir', 'sepia', 'vintage', 'fade', 'dramatic'] as const
const SLIDERS: { key: string; label: string; min: number; max: number }[] = [
  { key: 'exposure', label: 'Exposure', min: -100, max: 100 },
  { key: 'brightness', label: 'Brightness', min: -100, max: 100 },
  { key: 'contrast', label: 'Contrast', min: -100, max: 100 },
  { key: 'highlights', label: 'Highlights', min: -100, max: 100 },
  { key: 'shadows', label: 'Shadows', min: -100, max: 100 },
  { key: 'saturation', label: 'Saturation', min: -100, max: 100 },
  { key: 'warmth', label: 'Warmth', min: -100, max: 100 },
  { key: 'tint', label: 'Tint', min: -100, max: 100 },
  { key: 'hue', label: 'Hue', min: -180, max: 180 },
  { key: 'sharpness', label: 'Sharpness / blur', min: -100, max: 100 },
  { key: 'vignette', label: 'Vignette', min: -100, max: 100 },
  { key: 'fade', label: 'Fade', min: 0, max: 100 },
]
const TOOLS: { id: 'select' | LayerKind; label: string; hint: string }[] = [
  { id: 'select', label: 'Select', hint: 'Select, move and resize layers' },
  { id: 'text', label: 'Text', hint: 'Click to add text' },
  { id: 'draw', label: 'Draw', hint: 'Draw freehand' },
  { id: 'arrow', label: 'Arrow', hint: 'Drag from tail to tip' },
  { id: 'line', label: 'Line', hint: 'Drag to draw a line' },
  { id: 'rect', label: 'Box', hint: 'Drag to draw a rectangle' },
  { id: 'ellipse', label: 'Ellipse', hint: 'Drag to draw an ellipse' },
  { id: 'image', label: 'Logo / image', hint: 'Add a picture or logo' },
]
const PALETTE = ['#ffffff', '#000000', '#e53935', '#fb8c00', '#fdd835', '#43a047', '#1e88e5', '#8e24aa']

interface Edits {
  turns: number
  flip_h: boolean
  flip_v: boolean
  adjust: Record<string, number | string>
  layers: Layer[]
}

const EMPTY: Edits = { turns: 0, flip_h: false, flip_v: false, adjust: { filter: 'none' }, layers: [] }
let layerSeq = 0
const layerId = () => `l${++layerSeq}`

export function PhotoEditor() {
  const doc = useImageDoc()
  useToolRequest('photo-editor', (path) => void doc.open(path))
  return (
    <section className="tool tool-wide">
      <header className="tool-header">
        <h1>Photo editor</h1>
        <p>Adjust colour and light, apply a look, rotate, and add text, drawings, arrows, shapes and logos, all in one place. Every change can be undone.</p>
      </header>
      <ImageGate>{(image) => <EditorBody key={`${image.path}|${image.mtime}`} image={image} />}</ImageGate>
    </section>
  )
}

function EditorBody({ image }: { image: ImageInfo }) {
  const doc = useImageDoc()
  const flow = useSaveFlow()
  const history = useHistory<Edits>(() => EMPTY)
  const edits = history.value
  const [tool, setTool] = useState<'select' | LayerKind>('select')
  const [selected, setSelected] = useState<string | null>(null)
  const [panel, setPanel] = useState<'adjust' | 'layers' | 'export'>('adjust')
  const [pen, setPen] = useState({ stroke: '#e53935', width: 8 })
  const [format, setFormat] = useState('keep')
  const [quality, setQuality] = useState(92)
  const [error, setError] = useState<Error | null>(null)
  const [thumbs, setThumbs] = useState<Record<string, string>>({})

  const turned = edits.turns % 2 === 1
  const width = turned ? image.height : image.width
  const height = turned ? image.width : image.height
  const look = { turns: edits.turns, flip_h: edits.flip_h, flip_v: edits.flip_v, adjust: edits.adjust }
  const { result: preview, busy } = useRendered(JSON.stringify(look), () => call('photo_preview', image.path, look, 1600), 120)
  const sel = edits.layers.find((l) => l.id === selected) ?? null

  // Filter thumbnails, rendered once per photo.
  useEffect(() => {
    let active = true
    ;(async () => {
      for (const f of FILTERS) {
        try {
          const r = await call('photo_preview', image.path, { adjust: { filter: f } }, 140)
          if (!active) return
          setThumbs((t) => ({ ...t, [f]: r.data_url }))
        } catch {
          return
        }
      }
    })()
    return () => {
      active = false
    }
  }, [image.path])

  const patchLayer = useCallback(
    (id: string, patch: Partial<Layer>) =>
      history.set((e) => ({
        ...e,
        layers: e.layers.map((l) => {
          if (l.id !== id) return l
          const next = { ...l, ...patch }
          return next.type === 'text' && ('text' in patch || 'size' in patch || 'family' in patch || 'bold' in patch || 'italic' in patch || 'outline' in patch) ? { ...next, ...measureText(next) } : next
        }),
      })),
    [history],
  )
  const addLayer = (layer: Omit<Layer, 'id'>) => {
    const l = { ...layer, id: layerId() } as Layer
    history.set((e) => ({ ...e, layers: [...e.layers, l] }))
    setSelected(l.id)
    setTool('select')
    setPanel('layers')
  }
  const removeLayer = useCallback(
    (id: string) => {
      history.set((e) => ({ ...e, layers: e.layers.filter((l) => l.id !== id) }))
      setSelected(null)
    },
    [history],
  )
  const moveLayer = (id: string, delta: number) =>
    history.set((e) => {
      const i = e.layers.findIndex((l) => l.id === id)
      const j = i + delta
      if (i < 0 || j < 0 || j >= e.layers.length) return e
      const layers = [...e.layers]
      ;[layers[i], layers[j]] = [layers[j], layers[i]]
      return { ...e, layers }
    })

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const t = e.target as HTMLElement
      if (['INPUT', 'TEXTAREA', 'SELECT'].includes(t.tagName) || t.isContentEditable) return
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'z') {
        e.preventDefault()
        if (e.shiftKey) history.redo()
        else history.undo()
      } else if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'y') {
        e.preventDefault()
        history.redo()
      } else if (selected && (e.key === 'Delete' || e.key === 'Backspace')) {
        removeLayer(selected)
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [selected, history, removeLayer])

  function create(r: Rect) {
    const unit = Math.max(width, height) / 100
    if (tool === 'text') {
      const base = { type: 'text' as const, text: 'Your text', family: 'sans' as const, size: Math.round(unit * 6), color: '#ffffff', bold: true, outline: Math.round(unit * 0.25), outline_color: '#000000', shadow: false, opacity: 1, align: 'left' as const }
      const box = measureText(base)
      addLayer({ ...base, x: r.x, y: r.y, w: box.w, h: box.h })
    } else if (tool === 'rect' || tool === 'ellipse') {
      const w = r.w || unit * 25
      const h = r.h || unit * 18
      addLayer({ type: tool, x: r.x, y: r.y, w, h, stroke: pen.stroke, width: Math.max(1, Math.round(unit * 0.6)), fill: null, opacity: 1, radius: 0 })
    }
  }

  async function addImage() {
    try {
      const [path] = await call('pick_files', 'Images', IMAGE_EXTS, false)
      if (!path) return
      const [thumb] = await call('image_thumbnails', [path], 600)
      if (thumb.error || !thumb.data_url) throw new Error(thumb.error ?? 'Unreadable image')
      const w = width * 0.25
      const h = (w * (thumb.height ?? 1)) / (thumb.width ?? 1)
      addLayer({ type: 'image', x: width - w - width * 0.04, y: height - h - height * 0.04, w, h, src: path, preview: thumb.data_url, opacity: 1 })
    } catch (err) {
      setError(toError(err))
    }
  }

  const payload = useMemo(
    () => ({ ...edits, layers: edits.layers.map(({ id: _id, preview: _p, ...rest }) => rest) }),
    [edits],
  )
  /** Rotate or mirror what's on screen; layers move with the picture. */
  const view = (op: ViewOp) =>
    history.set((e) => {
      const odd = e.turns % 2 === 1
      const W = odd ? image.height : image.width
      const H = odd ? image.width : image.height
      const layers = transformLayers(e.layers, op, W, H)
      if (op === 'flip_h') return { ...e, flip_h: !e.flip_h, layers }
      if (op === 'flip_v') return { ...e, flip_v: !e.flip_v, layers }
      // Under a single mirror, turning the view one way turns the source the other way.
      const d = (op === 'cw' ? 1 : -1) * (e.flip_h !== e.flip_v ? -1 : 1)
      return { ...e, turns: (e.turns + d + 4) % 4, layers }
    })
  const setAdjust = (key: string, value: number | string) => history.set((e) => ({ ...e, adjust: { ...e.adjust, [key]: value } }))
  const ext = outputExt(image.path, format)
  const drawing = tool === 'draw' || tool === 'arrow' || tool === 'line'

  return (
    <>
      <div className="toolbar" role="toolbar">
        {TOOLS.map((t) => (
          <button
            key={t.id}
            type="button"
            className={cls('btn btn-ghost btn-sm', tool === t.id && 'is-tool')}
            title={t.hint}
            onClick={() => (t.id === 'image' ? void addImage() : setTool(t.id))}
          >
            {t.label}
          </button>
        ))}
        <span className="toolbar-sep" />
        <button type="button" className="icon-btn" title="Rotate left" aria-label="Rotate left" onClick={() => view('ccw')}>
          <RotateCcwIcon size={15} />
        </button>
        <button type="button" className="icon-btn" title="Rotate right" aria-label="Rotate right" onClick={() => view('cw')}>
          <RotateCwIcon size={15} />
        </button>
        <button type="button" className={cls('icon-btn', edits.flip_h && 'is-on')} title="Flip horizontally" aria-label="Flip horizontally" onClick={() => view('flip_h')}>
          ⇋
        </button>
        <button type="button" className={cls('icon-btn', edits.flip_v && 'is-on')} title="Flip vertically" aria-label="Flip vertically" onClick={() => view('flip_v')}>
          ⇵
        </button>
        <span className="toolbar-sep" />
        <button type="button" className="icon-btn" title="Undo (Ctrl+Z)" aria-label="Undo" disabled={!history.canUndo} onClick={history.undo}>
          <UndoIcon size={15} />
        </button>
        <button type="button" className="icon-btn" title="Redo (Ctrl+Y)" aria-label="Redo" disabled={!history.canRedo} onClick={history.redo}>
          <RedoIcon size={15} />
        </button>
        <span className="toolbar-spacer" />
        <span className="muted small">{TOOLS.find((t) => t.id === tool)?.hint}</span>
      </div>
      <ErrorNotice error={error} />
      <div className="split-layout editor-layout">
        <div className="split-main">
          <ImageStage
            src={preview?.data_url ?? null}
            width={width}
            height={height}
            checker={image.alpha}
            busy={busy}
            overlay={(scale) => (
              <>
                <BoxLayer
                  page={{ width, height }}
                  scale={scale}
                  boxes={edits.layers.map((l) => ({ ...l, content: layerContent(l, scale), className: `lbox-layer lbox-${l.type}` }))}
                  selected={selected}
                  onSelect={(id) => {
                    setSelected(id)
                    if (id) setPanel('layers')
                  }}
                  onChange={(id, r) => patchLayer(id, r)}
                  onCreate={tool === 'text' || tool === 'rect' || tool === 'ellipse' ? create : undefined}
                />
                {drawing && (
                  <DrawLayer
                    scale={scale}
                    width={width}
                    height={height}
                    mode={tool}
                    stroke={pen.stroke}
                    lineWidth={pen.width * (Math.max(width, height) / 1000)}
                    onDone={(box, points) => addLayer({ type: tool, ...box, points, stroke: pen.stroke, width: pen.width * (Math.max(width, height) / 1000), opacity: 1 })}
                  />
                )}
              </>
            )}
          />
        </div>
        <aside className="side-panel editor-panel">
          <div className="segmented">
            {(
              [
                ['adjust', 'Adjust'],
                ['layers', `Layers${edits.layers.length ? ` (${edits.layers.length})` : ''}`],
                ['export', 'Export'],
              ] as const
            ).map(([id, label]) => (
              <button key={id} type="button" className={cls('segment', panel === id && 'is-on')} onClick={() => setPanel(id)}>
                {label}
              </button>
            ))}
          </div>

          {panel === 'adjust' && (
            <>
              <h2 className="panel-title">Look</h2>
              <div className="filter-grid">
                {FILTERS.map((f) => (
                  <button key={f} type="button" className={cls('filter-chip', (edits.adjust.filter ?? 'none') === f && 'is-on')} onClick={() => setAdjust('filter', f)}>
                    <span className="filter-thumb">{thumbs[f] && <img src={thumbs[f]} alt="" />}</span>
                    <span>{f === 'none' ? 'Original' : f[0].toUpperCase() + f.slice(1)}</span>
                  </button>
                ))}
              </div>
              <h2 className="panel-title">Light & colour</h2>
              {SLIDERS.map((s) => {
                const v = Number(edits.adjust[s.key] ?? 0)
                return (
                  <label key={s.key} className="range-field slider-row" onDoubleClick={() => setAdjust(s.key, 0)} title="Double-click to reset">
                    <span className="slider-head">
                      {s.label}
                      <span className={cls('slider-value', v !== 0 && 'is-set')}>{v > 0 ? `+${v}` : v}</span>
                    </span>
                    <input type="range" min={s.min} max={s.max} value={v} onChange={(e) => setAdjust(s.key, Number(e.target.value))} />
                  </label>
                )
              })}
              <button type="button" className="btn btn-ghost btn-sm" onClick={() => history.set((e) => ({ ...e, adjust: { filter: 'none' } }))}>
                Reset adjustments
              </button>
            </>
          )}

          {panel === 'layers' && (
            <>
              {(drawing || tool === 'rect' || tool === 'ellipse') && (
                <>
                  <h2 className="panel-title">Pen</h2>
                  <div className="swatch-row">
                    {PALETTE.map((c) => (
                      <button key={c} type="button" className={cls('swatch', pen.stroke === c && 'is-on')} style={{ background: c }} aria-label={c} onClick={() => setPen((p) => ({ ...p, stroke: c }))} />
                    ))}
                    <input type="color" value={pen.stroke} onChange={(e) => setPen((p) => ({ ...p, stroke: e.target.value }))} aria-label="Pen colour" />
                  </div>
                  <label className="range-field">
                    Thickness ({pen.width})
                    <input type="range" min={1} max={40} value={pen.width} onChange={(e) => setPen((p) => ({ ...p, width: Number(e.target.value) }))} />
                  </label>
                </>
              )}
              {sel ? <LayerProps layer={sel} onChange={(p) => patchLayer(sel.id, p)} onRemove={() => removeLayer(sel.id)} onMove={(d) => moveLayer(sel.id, d)} /> : <p className="muted small">Pick a tool above and click or drag on the photo. Select a layer to change it.</p>}
              {edits.layers.length > 0 && (
                <>
                  <h2 className="panel-title">All layers (top first)</h2>
                  <ul className="layer-list">
                    {[...edits.layers].reverse().map((l) => (
                      <li key={l.id}>
                        <button type="button" className={cls('layer-row', selected === l.id && 'is-on')} onClick={() => setSelected(l.id)}>
                          <span className="layer-kind">{TOOLS.find((t) => t.id === l.type)?.label ?? l.type}</span>
                          <span className="layer-name">{l.type === 'text' ? l.text : ''}</span>
                        </button>
                      </li>
                    ))}
                  </ul>
                </>
              )}
            </>
          )}

          {panel === 'export' && (
            <>
              <div className="field-stack">
                <FormatSelect value={format} onChange={setFormat} formats={['jpg', 'png', 'webp', 'avif']} />
                {ext !== 'png' && <QualityField value={quality} onChange={setQuality} />}
              </div>
              <p className="muted small">
                {width} × {height} px. The original file isn't changed.
              </p>
            </>
          )}

          <button
            type="button"
            className="btn btn-primary"
            disabled={flow.busy}
            onClick={() =>
              flow.saveTo(
                () => call('image_suggest', image.path, '_edited', format),
                (out) => call('photo_save', image.path, out, payload, { format, quality, keep_metadata: true }),
                { label: 'Image', extensions: [ext] },
              )
            }
          >
            {flow.busy ? 'Saving…' : 'Save a copy…'}
          </button>
          <ErrorNotice error={flow.error} />
          {flow.saved && <ResultCard files={flow.saved} onDismiss={flow.dismiss} onContinue={(f) => void doc.open(f.path)} />}
        </aside>
      </div>
    </>
  )
}

function LayerProps({ layer, onChange, onRemove, onMove }: { layer: Layer; onChange: (p: Partial<Layer>) => void; onRemove: () => void; onMove: (delta: number) => void }) {
  const opacity = Math.round((layer.opacity ?? 1) * 100)
  return (
    <div className="props">
      <h2 className="panel-title">{TOOLS.find((t) => t.id === layer.type)?.label}</h2>
      {layer.type === 'text' && (
        <>
          <textarea className="props-text" rows={3} value={layer.text} onChange={(e) => onChange({ text: e.target.value })} aria-label="Text" />
          <div className="field-grid">
            <label>
              Font
              <select className="text-input" value={layer.family} onChange={(e) => onChange({ family: e.target.value as Layer['family'] })}>
                <option value="sans">Arial</option>
                <option value="serif">Times New Roman</option>
                <option value="mono">Courier New</option>
                <option value="display">Impact</option>
                <option value="script">Segoe Script</option>
                <option value="hand">Comic Sans</option>
              </select>
            </label>
            <label>
              Size (px)
              <input className="text-input num" type="number" min={4} max={2000} value={layer.size} onChange={(e) => onChange({ size: Math.max(4, Number(e.target.value)) })} />
            </label>
            <label>
              Colour
              <input type="color" value={layer.color ?? '#ffffff'} onChange={(e) => onChange({ color: e.target.value })} />
            </label>
            <label>
              Outline (px)
              <input className="text-input num" type="number" min={0} max={200} value={layer.outline ?? 0} onChange={(e) => onChange({ outline: Math.max(0, Number(e.target.value)) })} />
            </label>
            {(layer.outline ?? 0) > 0 && (
              <label>
                Outline colour
                <input type="color" value={layer.outline_color ?? '#000000'} onChange={(e) => onChange({ outline_color: e.target.value })} />
              </label>
            )}
          </div>
          <div className="button-row">
            <label className="check">
              <input type="checkbox" checked={!!layer.bold} onChange={(e) => onChange({ bold: e.target.checked })} /> Bold
            </label>
            <label className="check">
              <input type="checkbox" checked={!!layer.italic} onChange={(e) => onChange({ italic: e.target.checked })} /> Italic
            </label>
            <label className="check">
              <input type="checkbox" checked={!!layer.shadow} onChange={(e) => onChange({ shadow: e.target.checked })} /> Shadow
            </label>
          </div>
        </>
      )}
      {(layer.type === 'rect' || layer.type === 'ellipse') && (
        <div className="field-grid">
          <label className="check">
            <input type="checkbox" checked={!!layer.stroke} onChange={(e) => onChange({ stroke: e.target.checked ? '#e53935' : null })} /> Outline
          </label>
          {layer.stroke && <input type="color" value={layer.stroke} onChange={(e) => onChange({ stroke: e.target.value })} aria-label="Outline colour" />}
          {layer.stroke && (
            <label>
              Width (px)
              <input className="text-input num" type="number" min={1} max={200} value={layer.width ?? 4} onChange={(e) => onChange({ width: Math.max(1, Number(e.target.value)) })} />
            </label>
          )}
          <label className="check">
            <input type="checkbox" checked={!!layer.fill} onChange={(e) => onChange({ fill: e.target.checked ? '#ffeb3b' : null })} /> Fill
          </label>
          {layer.fill && <input type="color" value={layer.fill} onChange={(e) => onChange({ fill: e.target.value })} aria-label="Fill colour" />}
          {layer.type === 'rect' && (
            <label>
              Rounded corners
              <input className="text-input num" type="number" min={0} max={2000} value={layer.radius ?? 0} onChange={(e) => onChange({ radius: Math.max(0, Number(e.target.value)) })} />
            </label>
          )}
        </div>
      )}
      {(layer.type === 'draw' || layer.type === 'line' || layer.type === 'arrow') && (
        <div className="field-grid">
          <label>
            Colour
            <input type="color" value={layer.stroke ?? '#e53935'} onChange={(e) => onChange({ stroke: e.target.value })} />
          </label>
          <label>
            Thickness (px)
            <input className="text-input num" type="number" min={1} max={300} value={Math.round(layer.width ?? 6)} onChange={(e) => onChange({ width: Math.max(1, Number(e.target.value)) })} />
          </label>
        </div>
      )}
      <label className="range-field">
        Opacity ({opacity}%)
        <input type="range" min={5} max={100} value={opacity} onChange={(e) => onChange({ opacity: Number(e.target.value) / 100 })} />
      </label>
      <div className="button-row">
        <button type="button" className="btn btn-ghost btn-sm" onClick={() => onMove(1)}>
          Bring forward
        </button>
        <button type="button" className="btn btn-ghost btn-sm" onClick={() => onMove(-1)}>
          Send back
        </button>
        <button type="button" className="btn btn-ghost btn-sm" onClick={onRemove}>
          Delete
        </button>
      </div>
    </div>
  )
}

// --- Watermark ----------------------------------------------------------------------------

const POSITIONS = ['top-left', 'top-center', 'top-right', 'middle-left', 'middle-center', 'middle-right', 'bottom-left', 'bottom-center', 'bottom-right']

export function WatermarkImage() {
  const list = useImageList('img-watermark')
  const flow = useSaveFlow()
  const job = useJob()
  const [folder, setFolder] = useState<string | null>(null)
  const [focus, setFocus] = useState<string | null>(null)
  const [kind, setKind] = useState<'text' | 'image'>('text')
  const [text, setText] = useState('© Your name')
  const [family, setFamily] = useState('sans')
  const [bold, setBold] = useState(true)
  const [size, setSize] = useState(6)
  const [color, setColor] = useState('#ffffff')
  const [outline, setOutline] = useState(true)
  const [logo, setLogo] = useState<string | null>(null)
  const [scale, setScale] = useState(22)
  const [opacity, setOpacity] = useState(60)
  const [rotation, setRotation] = useState(0)
  const [position, setPosition] = useState('bottom-right')
  const [margin, setMargin] = useState(3)
  const [spacing, setSpacing] = useState(80)
  const [format, setFormat] = useState('keep')
  const [error, setError] = useState<Error | null>(null)

  const options = { kind, text, family, bold, size, color, outline, image: logo ?? '', scale: scale / 100, opacity: opacity / 100, rotation, position, margin, spacing, format, quality: 92 }
  const target = list.good.find((i) => i.path === focus) ?? list.good[0]
  const ready = kind === 'text' ? text.trim() !== '' : !!logo
  const { result: preview, busy, error: previewError } = useRendered(target && ready ? JSON.stringify([target.path, options]) : null, () => call('image_watermark_preview', target!.path, options, 1200))

  async function pickLogo() {
    try {
      const [p] = await call('pick_files', 'Images', IMAGE_EXTS, false)
      if (p) setLogo(p)
    } catch (err) {
      setError(toError(err))
    }
  }

  return (
    <section className="tool tool-wide">
      <header className="tool-header">
        <h1>Watermark Image</h1>
        <p>Stamp text or a logo on a batch of images to mark them as yours. The preview shows the real result on the selected image.</p>
      </header>
      <div className="split-layout">
        <div className="split-main">
          {target && preview ? (
            <ImageStage src={preview.data_url} width={preview.width} height={preview.height} busy={busy} maxHeight={520} />
          ) : (
            <div className="stage-empty muted">{list.items.length ? 'Preparing the preview…' : 'Add images below to see the preview.'}</div>
          )}
          <ErrorNotice error={previewError} />
          <ImageListView list={list} selected={target?.path ?? null} onSelect={setFocus} />
          <ErrorNotice error={list.error} />
        </div>
        <aside className="side-panel">
          <div className="segmented">
            {(['text', 'image'] as const).map((k) => (
              <button key={k} type="button" className={cls('segment', kind === k && 'is-on')} onClick={() => setKind(k)}>
                {k === 'text' ? 'Text' : 'Logo'}
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
                    <option value="display">Impact</option>
                    <option value="script">Segoe Script</option>
                    <option value="mono">Courier New</option>
                  </select>
                </label>
                <label>
                  Colour
                  <input type="color" value={color} onChange={(e) => setColor(e.target.value)} />
                </label>
                <label className="check">
                  <input type="checkbox" checked={bold} onChange={(e) => setBold(e.target.checked)} /> Bold
                </label>
                <label className="check">
                  <input type="checkbox" checked={outline} onChange={(e) => setOutline(e.target.checked)} /> Dark outline
                </label>
              </div>
              <label className="range-field">
                Size ({size}% of the shorter side)
                <input type="range" min={2} max={30} value={size} onChange={(e) => setSize(Number(e.target.value))} />
              </label>
            </>
          ) : (
            <>
              <div className="button-row">
                <button type="button" className="btn btn-secondary btn-sm" onClick={pickLogo}>
                  {logo ? 'Change logo…' : 'Choose a logo…'}
                </button>
                {logo && <span className="small mono">{logo.split(/[\\/]/).pop()}</span>}
              </div>
              <label className="range-field">
                Size ({scale}% of the width)
                <input type="range" min={3} max={90} value={scale} onChange={(e) => setScale(Number(e.target.value))} />
              </label>
            </>
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
            <input type="checkbox" checked={position === 'tile'} onChange={(e) => setPosition(e.target.checked ? 'tile' : 'bottom-right')} /> Repeat across the image
          </label>
          {position === 'tile' ? (
            <label className="range-field">
              Spacing ({spacing}%)
              <input type="range" min={10} max={300} value={spacing} onChange={(e) => setSpacing(Number(e.target.value))} />
            </label>
          ) : (
            <label className="range-field">
              Margin ({margin}%)
              <input type="range" min={0} max={20} value={margin} onChange={(e) => setMargin(Number(e.target.value))} />
            </label>
          )}
          <div className="field-stack">
            <FormatSelect value={format} onChange={setFormat} formats={['jpg', 'png', 'webp', 'avif']} />
          </div>
          <ErrorNotice error={error} />
        </aside>
      </div>
      <BatchRun count={list.good.length} label="Watermark" folder={folder} onFolder={setFolder} flow={flow} job={job} disabled={!ready} onRun={() => flow.runSave(() => job.run((id) => call('image_watermark', list.good.map((i) => i.path), folder, options, id)))} />
    </section>
  )
}
