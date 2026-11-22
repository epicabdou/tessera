import type { CSSProperties } from 'react'
import type { Rect } from '../editing/BoxLayer'

export type LayerKind = 'text' | 'rect' | 'ellipse' | 'arrow' | 'line' | 'draw' | 'image'

/** A layer in the photo editor (image pixels of the edited picture). */
export interface Layer extends Rect {
  id: string
  type: LayerKind
  opacity: number
  text?: string
  family?: 'sans' | 'serif' | 'mono' | 'display' | 'script' | 'hand'
  size?: number
  color?: string
  bold?: boolean
  italic?: boolean
  align?: 'left' | 'center' | 'right'
  outline?: number
  outline_color?: string
  shadow?: boolean
  stroke?: string | null
  fill?: string | null
  width?: number
  radius?: number
  /** Points within the box, 0..1 (lines, arrows, drawings). */
  points?: [number, number][]
  /** Image file path (what Python draws). */
  src?: string
  /** Data URL shown in the editor. */
  preview?: string
}

/** CSS stand-ins for the Windows fonts Python draws with. */
export const LAYER_FONTS: Record<NonNullable<Layer['family']>, string> = {
  sans: 'Arial, sans-serif',
  serif: '"Times New Roman", serif',
  mono: '"Courier New", monospace',
  display: 'Impact, sans-serif',
  script: '"Segoe Script", cursive',
  hand: '"Comic Sans MS", cursive',
}
export const LINE_HEIGHT = 1.2

let measureCanvas: HTMLCanvasElement | null = null

/** Box size of a text layer, as Python will draw it. */
export function measureText(l: Pick<Layer, 'text' | 'family' | 'size' | 'bold' | 'italic' | 'outline'>): { w: number; h: number } {
  measureCanvas ??= document.createElement('canvas')
  const ctx = measureCanvas.getContext('2d')!
  const size = l.size ?? 48
  ctx.font = `${l.italic ? 'italic ' : ''}${l.bold ? '700 ' : '400 '}${size}px ${LAYER_FONTS[l.family ?? 'sans']}`
  const lines = (l.text ?? '').split('\n')
  const w = Math.max(...lines.map((line) => ctx.measureText(line).width), size * 0.3)
  const pad = (l.outline ?? 0) * 2
  return { w: Math.ceil(w + pad + 2), h: Math.ceil(lines.length * size * LINE_HEIGHT + pad) }
}

/** How a layer looks while editing (the saved result is drawn by Python). */
export function layerContent(l: Layer, scale: number) {
  const opacity = l.opacity ?? 1
  if (l.type === 'text') {
    const outline = (l.outline ?? 0) * scale
    const style: CSSProperties = {
      fontFamily: LAYER_FONTS[l.family ?? 'sans'],
      fontSize: (l.size ?? 48) * scale,
      fontWeight: l.bold ? 700 : 400,
      fontStyle: l.italic ? 'italic' : 'normal',
      lineHeight: LINE_HEIGHT,
      color: l.color ?? '#ffffff',
      textAlign: l.align ?? 'left',
      opacity,
      WebkitTextStroke: outline ? `${outline * 2}px ${l.outline_color ?? '#000'}` : undefined,
      paintOrder: 'stroke fill',
      textShadow: l.shadow ? `${(l.size ?? 48) * 0.06 * scale}px ${(l.size ?? 48) * 0.06 * scale}px ${(l.size ?? 48) * 0.08 * scale}px rgba(0,0,0,0.6)` : undefined,
    }
    return (
      <div className="ly-text" style={style}>
        {l.text}
      </div>
    )
  }
  if (l.type === 'image') return <img className="eo-img" src={l.preview} alt="" draggable={false} style={{ opacity }} />
  if (l.type === 'rect' || l.type === 'ellipse') {
    const style: CSSProperties = {
      opacity,
      border: l.stroke ? `${Math.max(1, (l.width ?? 4) * scale)}px solid ${l.stroke}` : undefined,
      background: l.fill ?? 'transparent',
      borderRadius: l.type === 'ellipse' ? '50%' : (l.radius ?? 0) * scale,
    }
    return <div className="eo-shape" style={style} />
  }
  const w = l.w * scale
  const h = l.h * scale
  const pts = (l.points ?? []).map(([u, v]) => [u * w, v * h] as const)
  const sw = Math.max(1, (l.width ?? 6) * scale)
  const color = l.stroke ?? '#e53935'
  let head = null
  if (l.type === 'arrow' && pts.length >= 2) {
    const [x0, y0] = pts[0]
    const [x1, y1] = pts[1]
    const a = Math.atan2(y1 - y0, x1 - x0)
    const len = sw * 3.2
    head = <polygon points={`${x1},${y1} ${x1 - len * Math.cos(a - 0.45)},${y1 - len * Math.sin(a - 0.45)} ${x1 - len * Math.cos(a + 0.45)},${y1 - len * Math.sin(a + 0.45)}`} fill={color} />
  }
  return (
    <svg className="ly-svg" width={w} height={h} style={{ opacity }}>
      <polyline points={pts.map((p) => p.join(',')).join(' ')} fill="none" stroke={color} strokeWidth={sw} strokeLinecap="round" strokeLinejoin="round" />
      {head}
    </svg>
  )
}

export type ViewOp = 'cw' | 'ccw' | 'flip_h' | 'flip_v'

/**
 * Move layers with the picture when the view is rotated or mirrored (W × H = the view
 * before the change). Text and logos stay upright; shapes and strokes turn with it.
 */
export function transformLayers(layers: Layer[], op: ViewOp, W: number, H: number): Layer[] {
  const map = (x: number, y: number): [number, number] =>
    op === 'cw' ? [H - y, x] : op === 'ccw' ? [y, W - x] : op === 'flip_h' ? [W - x, y] : [x, H - y]
  const turns = op === 'cw' || op === 'ccw'
  return layers.map((l) => {
    if (l.points && (l.type === 'draw' || l.type === 'line' || l.type === 'arrow')) {
      const abs = l.points.map(([u, v]) => map(l.x + u * l.w, l.y + v * l.h))
      const xs = abs.map((p) => p[0])
      const ys = abs.map((p) => p[1])
      const x = Math.min(...xs)
      const y = Math.min(...ys)
      const w = Math.max(Math.max(...xs) - x, 1)
      const h = Math.max(Math.max(...ys) - y, 1)
      return { ...l, x, y, w, h, points: abs.map(([px, py]) => [(px - x) / w, (py - y) / h] as [number, number]) }
    }
    const [cx, cy] = map(l.x + l.w / 2, l.y + l.h / 2)
    const swap = turns && (l.type === 'rect' || l.type === 'ellipse')
    const w = swap ? l.h : l.w
    const h = swap ? l.w : l.h
    return { ...l, x: cx - w / 2, y: cy - h / 2, w, h }
  })
}
