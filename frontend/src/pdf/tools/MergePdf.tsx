import { useCallback, useEffect, useRef, useState, type DragEvent } from 'react'
import { DND_FILE } from '../../browser/fileKinds'
import { ErrorNotice } from '../../components/ErrorNotice'
import { ArrowDownIcon, ArrowUpIcon, CloseIcon, FilePdfIcon, PlusIcon } from '../../components/icons'
import { call, toError, type PdfInfo } from '../../lib/bridge'
import { cls } from '../../lib/cls'
import { formatBytes } from '../../lib/format'
import { isPdf, useToolRequest, useWorkspace } from '../../lib/workspace'
import { PageThumb, ResultCard } from '../components'
import { useSaveFlow } from '../useSaveFlow'

interface MergeItem {
  key: number
  info: PdfInfo
  pages: string
  /** Pages the range selects, or an error message. */
  count: number | string
}

const DND_ITEM = 'application/x-toolbox-merge-item'

export function MergePdf() {
  const { selected, openInTool } = useWorkspace()
  const [items, setItems] = useState<MergeItem[]>([])
  const [bookmarks, setBookmarks] = useState(true)
  const [dropSlot, setDropSlot] = useState<number | null>(null)
  const [addError, setAddError] = useState<Error | null>(null)
  const nextKey = useRef(1)
  const listRef = useRef<HTMLOListElement>(null)
  const flow = useSaveFlow()

  const add = useCallback(async (paths: string[]) => {
    setAddError(null)
    const added: MergeItem[] = []
    for (const path of paths) {
      try {
        const info = await call('pdf_info', path)
        added.push({ key: nextKey.current++, info, pages: '', count: info.page_count })
      } catch (err) {
        setAddError(toError(err))
      }
    }
    setItems((list) => [...list, ...added])
  }, [])

  useToolRequest('pdf-merge', (path) => void add([path]))

  async function addFromDialog() {
    try {
      const paths = await call('pick_pdfs', true)
      if (paths.length) await add(paths)
    } catch (err) {
      setAddError(toError(err))
    }
  }

  const update = (key: number, patch: Partial<MergeItem>) =>
    setItems((list) => list.map((it) => (it.key === key ? { ...it, ...patch } : it)))

  const move = (from: number, to: number) =>
    setItems((list) => {
      if (to < 0 || to >= list.length || from === to) return list
      const next = [...list]
      const [item] = next.splice(from, 1)
      next.splice(to, 0, item)
      return next
    })

  // --- drag & drop: files from the Explorer, and reordering ------------------

  function slotAt(e: DragEvent): number {
    const rows = listRef.current?.querySelectorAll<HTMLElement>('[data-merge-index]') ?? []
    for (const el of rows) {
      const r = el.getBoundingClientRect()
      if (e.clientY < r.top + r.height / 2) return Number(el.dataset.mergeIndex)
    }
    return items.length
  }

  const accepts = (e: DragEvent) => e.dataTransfer.types.includes(DND_FILE) || e.dataTransfer.types.includes(DND_ITEM)

  async function onDrop(e: DragEvent) {
    if (!accepts(e)) return
    e.preventDefault()
    const slot = slotAt(e)
    setDropSlot(null)
    const itemKey = e.dataTransfer.getData(DND_ITEM)
    if (itemKey) {
      const from = items.findIndex((it) => String(it.key) === itemKey)
      if (from !== -1) move(from, slot > from ? slot - 1 : slot)
      return
    }
    const path = e.dataTransfer.getData(DND_FILE)
    if (!isPdf(path)) {
      setAddError(new Error('Only PDF files can be merged'))
      return
    }
    const before = items.length
    await add([path])
    // add() appends; move the new file to where it was dropped.
    if (slot < before) {
      setItems((list) =>
        list.length > before ? [...list.slice(0, slot), list[list.length - 1], ...list.slice(slot, -1)] : list,
      )
    }
  }

  const totalPages = items.reduce((sum, it) => sum + (typeof it.count === 'number' ? it.count : 0), 0)
  const invalid = items.some((it) => typeof it.count === 'string')
  const selectedPdf = selected && !selected.is_dir && isPdf(selected.path) ? selected : null

  return (
    <section className="tool">
      <header className="tool-header">
        <h1>Merge PDF</h1>
        <p>Combine PDFs into one document, in the order listed. Optionally take only some pages from each file.</p>
      </header>

      <div className="button-row">
        <button type="button" className="btn btn-secondary" onClick={addFromDialog}>
          <PlusIcon size={15} /> Add PDFs…
        </button>
        {selectedPdf && (
          <button type="button" className="btn btn-secondary" onClick={() => add([selectedPdf.path])}>
            Add {selectedPdf.name}
          </button>
        )}
        {items.length > 1 && (
          <button
            type="button"
            className="btn btn-ghost btn-sm"
            onClick={() => setItems((list) => [...list].sort((a, b) => a.info.name.localeCompare(b.info.name, undefined, { numeric: true })))}
          >
            Sort A–Z
          </button>
        )}
        {items.length > 0 && (
          <button type="button" className="btn btn-ghost btn-sm" onClick={() => setItems([])}>
            Clear list
          </button>
        )}
      </div>

      <ErrorNotice error={addError} />

      <ol
        ref={listRef}
        className={cls('merge-list', items.length === 0 && 'is-empty', dropSlot !== null && 'is-drop-target')}
        onDragOver={(e) => {
          if (!accepts(e)) return
          e.preventDefault()
          setDropSlot(slotAt(e))
        }}
        onDragLeave={(e) => {
          if (!e.currentTarget.contains(e.relatedTarget as Node | null)) setDropSlot(null)
        }}
        onDrop={onDrop}
      >
        {items.length === 0 && (
          <li className="merge-empty">
            <FilePdfIcon size={28} />
            <span>Drag PDFs here from the Explorer, or use Add PDFs…</span>
          </li>
        )}
        {items.map((item, i) => (
          <MergeRow
            key={item.key}
            item={item}
            index={i}
            last={i === items.length - 1}
            dropBefore={dropSlot === i}
            onChange={(patch) => update(item.key, patch)}
            onMove={(delta) => move(i, i + delta)}
            onRemove={() => setItems((list) => list.filter((it) => it.key !== item.key))}
          />
        ))}
        {dropSlot !== null && dropSlot === items.length && items.length > 0 && <li className="drop-end" aria-hidden="true" />}
      </ol>

      <ErrorNotice error={flow.error} />
      {flow.saved && (
        <ResultCard files={flow.saved} onDismiss={flow.dismiss} onContinue={(f) => openInTool('pdf-organize', f.path)} />
      )}

      {items.length > 0 && (
        <div className="action-bar">
          <label className="check">
            <input type="checkbox" checked={bookmarks} onChange={(e) => setBookmarks(e.target.checked)} />
            Add a bookmark for each file
          </label>
          <span className="muted">
            {items.length} {items.length === 1 ? 'file' : 'files'} · {totalPages} pages
          </span>
          <button
            type="button"
            className="btn btn-primary"
            disabled={flow.busy || invalid}
            onClick={() =>
              flow.saveAs(items[0].info.path, 'merged', (output) =>
                call('pdf_merge', items.map((it) => ({ path: it.info.path, pages: it.pages })), output, bookmarks),
              )
            }
          >
            {flow.busy ? 'Merging…' : 'Merge and save…'}
          </button>
        </div>
      )}
    </section>
  )
}

