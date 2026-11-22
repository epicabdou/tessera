import { useEffect, useRef, useState } from 'react'
import { ErrorNotice } from '../components/ErrorNotice'
import { CloseIcon, FileIcon, PlusIcon } from '../components/icons'
import { call, toError, type ConversionEngines, type ConvertedPdf, type OfficeKind } from '../lib/bridge'
import { cls } from '../lib/cls'
import { dirname, formatBytes, samePath } from '../lib/format'
import { CONVERT_EXTS, extOf, useToolRequest, useWorkspace, type ToolId } from '../lib/workspace'
import { EmptyDrop, OutputChooser } from './shared'
import { basename, useFileDrop } from './util'

type Engine = 'auto' | 'office' | 'libreoffice'
type Options = Record<string, string | boolean>

interface Item {
  key: number
  path: string
  status: 'ready' | 'converting' | 'done' | 'error'
  result?: ConvertedPdf
  error?: string
}

const INFO: Record<OfficeKind, { tool: ToolId; title: string; app: string; label: string; noun: string; blurb: string; kindClass: string }> = {
  word: {
    tool: 'to-pdf-word',
    title: 'Word to PDF',
    app: 'Microsoft Word',
    label: 'Word documents',
    noun: 'document',
    blurb: 'Convert DOC and DOCX documents (also RTF and ODT) to PDF.',
    kindClass: 'kind-word',
  },
  powerpoint: {
    tool: 'to-pdf-powerpoint',
    title: 'PowerPoint to PDF',
    app: 'Microsoft PowerPoint',
    label: 'PowerPoint presentations',
    noun: 'presentation',
    blurb: 'Convert PPT and PPTX presentations to PDF, as slides, notes pages or handouts.',
    kindClass: 'kind-powerpoint',
  },
  excel: {
    tool: 'to-pdf-excel',
    title: 'Excel to PDF',
    app: 'Microsoft Excel',
    label: 'Excel spreadsheets',
    noun: 'spreadsheet',
    blurb: 'Convert XLS and XLSX spreadsheets (also CSV and ODS) to PDF.',
    kindClass: 'kind-excel',
  },
}

const DEFAULTS: Record<OfficeKind, Options> = {
  word: { bookmarks: true, markup: false, quality: 'print', pdfa: false },
  excel: { scope: 'workbook', fit_width: true, landscape: false, print_areas: true, quality: 'print', pdfa: false },
  powerpoint: { layout: 'slides', hidden_slides: false, frame: false, quality: 'print', pdfa: false },
}

export const WordToPdf = () => <OfficeToPdf kind="word" />
export const PowerPointToPdf = () => <OfficeToPdf kind="powerpoint" />
export const ExcelToPdf = () => <OfficeToPdf kind="excel" />

