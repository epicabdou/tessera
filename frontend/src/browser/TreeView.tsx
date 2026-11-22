import { useEffect, useRef, type KeyboardEvent, type MouseEvent, type ReactNode } from 'react'
import { ChevronIcon, FileIcon, FolderIcon, FolderOpenIcon, PinIcon } from '../components/icons'
import type { FsEntry } from '../lib/bridge'
import { cls } from '../lib/cls'
import { formatBytes, formatDate, samePath } from '../lib/format'
import { DND_FILE, DND_PATH, fileKind } from './fileKinds'
import type { TreeRow } from './useDirectoryTree'

interface Props {
  rows: TreeRow[]
  selectedPath: string | null
  isPinned: (path: string) => boolean
  empty: ReactNode
  onSelect: (entry: FsEntry) => void
  onSetOpen: (path: string, open: boolean) => void
  /** Double-click / Enter: open a file, or browse into a folder. */
  onActivate: (entry: FsEntry) => void
  onUp: () => void
  onEntryMenu: (e: { clientX: number; clientY: number }, entry: FsEntry) => void
  onBackgroundMenu: (e: MouseEvent) => void
}

const INDENT = 14
const TYPEAHEAD_RESET_MS = 700

function tooltip(entry: FsEntry): string {
  const lines = [entry.path]
  const details = [
    entry.size !== null ? formatBytes(entry.size) : null,
    entry.modified !== null ? `Modified ${formatDate(entry.modified)}` : null,
  ].filter(Boolean)
  if (details.length) lines.push(details.join(' · '))
  return lines.join('\n')
}

export function TreeView({
  rows,
  selectedPath,
  isPinned,
  empty,
  onSelect,
  onSetOpen,
  onActivate,
  onUp,
  onEntryMenu,
  onBackgroundMenu,
}: Props) {
  const ref = useRef<HTMLDivElement>(null)
  const typeahead = useRef({ text: '', at: 0 })

  useEffect(() => {
    ref.current?.querySelector('.tree-row.is-selected')?.scrollIntoView({ block: 'nearest' })
  }, [selectedPath])

  const selectedIndex = rows.findIndex((r) => r.kind === 'entry' && samePath(r.entry.path, selectedPath))

  function entryAt(i: number): FsEntry | null {
    const row = rows[i]
    return row?.kind === 'entry' ? row.entry : null
  }

  function step(from: number, delta: number): number {
    for (let i = from + delta; i >= 0 && i < rows.length; i += delta) if (rows[i].kind === 'entry') return i
    return from
  }

  function onKeyDown(e: KeyboardEvent) {
    const row = rows[selectedIndex]
    const current = row?.kind === 'entry' ? row : null
    const select = (i: number) => {
      const entry = entryAt(i)
      if (entry) onSelect(entry)
    }

    switch (e.key) {
      case 'ArrowDown':
        select(selectedIndex === -1 ? step(-1, 1) : step(selectedIndex, 1))
        break
      case 'ArrowUp':
        select(selectedIndex === -1 ? step(rows.length, -1) : step(selectedIndex, -1))
        break
      case 'Home':
        select(step(-1, 1))
        break
      case 'End':
        select(step(rows.length, -1))
        break
      case 'ArrowRight':
        if (current?.entry.is_dir) {
          if (!current.open) onSetOpen(current.entry.path, true)
          else select(step(selectedIndex, 1))
        }
        break
      case 'ArrowLeft':
        if (current?.entry.is_dir && current.open) {
          onSetOpen(current.entry.path, false)
        } else if (current && current.depth > 0) {
          for (let i = selectedIndex - 1; i >= 0; i--) {
            const r = rows[i]
            if (r.kind === 'entry' && r.depth === current.depth - 1) {
              select(i)
              break
            }
          }
        }
        break
      case 'Enter':
        if (current) onActivate(current.entry)
        break
      case 'Backspace':
        onUp()
        break
      case 'ContextMenu': {
        const el = ref.current?.querySelector('.tree-row.is-selected')
        if (current && el) {
          const r = el.getBoundingClientRect()
          onEntryMenu({ clientX: r.left + 24, clientY: r.bottom }, current.entry)
        }
        break
      }
      default:
        // Type the start of a name to jump to it.
        if (e.key.length === 1 && !e.ctrlKey && !e.altKey && !e.metaKey) {
          const now = performance.now()
          const t = typeahead.current
          t.text = now - t.at > TYPEAHEAD_RESET_MS ? e.key.toLowerCase() : t.text + e.key.toLowerCase()
          t.at = now
          // A single letter cycles to the next match; a longer prefix refines the current one.
          const start = t.text.length === 1 ? selectedIndex + 1 : Math.max(selectedIndex, 0)
          for (let k = 0; k < rows.length; k++) {
            const i = (start + k) % rows.length
            if (entryAt(i)?.name.toLowerCase().startsWith(t.text)) {
              select(i)
              break
            }
          }
          break
        }
        return
    }
    e.preventDefault()
  }

  return (
    <div
      ref={ref}
      className="tree"
      role="tree"
      tabIndex={0}
      aria-label="Files"
      onKeyDown={onKeyDown}
      onContextMenu={(e) => {
        e.preventDefault()
        onBackgroundMenu(e)
      }}
    >
      {rows.length === 0 && <div className="tree-empty">{empty}</div>}
      {rows.map((row) => {
        if (row.kind === 'note') {
          return (
            <div
              key={row.key}
              className={cls('tree-note', row.error && 'is-error')}
              style={{ paddingLeft: 28 + row.depth * INDENT }}
            >
              {row.text}
            </div>
          )
        }
        const { entry, depth, open } = row
        const selected = samePath(entry.path, selectedPath)
        const Icon = entry.is_dir ? (open ? FolderOpenIcon : FolderIcon) : FileIcon
        return (
          <div
            key={entry.path}
            role="treeitem"
            aria-level={depth + 1}
            aria-expanded={entry.is_dir ? open : undefined}
            aria-selected={selected}
            className={cls('tree-row', selected && 'is-selected', entry.hidden && 'is-dim')}
            style={{ paddingLeft: 4 + depth * INDENT }}
            title={tooltip(entry)}
            draggable
            onDragStart={(e) => {
              // Folders can be dropped on Pinned; files on tools (e.g. Merge PDF).
              e.dataTransfer.setData(entry.is_dir ? DND_PATH : DND_FILE, entry.path)
              e.dataTransfer.effectAllowed = 'copyMove'
            }}
            onClick={() => {
              onSelect(entry)
              if (entry.is_dir) onSetOpen(entry.path, !open)
            }}
            onDoubleClick={() => onActivate(entry)}
            onContextMenu={(e) => {
              e.preventDefault()
              e.stopPropagation()
              onSelect(entry)
              onEntryMenu(e, entry)
            }}
          >
            <span className="twisty">
              {entry.is_dir && <ChevronIcon size={13} className={cls('chev', open && 'is-open')} />}
            </span>
            <Icon size={16} className={entry.is_dir ? 'icon-folder' : `kind-${fileKind(entry.ext)}`} />
            <span className="tree-name">{entry.name}</span>
            {entry.is_dir && isPinned(entry.path) && <PinIcon size={12} className="tree-pin" />}
          </div>
        )
      })}
    </div>
  )
}
