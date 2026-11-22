import { useEffect, useState, type ReactNode } from 'react'
import { ErrorNotice } from '../components/ErrorNotice'
import { JobProgressBar } from '../components/JobProgressBar'
import { OutputChooser } from '../convert/shared'
import { call, toError, type ConversionEngines, type PdfInfo } from '../lib/bridge'
import { cls } from '../lib/cls'
import { dirname } from '../lib/format'
import { useJob } from '../lib/useJob'
import { useToolRequest, useWorkspace, type ToolId } from '../lib/workspace'
import { DocGate, ResultCard } from '../pdf/components'
import { usePdfDoc } from '../pdf/context'
import { useSaveFlow } from '../pdf/useSaveFlow'

/** Shell shared by the From-PDF tools: header + "open a PDF" gate, body keyed to the document. */
function FromPdf({ tool, title, blurb, body }: { tool: ToolId; title: string; blurb: string; body: (doc: PdfInfo) => ReactNode }) {
  const pdf = usePdfDoc()
  useToolRequest(tool, (path) => void pdf.open(path))
  return (
    <section className="tool">
      <header className="tool-header">
        <h1>{title}</h1>
        <p>{blurb}</p>
      </header>
      <DocGate>{(doc) => <div key={`${doc.path}|${doc.mtime}`} className="tool-body">{body(doc)}</div>}</DocGate>
    </section>
  )
}

function Footer({ flow, job, label, onRun, disabled }: { flow: ReturnType<typeof useSaveFlow>; job: ReturnType<typeof useJob>; label: string; onRun: () => void; disabled?: boolean }) {
  const { openInTool } = useWorkspace()
  return (
    <>
      <ErrorNotice error={flow.error} />
      {flow.saved && <ResultCard files={flow.saved} onDismiss={flow.dismiss} onContinue={(f) => openInTool('pdf-pages', f.path)} />}
      <div className="action-bar">
        <JobProgressBar busy={job.busy} progress={job.progress} />
        <button type="button" className="btn btn-primary" disabled={flow.busy || job.busy || disabled} onClick={onRun}>
          {flow.busy || job.busy ? 'Converting…' : label}
        </button>
      </div>
    </>
  )
}

function PagesField({ value, onChange, count }: { value: string; onChange: (v: string) => void; count: number }) {
  return (
    <label>
      Pages
      <input className="text-input" value={value} placeholder={`All ${count} pages`} spellCheck={false} onChange={(e) => onChange(e.target.value)} />
    </label>
  )
}

// --- PDF to Word -------------------------------------------------------------------

export function PdfToWord() {
  return (
    <FromPdf
      tool="from-pdf-word"
      title="PDF to Word"
      blurb="Turn a PDF into an editable Word document."
      body={(doc) => <WordBody doc={doc} />}
    />
  )
}

function WordBody({ doc }: { doc: PdfInfo }) {
  const flow = useSaveFlow()
  const job = useJob()
  const [engines, setEngines] = useState<ConversionEngines | null>(null)
  const [engine, setEngine] = useState('auto')
  const [fmt, setFmt] = useState('docx')
  useEffect(() => {
    call('conversion_engines').then(setEngines, () => {})
  }, [])
  const wordOk = !!engines?.office.word
  const builtin = engine === 'basic' || (engine === 'auto' && engines !== null && !wordOk)

  return (
    <>
      <div className="card conv-options">
        <div className="opt-grid">
          <label>
            Converter
            <select className="text-input" value={engine} onChange={(e) => setEngine(e.target.value)}>
              {wordOk && <option value="auto">Microsoft Word (keeps the layout)</option>}
              <option value={wordOk ? 'basic' : 'auto'}>Built-in (text, headings, lists, tables)</option>
            </select>
          </label>
          <label>
            Format
            <select className="text-input" value={fmt} onChange={(e) => setFmt(e.target.value)}>
              <option value="docx">Word document (.docx)</option>
              <option value="doc" disabled={builtin}>
                Word 97–2003 (.doc)
              </option>
            </select>
          </label>
        </div>
        <p className="muted small">
          {builtin
            ? 'The built-in converter rebuilds the text and its structure; images and exact positions are not kept.'
            : 'Microsoft Word reflows the PDF into an editable document. Complex layouts may shift a little.'}
        </p>
      </div>
      <Footer
        flow={flow}
        job={job}
        label="Convert to Word…"
        onRun={() =>
          flow.saveTo(
            () => call('frompdf_suggest', doc.path, fmt),
            (out) => job.run((id) => call('pdf_to_word', doc.path, out, engine, builtin ? 'docx' : fmt, id)),
            { label: 'Word documents', extensions: [builtin ? 'docx' : fmt] },
          )
        }
      />
    </>
  )
}

