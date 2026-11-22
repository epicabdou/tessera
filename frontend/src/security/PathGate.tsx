import { useState, type DragEvent, type ReactNode } from 'react'
import { DND_FILE } from '../browser/fileKinds'
import { FilePdfIcon } from '../components/icons'
import { call, toError } from '../lib/bridge'
import { cls } from '../lib/cls'
import { isPdf, useToolRequest, useWorkspace, type ToolId } from '../lib/workspace'

/**
 * Like DocGate, but only holds a path: for tools that must accept PDFs the page
 * renderer can't open (password-protected or damaged files).
 */
export function PathGate({ tool, children }: { tool: ToolId; children: (path: string, reopen: (path: string) => void) => ReactNode }) {
  const { selected } = useWorkspace()
  const [file, setFile] = useState<{ path: string; nonce: number } | null>(null)
  const [over, setOver] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const open = (path: string) => setFile((f) => ({ path, nonce: (f?.nonce ?? 0) + 1 }))
  useToolRequest(tool, open)
  const selectedPdf = selected && !selected.is_dir && isPdf(selected.path) ? selected : null

  async function pick() {
    try {
      const [path] = await call('pick_pdfs', false)
      if (path) open(path)
    } catch (err) {
      setError(toError(err).message)
    }
  }

  const dropProps = {
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
      if (!isPdf(path)) return
      e.preventDefault()
      open(path)
    },
  }

  if (!file) {
    return (
      <div className={cls('dropzone', over && 'is-over')} {...dropProps}>
        <FilePdfIcon size={34} className="dropzone-icon" />
        <p className="dropzone-title">Choose a PDF</p>
        <p className="muted">Drag a PDF here from the Explorer, or pick one.</p>
        <div className="button-row">
          <button type="button" className="btn btn-primary" onClick={pick}>
            Open PDF…
          </button>
          {selectedPdf && (
            <button type="button" className="btn btn-secondary" onClick={() => open(selectedPdf.path)}>
              Use {selectedPdf.name}
            </button>
          )}
        </div>
        {error && <div className="notice notice-error">{error}</div>}
      </div>
    )
  }

  const name = file.path.split(/[\\/]/).pop()
  return (
    <>
      <div className={cls('doc-bar', over && 'is-over')} {...dropProps}>
        <FilePdfIcon size={20} className="doc-icon" />
        <div className="doc-meta">
          <strong title={file.path}>{name}</strong>
          <span className="muted small mono">{file.path}</span>
        </div>
        <div className="doc-actions">
          <button type="button" className="btn btn-ghost btn-sm" onClick={pick}>
            Change…
          </button>
          <button type="button" className="btn btn-ghost btn-sm" onClick={() => setFile(null)}>
            Close
          </button>
        </div>
      </div>
      {error && <div className="notice notice-error">{error}</div>}
      <div key={`${file.path}|${file.nonce}`} className="tool-body">
        {children(file.path, open)}
      </div>
    </>
  )
}