function MergeRow({
  item,
  index,
  last,
  dropBefore,
  onChange,
  onMove,
  onRemove,
}: {
  item: MergeItem
  index: number
  last: boolean
  dropBefore: boolean
  onChange: (patch: Partial<MergeItem>) => void
  onMove: (delta: number) => void
  onRemove: () => void
}) {
  const { info } = item
  const onChangeRef = useRef(onChange)
  useEffect(() => {
    onChangeRef.current = onChange
  })

  // Validate the page range in Python (same parser the merge uses).
  useEffect(() => {
    const spec = item.pages.trim()
    let active = true
    const t = window.setTimeout(() => {
      if (!spec) {
        onChangeRef.current({ count: info.page_count })
        return
      }
      call('pdf_split_plan', info.page_count, 'ranges', spec).then(
        (groups) => {
          if (active) onChangeRef.current({ count: groups.reduce((n, g) => n + g.length, 0) })
        },
        (err) => {
          if (active) onChangeRef.current({ count: toError(err).message })
        },
      )
    }, 200)
    return () => {
      active = false
      window.clearTimeout(t)
    }
  }, [item.pages, info.page_count])

  const error = typeof item.count === 'string' ? item.count : null

  return (
    <li
      data-merge-index={index}
      className={cls('merge-row', dropBefore && 'drop-before')}
      draggable
      onDragStart={(e) => {
        if ((e.target as HTMLElement).closest('input')) {
          e.preventDefault()
          return
        }
        e.dataTransfer.setData(DND_ITEM, String(item.key))
        e.dataTransfer.effectAllowed = 'move'
      }}
    >
      <span className="merge-pos">{index + 1}</span>
      <PageThumb file={info} index={0} page={info.pages[0] ?? { width: 595, height: 842 }} box={52} renderWidth={120} />
      <div className="merge-meta">
        <strong title={info.path}>{info.name}</strong>
        <span className="muted small">
          {info.page_count} {info.page_count === 1 ? 'page' : 'pages'} · {formatBytes(info.size)}
        </span>
      </div>
      <div className="merge-range">
        <input
          value={item.pages}
          placeholder={`All ${info.page_count} pages`}
          aria-label={`Pages to take from ${info.name}`}
          aria-invalid={error !== null}
          spellCheck={false}
          onChange={(e) => onChange({ pages: e.target.value })}
        />
        {error ? <span className="field-error">{error}</span> : item.pages.trim() && <span className="muted small">{item.count} pages</span>}
      </div>
      <div className="row-actions">
        <button type="button" className="icon-btn" aria-label="Move up" title="Move up" disabled={index === 0} onClick={() => onMove(-1)}>
          <ArrowUpIcon size={14} />
        </button>
        <button type="button" className="icon-btn" aria-label="Move down" title="Move down" disabled={last} onClick={() => onMove(1)}>
          <ArrowDownIcon size={14} />
        </button>
        <button type="button" className="icon-btn" aria-label="Remove" title="Remove" onClick={onRemove}>
          <CloseIcon size={14} />
        </button>
      </div>
    </li>
  )
}