function OfficeToPdf({ kind }: { kind: OfficeKind }) {
  const info = INFO[kind]
  const exts = CONVERT_EXTS[info.tool] ?? []
  const { selected, filesChanged } = useWorkspace()
  const [items, setItems] = useState<Item[]>([])
  const [engines, setEngines] = useState<ConversionEngines | null>(null)
  const [engine, setEngine] = useState<Engine>('auto')
  const [folder, setFolder] = useState<string | null>(null)
  const [options, setOptions] = useState<Options>(DEFAULTS[kind])
  const [running, setRunning] = useState(false)
  const [notice, setNotice] = useState<Error | null>(null)
  const seq = useRef(1)

  useEffect(() => {
    call('conversion_engines').then(setEngines, (err) => setNotice(toError(err)))
  }, [])

  function add(paths: string[]) {
    const ok = paths.filter((p) => exts.includes(extOf(p)))
    setNotice(ok.length < paths.length ? new Error(`Skipped files that aren't ${info.label.toLowerCase()}.`) : null)
    setItems((list) => [
      ...list,
      ...ok.filter((p) => !list.some((i) => samePath(i.path, p))).map((path) => ({ key: seq.current++, path, status: 'ready' as const })),
    ])
  }

  useToolRequest(info.tool, (path) => add([path]))
  const drop = useFileDrop(add)

  async function pick() {
    try {
      add(await call('pick_files', info.label, exts, true))
    } catch (err) {
      setNotice(toError(err))
    }
  }

  const update = (key: number, patch: Partial<Item>) => setItems((list) => list.map((i) => (i.key === key ? { ...i, ...patch } : i)))

  async function convertAll() {
    setRunning(true)
    for (const item of items) {
      if (item.status === 'done') continue
      update(item.key, { status: 'converting', error: undefined })
      try {
        update(item.key, { status: 'done', result: await call('convert_office', kind, item.path, folder, engine, options) })
      } catch (err) {
        update(item.key, { status: 'error', error: toError(err).message })
      }
    }
    setRunning(false)
    filesChanged()
  }

  const officeOk = engines?.office[kind] ?? false
  const libreOk = !!engines?.libreoffice
  const using = engine === 'auto' ? (officeOk ? 'office' : libreOk ? 'libreoffice' : null) : engine
  const missing = engines !== null && !officeOk && !libreOk
  const selectedFile = selected && !selected.is_dir && exts.includes(extOf(selected.path)) ? selected : null
  const pending = items.filter((i) => i.status !== 'done').length
  const set = (patch: Options) => setOptions((o) => ({ ...o, ...patch }))

  return (
    <section className="tool">
      <header className="tool-header">
        <h1>{info.title}</h1>
        <p>{info.blurb}</p>
      </header>

      {missing ? (
        <div className="notice notice-error">
          Converting {info.label.toLowerCase()} needs {info.app} (part of Microsoft 365) or the free LibreOffice. Install either one, then
          reopen this tool.
        </div>
      ) : (
        <div className="engine-line">
          <span className="muted">Converts with</span>
          {officeOk && libreOk ? (
            <select className="text-input" value={engine} onChange={(e) => setEngine(e.target.value as Engine)} aria-label="Conversion engine">
              <option value="auto">{info.app} (best)</option>
              <option value="libreoffice">LibreOffice</option>
            </select>
          ) : (
            <strong>{engines === null ? '…' : using === 'office' ? info.app : 'LibreOffice'}</strong>
          )}
        </div>
      )}

      <div className="button-row">
        <button type="button" className="btn btn-secondary" onClick={pick} disabled={running}>
          <PlusIcon size={15} /> Add {info.label.toLowerCase()}…
        </button>
        {selectedFile && (
          <button type="button" className="btn btn-secondary" onClick={() => add([selectedFile.path])} disabled={running}>
            Add {selectedFile.name}
          </button>
        )}
        {items.length > 0 && (
          <button type="button" className="btn btn-ghost btn-sm" onClick={() => setItems([])} disabled={running}>
            Clear list
          </button>
        )}
      </div>

      <ErrorNotice error={notice} />

      <ul className={cls('conv-list', drop.over && 'is-over')} {...drop.props}>
        {items.length === 0 && (
          <li>
            <EmptyDrop icon={<FileIcon size={28} />} over={drop.over}>
              Drag {info.label.toLowerCase()} here from the Explorer, or use Add.
            </EmptyDrop>
          </li>
        )}
        {items.map((item) => (
          <ConvRow key={item.key} item={item} kindClass={info.kindClass} running={running} onRemove={() => setItems((l) => l.filter((i) => i.key !== item.key))} />
        ))}
      </ul>

      <div className="card conv-options">
        <h2 className="card-title">Options</h2>
        {kind === 'word' && (
          <div className="opt-grid">
            <label className="check span-2">
              <input type="checkbox" checked={!!options.bookmarks} onChange={(e) => set({ bookmarks: e.target.checked })} />
              Create bookmarks from headings
            </label>
            <label className="check span-2">
              <input type="checkbox" checked={!!options.markup} onChange={(e) => set({ markup: e.target.checked })} />
              Include comments and tracked changes
            </label>
          </div>
        )}
        {kind === 'excel' && (
          <div className="opt-grid">
            <label>
              Sheets
              <select className="text-input" value={String(options.scope)} onChange={(e) => set({ scope: e.target.value })}>
                <option value="workbook">Whole workbook</option>
                <option value="active">Active sheet only</option>
              </select>
            </label>
            <label className="check span-2">
              <input type="checkbox" checked={!!options.fit_width} onChange={(e) => set({ fit_width: e.target.checked })} />
              Fit each sheet to one page wide
            </label>
            <label className="check span-2">
              <input type="checkbox" checked={!!options.landscape} onChange={(e) => set({ landscape: e.target.checked })} />
              Landscape pages
            </label>
            <label className="check span-2">
              <input type="checkbox" checked={!!options.print_areas} onChange={(e) => set({ print_areas: e.target.checked })} />
              Use print areas set in the workbook
            </label>
          </div>
        )}
        {kind === 'powerpoint' && (
          <div className="opt-grid">
            <label>
              Layout
              <select className="text-input" value={String(options.layout)} onChange={(e) => set({ layout: e.target.value })}>
                <option value="slides">Slides</option>
                <option value="notes">Notes pages</option>
                <option value="handouts2">Handouts, 2 per page</option>
                <option value="handouts3">Handouts, 3 per page</option>
                <option value="handouts6">Handouts, 6 per page</option>
              </select>
            </label>
            <label className="check span-2">
              <input type="checkbox" checked={!!options.hidden_slides} onChange={(e) => set({ hidden_slides: e.target.checked })} />
              Include hidden slides
            </label>
            <label className="check span-2">
              <input type="checkbox" checked={!!options.frame} onChange={(e) => set({ frame: e.target.checked })} />
              Frame slides
            </label>
          </div>
        )}
        <div className="opt-grid">
          <label>
            Optimise for
            <select className="text-input" value={String(options.quality)} onChange={(e) => set({ quality: e.target.value })}>
              <option value="print">Printing (best quality)</option>
              <option value="small">Screen (smaller file)</option>
            </select>
          </label>
          <label className="check span-2">
            <input type="checkbox" checked={!!options.pdfa} onChange={(e) => set({ pdfa: e.target.checked })} />
            PDF/A (for long-term archiving)
          </label>
        </div>
        {using === 'libreoffice' && <p className="muted small">These options apply to {info.app}. LibreOffice uses its own defaults.</p>}
        <OutputChooser folder={folder} onChange={setFolder} what={info.noun} />
      </div>

      <div className="action-bar">
        <span className="muted">
          {items.length === 0 ? `No ${info.noun}s yet` : `${items.length} ${info.noun}${items.length === 1 ? '' : 's'}`}
          {running ? ' · converting…' : ''}
        </span>
        <button type="button" className="btn btn-primary" disabled={running || pending === 0 || missing} onClick={convertAll}>
          {running ? 'Converting…' : pending > 1 ? `Convert ${pending} to PDF` : 'Convert to PDF'}
        </button>
      </div>
    </section>
  )
}

