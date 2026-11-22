import { useEffect, useRef, useState } from 'react'
import { ErrorNotice } from '../components/ErrorNotice'
import { call, toError, type PdfInfo, type TextLine } from '../lib/bridge'
import { cls } from '../lib/cls'
import { CONVERT_EXTS, useToolRequest } from '../lib/workspace'
import { DocGate, PagePreview, ResultCard } from '../pdf/components'
import { usePdfDoc } from '../pdf/context'
import { PageNav } from '../pdf/PageNav'
import { useSaveFlow } from '../pdf/useSaveFlow'
import { BoxLayer, type Rect } from './BoxLayer'
import { newId, objectContent, toPayload, type EditObj, type Kind } from './objects'

type Tool = 'select' | 'edit-text' | Kind

const TOOLS: { id: Tool; label: string; hint: string }[] = [
  { id: 'select', label: 'Select', hint: 'Select, move and resize' },
  { id: 'edit-text', label: 'Edit text', hint: 'Click a line of existing text to change it' },
  { id: 'text', label: 'Text', hint: 'Click or drag to add text' },
  { id: 'image', label: 'Image', hint: 'Add a picture' },
  { id: 'rect', label: 'Box', hint: 'Drag to draw a rectangle' },
  { id: 'ellipse', label: 'Ellipse', hint: 'Drag to draw an ellipse' },
  { id: 'highlight', label: 'Highlight', hint: 'Drag over text to highlight it' },
  { id: 'whiteout', label: 'White-out', hint: 'Cover something with white' },
  { id: 'redact', label: 'Redact', hint: 'Black out and permanently remove the text underneath' },
]

export function EditPdf() {
  const pdf = usePdfDoc()
  useToolRequest('edit-pdf', (path) => void pdf.open(path))
  return (
    <section className="tool tool-wide">
      <header className="tool-header">
        <h1>Edit PDF</h1>
        <p>Change existing text, add text, pictures and shapes, highlight, white-out or redact. Changes are written into the pages when you save.</p>
      </header>
      <DocGate>{(doc) => <EditBody key={`${doc.path}|${doc.mtime}`} doc={doc} />}</DocGate>
    </section>
  )
}

