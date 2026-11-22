import { useCallback, useLayoutEffect, useMemo, useRef, useState, type CSSProperties, type DragEvent, type PointerEvent, type ReactNode } from 'react'
import { DND_FILE } from '../browser/fileKinds'
import { ErrorNotice } from '../components/ErrorNotice'
import { JobProgressBar } from '../components/JobProgressBar'
import { OutputChooser } from '../convert/shared'
import type { useJob } from '../lib/useJob'
import { ResultCard } from '../pdf/components'
import type { useSaveFlow } from '../pdf/useSaveFlow'
import { CloseIcon, ImageIcon, PlusIcon } from '../components/icons'
import { call, toError, type AiModelStatus, type ImageFormat, type ImageInfo } from '../lib/bridge'
import { cls } from '../lib/cls'
import { formatBytes } from '../lib/format'
import { IMAGE_EXTS, isImage, useWorkspace } from '../lib/workspace'
import { FORMAT_LABELS, formatBytesShort, ImageDocContext, useImageDoc, type ImageDocState } from './context'
import type { ListItem, useImageList } from './hooks'

export function ImageDocProvider({ children }: { children: ReactNode }) {
  const [image, setImage] = useState<ImageInfo | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const open = useCallback(async (path: string) => {
    setLoading(true)
    setError(null)
    try {
      setImage(await call('image_info', path))
      return true
    } catch (err) {
      setError(toError(err).message)
      return false
    } finally {
      setLoading(false)
    }
  }, [])

  const pick = useCallback(async () => {
    try {
      const [path] = await call('pick_files', 'Images', IMAGE_EXTS, false)
      if (path) await open(path)
    } catch (err) {
      setError(toError(err).message)
    }
  }, [open])

  const close = useCallback(() => {
    setImage(null)
    setError(null)
  }, [])

  const value = useMemo<ImageDocState>(() => ({ image, loading, error, open, pick, close }), [image, loading, error, open, pick, close])
  return <ImageDocContext.Provider value={value}>{children}</ImageDocContext.Provider>
}

function useExplorerDrop(onPath: (path: string) => void) {
  const [over, setOver] = useState(false)
  return {
    over,
    props: {
      onDragOver: (e: DragEvent) => {
        if (!e.dataTransfer.types.includes(DND_FILE)) return
        e.preventDefault()
        setOver(true)
      },
      onDragLeave: (e: DragEvent) => {
        if (!e.currentTarget.contains(e.relatedTarget as Node | null)) setOver(false)
      },
      onDrop: (e: DragEvent) => {
        setOver(false)
        const path = e.dataTransfer.getData(DND_FILE)
        if (!isImage(path)) return
        e.preventDefault()
        onPath(path)
      },
    },
  }
}

/** "Choose an image" until one is open, then a bar with its details and the tool. */
export function ImageGate({ children }: { children: (image: ImageInfo) => ReactNode }) {
  const { image, loading, error, open, pick, close } = useImageDoc()
  const { selected } = useWorkspace()
  const drop = useExplorerDrop((p) => void open(p))
  const selectedImage = selected && !selected.is_dir && isImage(selected.path) ? selected : null

  if (!image) {
    return (
      <div className={cls('dropzone', drop.over && 'is-over')} {...drop.props}>
        <ImageIcon size={34} className="dropzone-icon" />
        <p className="dropzone-title">{loading ? 'Opening…' : 'Choose an image'}</p>
        <p className="muted">JPG, PNG, WebP, HEIC, AVIF, GIF, BMP or TIFF. Drag one here from the Explorer, or pick one.</p>
        <div className="button-row">
          <button type="button" className="btn btn-primary" onClick={pick} disabled={loading}>
            Open image…
          </button>
          {selectedImage && (
            <button type="button" className="btn btn-secondary" onClick={() => open(selectedImage.path)} disabled={loading}>
              Use {selectedImage.name}
            </button>
          )}
        </div>
        {error && <div className="notice notice-error">{error}</div>}
      </div>
    )
  }

  return (
    <>
      <div className={cls('doc-bar', drop.over && 'is-over')} {...drop.props}>
        <ImageIcon size={20} className="kind-image" />
        <div className="doc-meta">
          <strong title={image.path}>{image.name}</strong>
          <span className="muted small">
            {image.width} × {image.height} px · {image.format} · {formatBytes(image.size)}
            {image.alpha ? ' · transparency' : ''}
          </span>
        </div>
        <div className="doc-actions">
          {selectedImage && selectedImage.path.toLowerCase() !== image.path.toLowerCase() && (
            <button type="button" className="btn btn-ghost btn-sm" onClick={() => open(selectedImage.path)}>
              Use {selectedImage.name}
            </button>
          )}
          <button type="button" className="btn btn-ghost btn-sm" onClick={pick}>
            Change…
          </button>
          <button type="button" className="btn btn-ghost btn-sm" onClick={close}>
            Close
          </button>
        </div>
      </div>
      {error && <div className="notice notice-error">{error}</div>}
      {children(image)}
    </>
  )
}

