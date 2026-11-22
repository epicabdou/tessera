import { useEffect, useMemo, useRef, useState } from 'react'
import { cls } from '../lib/cls'
import type { ToolId } from '../lib/workspace'
import { CATEGORIES } from '../tools/registry'
import { SearchIcon } from './icons'

/** Ctrl+K: find any tool by name, what it does, or its category. */
export function CommandPalette({ current, onPick, onClose }: { current: ToolId; onPick: (id: ToolId) => void; onClose: () => void }) {
  const [query, setQuery] = useState('')
  const [active, setActive] = useState(0)
  const input = useRef<HTMLInputElement>(null)
  const list = useRef<HTMLUListElement>(null)

  const items = useMemo(() => {
    const all = CATEGORIES.flatMap((c) => c.tools.map((t) => ({ ...t, category: c })))
    const q = query.trim().toLowerCase()
    if (!q) return all
    const words = q.split(/\s+/)
    return all
      .map((t) => {
        const label = t.label.toLowerCase()
        const hay = `${label} ${t.hint} ${t.category.label} ${t.category.short}`.toLowerCase()
        if (!words.every((w) => hay.includes(w))) return null
        return { t, score: label.startsWith(q) ? 0 : label.includes(q) ? 1 : 2 }
      })
      .filter((x) => x !== null)
      .sort((a, b) => a.score - b.score)
      .map((x) => x.t)
  }, [query])

  useEffect(() => {
    input.current?.focus()
  }, [])

  useEffect(() => {
    list.current?.querySelector('[aria-selected="true"]')?.scrollIntoView({ block: 'nearest' })
  }, [active, items])

  const pick = (id: ToolId | undefined) => {
    if (id) onPick(id)
  }

  return (
    <div className="palette-backdrop" onMouseDown={onClose}>
      <div className="palette" role="dialog" aria-label="Find a tool" onMouseDown={(e) => e.stopPropagation()}>
        <div className="palette-search">
          <SearchIcon size={17} />
          <input
            ref={input}
            value={query}
            placeholder="Find a tool…  e.g. merge, sign, word"
            aria-label="Find a tool"
            aria-controls="palette-list"
            onChange={(e) => {
              setQuery(e.target.value)
              setActive(0)
            }}
            onKeyDown={(e) => {
              if (e.key === 'ArrowDown') {
                e.preventDefault()
                setActive((i) => Math.min(items.length - 1, i + 1))
              } else if (e.key === 'ArrowUp') {
                e.preventDefault()
                setActive((i) => Math.max(0, i - 1))
              } else if (e.key === 'Enter') {
                e.preventDefault()
                pick(items[active]?.id)
              } else if (e.key === 'Escape') {
                e.preventDefault()
                onClose()
              }
            }}
          />
          <kbd>Esc</kbd>
        </div>
        <ul ref={list} id="palette-list" className="palette-list" role="listbox">
          {items.map((t, i) => (
            <li key={t.id} role="option" aria-selected={i === active}>
              <button
                type="button"
                className={cls('palette-item', i === active && 'is-active')}
                onMouseMove={() => setActive(i)}
                onClick={() => pick(t.id)}
              >
                <span className="palette-icon">{t.icon}</span>
                <span className="palette-text">
                  <strong>{t.label}</strong>
                  <span>{t.hint}</span>
                </span>
                {t.id === current ? <span className="palette-tag is-current">Open</span> : <span className="palette-tag">{t.category.short}</span>}
              </button>
            </li>
          ))}
          {items.length === 0 && <li className="palette-empty">No tool matches “{query}”.</li>}
        </ul>
        <div className="palette-foot">
          <span>
            <kbd>↑</kbd> <kbd>↓</kbd> to move
          </span>
          <span>
            <kbd>Enter</kbd> to open
          </span>
        </div>
      </div>
    </div>
  )
}
