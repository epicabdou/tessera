import { useEffect, useLayoutEffect, useRef, useState, type ReactNode } from 'react'
import { fileKind } from '../browser/fileKinds'
import { IconButton } from '../components/IconButton'
import { CloseIcon, FileIcon, FilePdfIcon, FolderIcon } from '../components/icons'
import { call, toError, type FilePreview } from '../lib/bridge'
import { cls } from '../lib/cls'
import { dirname, formatBytes, formatDate, MM_PER_POINT } from '../lib/format'
import { convertToolFor, useWorkspace } from '../lib/workspace'
import { FolderView, ImageView, NoPreview, PdfView, TableView, TextView } from './views'
import './preview.css'

const DEBOUNCE_MS = 120

/** Right-hand panel showing the item selected in the Explorer. */
export function PreviewPanel({ filesVersion, onClose }: { filesVersion: number; onClose: () => void }) {
  const { selected, openInTool } = useWorkspace()
  const [data, setData] = useState<FilePreview | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)
  const seq = useRef(0)
  const bodyRef = useRef<HTMLDivElement>(null)
  const [bodyWidth, setBodyWidth] = useState(300)

  const path = selected?.path ?? null
  const stamp = selected?.modified ?? null

  // Arrow-keying through the tree changes the selection quickly: debounce, and
  // ignore answers for anything that's no longer selected.
  useEffect(() => {
    const id = ++seq.current
    const t = window.setTimeout(async () => {
      if (!path) {
        setData(null)
        setError(null)
        return
      }
      setLoading(true)
      try {
        const result = await call('preview_file', path)
        if (id === seq.current) {
          setData(result)
          setError(null)
        }
      } catch (err) {
        if (id === seq.current) {
          setData(null)
          setError(toError(err).message)
        }
      } finally {
        if (id === seq.current) setLoading(false)
      }
    }, DEBOUNCE_MS)
    return () => window.clearTimeout(t)
  }, [path, stamp, filesVersion])

  useLayoutEffect(() => {
    const el = bodyRef.current
    if (!el) return
    const ro = new ResizeObserver(() => setBodyWidth(el.clientWidth))
    ro.observe(el)
    return () => ro.disconnect()
  }, [])

  useEffect(() => {
    if (!notice) return
    const t = window.setTimeout(() => setNotice(null), 2500)
    return () => window.clearTimeout(t)
  }, [notice])

  const act = (fn: () => Promise<unknown>) => fn().catch((err) => setNotice(toError(err).message))

  let content: ReactNode
  if (!path) {
    content = (
      <div className="pv-empty">
        <FileIcon size={36} />
        <p>Select a file or folder in the Explorer to preview it.</p>
      </div>
    )
  } else if (error) {
    content = <div className="notice notice-error">{error}</div>
  } else if (data) {
    const convertTool = convertToolFor(data.path)
    content = (
      <>
        <PreviewHeader data={data} />
        <div className="pv-actions">
          <button type="button" className="btn btn-secondary btn-sm" onClick={() => act(() => call('open_path', data.path))}>
            {data.is_dir ? 'Open in File Explorer' : 'Open'}
          </button>
          {!data.is_dir && (
            <button type="button" className="btn btn-ghost btn-sm" onClick={() => act(() => call('reveal_path', data.path))}>
              Show in folder
            </button>
          )}
          {data.kind === 'pdf' && (
            <button type="button" className="btn btn-ghost btn-sm" onClick={() => openInTool('pdf-pages', data.path)}>
              PDF tools
            </button>
          )}
          {data.kind === 'image' && (
            <button type="button" className="btn btn-ghost btn-sm" onClick={() => openInTool('photo-editor', data.path)}>
              Edit photo
            </button>
          )}
          {!data.is_dir && convertTool && (
            <button type="button" className="btn btn-ghost btn-sm" onClick={() => openInTool(convertTool, data.path)}>
              Convert to PDF
            </button>
          )}
          <button
            type="button"
            className="btn btn-ghost btn-sm"
            onClick={() => act(() => navigator.clipboard.writeText(data.path).then(() => setNotice('Path copied')))}
          >
            Copy path
          </button>
        </div>
        <PreviewBody data={data} width={bodyWidth} />
        <Details data={data} />
      </>
    )
  }

  return (
    <div className="preview-panel" data-preview-kind={data?.kind ?? (path ? 'loading' : 'none')}>
      <div className="preview-head">
        <span className="browser-title">Preview</span>
        <IconButton label="Hide preview" onClick={onClose}>
          <CloseIcon size={14} />
        </IconButton>
      </div>
      {loading && <div className="pv-progress" />}
      <div ref={bodyRef} className={cls('preview-body', loading && data && data.path !== path && 'is-stale')}>
        {content}
      </div>
      {notice && <div className="toast">{notice}</div>}
    </div>
  )
}