// --- PDF to PowerPoint -------------------------------------------------------------

export function PdfToPowerPoint() {
  return (
    <FromPdf
      tool="from-pdf-powerpoint"
      title="PDF to PowerPoint"
      blurb="One slide per page. Each slide shows the page exactly; its text goes into the speaker notes."
      body={(doc) => <PptBody doc={doc} />}
    />
  )
}

function PptBody({ doc }: { doc: PdfInfo }) {
  const flow = useSaveFlow()
  const job = useJob()
  const [dpi, setDpi] = useState(150)
  const [notes, setNotes] = useState(true)
  return (
    <>
      <div className="card conv-options">
        <div className="opt-grid">
          <label>
            Slide image quality
            <select className="text-input" value={dpi} onChange={(e) => setDpi(Number(e.target.value))}>
              <option value={110}>Smaller file</option>
              <option value={150}>Standard</option>
              <option value={220}>High (large screens, printing)</option>
            </select>
          </label>
          <label className="check span-2">
            <input type="checkbox" checked={notes} onChange={(e) => setNotes(e.target.checked)} />
            Put each page's text into the slide notes
          </label>
        </div>
        <p className="muted small">{doc.page_count} slides will be created.</p>
      </div>
      <Footer
        flow={flow}
        job={job}
        label="Convert to PowerPoint…"
        onRun={() =>
          flow.saveTo(
            () => call('frompdf_suggest', doc.path, 'pptx'),
            (out) => job.run((id) => call('pdf_to_powerpoint', doc.path, out, dpi, notes, id)),
            { label: 'PowerPoint presentations', extensions: ['pptx'] },
          )
        }
      />
    </>
  )
}

// --- PDF to Excel --------------------------------------------------------------------

export function PdfToExcel() {
  return (
    <FromPdf
      tool="from-pdf-excel"
      title="PDF to Excel"
      blurb="Find the tables in a PDF and put each one on its own sheet, with numbers as real numbers."
      body={(doc) => <ExcelBody doc={doc} />}
    />
  )
}

function ExcelBody({ doc }: { doc: PdfInfo }) {
  const flow = useSaveFlow()
  const job = useJob()
  const [pages, setPages] = useState('')
  const [detection, setDetection] = useState('auto')
  return (
    <>
      <div className="card conv-options">
        <div className="opt-grid">
          <PagesField value={pages} onChange={setPages} count={doc.page_count} />
          <label>
            Find tables by
            <select className="text-input" value={detection} onChange={(e) => setDetection(e.target.value)}>
              <option value="auto">Automatic</option>
              <option value="lines">Ruled lines (grid tables)</option>
              <option value="text">Aligned text (tables without lines)</option>
            </select>
          </label>
        </div>
      </div>
      <Footer
        flow={flow}
        job={job}
        label="Convert to Excel…"
        onRun={() =>
          flow.saveTo(
            () => call('frompdf_suggest', doc.path, 'xlsx'),
            (out) => job.run((id) => call('pdf_to_excel', doc.path, out, pages, detection, id)),
            { label: 'Excel workbooks', extensions: ['xlsx'] },
          )
        }
      />
    </>
  )
}

// --- PDF to JPG ------------------------------------------------------------------------

export function PdfToImages() {
  return (
    <FromPdf tool="from-pdf-images" title="PDF to JPG" blurb="Save pages as images, or pull out the pictures embedded in the PDF." body={(doc) => <ImagesBody doc={doc} />} />
  )
}

