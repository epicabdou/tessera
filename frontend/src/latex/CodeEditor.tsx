import { autocompletion, type CompletionContext } from '@codemirror/autocomplete'
import { indentWithTab } from '@codemirror/commands'
import { HighlightStyle, StreamLanguage, syntaxHighlighting } from '@codemirror/language'
import { stex } from '@codemirror/legacy-modes/mode/stex'
import { EditorState, Prec } from '@codemirror/state'
import { EditorView, keymap } from '@codemirror/view'
import { tags as t } from '@lezer/highlight'
import { basicSetup } from 'codemirror'
import { forwardRef, useEffect, useImperativeHandle, useRef } from 'react'

export interface CodeEditorHandle {
  /** Replace the selection (or insert at the cursor); `|` in `text` marks where the cursor goes. */
  insert(text: string): void
  goToLine(line: number): void
  focus(): void
}

const COMMANDS = [
  'section{}', 'subsection{}', 'subsubsection{}', 'paragraph{}', 'chapter{}', 'textbf{}', 'textit{}', 'emph{}', 'underline{}', 'texttt{}',
  'begin{}', 'end{}', 'item', 'label{}', 'ref{}', 'eqref{}', 'cite{}', 'footnote{}', 'url{}', 'href{}{}', 'includegraphics[width=\\linewidth]{}',
  'usepackage{}', 'documentclass{}', 'title{}', 'author{}', 'date{}', 'maketitle', 'tableofcontents', 'newpage', 'clearpage', 'centering',
  'caption{}', 'frac{}{}', 'sqrt{}', 'sum', 'int', 'infty', 'alpha', 'beta', 'gamma', 'delta', 'lambda', 'mu', 'pi', 'sigma', 'theta', 'omega',
  'left(', 'right)', 'cdot', 'times', 'leq', 'geq', 'neq', 'approx', 'mathbb{}', 'mathrm{}', 'hline', 'vspace{}', 'hspace{}', 'noindent',
]
const ENVIRONMENTS = ['itemize', 'enumerate', 'description', 'equation', 'equation*', 'align', 'align*', 'figure', 'table', 'tabular', 'center', 'abstract', 'quote', 'verbatim', 'frame', 'minipage']