function kindLabel(d: FilePreview): string {
  switch (d.kind) {
    case 'folder':
      return 'Folder'
    case 'pdf':
      return 'PDF document'
    case 'image':
      return `${d.image?.format ?? d.ext.toUpperCase()} image`
    case 'table':
      return `${d.ext.toUpperCase()} table`
    case 'text':
      return d.ext ? `${d.ext.toUpperCase()} file` : 'Text file'
    default:
      return d.ext ? `${d.ext.toUpperCase()} file` : 'File'
  }
}

function PreviewHeader({ data }: { data: FilePreview }) {
  const Icon = data.is_dir ? FolderIcon : data.kind === 'pdf' ? FilePdfIcon : FileIcon
  const iconClass = data.is_dir ? 'icon-folder' : data.kind === 'pdf' ? 'doc-icon' : `kind-${fileKind(data.ext)}`
  const summary = [
    kindLabel(data),
    data.pdf && `${data.pdf.page_count} ${data.pdf.page_count === 1 ? 'page' : 'pages'}`,
    data.image?.width && `${data.image.width} × ${data.image.height}`,
    data.size !== null && formatBytes(data.size),
  ].filter(Boolean)
  return (
    <div className="pv-header">
      <Icon size={28} className={iconClass} />
      <div className="pv-title">
        <strong title={data.path}>{data.name}</strong>
        <span className="muted small">{summary.join(' · ')}</span>
      </div>
    </div>
  )
}

function PreviewBody({ data, width }: { data: FilePreview; width: number }) {
  if (data.kind === 'pdf' && data.pdf) return <PdfView pdf={data.pdf} width={width - 32} />
  if (data.kind === 'image' && data.image) return <ImageView image={data.image} />
  if (data.kind === 'text' && data.text) return <TextView text={data.text} />
  if (data.kind === 'table' && data.table) return <TableView table={data.table} />
  if (data.kind === 'folder' && data.folder) return <FolderView folder={data.folder} />
  return <NoPreview error={data.error} />
}

function Details({ data }: { data: FilePreview }) {
  const mm = (pt: number) => Math.round(pt * MM_PER_POINT)
  const rows: [string, ReactNode][] = [
    ['Type', kindLabel(data)],
    ...(data.size !== null ? [['Size', `${formatBytes(data.size)} (${data.size.toLocaleString()} bytes)`] as [string, ReactNode]] : []),
    ['Modified', formatDate(data.modified)],
    ['Created', formatDate(data.created)],
    [
      'Location',
      <span key="location" className="mono small">
        {dirname(data.path)}
      </span>,
    ],
  ]
  if (data.pdf) {
    const first = data.pdf.pages[0]
    if (data.pdf.title) rows.push(['Title', data.pdf.title])
    if (first) rows.push(['Page size', `${mm(first.width)} × ${mm(first.height)} mm`])
  }
  if (data.image) {
    if (data.image.mode) rows.push(['Colour', data.image.mode])
    if (data.image.frames > 1) rows.push(['Frames', `${data.image.frames} (animated; first frame shown)`])
  }
  return (
    <dl className="pv-details">
      {rows.map(([k, v]) => (
        <div key={k}>
          <dt>{k}</dt>
          <dd>{v}</dd>
        </div>
      ))}
    </dl>
  )
}
