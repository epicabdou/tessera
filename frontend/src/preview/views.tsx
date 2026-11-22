import { useMemo, useState } from 'react'
import { FileIcon } from '../components/icons'
import type { FolderSummary, ImagePreview, PdfInfo, TablePreview, TextPreview } from '../lib/bridge'
import { cls } from '../lib/cls'
import { formatBytes, formatDate } from '../lib/format'
import { PageThumb } from '../pdf/components'

export function PdfView({ pdf, width }: { pdf: PdfInfo; width: number }) {
  const fit = Math.max(80, Math.floor(width))
  // Coarse render sizes so a resize reuses cached pages instead of re-rendering.
  const renderWidth = Math.min(1200, Math.ceil((fit * Math.min(2, window.devicePixelRatio || 1)) / 160) * 160)
  return (
    <div className="pv-pages">
      {pdf.pages.map((page, i) => (
        <figure key={i} className="pv-page">
          <PageThumb file={pdf} index={i} page={page} fitWidth={fit} renderWidth={renderWidth} />
          <figcaption>{i + 1}</figcaption>
        </figure>
      ))}
    </div>
  )
}

export function ImageView({ image }: { image: ImagePreview }) {
  const [actual, setActual] = useState(false)
  return (
    <div
      className={cls('pv-image', actual && 'is-actual')}
      title={actual ? 'Click to fit' : 'Click for actual size'}
      onClick={() => setActual((a) => !a)}
    >
      <img src={image.data_url} alt="" draggable={false} />
    </div>
  )
}

export function TextView({ text }: { text: TextPreview }) {
  const [wrap, setWrap] = useState(false)
  const gutter = useMemo(() => Array.from({ length: text.lines }, (_, i) => i + 1).join('\n'), [text.lines])
  return (
    <>
      <div className="pv-toolbar">
        <span className="muted small">
          {text.lines.toLocaleString()} lines · {text.encoding} · {text.line_endings}
        </span>
        <label className="check small">
          <input type="checkbox" checked={wrap} onChange={(e) => setWrap(e.target.checked)} />
          Wrap
        </label>
      </div>
      <div className={cls('pv-code', wrap && 'is-wrapped')}>
        {!wrap && (
          <pre className="pv-gutter" aria-hidden="true">
            {gutter}
          </pre>
        )}
        <pre className="pv-text">{text.content}</pre>
      </div>
      {text.truncated && <p className="muted small">Showing the first 256 KB.</p>}
    </>
  )
}

const DELIMITERS: Record<string, string> = { ',': 'comma', ';': 'semicolon', '\t': 'tab', '|': 'pipe' }

export function TableView({ table }: { table: TablePreview }) {
  const [header, ...body] = table.rows
  const cols = Array.from({ length: table.columns }, (_, c) => c)
  return (
    <>
      <div className="pv-toolbar">
        <span className="muted small">
          {table.rows.length.toLocaleString()} rows{table.truncated ? '+' : ''} · {table.columns} columns ·{' '}
          {DELIMITERS[table.delimiter] ?? `“${table.delimiter}”`}-separated
        </span>
      </div>
      <div className="pv-table-wrap">
        <table className="pv-table">
          {header && (
            <thead>
              <tr>
                <th className="rownum">1</th>
                {cols.map((c) => (
                  <th key={c}>{header[c] ?? ''}</th>
                ))}
              </tr>
            </thead>
          )}
          <tbody>
            {body.map((row, r) => (
              <tr key={r}>
                <td className="rownum">{r + 2}</td>
                {cols.map((c) => (
                  <td key={c}>{row[c] ?? ''}</td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {table.truncated && <p className="muted small">Showing the first {table.rows.length} rows.</p>}
    </>
  )
}

export function FolderView({ folder }: { folder: FolderSummary }) {
  return (
    <div className="pv-folder">
      <div className="pv-stats">
        <div>
          <strong>{folder.folders.toLocaleString()}</strong>
          <span>folders</span>
        </div>
        <div>
          <strong>{folder.files.toLocaleString()}</strong>
          <span>files</span>
        </div>
        <div>
          <strong>{formatBytes(folder.total_size)}</strong>
          <span>in files</span>
        </div>
      </div>
      {folder.types.length > 0 && (
        <div className="pv-chips">
          {folder.types.map((t) => (
            <span key={t.ext} className="pv-chip">
              {t.ext === '(none)' ? 'no extension' : `.${t.ext}`} <b>{t.count}</b>
            </span>
          ))}
        </div>
      )}
      {folder.latest && (
        <p className="muted small">
          Last changed: <span className="pv-strong">{folder.latest.name}</span>, {formatDate(folder.latest.modified)}
        </p>
      )}
      <p className="muted small">
        Counts cover what's directly inside, not subfolders{folder.truncated ? ' (first 20,000 items)' : ''}.
      </p>
    </div>
  )
}

export function NoPreview({ error }: { error?: string }) {
  return (
    <div className="pv-none">
      <FileIcon size={40} />
      <p>{error ?? 'No preview for this type of file.'}</p>
    </div>
  )
}
