import { useRef, type PointerEvent, type ReactNode } from 'react'
import { cls } from '../lib/cls'

export interface Rect {
  x: number
  y: number
  w: number
  h: number
}

export interface LayerBox extends Rect {
  id: string
  content?: ReactNode
  className?: string
  /** Can be selected but not moved or resized. */
  locked?: boolean
  title?: string
}

type Edge = 'n' | 'e' | 's' | 'w'
const HANDLES: { name: string; edges: Edge[] }[] = [
  { name: 'n', edges: ['n'] },
  { name: 'e', edges: ['e'] },
  { name: 's', edges: ['s'] },
  { name: 'w', edges: ['w'] },
  { name: 'ne', edges: ['n', 'e'] },
  { name: 'se', edges: ['s', 'e'] },
  { name: 'sw', edges: ['s', 'w'] },
  { name: 'nw', edges: ['n', 'w'] },
]
const MIN = 4 // points
const clamp = (v: number, lo: number, hi: number) => Math.min(hi, Math.max(lo, v))

interface Props {
  page: { width: number; height: number }
  /** Pixels per point (from PagePreview). */
  scale: number
  boxes: LayerBox[]
  selected: string | null
  onSelect: (id: string | null) => void
  onChange?: (id: string, rect: Rect) => void
  /** When set, dragging on empty space draws a new box (a plain click gives w = h = 0). */
  onCreate?: (rect: Rect) => void
  children?: ReactNode
}

/** Boxes over a page preview: select, move, resize, or draw new ones. Coordinates are points from the top-left. */
export function BoxLayer({ page, scale, boxes, selected, onSelect, onChange, onCreate, children }: Props) {
  const drag = useRef<{ mode: 'move' | 'create' | Edge[]; id: string | null; start: Rect; x0: number; y0: number; origin: { x: number; y: number } } | null>(null)
  const W = page.width
  const H = page.height

  function point(e: PointerEvent) {
    const r = (e.currentTarget as HTMLElement).closest('.box-layer')!.getBoundingClientRect()
    return { x: clamp((e.clientX - r.left) / scale, 0, W), y: clamp((e.clientY - r.top) / scale, 0, H) }
  }

  function begin(e: PointerEvent, mode: 'move' | 'create' | Edge[], box?: LayerBox) {
    e.stopPropagation()
    const layer = (e.currentTarget as HTMLElement).closest('.box-layer') as HTMLElement
    try {
      layer.setPointerCapture(e.pointerId)
    } catch {
      /* pointer already released */
    }
    const p = point(e)
    drag.current = { mode, id: box?.id ?? null, start: box ? { x: box.x, y: box.y, w: box.w, h: box.h } : { x: p.x, y: p.y, w: 0, h: 0 }, x0: p.x, y0: p.y, origin: p }
  }

  function move(e: PointerEvent) {
    const d = drag.current
    if (!d) return
    const p = point(e)
    const dx = p.x - d.x0
    const dy = p.y - d.y0
    const s = d.start
    if (d.mode === 'create') return
    if (!d.id || !onChange) return
    if (d.mode === 'move') {
      onChange(d.id, { x: clamp(s.x + dx, 0, W - s.w), y: clamp(s.y + dy, 0, H - s.h), w: s.w, h: s.h })
      return
    }
    let { x, y, w, h } = s
    for (const edge of d.mode) {
      if (edge === 'w') {
        const nx = clamp(s.x + dx, 0, s.x + s.w - MIN)
        w = s.w + (s.x - nx)
        x = nx
      }
      if (edge === 'e') w = clamp(s.w + dx, MIN, W - s.x)
      if (edge === 'n') {
        const ny = clamp(s.y + dy, 0, s.y + s.h - MIN)
        h = s.h + (s.y - ny)
        y = ny
      }
      if (edge === 's') h = clamp(s.h + dy, MIN, H - s.y)
    }
    onChange(d.id, { x, y, w, h })
  }

  function end(e: PointerEvent) {
    const d = drag.current
    drag.current = null
    if (d?.mode === 'create' && onCreate) {
      const p = point(e)
      const x = Math.min(d.origin.x, p.x)
      const y = Math.min(d.origin.y, p.y)
      const w = Math.abs(p.x - d.origin.x)
      const h = Math.abs(p.y - d.origin.y)
      onCreate(w < MIN || h < MIN ? { x: d.origin.x, y: d.origin.y, w: 0, h: 0 } : { x, y, w, h })
    }
  }

  return (
    <div
      className={cls('box-layer', onCreate && 'is-creating')}
      onPointerDown={(e) => {
        if (onCreate) begin(e, 'create')
        else onSelect(null)
      }}
      onPointerMove={move}
      onPointerUp={end}
      onPointerCancel={() => (drag.current = null)}
    >
      {children}
      {boxes.map((b) => {
        const isSel = b.id === selected
        return (
          <div
            key={b.id}
            className={cls('lbox', b.className, isSel && 'is-selected', b.locked && 'is-locked')}
            style={{ left: b.x * scale, top: b.y * scale, width: b.w * scale, height: b.h * scale }}
            title={b.title}
            onPointerDown={(e) => {
              onSelect(b.id)
              if (!b.locked && onChange) begin(e, 'move', b)
              else e.stopPropagation()
            }}
          >
            {b.content}
            {isSel && !b.locked && onChange && HANDLES.map((hd) => <span key={hd.name} className={`crop-handle h-${hd.name}`} onPointerDown={(e) => begin(e, hd.edges, b)} />)}
          </div>
        )
      })}
    </div>
  )
}
