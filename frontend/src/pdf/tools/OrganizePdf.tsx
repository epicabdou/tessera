import { useRef, useState, type DragEvent, type KeyboardEvent, type MouseEvent } from 'react'
import { DND_FILE } from '../../browser/fileKinds'
import { ErrorNotice } from '../../components/ErrorNotice'
import {
  BlankPageIcon,
  DuplicateIcon,
  FilePdfIcon,
  RedoIcon,
  RotateCcwIcon,
  RotateCwIcon,
  TrashIcon,
  UndoIcon,
} from '../../components/icons'
import { call, toError, type OrganizeItem, type PdfInfo } from '../../lib/bridge'
import { cls } from '../../lib/cls'
import { isPdf, useToolRequest } from '../../lib/workspace'
import { DocGate, PageThumb, ResultCard } from '../components'
import { usePdfDoc } from '../context'
import { useHistory } from '../useHistory'
import { useSaveFlow } from '../useSaveFlow'

interface OrgPage {
  key: string
  source: string
  index: number
  rotate: number
  blank?: { width: number; height: number }
}

const DND_PAGES = 'application/x-toolbox-pages'
const A4 = { width: 595.28, height: 841.89 }

export function OrganizePdf() {
  const pdf = usePdfDoc()
  useToolRequest('pdf-organize', (path) => void pdf.open(path))
  return (
    <section className="tool tool-wide">
      <header className="tool-header">
        <h1>Organize PDF</h1>
        <p>Drag pages to reorder them; rotate, duplicate or delete them; insert blank pages or pages from another PDF.</p>
      </header>
      <DocGate>{(doc) => <OrganizeBody key={`${doc.path}|${doc.mtime}`} doc={doc} />}</DocGate>
    </section>
  )
}

