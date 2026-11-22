import type { JobProgress } from '../lib/bridge'

/** Determinate bar when the job reports progress, otherwise an indeterminate one. */
export function JobProgressBar({ busy, progress, label = 'Working…' }: { busy: boolean; progress: JobProgress | null; label?: string }) {
  if (!busy) return null
  const pct = progress && progress.total ? Math.round((progress.done / progress.total) * 100) : null
  return (
    <div className="job-progress" role="progressbar" aria-valuenow={pct ?? undefined} aria-valuemin={0} aria-valuemax={100}>
      <div className="job-track">
        <div className={pct === null ? 'job-fill is-indeterminate' : 'job-fill'} style={pct === null ? undefined : { width: `${pct}%` }} />
      </div>
      <span className="muted small">
        {progress?.message || label}
        {pct !== null ? ` · ${pct}%` : ''}
      </span>
    </div>
  )
}
