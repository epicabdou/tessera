import { useCallback, useEffect, useState } from 'react'
import { ErrorNotice } from '../components/ErrorNotice'
import { call, toError, type FormField, type PdfInfo } from '../lib/bridge'
import { cls } from '../lib/cls'
import { useToolRequest } from '../lib/workspace'
import { DocGate, PagePreview, ResultCard } from '../pdf/components'
import { usePdfDoc } from '../pdf/context'
import { PageNav } from '../pdf/PageNav'
import { useSaveFlow } from '../pdf/useSaveFlow'
import { BoxLayer, type Rect } from './BoxLayer'

type NewType = 'text' | 'multiline' | 'checkbox' | 'dropdown' | 'listbox'
interface NewField extends Rect {
  id: string
  page: number
  type: NewType
  name: string
  options: string
  required: boolean
  value: string
}

const TYPES: { id: NewType; label: string; size: [number, number] }[] = [
  { id: 'text', label: 'Text box', size: [180, 22] },
  { id: 'multiline', label: 'Multi-line text', size: [240, 64] },
  { id: 'checkbox', label: 'Checkbox', size: [14, 14] },
  { id: 'dropdown', label: 'Dropdown', size: [160, 22] },
  { id: 'listbox', label: 'List box', size: [160, 64] },
]

export function PdfForms() {
  const pdf = usePdfDoc()
  useToolRequest('pdf-forms', (path) => void pdf.open(path))
  return (
    <section className="tool tool-wide">
      <header className="tool-header">
        <h1>PDF Forms</h1>
        <p>Fill in an existing form, or design one by adding text boxes, checkboxes and dropdowns.</p>
      </header>
      <DocGate>{(doc) => <FormsBody key={`${doc.path}|${doc.mtime}`} doc={doc} />}</DocGate>
    </section>
  )
}

function FormsBody({ doc }: { doc: PdfInfo }) {
  const [fields, setFields] = useState<FormField[] | null>(null)
  const [mode, setMode] = useState<'fill' | 'design'>('fill')
  const [error, setError] = useState<Error | null>(null)

  const load = useCallback(() => {
    call('form_fields', doc.path).then(
      (f) => {
        setFields(f)
        if (!f.length) setMode('design')
      },
      (err) => setError(toError(err)),
    )
  }, [doc.path])
  useEffect(load, [load])

  return (
    <>
      <div className="segmented" role="radiogroup">
        {(
          [
            ['fill', `Fill form${fields ? ` (${fields.length} fields)` : ''}`],
            ['design', 'Design fields'],
          ] as const
        ).map(([id, label]) => (
          <button key={id} type="button" role="radio" aria-checked={mode === id} className={cls('segment', mode === id && 'is-on')} onClick={() => setMode(id)}>
            {label}
          </button>
        ))}
      </div>
      <ErrorNotice error={error} />
      {fields && (mode === 'fill' ? <FillMode doc={doc} fields={fields} /> : <DesignMode doc={doc} existing={fields} />)}
    </>
  )
}

