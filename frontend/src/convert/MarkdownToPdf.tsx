import { useEffect, useState } from 'react'
import { ErrorNotice } from '../components/ErrorNotice'
import { call, toError, type WebPrintOptions } from '../lib/bridge'
import { cls } from '../lib/cls'
import { dirname, samePath } from '../lib/format'
import { CONVERT_EXTS, extOf, useToolRequest, useWorkspace } from '../lib/workspace'
import { ResultCard } from '../pdf/components'
import { useSaveFlow } from '../pdf/useSaveFlow'
import { PrintOptions } from './shared'
import { basename, DEFAULT_PRINT, stem, useFileDrop } from './util'

const EXTS = CONVERT_EXTS['to-pdf-markdown'] ?? []
const THEMES = [
  ['github', 'GitHub'],
  ['document', 'Document (serif)'],
  ['compact', 'Compact'],
]
const SAMPLE = `# Project notes

Write **Markdown** here, or open a \`.md\` file.

| Feature | Status |
|---|---|
| Tables | ✓ |
| Code highlighting | ✓ |

\`\`\`python
def greet(name):
    return f"Hello, {name}!"
\`\`\`
`

export function MarkdownToPdf() {
  const { selected, openInTool } = useWorkspace()
  const [text, setText] = useState(SAMPLE)
  const [file, setFile] = useState<string | null>(null)
  const [theme, setTheme] = useState('github')
  const [options, setOptions] = useState<WebPrintOptions>({ ...DEFAULT_PRINT, margin: 'wide' })
  const [html, setHtml] = useState('')
  const [notice, setNotice] = useState<Error | null>(null)
  const flow = useSaveFlow()

  const title = file ? stem(file) : (text.match(/^#\s+(.+)$/m)?.[1].trim() ?? 'document')
  const baseDir = file ? dirname(file) : null

  async function load(path: string) {
    if (!EXTS.includes(extOf(path))) {
      setNotice(new Error('Choose a .md file'))
      return
    }
    try {
      const doc = await call('read_text_file', path)
      setText(doc.text)
      setFile(path)
      setNotice(null)
    } catch (err) {
      setNotice(toError(err))
    }
  }
  useToolRequest('to-pdf-markdown', (path) => void load(path))
  const drop = useFileDrop(([path]) => void load(path))

  async function pick() {
    try {
      const [path] = await call('pick_files', 'Markdown files', EXTS, false)
      if (path) await load(path)
    } catch (err) {
      setNotice(toError(err))
    }
  }

  // Live preview, rendered by the same Python code that makes the PDF.
  useEffect(() => {
    let active = true
    const t = window.setTimeout(() => {
      call('markdown_html', text, baseDir, theme, title).then(
        (doc) => active && setHtml(doc),
        (err) => active && setNotice(toError(err)),
      )
    }, 250)
    return () => {
      active = false
      window.clearTimeout(t)
    }
  }, [text, baseDir, theme, title])

  const selectedMd =
    selected && !selected.is_dir && EXTS.includes(extOf(selected.path)) && !samePath(selected.path, file) ? selected : null

  return (
    <section className="tool tool-wide">
      <header className="tool-header">
        <h1>Markdown to PDF</h1>
        <p>Convert a .md file or Markdown text into a formatted PDF, with tables, code highlighting and local images.</p>
      </header>

      <div className="toolbar">
        <button type="button" className="btn btn-ghost btn-sm" onClick={pick}>
          Open .md file…
        </button>
        {selectedMd && (
          <button type="button" className="btn btn-ghost btn-sm" onClick={() => load(selectedMd.path)}>
            Use {selectedMd.name}
          </button>
        )}
        {file && (
          <>
            <span className="source-tag" title={file}>
              {basename(file)}
            </span>
            <button
              type="button"
              className="btn btn-ghost btn-sm"
              onClick={() => {
                setFile(null)
                setText('')
              }}
            >
              New text
            </button>
          </>
        )}
        <span className="toolbar-spacer" />
        <label className="inline-field small">
          Theme
          <select className="text-input" value={theme} onChange={(e) => setTheme(e.target.value)}>
            {THEMES.map(([id, label]) => (
              <option key={id} value={id}>
                {label}
              </option>
            ))}
          </select>
        </label>
      </div>

      <ErrorNotice error={notice} />

      <div className={cls('md-split', drop.over && 'is-over')} {...drop.props}>
        <textarea value={text} onChange={(e) => setText(e.target.value)} spellCheck={false} aria-label="Markdown" placeholder="Type Markdown, or drop a .md file here" />
        <iframe className="md-preview" title="Preview" sandbox="" srcDoc={html} />
      </div>
      {file && <p className="muted small">Edits here change the PDF only; the .md file isn't modified.</p>}

      <div className="card conv-options">
        <h2 className="card-title">Page setup</h2>
        <PrintOptions value={options} onChange={setOptions} />
      </div>

      <ErrorNotice error={flow.error} />
      {flow.saved && <ResultCard files={flow.saved} onDismiss={flow.dismiss} onContinue={(f) => openInTool('pdf-pages', f.path)} />}

      <div className="action-bar">
        <button
          type="button"
          className="btn btn-primary"
          disabled={flow.busy || !text.trim()}
          onClick={() =>
            flow.saveTo(
              () => call('suggest_pdf_path', file, title),
              (output) => call('markdown_to_pdf', text, baseDir, theme, title, output, options),
            )
          }
        >
          {flow.busy ? 'Rendering…' : 'Convert and save…'}
        </button>
      </div>
    </section>
  )
}
