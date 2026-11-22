import type { FsEntry } from '../lib/bridge'
import { formatBytes, formatDate } from '../lib/format'
import { latexSummary, useComponents } from '../lib/useComponents'

export function StatusBar({ entry }: { entry: FsEntry | null }) {
  const latex = useComponents()
  const setup = latex && ['downloading', 'installing', 'warming', 'error'].includes(latex.state)
  return (
    <footer className="statusbar">
      {entry ? (
        <>
          <span className="status-path" title={entry.path}>
            {entry.path}
          </span>
          <span>{entry.is_dir ? 'Folder' : entry.size !== null ? formatBytes(entry.size) : 'File'}</span>
          {entry.modified !== null && <span>Modified {formatDate(entry.modified)}</span>}
        </>
      ) : (
        <span>Select a file or folder in the explorer</span>
      )}
      {setup && (
        <span className={`status-setup${latex.state === 'error' ? ' is-error' : ''}`} title={latex.error ?? 'First-run setup: the LaTeX editor needs this'}>
          {latex.state !== 'error' && <span className="spinner" />}
          {latexSummary(latex)}
        </span>
      )}
    </footer>
  )
}
