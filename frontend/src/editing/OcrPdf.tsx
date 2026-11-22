import { useEffect, useState } from 'react'
import { ErrorNotice } from '../components/ErrorNotice'
import { JobProgressBar } from '../components/JobProgressBar'
import { call, toError, type OcrEngines, type PdfInfo } from '../lib/bridge'
import { useJob } from '../lib/useJob'
import { useToolRequest } from '../lib/workspace'
import { DocGate, ResultCard } from '../pdf/components'
import { usePdfDoc } from '../pdf/context'
import { useSaveFlow } from '../pdf/useSaveFlow'

const LANG_NAMES: Record<string, string> = { eng: 'English', fra: 'French', deu: 'German', spa: 'Spanish', ara: 'Arabic', ita: 'Italian', por: 'Portuguese', nld: 'Dutch' }

export function OcrPdf() {
  const pdf = usePdfDoc()
  useToolRequest('ocr-pdf', (path) => void pdf.open(path))
  return (
    <section className="tool">
      <header className="tool-header">
        <h1>OCR PDF</h1>
        <p>Recognise the text in scanned pages and add it as an invisible layer, so the PDF becomes searchable and its text can be selected and copied.</p>
      </header>
      <DocGate>{(doc) => <OcrBody key={`${doc.path}|${doc.mtime}`} doc={doc} />}</DocGate>
    </section>
  )
}

function OcrBody({ doc }: { doc: PdfInfo }) {
  const pdf = usePdfDoc()
  const flow = useSaveFlow()
  const job = useJob()
  const [engines, setEngines] = useState<OcrEngines | null>(null)
  const [engine, setEngine] = useState<'tesseract' | 'windows'>('tesseract')
  const [language, setLanguage] = useState('')
  const [dpi, setDpi] = useState(300)
  const [skip, setSkip] = useState(true)
  const [pages, setPages] = useState('')
  const [error, setError] = useState<Error | null>(null)
  const [summary, setSummary] = useState<string | null>(null)

  useEffect(() => {
    call('ocr_engines').then(
      (e) => {
        setEngines(e)
        const useTess = !!e.tesseract.path
        setEngine(useTess ? 'tesseract' : 'windows')
        setLanguage(useTess ? (e.tesseract.languages.includes('eng') ? 'eng' : e.tesseract.languages[0] ?? '') : e.windows.languages[0] ?? '')
      },
      (err) => setError(toError(err)),
    )
  }, [])

  const languages = engine === 'tesseract' ? (engines?.tesseract.languages ?? []) : (engines?.windows.languages ?? [])
  const none = engines !== null && !engines.tesseract.path && engines.windows.languages.length === 0

  return (
    <>
      {none && (
        <div className="notice notice-error">
          No OCR engine was found. Install Tesseract OCR, or add a language with “Optical character recognition” in Windows Settings → Time &amp; language.
        </div>
      )}
      <div className="card conv-options">
        <div className="opt-grid">
          <label>
            Engine
            <select
              className="text-input"
              value={engine}
              onChange={(e) => {
                const next = e.target.value as 'tesseract' | 'windows'
                setEngine(next)
                setLanguage((next === 'tesseract' ? engines?.tesseract.languages : engines?.windows.languages)?.[0] ?? '')
              }}
            >
              <option value="tesseract" disabled={!engines?.tesseract.path}>
                Tesseract{engines?.tesseract.path ? '' : ' (not installed)'}
              </option>
              <option value="windows" disabled={!engines?.windows.languages.length}>
                Windows OCR (built in)
              </option>
            </select>
          </label>
          <label>
            Document language
            <select className="text-input" value={language} onChange={(e) => setLanguage(e.target.value)}>
              {languages.map((l) => (
                <option key={l} value={l}>
                  {LANG_NAMES[l] ?? l}
                </option>
              ))}
            </select>
          </label>
          <label>
            Scan resolution
            <select className="text-input" value={dpi} onChange={(e) => setDpi(Number(e.target.value))}>
              <option value={200}>200 dpi (faster)</option>
              <option value={300}>300 dpi (recommended)</option>
              <option value={400}>400 dpi (small print)</option>
            </select>
          </label>
          <label>
            Pages
            <input className="text-input" value={pages} placeholder={`All ${doc.page_count} pages`} onChange={(e) => setPages(e.target.value)} spellCheck={false} />
          </label>
          <label className="check span-2">
            <input type="checkbox" checked={skip} onChange={(e) => setSkip(e.target.checked)} />
            Skip pages that already have text
          </label>
        </div>
        <p className="muted small">The pages keep their exact appearance; only invisible, searchable text is added.</p>
      </div>
      <ErrorNotice error={error} />
      {summary && <p className="small">{summary}</p>}
      <ErrorNotice error={flow.error} />
      {flow.saved && <ResultCard files={flow.saved} onDismiss={flow.dismiss} onContinue={(f) => void pdf.open(f.path)} />}
      <div className="action-bar">
        <JobProgressBar busy={job.busy} progress={job.progress} label="Starting OCR…" />
        <button
          type="button"
          className="btn btn-primary"
          disabled={flow.busy || job.busy || none || !language}
          onClick={async () => {
            setSummary(null)
            const res = await flow.saveAs(doc.path, 'ocr', (out) =>
              job.run(async (id) => {
                const r = await call('ocr_pdf', doc.path, out, engine, language, dpi, skip, pages, id)
                setSummary(`${r.pages_recognised} page(s) recognised, ${r.pages_skipped} skipped, ${r.words.toLocaleString()} words found.`)
                return r
              }),
            )
            void res
          }}
        >
          {job.busy ? 'Recognising…' : 'Make searchable…'}
        </button>
      </div>
    </>
  )
}