/** An image fitted to the available width; `overlay(scale)` draws on top (scale = screen px per image px). */
export function ImageStage({
  src,
  width,
  height,
  maxHeight = 620,
  checker = false,
  overlay,
  busy = false,
}: {
  src: string | null
  width: number
  height: number
  maxHeight?: number
  checker?: boolean
  overlay?: (scale: number) => ReactNode
  busy?: boolean
}) {
  const wrap = useRef<HTMLDivElement>(null)
  const [available, setAvailable] = useState(600)
  useLayoutEffect(() => {
    const el = wrap.current
    if (!el) return
    const ro = new ResizeObserver(() => setAvailable(el.clientWidth))
    ro.observe(el)
    return () => ro.disconnect()
  }, [])
  const scale = Math.min(available / width, maxHeight / height, 4)
  return (
    <div ref={wrap} className="preview-wrap">
      <div className={cls('image-stage', checker && 'is-checker', busy && 'is-busy')} style={{ width: width * scale, height: height * scale }}>
        {src ? <img src={src} alt="" draggable={false} /> : <div className="thumb-placeholder" />}
        {overlay?.(scale)}
      </div>
    </div>
  )
}

/** Before / after with a draggable divider. With `zoom` > 1 both sides are magnified around the pointer. */
export function CompareSlider({
  before,
  after,
  width,
  height,
  maxHeight = 620,
  checker = false,
  zoom = 1,
}: {
  before: string
  after: string
  width: number
  height: number
  maxHeight?: number
  checker?: boolean
  zoom?: number
}) {
  const [pos, setPos] = useState(50)
  const [origin, setOrigin] = useState('50% 50%')
  const dragging = useRef(false)
  const move = (e: PointerEvent<HTMLDivElement>) => {
    const r = e.currentTarget.getBoundingClientRect()
    const fx = Math.max(0, Math.min(1, (e.clientX - r.left) / r.width))
    const fy = Math.max(0, Math.min(1, (e.clientY - r.top) / r.height))
    if (dragging.current) setPos(fx * 100)
    else if (zoom > 1) setOrigin(`${fx * 100}% ${fy * 100}%`)
  }
  const zoomed: CSSProperties = { transform: `scale(${zoom})`, transformOrigin: origin }
  return (
    <ImageStage
      src={null}
      width={width}
      height={height}
      maxHeight={maxHeight}
      checker={checker}
      overlay={() => (
        <div
          className={cls('compare-layer', zoom > 1 && 'is-zoomed')}
          onPointerDown={(e) => {
            dragging.current = true
            e.currentTarget.setPointerCapture(e.pointerId)
            move(e)
          }}
          onPointerMove={move}
          onPointerUp={() => {
            dragging.current = false
          }}
        >
          <div className="compare-clip">
            <div className="compare-pane" style={zoomed}>
              <img src={after} alt="" draggable={false} />
            </div>
          </div>
          <div className="compare-clip" style={{ clipPath: `inset(0 ${100 - pos}% 0 0)` }}>
            <div className="compare-pane" style={zoomed}>
              <img src={before} alt="" draggable={false} />
            </div>
          </div>
          <div className="compare-line" style={{ left: `${pos}%` }}>
            <span className="compare-knob">⟷</span>
          </div>
          <span className="compare-tag is-left">Before</span>
          <span className="compare-tag is-right">After</span>
        </div>
      )}
    />
  )
}