function EditBody({ doc }: { doc: PdfInfo }) {
  const pdf = usePdfDoc()
  const [objects, setObjects] = useState<EditObj[]>([])
  const [selected, setSelected] = useState<string | null>(null)
  const [tool, setTool] = useState<Tool>('select')
  const [current, setCurrent] = useState(0)
  const [lines, setLines] = useState<TextLine[]>([])
  const [error, setError] = useState<Error | null>(null)
  const flow = useSaveFlow()
  const panelRef = useRef<HTMLDivElement>(null)
  const page = doc.pages[current]
  const sel = objects.find((o) => o.id === selected) ?? null

  useEffect(() => {
    if (tool !== 'edit-text') return
    let active = true
    call('pdf_text_lines', doc.path, current).then(
      (l) => active && setLines(l),
      (err) => active && setError(toError(err)),
    )
    return () => {
      active = false
    }
  }, [tool, current, doc.path])

  // Delete key removes the selected object (unless typing in a field).
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const tag = (e.target as HTMLElement)?.tagName
      if (!selected || tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT') return
      if (e.key === 'Delete' || e.key === 'Backspace') {
        setObjects((list) => list.filter((o) => o.id !== selected))
        setSelected(null)
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [selected])

  const update = (id: string, patch: Partial<EditObj>) => setObjects((list) => list.map((o) => (o.id === id ? { ...o, ...patch } : o)))
  const add = (obj: EditObj) => {
    setObjects((list) => [...list, obj])
    setSelected(obj.id)
    setTool('select')
  }

  function create(r: Rect) {
    if (tool === 'select' || tool === 'edit-text' || tool === 'image') return
    const sized = (w: number, h: number) => (r.w ? r : { x: Math.max(0, r.x - w / 2), y: Math.max(0, r.y - h / 2), w, h })
    if (tool === 'text') {
      const box = r.w ? r : { x: r.x, y: r.y, w: 180, h: 22 }
      add({ id: newId(), type: 'text', page: current, ...box, text: 'Text', size: 14, family: 'sans', color: '#000000' })
      return
    }
    const defaults: Partial<EditObj> =
      tool === 'rect' || tool === 'ellipse' ? { stroke: '#d32f2f', fill: null, width: 1.5 } : {}
    add({ id: newId(), type: tool, page: current, ...sized(120, tool === 'highlight' ? 16 : 40), ...defaults })
  }

  async function addImage() {
    try {
      const [path] = await call('pick_files', 'Images', CONVERT_EXTS['to-pdf-images'] ?? [], false)
      if (!path) return
      const [thumb] = await call('image_thumbnails', [path], 600)
      if (thumb.error || !thumb.data_url) throw new Error(thumb.error ?? 'Unreadable image')
      const w = Math.min(page.width * 0.4, 220)
      const h = (w * (thumb.height ?? 1)) / (thumb.width ?? 1)
      add({ id: newId(), type: 'image', page: current, x: (page.width - w) / 2, y: (page.height - h) / 2, w, h, src: path, preview: thumb.data_url })
    } catch (err) {
      setError(toError(err))
    }
  }

  function editLine(line: TextLine) {
    const cover: EditObj = { id: newId(), type: 'whiteout', page: current, x: line.x - 1, y: line.y - 1, w: line.w + 2, h: line.h + 2, remove_text: true }
    const text: EditObj = {
      id: newId(),
      type: 'text',
      page: current,
      x: line.x,
      y: line.y,
      w: line.w + 40,
      h: line.h + 4,
      text: line.text,
      size: line.size,
      bold: line.bold,
      family: line.family,
      color: '#000000',
    }
    setObjects((list) => [...list, cover, text])
    setSelected(text.id)
    setTool('select')
    window.setTimeout(() => panelRef.current?.querySelector('textarea')?.focus(), 50)
  }

  const onPage = objects.filter((o) => o.page === current)
  const counts = objects.reduce<Record<number, number>>((acc, o) => ({ ...acc, [o.page]: (acc[o.page] ?? 0) + 1 }), {})

  function save() {
    return flow.saveAs(doc.path, 'edited', (out) => call('pdf_apply_edits', doc.path, out, toPayload(objects)))
  }

  return (
    <>
      <div className="toolbar" role="toolbar" aria-label="Edit tools">
        {TOOLS.map((t) => (
          <button
            key={t.id}
            type="button"
            className={cls('btn btn-ghost btn-sm', tool === t.id && 'is-tool')}
            title={t.hint}
            aria-pressed={tool === t.id}
            onClick={() => (t.id === 'image' ? void addImage() : setTool(t.id))}
          >
            {t.label}
          </button>
        ))}
        <span className="toolbar-spacer" />
        <span className="muted small">{TOOLS.find((t) => t.id === tool)?.hint}</span>
      </div>
      <ErrorNotice error={error} />

      <div className="split-layout">
        <div className="split-main">
          <PagePreview
            file={doc}
            index={current}
            page={page}
            maxHeight={720}
            overlay={(scale) => (
              <BoxLayer
                page={page}
                scale={scale}
                boxes={onPage.map((o) => ({ ...o, className: `lbox-${o.type}`, content: objectContent(o, scale) }))}
                selected={selected}
                onSelect={setSelected}
                onChange={(id, r) => update(id, r)}
                onCreate={tool !== 'select' && tool !== 'edit-text' ? create : undefined}
              >
                {tool === 'edit-text' &&
                  lines.map((l, i) => (
                    <button
                      key={i}
                      type="button"
                      className="line-hit"
                      title={`Edit: ${l.text}`}
                      style={{ left: (l.x - 2) * scale, top: (l.y - 2) * scale, width: (l.w + 4) * scale, height: (l.h + 4) * scale }}
                      onPointerDown={(e) => e.stopPropagation()}
                      onClick={() => editLine(l)}
                    />
                  ))}
              </BoxLayer>
            )}
          />
          <PageNav index={current} count={doc.page_count} onChange={setCurrent} />
        </div>

        <aside className="side-panel" ref={panelRef}>
          {sel ? <Properties obj={sel} onChange={(p) => update(sel.id, p)} onDelete={() => {
                setObjects((l) => l.filter((o) => o.id !== sel.id))
                setSelected(null)
              }} /> : (
            <p className="muted small">Choose a tool above, then click or drag on the page. Select an object to change it here.</p>
          )}
          <h2 className="panel-title">Changes</h2>
          <p className="small">
            {objects.length === 0
              ? 'None yet.'
              : Object.entries(counts)
                  .map(([p, n]) => `page ${Number(p) + 1}: ${n}`)
                  .join(' · ')}
          </p>
          <div className="button-row">
            <button type="button" className="btn btn-ghost btn-sm" disabled={!objects.length} onClick={() => {
                setObjects([])
                setSelected(null)
              }}>
              Discard all
            </button>
          </div>
          <button type="button" className="btn btn-primary" disabled={flow.busy || !objects.length} onClick={save}>
            {flow.busy ? 'Saving…' : 'Save edited PDF…'}
          </button>
          <ErrorNotice error={flow.error} />
          {flow.saved && <ResultCard files={flow.saved} onDismiss={flow.dismiss} onContinue={(f) => void pdf.open(f.path)} />}
        </aside>
      </div>
    </>
  )
}

function Properties({ obj, onChange, onDelete }: { obj: EditObj; onChange: (p: Partial<EditObj>) => void; onDelete: () => void }) {
  const opacity = Math.round((obj.opacity ?? 1) * 100)
  return (
    <div className="props">
      <h2 className="panel-title">{TOOLS.find((t) => t.id === obj.type)?.label ?? obj.type}</h2>
      {obj.type === 'text' && (
        <>
          <textarea className="props-text" value={obj.text} onChange={(e) => onChange({ text: e.target.value })} rows={3} aria-label="Text" />
          <div className="field-grid">
            <label>
              Font
              <select className="text-input" value={obj.family} onChange={(e) => onChange({ family: e.target.value as EditObj['family'] })}>
                <option value="sans">Arial</option>
                <option value="serif">Times New Roman</option>
                <option value="mono">Courier New</option>
              </select>
            </label>
            <label>
              Size (pt)
              <input className="text-input num" type="number" min={4} max={200} value={obj.size} onChange={(e) => onChange({ size: Number(e.target.value) })} />
            </label>
            <label>
              Colour
              <input type="color" value={obj.color ?? '#000000'} onChange={(e) => onChange({ color: e.target.value })} />
            </label>
          </div>
          <div className="button-row">
            <label className="check">
              <input type="checkbox" checked={!!obj.bold} onChange={(e) => onChange({ bold: e.target.checked })} /> Bold
            </label>
            <label className="check">
              <input type="checkbox" checked={!!obj.italic} onChange={(e) => onChange({ italic: e.target.checked })} /> Italic
            </label>
          </div>
        </>
      )}
      {(obj.type === 'rect' || obj.type === 'ellipse') && (
        <div className="field-grid">
          <label className="check">
            <input type="checkbox" checked={!!obj.stroke} onChange={(e) => onChange({ stroke: e.target.checked ? '#d32f2f' : null })} /> Outline
          </label>
          {obj.stroke && <input type="color" value={obj.stroke} onChange={(e) => onChange({ stroke: e.target.value })} aria-label="Outline colour" />}
          <label className="check">
            <input type="checkbox" checked={!!obj.fill} onChange={(e) => onChange({ fill: e.target.checked ? '#fff59d' : null })} /> Fill
          </label>
          {obj.fill && <input type="color" value={obj.fill} onChange={(e) => onChange({ fill: e.target.value })} aria-label="Fill colour" />}
          <label>
            Line width
            <input className="text-input num" type="number" min={0.5} max={20} step={0.5} value={obj.width ?? 1.5} onChange={(e) => onChange({ width: Number(e.target.value) })} />
          </label>
        </div>
      )}
      {obj.type === 'whiteout' && (
        <label className="check">
          <input type="checkbox" checked={!!obj.remove_text} onChange={(e) => onChange({ remove_text: e.target.checked })} /> Also remove the text underneath
        </label>
      )}
      {obj.type === 'redact' && <p className="muted small">The text under this box is deleted from the file, not just covered.</p>}
      {obj.type !== 'redact' && obj.type !== 'whiteout' && (
        <label className="range-field">
          Opacity ({opacity}%)
          <input type="range" min={10} max={100} value={opacity} onChange={(e) => onChange({ opacity: Number(e.target.value) / 100 })} />
        </label>
      )}
      <p className="muted small">
        {Math.round(obj.x)}, {Math.round(obj.y)} · {Math.round(obj.w)} × {Math.round(obj.h)} pt
      </p>
      <button type="button" className="btn btn-ghost btn-sm" onClick={onDelete}>
        Delete (Del)
      </button>
    </div>
  )
}
