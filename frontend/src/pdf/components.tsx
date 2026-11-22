import { useEffect, useLayoutEffect, useRef, useState, type DragEvent, type ReactNode } from 'react'
import { DND_FILE } from '../browser/fileKinds'
import { CloseIcon, FileIcon, FilePdfIcon, ImageIcon } from '../components/icons'
import { call, toError, type PdfInfo, type SavedFile } from '../lib/bridge'
import { cls } from '../lib/cls'
import { formatBytes, samePath } from '../lib/format'
import { isImage, isPdf, useWorkspace } from '../lib/workspace'
import { usePdfDoc, useThumbStore, type FileRef } from './context'

interface PageSize {
  width: number
  height: number
}

const quarterTurn = (deg: number) => (((deg % 360) + 360) % 360) as 0 | 90 | 180 | 270

/**
 * Lazy page thumbnail: renders once scrolled into view; `rotate` previews extra rotation.
 * Fits a `box`-pixel square, or with `fitWidth` fills that width at the page's own aspect ratio.
 */
export function PageThumb({
  file,
  index,
  page,
  rotate = 0,
  box = 150,
  fitWidth,
  renderWidth = 220,
  blank = false,
}: {
  file: FileRef | null
  index: number
  page: PageSize
  rotate?: number
  box?: number
  fitWidth?: number
  renderWidth?: number
  blank?: boolean
}) {
  const store = useThumbStore()
  const ref = useRef<HTMLDivElement>(null)
  const [visible, setVisible] = useState(false)

  useEffect(() => {
    const el = ref.current
    if (!el || visible) return
    const io = new IntersectionObserver((entries) => {
      if (entries.some((e) => e.isIntersecting)) {
        setVisible(true)
        io.disconnect()
      }
    })
    io.observe(el)
    return () => io.disconnect()
  }, [visible])

  const url = file && !blank ? store.get(file, index, renderWidth) : undefined
  useEffect(() => {
    if (file && !blank && visible && !url) store.request(file, index, renderWidth)
  }, [file, blank, visible, url, store, index, renderWidth])

  const turn = quarterTurn(rotate)
  const turned = turn % 180 !== 0
  const vw = turned ? page.height : page.width
  const vh = turned ? page.width : page.height
  const scale = fitWidth ? fitWidth / vw : Math.min(box / vw, box / vh)
  // The image is laid out unrotated, then turned about its centre.
  const style = {
    width: (turned ? vh : vw) * scale,
    height: (turned ? vw : vh) * scale,
    transform: turn ? `rotate(${turn}deg)` : undefined,
  }
  const frame = fitWidth ? { width: fitWidth, height: vh * scale } : { width: box, height: box }

  return (
    <div ref={ref} className="thumb" style={frame}>
      {url ? (
        <img src={url} alt="" draggable={false} style={style} />
      ) : (
        <div className={cls('thumb-placeholder', blank && 'is-blank')} style={style} />
      )}
    </div>
  )
}

/** One large page, fitted to the available width; `overlay(scale)` draws on top (scale = px per point). */
export function PagePreview({
  file,
  index,
  page,
  maxHeight = 640,
  overlay,
}: {
  file: FileRef
  index: number
  page: PageSize
  maxHeight?: number
  overlay?: (scale: number) => ReactNode
}) {
  const store = useThumbStore()
  const wrapRef = useRef<HTMLDivElement>(null)
  const [available, setAvailable] = useState(560)

  useLayoutEffect(() => {
    const el = wrapRef.current
    if (!el) return
    const ro = new ResizeObserver(() => setAvailable(el.clientWidth))
    ro.observe(el)
    return () => ro.disconnect()
  }, [])

  const scale = Math.min(available / page.width, maxHeight / page.height)
  const width = page.width * scale
  const height = page.height * scale
  // Render in coarse steps so small resizes reuse the cached image.
  const renderWidth = Math.min(1600, Math.ceil((width * Math.min(2, window.devicePixelRatio || 1)) / 200) * 200)
  const url = store.get(file, index, renderWidth)

  useEffect(() => {
    if (!url && width > 0) store.request(file, index, renderWidth)
  }, [url, width, store, file, index, renderWidth])

  return (
    <div ref={wrapRef} className="preview-wrap">
      <div className="preview-stage" style={{ width, height }}>
        {url ? <img src={url} alt="" draggable={false} /> : <div className="thumb-placeholder" />}
        {overlay?.(scale)}
      </div>
    </div>
  )
}

function acceptsFile(e: DragEvent) {
  return e.dataTransfer.types.includes(DND_FILE)
}

