import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { call, toError, type DirListing, type FsEntry } from '../lib/bridge'

export type DirState = { status: 'ready'; listing: DirListing } | { status: 'error'; error: string }

/** The tree is rendered as a flat list of rows: entries, plus notes such as "Loading…". */
export type TreeRow =
  | { kind: 'entry'; entry: FsEntry; depth: number; open: boolean }
  | { kind: 'note'; key: string; depth: number; text: string; error?: boolean }

const NONE: ReadonlySet<string> = new Set()

/**
 * Lazily loads folder listings for a tree rooted at `root`.
 *
 * Listings are cached per (path, showHidden). Each root remembers its own
 * expanded folders, so Back/Forward brings the tree back as you left it.
 */
export function useDirectoryTree(root: string | null, showHidden: boolean, filter: string) {
  // A folder that's been requested but has no entry here yet is loading.
  const [dirs, setDirs] = useState<Record<string, DirState>>({})
  const [expandedByRoot, setExpandedByRoot] = useState<Record<string, ReadonlySet<string>>>({})
  const requested = useRef(new Set<string>())
  // Bumped by refresh(); responses from an older generation are dropped.
  const generation = useRef(0)

  const expanded = (root && expandedByRoot[root]) || NONE
  const keyOf = useCallback((path: string) => `${showHidden ? 'all' : 'visible'}|${path}`, [showHidden])

  const fetchInto = useCallback(
    (paths: string[]) => {
      const gen = generation.current
      for (const path of paths) {
        const key = keyOf(path)
        call('list_dir', path, showHidden).then(
          (listing) => {
            if (gen === generation.current) setDirs((d) => ({ ...d, [key]: { status: 'ready', listing } }))
          },
          (err) => {
            if (gen === generation.current) setDirs((d) => ({ ...d, [key]: { status: 'error', error: toError(err).message } }))
          },
        )
      }
    },
    [keyOf, showHidden],
  )

  // Fetch whatever the tree needs that hasn't been requested yet.
  useEffect(() => {
    if (!root) return
    const missing = [root, ...expanded].filter((p) => !requested.current.has(keyOf(p)))
    for (const p of missing) requested.current.add(keyOf(p))
    if (missing.length) fetchInto(missing)
  }, [root, expanded, keyOf, fetchInto])

  /** Re-read what's on screen, keeping current rows until fresh ones arrive. */
  const refresh = useCallback(() => {
    if (!root) return
    generation.current += 1
    const visible = [root, ...expanded]
    const keep = new Set(visible.map(keyOf))
    // Anything off-screen is forgotten and re-read when it's next shown.
    requested.current = new Set(keep)
    setDirs((d) => Object.fromEntries(Object.entries(d).filter(([k]) => keep.has(k))))
    fetchInto(visible)
  }, [root, expanded, keyOf, fetchInto])

  const setOpen = useCallback(
    (path: string, open: boolean) => {
      if (!root) return
      setExpandedByRoot((m) => {
        const next = new Set(m[root] ?? [])
        if (open) next.add(path)
        else next.delete(path)
        return { ...m, [root]: next }
      })
    },
    [root],
  )

  const rootState = root ? dirs[keyOf(root)] : undefined

  const rows = useMemo(
    () => (root ? buildRows(root, (p) => dirs[keyOf(p)], expanded, filter) : []),
    [root, dirs, keyOf, expanded, filter],
  )

  return { rows, rootState, setOpen, refresh }
}

function buildRows(
  root: string,
  lookup: (path: string) => DirState | undefined,
  expanded: ReadonlySet<string>,
  filter: string,
): TreeRow[] {
  const query = filter.trim().toLowerCase()
  const rows: TreeRow[] = []

  // Returns true if anything under `path` survived the filter.
  const walk = (path: string, depth: number): boolean => {
    const state = lookup(path)
    if (!state) {
      if (depth > 0 && !query) rows.push({ kind: 'note', key: `${path}|loading`, depth, text: 'Loading…' })
      return false
    }
    if (state.status === 'error') {
      if (depth > 0 && !query) rows.push({ kind: 'note', key: `${path}|error`, depth, text: state.error, error: true })
      return false
    }

    const { entries, truncated } = state.listing
    let anyVisible = false
    for (const entry of entries) {
      const start = rows.length
      const open = entry.is_dir && expanded.has(entry.path)
      rows.push({ kind: 'entry', entry, depth, open })
      const childVisible = open && walk(entry.path, depth + 1)
      // With a filter, keep a row if it matches or leads to a match.
      if (query && !childVisible && !entry.name.toLowerCase().includes(query)) rows.length = start
      else anyVisible = true
    }
    if (!query && depth > 0 && entries.length === 0) {
      rows.push({ kind: 'note', key: `${path}|empty`, depth, text: 'Empty' })
    }
    if (!query && truncated) {
      rows.push({ kind: 'note', key: `${path}|more`, depth, text: `Showing the first ${entries.length.toLocaleString()} items` })
    }
    return anyVisible
  }

  walk(root, 0)
  return rows
}