function FillMode({ doc, fields }: { doc: PdfInfo; fields: FormField[] }) {
  const pdf = usePdfDoc()
  const flow = useSaveFlow()
  const [values, setValues] = useState<Record<string, string | boolean>>(() =>
    Object.fromEntries(fields.map((f) => [f.name, f.type === 'checkbox' ? f.value !== '' : f.value])),
  )
  const [changed, setChanged] = useState<Set<string>>(new Set())
  const [flatten, setFlatten] = useState(false)
  const [current, setCurrent] = useState(0)
  const [focus, setFocus] = useState<string | null>(null)
  const fillable = fields.filter((f) => !['signature', 'button'].includes(f.type))
  const set = (name: string, value: string | boolean) => {
    setValues((v) => ({ ...v, [name]: value }))
    setChanged((c) => new Set(c).add(name))
  }

  if (!fields.length) return <p className="muted">This PDF has no form fields yet. Switch to “Design fields” to add some.</p>

  const page = doc.pages[current]
  const boxes = fillable.flatMap((f) =>
    f.widgets.filter((w) => w.page === current).map((w, i) => ({ id: `${f.name}#${i}`, x: w.x, y: w.y, w: w.w, h: w.h, locked: true, className: 'lbox-field', title: f.name })),
  )

  return (
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
              boxes={boxes}
              selected={focus ? boxes.find((b) => b.id.startsWith(`${focus}#`))?.id ?? null : null}
              onSelect={(id) => {
                const name = id?.split('#')[0] ?? null
                setFocus(name)
                if (name) document.getElementById(`ff-${name}`)?.focus()
              }}
            />
          )}
        />
        <PageNav index={current} count={doc.page_count} onChange={setCurrent} />
      </div>
      <aside className="side-panel form-panel">
        <h2 className="panel-title">Fields</h2>
        {fillable.map((f) => (
          <label key={f.name} className={cls('form-field', focus === f.name && 'is-focus')} onFocus={() => {
            setFocus(f.name)
            const w = f.widgets[0]
            if (w && w.page !== current) setCurrent(w.page)
          }}>
            <span className="form-field-name">
              {f.name}
              {f.required && <span className="field-error"> *</span>}
            </span>
            {f.type === 'checkbox' ? (
              <input id={`ff-${f.name}`} type="checkbox" checked={!!values[f.name]} disabled={f.readonly} onChange={(e) => set(f.name, e.target.checked)} />
            ) : f.type === 'multiline' ? (
              <textarea id={`ff-${f.name}`} rows={3} value={String(values[f.name] ?? '')} disabled={f.readonly} onChange={(e) => set(f.name, e.target.value)} />
            ) : f.type === 'dropdown' || f.type === 'listbox' || f.type === 'radio' ? (
              <select id={`ff-${f.name}`} className="text-input" value={String(values[f.name] ?? '')} disabled={f.readonly} onChange={(e) => set(f.name, e.target.value)}>
                <option value="">—</option>
                {f.options.map((o) => (
                  <option key={o} value={o}>
                    {o}
                  </option>
                ))}
              </select>
            ) : (
              <input id={`ff-${f.name}`} className="text-input" value={String(values[f.name] ?? '')} disabled={f.readonly} onChange={(e) => set(f.name, e.target.value)} />
            )}
          </label>
        ))}
        <label className="check">
          <input type="checkbox" checked={flatten} onChange={(e) => setFlatten(e.target.checked)} /> Flatten (make the answers part of the page; no longer editable)
        </label>
        <button
          type="button"
          className="btn btn-primary"
          disabled={flow.busy || changed.size === 0}
          onClick={() =>
            flow.saveAs(doc.path, 'filled', (out) =>
              call('form_fill', doc.path, out, Object.fromEntries([...changed].map((n) => [n, values[n]])), flatten),
            )
          }
        >
          {flow.busy ? 'Saving…' : 'Save filled form…'}
        </button>
        <ErrorNotice error={flow.error} />
        {flow.saved && <ResultCard files={flow.saved} onDismiss={flow.dismiss} onContinue={(f) => void pdf.open(f.path)} />}
      </aside>
    </div>
  )
}