/** The batch list: thumbnails, details, a per-tool `extra` column and the result of the last run. */
export function ImageListView({
  list,
  extra,
  thumbStyle,
  results,
  selected,
  onSelect,
  hint = 'Drag images here from the Explorer, or add them.',
}: {
  list: ReturnType<typeof useImageList>
  extra?: (item: ListItem) => ReactNode
  thumbStyle?: (item: ListItem) => CSSProperties
  results?: Record<string, ReactNode>
  selected?: string | null
  onSelect?: (path: string) => void
  hint?: string
}) {
  const drop = useExplorerDropMany((paths) => void list.add(paths))
  return (
    <div className="img-list-wrap">
      <div className="button-row">
        <button type="button" className="btn btn-secondary btn-sm" onClick={list.pick}>
          <PlusIcon size={14} /> Add images…
        </button>
        {list.items.length > 0 && (
          <>
            <span className="muted small">
              {list.items.length} image{list.items.length === 1 ? '' : 's'}
            </span>
            <button type="button" className="btn btn-ghost btn-sm" onClick={list.clear}>
              Clear list
            </button>
          </>
        )}
      </div>
      <ul className={cls('conv-list img-list', drop.over && 'is-over')} {...drop.props}>
        {list.items.length === 0 && (
          <li className="conv-empty">
            <ImageIcon size={26} />
            <span>{hint}</span>
          </li>
        )}
        {list.items.map((item) => (
          <li
            key={item.path}
            className={cls('conv-row img-row', selected === item.path && 'is-selected', onSelect && 'is-clickable')}
            onClick={() => onSelect?.(item.path)}
          >
            <span className="img-thumb">{item.data_url ? <img src={item.data_url} alt="" style={thumbStyle?.(item)} draggable={false} /> : <ImageIcon size={22} />}</span>
            <span className="conv-meta">
              <strong title={item.path}>{item.name}</strong>
              <span className="muted small">
                {item.error ? <span className="field-error">{item.error}</span> : `${item.width} × ${item.height} px${item.size ? ` · ${formatBytesShort(item.size)}` : ''}`}
              </span>
            </span>
            {extra && !item.error && <span className="img-extra">{extra(item)}</span>}
            {results?.[item.path] && <span className="img-result small">{results[item.path]}</span>}
            <button
              type="button"
              className="icon-btn"
              aria-label={`Remove ${item.name}`}
              onClick={(e) => {
                e.stopPropagation()
                list.remove(item.path)
              }}
            >
              <CloseIcon size={14} />
            </button>
          </li>
        ))}
      </ul>
    </div>
  )
}

function useExplorerDropMany(onPaths: (paths: string[]) => void) {
  const [over, setOver] = useState(false)
  return {
    over,
    props: {
      onDragOver: (e: DragEvent) => {
        if (!e.dataTransfer.types.includes(DND_FILE)) return
        e.preventDefault()
        setOver(true)
      },
      onDragLeave: (e: DragEvent) => {
        if (!e.currentTarget.contains(e.relatedTarget as Node | null)) setOver(false)
      },
      onDrop: (e: DragEvent) => {
        setOver(false)
        if (!e.dataTransfer.types.includes(DND_FILE)) return
        e.preventDefault()
        onPaths([e.dataTransfer.getData(DND_FILE)])
      },
    },
  }
}

/** Output format select. `keep` adds "Same as the original". */
export function FormatSelect({
  value,
  onChange,
  formats = ['jpg', 'png', 'webp', 'avif'],
  keep = true,
  label = 'Format',
}: {
  value: string
  onChange: (v: string) => void
  formats?: ImageFormat[]
  keep?: boolean
  label?: string
}) {
  return (
    <label>
      {label}
      <select className="text-input" value={value} onChange={(e) => onChange(e.target.value)}>
        {keep && <option value="keep">Same as the original</option>}
        {formats.map((f) => (
          <option key={f} value={f}>
            {FORMAT_LABELS[f]}
          </option>
        ))}
      </select>
    </label>
  )
}

/** Quality slider for lossy formats. */
export function QualityField({ value, onChange, label = 'Quality' }: { value: number; onChange: (v: number) => void; label?: string }) {
  return (
    <label className="range-field">
      {label} ({value})
      <input type="range" min={10} max={100} value={value} onChange={(e) => onChange(Number(e.target.value))} />
    </label>
  )
}

/** "First use downloads …" for the AI tools. */
export function ModelNotice({ model }: { model: AiModelStatus | null }) {
  if (!model || model.installed) return null
  return (
    <div className="notice model-notice small">
      The first time you use this tool, it downloads the <strong>{model.title}</strong> model ({formatBytesShort(model.size)}, {model.license}, from {model.source}). After that it works
      offline; your images never leave this computer.
    </div>
  )
}

/** Where to save + the run button + progress + the result, for the batch image tools. */
export function BatchRun({
  count,
  label,
  folder,
  onFolder,
  flow,
  job,
  onRun,
  disabled = false,
  note,
}: {
  count: number
  label: string
  folder: string | null
  onFolder: (folder: string | null) => void
  flow: ReturnType<typeof useSaveFlow>
  job: ReturnType<typeof useJob>
  onRun: () => void
  disabled?: boolean
  note?: ReactNode
}) {
  return (
    <>
      <div className="card conv-options">
        <OutputChooser folder={folder} onChange={onFolder} what="image" />
      </div>
      <div className="action-bar">
        {note ?? <span />}
        <JobProgressBar busy={job.busy} progress={job.progress} label="Working…" />
        <button type="button" className="btn btn-primary" disabled={disabled || !count || flow.busy || job.busy} onClick={onRun}>
          {job.busy ? 'Working…' : count > 1 ? `${label} ${count} images` : label}
        </button>
      </div>
      <ErrorNotice error={flow.error} />
      {flow.saved && <ResultCard files={flow.saved} onDismiss={flow.dismiss} />}
    </>
  )
}