/** Shows an "open a PDF" panel until a document is loaded, then the tool. */
export function DocGate({ children }: { children: (doc: PdfInfo) => ReactNode }) {
  const { doc, loading, error, open, pick, close } = usePdfDoc()
  const { selected } = useWorkspace()
  const [over, setOver] = useState(false)
  const selectedPdf = selected && !selected.is_dir && isPdf(selected.path) ? selected : null

  const dropProps = {
    onDragOver: (e: DragEvent) => {
      if (!acceptsFile(e)) return
      e.preventDefault()
      setOver(true)
    },
    onDragLeave: (e: DragEvent) => {
      if (!e.currentTarget.contains(e.relatedTarget as Node | null)) setOver(false)
    },
    onDrop: (e: DragEvent) => {
      setOver(false)
      const path = e.dataTransfer.getData(DND_FILE)
      if (!isPdf(path)) return
      e.preventDefault()
      void open(path)
    },
  }

  if (!doc) {
    return (
      <div className={cls('dropzone', over && 'is-over')} {...dropProps}>
        <FilePdfIcon size={34} className="dropzone-icon" />
        <p className="dropzone-title">{loading ? 'Opening…' : 'Choose a PDF to work on'}</p>
        <p className="muted">Drag a PDF here from the Explorer, or right-click one and choose Open in PDF tools.</p>
        <div className="button-row">
          <button type="button" className="btn btn-primary" onClick={pick} disabled={loading}>
            Open PDF…
          </button>
          {selectedPdf && (
            <button type="button" className="btn btn-secondary" onClick={() => open(selectedPdf.path)} disabled={loading}>
              Use {selectedPdf.name}
            </button>
          )}
        </div>
        {error && <div className="notice notice-error">{error}</div>}
      </div>
    )
  }

  return (
    <>
      <div className={cls('doc-bar', over && 'is-over')} {...dropProps}>
        <FilePdfIcon size={20} className="doc-icon" />
        <div className="doc-meta">
          <strong title={doc.path}>{doc.name}</strong>
          <span className="muted small">
            {doc.page_count} {doc.page_count === 1 ? 'page' : 'pages'} · {formatBytes(doc.size)}
          </span>
        </div>
        <div className="doc-actions">
          {selectedPdf && !samePath(selectedPdf.path, doc.path) && (
            <button type="button" className="btn btn-ghost btn-sm" onClick={() => open(selectedPdf.path)}>
              Use {selectedPdf.name}
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
      {children(doc)}
    </>
  )
}

const RESULT_LIMIT = 12

/** "Saved" card with Open / Show in folder, and optionally Keep editing. */
export function ResultCard({
  files,
  onContinue,
  onDismiss,
}: {
  files: SavedFile[]
  onContinue?: (file: SavedFile) => void
  onDismiss: () => void
}) {
  const [error, setError] = useState<string | null>(null)
  const act = (fn: () => Promise<unknown>) => fn().catch((err) => setError(toError(err).message))
  const shown = files.slice(0, RESULT_LIMIT)

  return (
    <div className="card result-card" role="status">
      <div className="result-head">
        <span className="result-check">✓</span>
        <strong>{files.length === 1 ? 'Saved' : `Saved ${files.length} files`}</strong>
        <button type="button" className="icon-btn" aria-label="Dismiss" onClick={onDismiss}>
          <CloseIcon size={14} />
        </button>
      </div>
      <ul className="result-list">
        {shown.map((f) => (
          <li key={f.path}>
            {isPdf(f.path) ? <FilePdfIcon size={18} className="doc-icon" /> : isImage(f.path) ? <ImageIcon size={18} className="kind-image" /> : <FileIcon size={18} />}
            <div className="result-file">
              <span title={f.path}>{f.name}</span>
              <span className="muted small">
                {f.page_count !== undefined ? `${f.page_count} ${f.page_count === 1 ? 'page' : 'pages'} · ` : ''}
                {f.width && f.height ? `${f.width} × ${f.height} px · ` : ''}
                {formatBytes(f.size)}
              </span>
            </div>
            <div className="result-actions">
              <button type="button" className="btn btn-ghost btn-sm" onClick={() => act(() => call('open_path', f.path))}>
                Open
              </button>
              <button type="button" className="btn btn-ghost btn-sm" onClick={() => act(() => call('reveal_path', f.path))}>
                Show in folder
              </button>
              {onContinue && files.length === 1 && (isPdf(f.path) || isImage(f.path)) && (
                <button type="button" className="btn btn-secondary btn-sm" onClick={() => onContinue(f)}>
                  Keep editing this file
                </button>
              )}
            </div>
          </li>
        ))}
      </ul>
      {files.length > RESULT_LIMIT && <p className="muted small">…and {files.length - RESULT_LIMIT} more</p>}
      {error && <div className="notice notice-error">{error}</div>}
    </div>
  )
}
