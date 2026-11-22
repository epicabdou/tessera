import { useCallback, useEffect, useRef, useState } from 'react'
import { call, setPreference, toError, type HistoryEntry } from '../lib/bridge'
import { cls } from '../lib/cls'
import { formatBytes } from '../lib/format'
import { ErrorNotice } from './ErrorNotice'
import { CloseIcon, FolderOpenIcon, HistoryIcon, SearchIcon } from './icons'
import { IconButton } from './IconButton'

const PAGE = 40
const OUTPUTS_SHOWN = 3

/** Top-bar button; opens the activity history: what each tool made, from what, and when. */
export function HistoryButton() {
  const [open, setOpen] = useState(false)
  const root = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!open) return
    const onDown = (e: MouseEvent) => {
      if (!root.current?.contains(e.target as Node)) setOpen(false)
    }
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setOpen(false)
    }
    document.addEventListener('mousedown', onDown)
    document.addEventListener('keydown', onKey)
    return () => {
      document.removeEventListener('mousedown', onDown)
      document.removeEventListener('keydown', onKey)
    }
  }, [open])

  return (
    <div className="status-wrap" ref={root}>
      <IconButton label="History" active={open} onClick={() => setOpen((o) => !o)}>
        <HistoryIcon size={16} />
      </IconButton>
      {open && <HistoryPanel />}
    </div>
  )
}