function latexCompletions(ctx: CompletionContext) {
  const env = ctx.matchBefore(/\\begin\{[\w*]*/)
  if (env) {
    const from = env.from + '\\begin{'.length
    return { from, options: ENVIRONMENTS.map((e) => ({ label: e, type: 'type', apply: `${e}}` })) }
  }
  const word = ctx.matchBefore(/\\[a-zA-Z]*/)
  if (!word || (word.from === word.to && !ctx.explicit)) return null
  return {
    from: word.from + 1,
    options: COMMANDS.map((c) => ({ label: c.replace(/[{[(].*$/, ''), detail: c.includes('{') ? c.slice(c.indexOf('{')) : undefined, type: 'keyword', apply: c.replace(/\{\}.*$/, '{}') })),
    validFor: /^[a-zA-Z]*$/,
  }
}

const highlight = HighlightStyle.define([
  { tag: t.keyword, color: 'var(--tex-command)' },
  { tag: t.tagName, color: 'var(--tex-command)' },
  { tag: t.atom, color: 'var(--tex-env)' },
  { tag: t.bracket, color: 'var(--tex-bracket)' },
  { tag: t.comment, color: 'var(--text-muted)', fontStyle: 'italic' },
  { tag: t.number, color: 'var(--tex-number)' },
  { tag: t.string, color: 'var(--tex-math)' },
  { tag: t.variableName, color: 'var(--tex-env)' },
])

const theme = EditorView.theme({
  '&': { height: '100%', fontSize: '13.5px', backgroundColor: 'var(--bg-sunken)', color: 'var(--text)' },
  '.cm-scroller': { fontFamily: 'var(--mono)', lineHeight: '1.55' },
  '.cm-content': { caretColor: 'var(--accent)' },
  '.cm-cursor': { borderLeftColor: 'var(--accent)' },
  '.cm-gutters': { backgroundColor: 'var(--bg-sunken)', color: 'var(--text-muted)', border: 'none', borderRight: '1px solid var(--border)' },
  '.cm-activeLine': { backgroundColor: 'var(--bg-hover)' },
  '.cm-activeLineGutter': { backgroundColor: 'var(--bg-hover)' },
  '&.cm-focused .cm-selectionBackground, .cm-selectionBackground, ::selection': { backgroundColor: 'var(--accent-soft)' },
  '.cm-selectionMatch': { backgroundColor: 'var(--accent-soft)' },
  '.cm-panels': { backgroundColor: 'var(--glass-strong)', color: 'var(--text)' },
  '.cm-tooltip': { backgroundColor: 'var(--glass-strong)', backdropFilter: 'var(--glass-blur)', border: '1px solid var(--glass-border)', borderRadius: '10px', overflow: 'hidden' },
  '.cm-tooltip-autocomplete ul li[aria-selected]': { backgroundColor: 'var(--accent-soft)', color: 'var(--text)' },
})

interface Props {
  value: string
  onChange: (text: string) => void
  /** Ctrl+S */
  onSave: () => void
  /** Ctrl+Enter */
  onCompile: () => void
}

/** CodeMirror 6 with LaTeX highlighting. Uncontrolled after mount: `value` only seeds a new document (change `key` to load another). */
export const CodeEditor = forwardRef<CodeEditorHandle, Props>(function CodeEditor({ value, onChange, onSave, onCompile }, ref) {
  const host = useRef<HTMLDivElement>(null)
  const view = useRef<EditorView | null>(null)
  const handlers = useRef({ onChange, onSave, onCompile })

  useEffect(() => {
    handlers.current = { onChange, onSave, onCompile }
  })

  useEffect(() => {
    const v = new EditorView({
      parent: host.current!,
      state: EditorState.create({
        doc: value,
        extensions: [
          basicSetup,
          StreamLanguage.define(stex),
          syntaxHighlighting(highlight),
          autocompletion({ override: [latexCompletions] }),
          EditorView.lineWrapping,
          theme,
          // Highest precedence: basicSetup's default keymap binds Mod-Enter to "insert blank line",
          // and at equal precedence the first keymap listed wins.
          Prec.highest(keymap.of([
            indentWithTab,
            {
              key: 'Mod-s',
              preventDefault: true,
              run: () => {
                handlers.current.onSave()
                return true
              },
            },
            {
              key: 'Mod-Enter',
              preventDefault: true,
              run: () => {
                handlers.current.onCompile()
                return true
              },
            },
          ])),
          EditorView.updateListener.of((u) => {
            if (u.docChanged) handlers.current.onChange(u.state.doc.toString())
          }),
        ],
      }),
    })
    view.current = v
    return () => {
      v.destroy()
      view.current = null
    }
    // Seeded once per mount; the parent remounts (via key) to load another file.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  useImperativeHandle(ref, () => ({
    insert(text: string) {
      const v = view.current
      if (!v) return
      const { from, to } = v.state.selection.main
      const selected = v.state.sliceDoc(from, to)
      const at = text.indexOf('|')
      const before = at >= 0 ? text.slice(0, at) : text
      const after = at >= 0 ? text.slice(at + 1) : ''
      v.dispatch({
        changes: { from, to, insert: before + selected + after },
        selection: { anchor: from + before.length + selected.length },
        scrollIntoView: true,
      })
      v.focus()
    },
    goToLine(line: number) {
      const v = view.current
      if (!v) return
      const l = v.state.doc.line(Math.max(1, Math.min(v.state.doc.lines, line)))
      v.dispatch({ selection: { anchor: l.from, head: l.to }, scrollIntoView: true })
      v.focus()
    },
    focus() {
      view.current?.focus()
    },
  }))

  return <div ref={host} className="code-editor" />
})