function ConvRow({ item, kindClass, running, onRemove }: { item: Item; kindClass: string; running: boolean; onRemove: () => void }) {
  const [error, setError] = useState<string | null>(null)
  const act = (fn: () => Promise<unknown>) => fn().catch((err) => setError(toError(err).message))
  return (
    <li className={cls('conv-row', `is-${item.status}`)}>
      <FileIcon size={20} className={kindClass} />
      <div className="conv-meta">
        <strong title={item.path}>{basename(item.path)}</strong>
        <span className="muted small mono">{dirname(item.path)}</span>
      </div>
      <div className="conv-status">
        {item.status === 'ready' && <span className="muted small">Ready</span>}
        {item.status === 'converting' && (
          <span className="small">
            <span className="spinner" /> Converting…
          </span>
        )}
        {item.status === 'done' && item.result && (
          <>
            <span className="small">
              <span className="ok-mark">✓</span> {item.result.name} · {item.result.page_count} pages · {formatBytes(item.result.size)}
            </span>
            <button type="button" className="btn btn-ghost btn-sm" onClick={() => act(() => call('open_path', item.result!.path))}>
              Open
            </button>
            <button type="button" className="btn btn-ghost btn-sm" onClick={() => act(() => call('reveal_path', item.result!.path))}>
              Show in folder
            </button>
          </>
        )}
        {item.status === 'error' && <span className="field-error small">{item.error}</span>}
        {error && <span className="field-error small">{error}</span>}
      </div>
      <button type="button" className="icon-btn" aria-label="Remove" title="Remove" disabled={running} onClick={onRemove}>
        <CloseIcon size={14} />
      </button>
    </li>
  )
}