function HistoryPanel() {
  const [entries, setEntries] = useState<HistoryEntry[]>([])
  const [more, setMore] = useState(false)
  const [enabled, setEnabled] = useState(true)
  const [loaded, setLoaded] = useState(false)
  const [query, setQuery] = useState('')
  const [error, setError] = useState<Error | null>(null)
  const [confirmClear, setConfirmClear] = useState(false)
  const seq = useRef(0)

  const load = useCallback(async (q: string, before: number | null) => {
    const n = ++seq.current
    try {
      const page = await call('history_list', q, PAGE, before)
      if (n !== seq.current) return // a newer search has started
      setEntries((list) => (before === null ? page.entries : [...list, ...page.entries]))
      setMore(page.more)
      setEnabled(page.enabled)
      setError(null)
    } catch (err) {
      if (n === seq.current) setError(toError(err))
    } finally {
      if (n === seq.current) setLoaded(true)
    }
  }, [])

  // First load at once; searches once typing pauses.
  useEffect(() => {
    const t = window.setTimeout(() => void load(query, null), query ? 220 : 0)
    return () => window.clearTimeout(t)
  }, [query, load])

  const act = (fn: () => Promise<unknown>) => fn().catch((err) => setError(toError(err)))

  async function toggle(on: boolean) {
    setEnabled(on)
    await act(() => setPreference('history_enabled', on))
  }

  async function remove(id: number) {
    setEntries((list) => list.filter((e) => e.id !== id))
    await act(() => call('history_delete', [id]))
  }

  async function clearAll() {
    setConfirmClear(false)
    setEntries([])
    setMore(false)
    await act(() => call('history_clear'))
  }

  return (
    <div className="popover history" role="dialog" aria-label="History">
      <div className="history-head">
        <strong>History</strong>
        <label className="check small" title="Record each file Tessera makes. Only file names, places and times are kept.">
          <input type="checkbox" checked={enabled} onChange={(e) => void toggle(e.target.checked)} /> Keep history
        </label>
      </div>

      <div className="history-search">
        <SearchIcon size={14} />
        <input
          className="text-input"
          type="search"
          value={query}
          placeholder="Search tools and file names"
          aria-label="Search history"
          spellCheck={false}
          autoFocus
          onChange={(e) => setQuery(e.target.value)}
        />
      </div>

      {!enabled && <p className="muted small history-note">History is off: new runs aren't recorded.</p>}
      <ErrorNotice error={error} />

      <div className="history-list">
        {loaded && entries.length === 0 && !error && (
          <p className="muted small history-empty">
            {query ? 'Nothing matches.' : 'Nothing yet. Files you make with any tool show up here, with where they came from.'}
          </p>
        )}
        {groupByDay(entries).map(([day, group]) => (
          <section key={day} className="history-day">
            <h3>{day}</h3>
            <ul>
              {group.map((e) => (
                <EntryRow key={e.id} entry={e} onRemove={() => void remove(e.id)} onError={setError} />
              ))}
            </ul>
          </section>
        ))}
        {more && (
          <button type="button" className="btn btn-ghost btn-sm history-more" onClick={() => void load(query, entries[entries.length - 1]?.id ?? null)}>
            Show older
          </button>
        )}
      </div>

      {entries.length > 0 && !query && (
        <div className="history-foot">
          {confirmClear ? (
            <>
              <span className="small">Clear the whole history? Your files stay where they are.</span>
              <button type="button" className="btn btn-ghost btn-sm" onClick={() => setConfirmClear(false)}>
                Cancel
              </button>
              <button type="button" className="btn btn-danger btn-sm" onClick={() => void clearAll()}>
                Clear
              </button>
            </>
          ) : (
            <button type="button" className="btn btn-ghost btn-sm" onClick={() => setConfirmClear(true)}>
              Clear history…
            </button>
          )}
        </div>
      )}
    </div>
  )
}

function EntryRow({ entry: e, onRemove, onError }: { entry: HistoryEntry; onRemove: () => void; onError: (err: Error) => void }) {
  const [expanded, setExpanded] = useState(false)
  const act = (fn: () => Promise<unknown>) => fn().catch((err) => onError(toError(err)))
  const outputs = expanded ? e.outputs : e.outputs.slice(0, OUTPUTS_SHOWN)
  const hidden = e.outputs.length - outputs.length

  return (
    <li className={cls('history-entry', e.status === 'error' && 'is-error')}>
      <div className="history-entry-head">
        <span className={cls('history-dot', e.status === 'error' && 'is-error')} aria-hidden="true" />
        <strong>{e.label}</strong>
        <span className="muted small">
          {timeFormat.format(new Date(e.started_at * 1000))} · {formatDuration(e.duration_ms)}
        </span>
        <button type="button" className="icon-btn history-remove" title="Remove from history" aria-label="Remove from history" onClick={onRemove}>
          <CloseIcon size={13} />
        </button>
      </div>

      {e.status === 'error' && <p className="history-error small">{e.error}</p>}

      {outputs.length > 0 && (
        <ul className="history-files">
          {outputs.map((o) => (
            <li key={o.path} className={cls(!o.exists && 'is-missing')} title={o.path}>
              {o.exists ? (
                <button type="button" className="history-file" onClick={() => void act(() => call('open_path', o.path))}>
                  {o.name}
                </button>
              ) : (
                <span className="history-file">{o.name}</span>
              )}
              <span className="muted small">{o.exists ? (o.size !== null ? formatBytes(o.size) : '') : 'moved or deleted'}</span>
              {o.exists && (
                <button type="button" className="icon-btn" title="Show in folder" aria-label={`Show ${o.name} in folder`} onClick={() => void act(() => call('reveal_path', o.path))}>
                  <FolderOpenIcon size={14} />
                </button>
              )}
            </li>
          ))}
          {hidden > 0 && (
            <li>
              <button type="button" className="history-expand small" onClick={() => setExpanded(true)}>
                and {hidden} more
              </button>
            </li>
          )}
        </ul>
      )}

      {e.inputs.length > 0 && (
        <p className="muted small history-from" title={e.inputs.map((i) => i.path).join('\n')}>
          from {e.inputs.slice(0, 2).map((i) => i.name).join(', ')}
          {e.inputs.length > 2 ? ` and ${e.inputs.length - 2} more` : ''}
        </p>
      )}
    </li>
  )
}

const timeFormat = new Intl.DateTimeFormat(undefined, { timeStyle: 'short' })
const dayFormat = new Intl.DateTimeFormat(undefined, { weekday: 'long', day: 'numeric', month: 'long' })
const yearFormat = new Intl.DateTimeFormat(undefined, { dateStyle: 'long' })

/** Entries (newest first) under "Today", "Yesterday", or their date. */
function groupByDay(entries: HistoryEntry[]): [string, HistoryEntry[]][] {
  const today = new Date()
  const yesterday = new Date(today.getFullYear(), today.getMonth(), today.getDate() - 1)
  const groups = new Map<string, HistoryEntry[]>()
  for (const e of entries) {
    const d = new Date(e.started_at * 1000)
    const key =
      d.toDateString() === today.toDateString()
        ? 'Today'
        : d.toDateString() === yesterday.toDateString()
          ? 'Yesterday'
          : d.getFullYear() === today.getFullYear()
            ? dayFormat.format(d)
            : yearFormat.format(d)
    const group = groups.get(key)
    if (group) group.push(e)
    else groups.set(key, [e])
  }
  return [...groups]
}

function formatDuration(ms: number): string {
  if (ms < 1000) return `${ms} ms`
  if (ms < 60_000) return `${(ms / 1000).toFixed(ms < 10_000 ? 1 : 0)} s`
  const m = Math.floor(ms / 60_000)
  return `${m} min ${Math.round((ms % 60_000) / 1000)} s`
}
