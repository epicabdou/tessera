import { useRef, type PointerEvent } from 'react'
import { cls } from '../lib/cls'
import type { Rect } from '../editing/BoxLayer'

type Edge = 'n' | 'e' | 's' | 'w'
const CORNERS: { name: string; edges: Edge[] }[] = [
  { name: 'nw', edges: ['n', 'w'] },
  { name: 'ne', edges: ['n', 'e'] },
  { name: 'se', edges: ['s', 'e'] },
  { name: 'sw', edges: ['s', 'w'] },
]
const SIDES: { name: string; edges: Edge[] }[] = [
  { name: 'n', edges: ['n'] },
  { name: 'e', edges: ['e'] },
  { name: 's', edges: ['s'] },
  { name: 'w', edges: ['w'] },
]
const MIN = 8 // image pixels
const clamp = (v: number, lo: number, hi: number) => Math.min(hi, Math.max(lo, v))

function resize(start: Rect, edges: Edge[], dx: number, dy: number, aspect: number | null, W: number, H: number): Rect {
  if (aspect) {
    // Corner drag with a fixed ratio: the opposite corner stays put.
    const left = edges.includes('w')
    const top = edges.includes('n')
    const ax = left ? start.x + start.w : start.x
    const ay = top ? start.y + start.h : start.y
    let w = Math.max(MIN, start.w + (left ? -dx : dx))
    w = Math.min(w, left ? ax : W - ax, (top ? ay : H - ay) * aspect)
    const h = w / aspect
    return { x: left ? ax - w : ax, y: top ? ay - h : ay, w, h }
  }
  let { x, y, w, h } = start
  if (edges.includes('w')) {
    x = clamp(start.x + dx, 0, start.x + start.w - MIN)
    w = start.w + (start.x - x)
  }
  if (edges.includes('e')) w = clamp(start.w + dx, MIN, W - start.x)
  if (edges.includes('n')) {
    y = clamp(start.y + dy, 0, start.y + start.h - MIN)
    h = start.h + (start.y - y)
  }
  if (edges.includes('s')) h = clamp(start.h + dy, MIN, H - start.y)
  return { x, y, w, h }
}

/** Crop rectangle over an image: drag to move, handles to resize, drag outside to draw a new one. */
export function CropBox({
  width,
  height,
  scale,
  rect,
  aspect,
  round = false,
  onChange,
}: {
  width: number
  height: number
  scale: number
  rect: Rect
  aspect: number | null
  round?: boolean
  onChange: (r: Rect) => void
}) {
  const drag = useRef<{ mode: 'move' | 'new' | Edge[]; start: Rect; x0: number; y0: number } | null>(null)

  const point = (e: PointerEvent) => {
    const r = (e.currentTarget as HTMLElement).closest('.cropbox-layer')!.getBoundingClientRect()
    return { x: clamp((e.clientX - r.left) / scale, 0, width), y: clamp((e.clientY - r.top) / scale, 0, height) }
  }

  function begin(e: PointerEvent, mode: 'move' | 'new' | Edge[]) {
    e.stopPropagation()
    e.preventDefault()
    ;(e.currentTarget as HTMLElement).closest('.cropbox-layer')!.setPointerCapture(e.pointerId)
    const p = point(e)
    drag.current = { mode, start: mode === 'new' ? { x: p.x, y: p.y, w: 0, h: 0 } : rect, x0: p.x, y0: p.y }
  }

  function move(e: PointerEvent) {
    const d = drag.current
    if (!d) return
    const p = point(e)
    const dx = p.x - d.x0
    const dy = p.y - d.y0
    if (d.mode === 'move') {
      onChange({ ...d.start, x: clamp(d.start.x + dx, 0, width - d.start.w), y: clamp(d.start.y + dy, 0, height - d.start.h) })
    } else if (d.mode === 'new') {
      let w = Math.abs(dx)
      let h = Math.abs(dy)
      if (aspect) {
        if (w / Math.max(h, 1e-6) > aspect) w = h * aspect
        else h = w / aspect
      }
      const x = dx < 0 ? d.x0 - w : d.x0
      const y = dy < 0 ? d.y0 - h : d.y0
      if (w >= MIN && h >= MIN && x >= 0 && y >= 0 && x + w <= width && y + h <= height) onChange({ x, y, w, h })
    } else {
      onChange(resize(d.start, d.mode, dx, dy, aspect, width, height))
    }
  }

  const style = { left: rect.x * scale, top: rect.y * scale, width: rect.w * scale, height: rect.h * scale }
  return (
    <div
      className="cropbox-layer"
      onPointerDown={(e) => begin(e, 'new')}
      onPointerMove={move}
      onPointerUp={() => {
        drag.current = null
      }}
    >
      <div className={cls('cropbox', round && 'is-round')} style={style} onPointerDown={(e) => begin(e, 'move')}>
        <span className="crop-third v1" />
        <span className="crop-third v2" />
        <span className="crop-third h1" />
        <span className="crop-third h2" />
        {[...CORNERS, ...(aspect ? [] : SIDES)].map((hd) => (
          <span key={hd.name} className={`crop-handle h-${hd.name}`} onPointerDown={(e) => begin(e, hd.edges)} />
        ))}
        <span className="crop-size">
          {Math.round(rect.w)} × {Math.round(rect.h)}
        </span>
      </div>
    </div>
  )
}
