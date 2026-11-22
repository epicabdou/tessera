import { useRef, useState, type PointerEvent } from 'react'
import type { Rect } from '../editing/BoxLayer'

/** Freehand pen, or a straight line/arrow from where you press to where you let go. */
export function DrawLayer({
  scale,
  width,
  height,
  mode,
  stroke,
  lineWidth,
  onDone,
}: {
  scale: number
  width: number
  height: number
  mode: 'draw' | 'line' | 'arrow'
  stroke: string
  lineWidth: number
  onDone: (box: Rect, points: [number, number][]) => void
}) {
  const [pts, setPts] = useState<[number, number][]>([])
  const active = useRef(false)
  const at = (e: PointerEvent<HTMLDivElement>): [number, number] => {
    const r = e.currentTarget.getBoundingClientRect()
    return [Math.min(width, Math.max(0, (e.clientX - r.left) / scale)), Math.min(height, Math.max(0, (e.clientY - r.top) / scale))]
  }
  function finish() {
    active.current = false
    if (pts.length < 2) {
      setPts([])
      return
    }
    const pad = lineWidth / 2 + 1
    const xs = pts.map((p) => p[0])
    const ys = pts.map((p) => p[1])
    const x = Math.min(...xs) - pad
    const y = Math.min(...ys) - pad
    const w = Math.max(...xs) + pad - x
    const h = Math.max(...ys) + pad - y
    onDone({ x, y, w, h }, pts.map(([px, py]) => [(px - x) / w, (py - y) / h]))
    setPts([])
  }
  return (
    <div
      className="draw-layer"
      onPointerDown={(e) => {
        e.currentTarget.setPointerCapture(e.pointerId)
        active.current = true
        const p = at(e)
        setPts(mode === 'draw' ? [p] : [p, p])
      }}
      onPointerMove={(e) => {
        if (!active.current) return
        const p = at(e)
        setPts((l) => (mode === 'draw' ? [...l, p] : [l[0], p]))
      }}
      onPointerUp={finish}
    >
      <svg width={width * scale} height={height * scale}>
        <polyline points={pts.map(([x, y]) => `${x * scale},${y * scale}`).join(' ')} fill="none" stroke={stroke} strokeWidth={Math.max(1, lineWidth * scale)} strokeLinecap="round" strokeLinejoin="round" />
      </svg>
    </div>
  )
}