function ImagesBody({ doc }: { doc: PdfInfo }) {
  const flow = useSaveFlow()
  const job = useJob()
  const [mode, setMode] = useState<'pages' | 'extract'>('pages')
  const [fmt, setFmt] = useState('jpg')
  const [dpi, setDpi] = useState(150)
  const [quality, setQuality] = useState(90)
  const [pages, setPages] = useState('')
  const [folder, setFolder] = useState<string | null>(null)
  const first = doc.pages[0]
  const px = first ? `${Math.round((first.width / 72) * dpi)} × ${Math.round((first.height / 72) * dpi)} px per page` : ''
  return (
    <>
      <div className="segmented" role="radiogroup">
        {(
          [
            ['pages', 'Pages as images'],
            ['extract', 'Extract embedded images'],
          ] as const
        ).map(([id, label]) => (
          <button key={id} type="button" role="radio" aria-checked={mode === id} className={cls('segment', mode === id && 'is-on')} onClick={() => setMode(id)}>
            {label}
          </button>
        ))}
      </div>
      <div className="card conv-options">
        <div className="opt-grid">
          <PagesField value={pages} onChange={setPages} count={doc.page_count} />
          {mode === 'pages' && (
            <>
              <label>
                Format
                <select className="text-input" value={fmt} onChange={(e) => setFmt(e.target.value)}>
                  <option value="jpg">JPG</option>
                  <option value="png">PNG (lossless)</option>
                </select>
              </label>
              <label>
                Resolution
                <select className="text-input" value={dpi} onChange={(e) => setDpi(Number(e.target.value))}>
                  {[72, 96, 150, 220, 300, 600].map((d) => (
                    <option key={d} value={d}>
                      {d} dpi
                    </option>
                  ))}
                </select>
              </label>
              {fmt === 'jpg' && (
                <label>
                  JPG quality ({quality})
                  <input type="range" min={40} max={100} value={quality} onChange={(e) => setQuality(Number(e.target.value))} />
                </label>
              )}
            </>
          )}
        </div>
        <p className="muted small">{mode === 'pages' ? px : 'Images are saved in their original format and size.'}</p>
        <OutputChooser folder={folder} onChange={setFolder} what="PDF" />
      </div>
      <Footer
        flow={flow}
        job={job}
        label={mode === 'pages' ? 'Save images' : 'Extract images'}
        onRun={() =>
          flow.runSave(async () => (await job.run((id) => call('pdf_to_images', doc.path, folder ?? dirname(doc.path), pages, fmt, dpi, quality, mode, id))).files)
        }
      />
    </>
  )
}

// --- PDF to Markdown -----------------------------------------------------------------------

export function PdfToMarkdown() {
  return (
    <FromPdf
      tool="from-pdf-markdown"
      title="PDF to Markdown"
      blurb="Turn the PDF's text and structure (headings, lists, tables) into Markdown."
      body={(doc) => <MarkdownBody doc={doc} />}
    />
  )
}

function MarkdownBody({ doc }: { doc: PdfInfo }) {
  const flow = useSaveFlow()
  const job = useJob()
  const [pages, setPages] = useState('')
  const [breaks, setBreaks] = useState(false)
  const [markdown, setMarkdown] = useState('')
  const [html, setHtml] = useState('')
  const [raw, setRaw] = useState(false)
  const [error, setError] = useState<Error | null>(null)

  useEffect(() => {
    let active = true
    const t = window.setTimeout(async () => {
      try {
        const md = await call('pdf_markdown_preview', doc.path, pages)
        const page = await call('markdown_html', md, null, 'github', doc.name)
        if (active) {
          setMarkdown(md)
          setHtml(page)
          setError(null)
        }
      } catch (err) {
        if (active) setError(toError(err))
      }
    }, 300)
    return () => {
      active = false
      window.clearTimeout(t)
    }
  }, [doc.path, doc.name, pages])

  return (
    <>
      <div className="card conv-options">
        <div className="opt-grid">
          <PagesField value={pages} onChange={setPages} count={doc.page_count} />
          <label className="check span-2">
            <input type="checkbox" checked={breaks} onChange={(e) => setBreaks(e.target.checked)} />
            Mark page breaks with comments
          </label>
        </div>
      </div>
      <ErrorNotice error={error} />
      <div className="md-result">
        <div className="pv-toolbar">
          <span className="muted small">Preview of the first pages</span>
          <label className="check small">
            <input type="checkbox" checked={raw} onChange={(e) => setRaw(e.target.checked)} /> Show Markdown source
          </label>
        </div>
        {raw ? <pre className="md-raw">{markdown}</pre> : <iframe className="md-preview" title="Markdown preview" sandbox="" srcDoc={html} />}
      </div>
      <Footer
        flow={flow}
        job={job}
        label="Save as Markdown…"
        onRun={() =>
          flow.saveTo(
            () => call('frompdf_suggest', doc.path, 'md'),
            (out) => job.run((id) => call('pdf_to_markdown', doc.path, out, pages, breaks, id)),
            { label: 'Markdown files', extensions: ['md'] },
          )
        }
      />
    </>
  )
}