function OrganizeBody({ doc }: { doc: PdfInfo }) {
  const pdf = usePdfDoc()
  const [sources, setSources] = useState<Record<string, PdfInfo>>({ doc })
  const history = useHistory<OrgPage[]>(() => doc.pages.map((_, i) => ({ key: `doc:${i}`, source: 'doc', index: i, rotate: 0 })))
  const pages = history.value
  const [selection, setSelection] = useState<ReadonlySet<string>>(new Set())
  const [dragKeys, setDragKeys] = useState<string[] | null>(null)
  const [dropSlot, setDropSlot] = useState<number | null>(null)
  const [error, setError] = useState<Error | null>(null)
  const anchor = useRef<string | null>(null)
  const seq = useRef(0)
  const gridRef = useRef<HTMLDivElement>(null)
  const flow = useSaveFlow()

  const newKey = (prefix: string) => `${prefix}:${++seq.current}`

  const sizeOf = (p: OrgPage) => p.blank ?? sources[p.source]?.pages[p.index] ?? A4

  /** Act on the selection, or on just `key` if it isn't part of the selection. */
  const targetsFor = (key?: string) => (key && !selection.has(key) ? new Set([key]) : selection)

  // --- edits -----------------------------------------------------------------

  const rotate = (keys: ReadonlySet<string>, delta: number) =>
    history.set((list) => list.map((p) => (keys.has(p.key) ? { ...p, rotate: (p.rotate + delta + 360) % 360 } : p)))

  const duplicate = (keys: ReadonlySet<string>) =>
    history.set((list) => list.flatMap((p) => (keys.has(p.key) ? [p, { ...p, key: newKey('dup') }] : [p])))

  const remove = (keys: ReadonlySet<string>) => {
    history.set((list) => list.filter((p) => !keys.has(p.key)))
    setSelection((s) => new Set([...s].filter((k) => !keys.has(k))))
  }

  /** Insert after the last selected page, or at the end. */
  const insertionPoint = () => {
    let at = pages.length
    pages.forEach((p, i) => selection.has(p.key) && (at = i + 1))
    return at
  }

  function insertBlank() {
    const at = insertionPoint()
    const neighbour = pages[at - 1]
    let size = neighbour ? sizeOf(neighbour) : A4
    if (neighbour && neighbour.rotate % 180) size = { width: size.height, height: size.width }
    history.set((list) => [...list.slice(0, at), { key: newKey('blank'), source: '', index: 0, rotate: 0, blank: size }, ...list.slice(at)])
  }

  async function insertPdf(path: string, at: number) {
    try {
      const info = await call('pdf_info', path)
      const id = `ins${++seq.current}`
      setSources((s) => ({ ...s, [id]: info }))
      const added = info.pages.map((_, i) => ({ key: newKey(id), source: id, index: i, rotate: 0 }))
      history.set((list) => [...list.slice(0, at), ...added, ...list.slice(at)])
      setSelection(new Set(added.map((p) => p.key)))
    } catch (err) {
      setError(toError(err))
    }
  }

  async function insertFromDialog() {
    try {
      const [path] = await call('pick_pdfs', false)
      if (path) await insertPdf(path, insertionPoint())
    } catch (err) {
      setError(toError(err))
    }
  }

  function moveTo(keys: string[], slot: number) {
    const moving = new Set(keys)
    history.set((list) => {
      const before = list.slice(0, slot).filter((p) => !moving.has(p.key)).length
      const rest = list.filter((p) => !moving.has(p.key))
      const block = list.filter((p) => moving.has(p.key))
      const next = [...rest.slice(0, before), ...block, ...rest.slice(before)]
      return next.every((p, i) => p === list[i]) ? list : next
    })
  }

  // --- selection ---------------------------------------------------------------

  function onCardClick(e: MouseEvent, key: string) {
    e.stopPropagation()
    if (e.shiftKey && anchor.current) {
      const a = pages.findIndex((p) => p.key === anchor.current)
      const b = pages.findIndex((p) => p.key === key)
      const range = pages.slice(Math.min(a, b), Math.max(a, b) + 1).map((p) => p.key)
      setSelection((s) => new Set(e.ctrlKey || e.metaKey ? [...s, ...range] : range))
      return
    }
    anchor.current = key
    if (e.ctrlKey || e.metaKey) {
      setSelection((s) => {
        const next = new Set(s)
        if (next.has(key)) next.delete(key)
        else next.add(key)
        return next
      })
    } else {
      setSelection(new Set([key]))
    }
  }

  function onGridKeyDown(e: KeyboardEvent) {
    const ctrl = e.ctrlKey || e.metaKey
    if ((e.key === 'Delete' || e.key === 'Backspace') && selection.size) remove(selection)
    else if (ctrl && e.key.toLowerCase() === 'a') setSelection(new Set(pages.map((p) => p.key)))
    else if (ctrl && e.key.toLowerCase() === 'z' && !e.shiftKey) history.undo()
    else if (ctrl && (e.key.toLowerCase() === 'y' || (e.key.toLowerCase() === 'z' && e.shiftKey))) history.redo()
    else if (e.key === 'Escape') setSelection(new Set())
    else return
    e.preventDefault()
  }

  // --- drag & drop -------------------------------------------------------------

  function slotAt(e: DragEvent): number {
    let best = pages.length
    let bestDistance = Infinity
    for (const el of gridRef.current?.querySelectorAll<HTMLElement>('[data-org-index]') ?? []) {
      const r = el.getBoundingClientRect()
      const cx = r.left + r.width / 2
      const d = Math.hypot(e.clientX - cx, e.clientY - (r.top + r.height / 2))
      if (d < bestDistance) {
        bestDistance = d
        best = Number(el.dataset.orgIndex) + (e.clientX < cx ? 0 : 1)
      }
    }
    return best
  }

  const accepts = (e: DragEvent) => e.dataTransfer.types.includes(DND_PAGES) || e.dataTransfer.types.includes(DND_FILE)

  function onDrop(e: DragEvent) {
    if (!accepts(e)) return
    e.preventDefault()
    const slot = slotAt(e)
    setDropSlot(null)
    if (dragKeys) {
      moveTo(dragKeys, slot)
      setDragKeys(null)
      return
    }
    const path = e.dataTransfer.getData(DND_FILE)
    if (isPdf(path)) void insertPdf(path, slot)
    else setError(new Error('Only PDF pages can be inserted'))
  }

  // --- save --------------------------------------------------------------------

  function save() {
    const used = new Set(pages.filter((p) => !p.blank).map((p) => p.source))
    const sourcePaths = Object.fromEntries([...used].map((id) => [id, sources[id].path]))
    const items: OrganizeItem[] = pages.map((p) =>
      p.blank ? { blank: true, ...p.blank } : { source: p.source, index: p.index, rotate: p.rotate },
    )
    return flow.saveAs(doc.path, 'organized', (output) => call('pdf_organize', output, sourcePaths, items))
  }

  const changed = history.canUndo
  const sel = selection.size

  return (
    <>
      <div className="toolbar" role="toolbar" aria-label="Page actions">
        <button type="button" className="icon-btn" title="Undo (Ctrl+Z)" aria-label="Undo" disabled={!history.canUndo} onClick={history.undo}>
          <UndoIcon size={16} />
        </button>
        <button type="button" className="icon-btn" title="Redo (Ctrl+Y)" aria-label="Redo" disabled={!history.canRedo} onClick={history.redo}>
          <RedoIcon size={16} />
        </button>
        <span className="toolbar-sep" />
        <button type="button" className="btn btn-ghost btn-sm" disabled={!sel} onClick={() => rotate(selection, -90)}>
          <RotateCcwIcon size={14} /> Left
        </button>
        <button type="button" className="btn btn-ghost btn-sm" disabled={!sel} onClick={() => rotate(selection, 90)}>
          <RotateCwIcon size={14} /> Right
        </button>
        <button type="button" className="btn btn-ghost btn-sm" disabled={!sel} onClick={() => duplicate(selection)}>
          <DuplicateIcon size={14} /> Duplicate
        </button>
        <button type="button" className="btn btn-ghost btn-sm" disabled={!sel} onClick={() => remove(selection)}>
          <TrashIcon size={14} /> Delete
        </button>
        <span className="toolbar-sep" />
        <button type="button" className="btn btn-ghost btn-sm" onClick={insertBlank}>
          <BlankPageIcon size={14} /> Blank page
        </button>
        <button type="button" className="btn btn-ghost btn-sm" onClick={insertFromDialog}>
          <FilePdfIcon size={14} /> Insert PDF…
        </button>
        <span className="toolbar-spacer" />
        <span className="muted small">{sel ? `${sel} selected` : 'Click to select · Ctrl/Shift for more'}</span>
        <button
          type="button"
          className="btn btn-ghost btn-sm"
          disabled={!changed}
          onClick={() => {
            history.reset(doc.pages.map((_, i) => ({ key: `doc:${i}`, source: 'doc', index: i, rotate: 0 })))
            setSelection(new Set())
          }}
        >
          Reset
        </button>
      </div>

      <ErrorNotice error={error} />

      <div
        ref={gridRef}
        className="page-grid is-sortable"
        tabIndex={0}
        aria-label="Pages"
        onKeyDown={onGridKeyDown}
        onClick={() => setSelection(new Set())}
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
        {pages.length === 0 && <p className="muted grid-empty">No pages left. Undo, insert pages, or drop a PDF here.</p>}
        {pages.map((p, i) => {
          const src = p.blank ? null : sources[p.source]
          const origin = p.blank ? 'Blank' : p.source === 'doc' ? `p. ${p.index + 1}` : `${src?.name} · p. ${p.index + 1}`
          return (
            <div
              key={p.key}
              data-org-index={i}
              className={cls(
                'page-card',
                'is-clickable',
                selection.has(p.key) && 'is-selected',
                dragKeys?.includes(p.key) && 'is-dragging',
                dropSlot === i && 'drop-before',
                dropSlot === pages.length && i === pages.length - 1 && 'drop-after',
              )}
              title={`Page ${i + 1} (${origin})`}
              draggable
              onDragStart={(e) => {
                const keys = selection.has(p.key) ? pages.filter((q) => selection.has(q.key)).map((q) => q.key) : [p.key]
                setDragKeys(keys)
                e.dataTransfer.setData(DND_PAGES, keys.join(','))
                e.dataTransfer.effectAllowed = 'move'
              }}
              onDragEnd={() => {
                setDragKeys(null)
                setDropSlot(null)
              }}
              onClick={(e) => onCardClick(e, p.key)}
            >
              <PageThumb file={src} index={p.index} page={sizeOf(p)} rotate={p.rotate} blank={!!p.blank} />
              <div className="card-tools" onClick={(e) => e.stopPropagation()}>
                <button type="button" title="Rotate left" aria-label="Rotate left" onClick={() => rotate(targetsFor(p.key), -90)}>
                  <RotateCcwIcon size={13} />
                </button>
                <button type="button" title="Rotate right" aria-label="Rotate right" onClick={() => rotate(targetsFor(p.key), 90)}>
                  <RotateCwIcon size={13} />
                </button>
                <button type="button" title="Duplicate" aria-label="Duplicate" onClick={() => duplicate(targetsFor(p.key))}>
                  <DuplicateIcon size={13} />
                </button>
                <button type="button" title="Delete" aria-label="Delete" onClick={() => remove(targetsFor(p.key))}>
                  <TrashIcon size={13} />
                </button>
              </div>
              <span className="page-label">
                {i + 1}
                <span className="page-origin">{origin}</span>
              </span>
            </div>
          )
        })}
      </div>

      <div className="action-bar">
        <span className="muted">
          {pages.length} {pages.length === 1 ? 'page' : 'pages'}
          {changed ? ' · edited' : ''}
        </span>
        <button type="button" className="btn btn-primary" disabled={flow.busy || pages.length === 0 || !changed} onClick={save}>
          {flow.busy ? 'Saving…' : 'Save PDF…'}
        </button>
      </div>

      <ErrorNotice error={flow.error} />
      {flow.saved && <ResultCard files={flow.saved} onDismiss={flow.dismiss} onContinue={(f) => void pdf.open(f.path)} />}
    </>
  )
}
