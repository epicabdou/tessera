import { useState } from 'react'
import { ErrorNotice } from '../components/ErrorNotice'
import { call, toError, type WebPrintOptions } from '../lib/bridge'
import { cls } from '../lib/cls'
import { dirname, samePath } from '../lib/format'
import { CONVERT_EXTS, extOf, useToolRequest, useWorkspace } from '../lib/workspace'
import { ResultCard } from '../pdf/components'
import { useSaveFlow } from '../pdf/useSaveFlow'
import { PrintOptions } from './shared'
import { basename, DEFAULT_PRINT, useFileDrop } from './util'

type Source = 'url' | 'file' | 'code'

const EXTS = CONVERT_EXTS['to-pdf-html'] ?? []
const SAMPLE = `<h1>Hello</h1>
<p>Paste or type <strong>HTML</strong> here. Styles in &lt;style&gt; tags are kept.</p>`

export function HtmlToPdf() {
  const { selected, openInTool } = useWorkspace()
  const [source, setSource] = useState<Source>('url')
  const [url, setUrl] = useState('')
  const [file, setFile] = useState<string | null>(null)
  const [code, setCode] = useState(SAMPLE)
  const [options, setOptions] = useState<WebPrintOptions>(DEFAULT_PRINT)
  const [notice, setNotice] = useState<Error | null>(null)
  const flow = useSaveFlow()

  const chooseFile = (path: string) => {
    if (!EXTS.includes(extOf(path))) {
      setNotice(new Error('Choose an .html or .htm file'))
      return
    }
    setNotice(null)
    setFile(path)
    setSource('file')
  }
  useToolRequest('to-pdf-html', chooseFile)
  const drop = useFileDrop(([path]) => chooseFile(path))

  async function pickFile() {
    try {
      const [path] = await call('pick_files', 'Web pages', EXTS, false)
      if (path) chooseFile(path)
    } catch (err) {
      setNotice(toError(err))
    }
  }

  function hostHint(text: string) {
    try {
      const u = new URL(/^[a-z]+:\/\//i.test(text) ? text : `https://${text}`)
      return u.hostname + (u.pathname.length > 1 ? u.pathname.replace(/\.[a-z]+$/i, '').replace(/[/]+/g, '-') : '')
    } catch {
      return 'web-page'
    }
  }

  function convert() {
    if (source === 'url') {
      return flow.saveTo(
        () => call('suggest_pdf_path', null, hostHint(url)),
        (output) => call('html_to_pdf', 'url', url, output, options),
      )
    }
    if (source === 'file' && file) {
      return flow.saveTo(
        () => call('suggest_pdf_path', file, ''),
        (output) => call('html_to_pdf', 'file', file, output, options),
      )
    }
    return flow.saveTo(
      () => call('suggest_pdf_path', null, 'page'),
      (output) => call('html_to_pdf', 'code', code, output, options),
    )
  }

  const selectedHtml =
    selected && !selected.is_dir && EXTS.includes(extOf(selected.path)) && !samePath(selected.path, file) ? selected : null
  const ready = source === 'url' ? url.trim() !== '' : source === 'file' ? file !== null : code.trim() !== ''

  return (
    <section className="tool">
      <header className="tool-header">
        <h1>HTML to PDF</h1>
        <p>Render a web page, an HTML file or HTML code as a PDF, with the same engine as Microsoft Edge.</p>
      </header>

      <div className="segmented" role="radiogroup" aria-label="Source">
        {(
          [
            ['url', 'Web page'],
            ['file', 'HTML file'],
            ['code', 'HTML code'],
          ] as [Source, string][]
        ).map(([id, label]) => (
          <button key={id} type="button" role="radio" aria-checked={source === id} className={cls('segment', source === id && 'is-on')} onClick={() => setSource(id)}>
            {label}
          </button>
        ))}
      </div>

      {source === 'url' && (
        <input
          className="text-input big"
          value={url}
          placeholder="https://example.com/article"
          spellCheck={false}
          aria-label="Web address"
          onChange={(e) => setUrl(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && ready && void convert()}
        />
      )}

      {source === 'file' && (
        <div className={cls('file-pick', drop.over && 'is-over')} {...drop.props}>
          {file ? (
            <div className="conv-meta">
              <strong title={file}>{basename(file)}</strong>
              <span className="muted small mono">{dirname(file)}</span>
            </div>
          ) : (
            <span className="muted">Drag an .html file here from the Explorer, or choose one.</span>
          )}
          <div className="button-row">
            <button type="button" className="btn btn-secondary btn-sm" onClick={pickFile}>
              Choose file…
            </button>
            {selectedHtml && (
              <button type="button" className="btn btn-ghost btn-sm" onClick={() => chooseFile(selectedHtml.path)}>
                Use {selectedHtml.name}
              </button>
            )}
          </div>
        </div>
      )}

      {source === 'code' && (
        <div className="code-split">
          <textarea value={code} onChange={(e) => setCode(e.target.value)} spellCheck={false} aria-label="HTML code" />
          {/* Sandboxed: no scripts, no access to the app. */}
          <iframe className="html-preview" title="Preview" sandbox="" srcDoc={code} />
        </div>
      )}

      <ErrorNotice error={notice} />

      <div className="card conv-options">
        <h2 className="card-title">Page setup</h2>
        <PrintOptions value={options} onChange={setOptions} web={source === 'url'} />
      </div>

      <ErrorNotice error={flow.error} />
      {flow.saved && <ResultCard files={flow.saved} onDismiss={flow.dismiss} onContinue={(f) => openInTool('pdf-pages', f.path)} />}

      <div className="action-bar">
        <span className="muted small">
          {source === 'url' ? 'The page is loaded in a hidden window; sites that need a login print as a logged-out visitor.' : ''}
        </span>
        <button type="button" className="btn btn-primary" disabled={flow.busy || !ready} onClick={convert}>
          {flow.busy ? 'Rendering…' : 'Convert and save…'}
        </button>
      </div>
    </section>
  )
}