function DesignMode({ doc, existing }: { doc: PdfInfo; existing: FormField[] }) {
  const pdf = usePdfDoc()
  const flow = useSaveFlow()
  const [specs, setSpecs] = useState<NewField[]>([])
  const [tool, setTool] = useState<NewType | null>('text')
  const [selected, setSelected] = useState<string | null>(null)
  const [current, setCurrent] = useState(0)
  const page = doc.pages[current]
  const sel = specs.find((s) => s.id === selected) ?? null
  const taken = new Set([...existing.map((f) => f.name), ...specs.map((s) => s.name)])

  const update = (id: string, patch: Partial<NewField>) => setSpecs((list) => list.map((s) => (s.id === id ? { ...s, ...patch } : s)))
  function create(r: Rect) {
    if (!tool) return
    const [w, h] = TYPES.find((t) => t.id === tool)!.size
    let n = specs.length + existing.length + 1
    while (taken.has(`field${n}`)) n++
    const spec: NewField = {
      id: `f${Date.now()}`,
      page: current,
      type: tool,
      name: `field${n}`,
      options: tool === 'dropdown' || tool === 'listbox' ? 'Option 1\nOption 2' : '',
      required: false,
      value: '',
      ...(r.w ? r : { x: r.x, y: r.y, w, h }),
    }
    setSpecs((list) => [...list, spec])
    setSelected(spec.id)
  }

  const boxes = [
    ...existing.flatMap((f) =>
      f.widgets.filter((w) => w.page === current).map((w, i) => ({ id: `old:${f.name}#${i}`, ...w, locked: true, className: 'lbox-field is-existing', title: `${f.name} (existing)` })),
    ),
    ...specs.filter((s) => s.page === current).map((s) => ({ ...s, className: `lbox-field lbox-new-${s.type}`, content: <span className="lbox-label">{s.name}</span> })),
  ]
  const nameError = sel && (!sel.name.trim() ? 'Enter a name' : [...taken].filter((n) => n === sel.name).length > 1 || existing.some((f) => f.name === sel.name) ? 'Name already used' : null)
  const anyError = specs.some((s) => !s.name.trim() || existing.some((f) => f.name === s.name) || specs.filter((o) => o.name === s.name).length > 1)

  return (
    <>
      <div className="toolbar" role="toolbar">
        <span className="muted small">Add:</span>
        {TYPES.map((t) => (
          <button key={t.id} type="button" className={cls('btn btn-ghost btn-sm', tool === t.id && 'is-tool')} onClick={() => setTool(t.id)}>
            {t.label}
          </button>
        ))}
        <button type="button" className={cls('btn btn-ghost btn-sm', tool === null && 'is-tool')} onClick={() => setTool(null)}>
          Select
        </button>
        <span className="toolbar-spacer" />
        <span className="muted small">{tool ? 'Click or drag on the page to place it' : 'Drag fields to move or resize them'}</span>
      </div>
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
                boxes={boxes}
                selected={selected}
                onSelect={(id) => setSelected(id && !id.startsWith('old:') ? id : null)}
                onChange={(id, r) => update(id, r)}
                onCreate={tool ? create : undefined}
              />
            )}
          />
          <PageNav index={current} count={doc.page_count} onChange={setCurrent} />
        </div>
        <aside className="side-panel">
          {sel ? (
            <>
              <h2 className="panel-title">{TYPES.find((t) => t.id === sel.type)?.label}</h2>
              <label className="form-field">
                <span className="form-field-name">Name</span>
                <input className="text-input" value={sel.name} aria-invalid={!!nameError} onChange={(e) => update(sel.id, { name: e.target.value.replace(/\s+/g, '_') })} />
                {nameError && <span className="field-error small">{nameError}</span>}
              </label>
              {(sel.type === 'dropdown' || sel.type === 'listbox') && (
                <label className="form-field">
                  <span className="form-field-name">Options (one per line)</span>
                  <textarea rows={4} value={sel.options} onChange={(e) => update(sel.id, { options: e.target.value })} />
                </label>
              )}
              {sel.type !== 'checkbox' && (
                <label className="form-field">
                  <span className="form-field-name">Default value</span>
                  <input className="text-input" value={sel.value} onChange={(e) => update(sel.id, { value: e.target.value })} />
                </label>
              )}
              <label className="check">
                <input type="checkbox" checked={sel.required} onChange={(e) => update(sel.id, { required: e.target.checked })} /> Required
              </label>
              <button
                type="button"
                className="btn btn-ghost btn-sm"
                onClick={() => {
                  setSpecs((l) => l.filter((s) => s.id !== sel.id))
                  setSelected(null)
                }}
              >
                Remove field
              </button>
            </>
          ) : (
            <p className="muted small">Pick a field type above and click on the page. Existing fields are shown in grey.</p>
          )}
          <h2 className="panel-title">New fields</h2>
          <p className="small">{specs.length ? specs.map((s) => s.name).join(', ') : 'None yet.'}</p>
          <button
            type="button"
            className="btn btn-primary"
            disabled={flow.busy || !specs.length || anyError}
            onClick={() =>
              flow.saveAs(doc.path, 'form', (out) =>
                call(
                  'form_add_fields',
                  doc.path,
                  out,
                  specs.map((s) => ({
                    page: s.page,
                    type: s.type,
                    name: s.name,
                    x: s.x,
                    y: s.y,
                    w: s.w,
                    h: s.h,
                    required: s.required,
                    value: s.type === 'checkbox' ? false : s.value,
                    options: s.options.split('\n').map((o) => o.trim()).filter(Boolean),
                  })),
                ),
              )
            }
          >
            {flow.busy ? 'Saving…' : 'Save form…'}
          </button>
          <ErrorNotice error={flow.error} />
          {flow.saved && <ResultCard files={flow.saved} onDismiss={flow.dismiss} onContinue={(f) => void pdf.open(f.path)} />}
        </aside>
      </div>
    </>
  )
}
