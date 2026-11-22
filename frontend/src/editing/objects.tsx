import type { CSSProperties } from 'react'
import type { Rect } from './BoxLayer'

export type Kind = 'text' | 'image' | 'rect' | 'ellipse' | 'highlight' | 'whiteout' | 'redact'

/** An object placed on a page in the editor (and what Python draws on save). */
export interface EditObj extends Rect {
  id: string
  type: Kind
  page: number
  text?: string
  size?: number
  family?: 'sans' | 'serif' | 'mono'
  bold?: boolean
  italic?: boolean
  color?: string
  stroke?: string | null
  fill?: string | null
  width?: number
  opacity?: number
  /** Image file path or data: URL (what Python draws). */
  src?: string
  /** Data URL shown in the editor. */
  preview?: string
  remove_text?: boolean
}

/** CSS stand-ins for the fonts Python embeds (Arial, Times New Roman, Courier New). */
export const FONT_CSS = { sans: 'Arial, sans-serif', serif: '"Times New Roman", serif', mono: '"Courier New", monospace' }

let seq = 0
export const newId = () => `o${++seq}`

/** Strip editor-only fields before sending to Python. */
export const toPayload = (objects: EditObj[]) => objects.map(({ id: _id, preview: _p, ...rest }) => rest)

/** How an object looks in the editor. */
export function objectContent(o: EditObj, scale: number) {
  const opacity = o.opacity ?? 1
  if (o.type === 'text') {
    const style: CSSProperties = {
      fontSize: (o.size ?? 12) * scale,
      fontFamily: FONT_CSS[o.family ?? 'sans'],
      fontWeight: o.bold ? 700 : 400,
      fontStyle: o.italic ? 'italic' : 'normal',
      color: o.color ?? '#000000',
      opacity,
    }
    return (
      <div className="eo-text" style={style}>
        {o.text}
      </div>
    )
  }
  if (o.type === 'image') return <img className="eo-img" src={o.preview} alt="" draggable={false} style={{ opacity }} />
  const style: CSSProperties = { opacity }
  if (o.type === 'rect' || o.type === 'ellipse') {
    style.border = o.stroke ? `${Math.max(1, (o.width ?? 1.5) * scale)}px solid ${o.stroke}` : undefined
    style.background = o.fill ?? 'transparent'
    if (o.type === 'ellipse') style.borderRadius = '50%'
  } else if (o.type === 'highlight') {
    style.background = o.fill ?? '#ffeb3b'
    style.opacity = Math.min(opacity, 0.4)
  } else if (o.type === 'whiteout') {
    style.background = o.fill ?? '#ffffff'
  } else if (o.type === 'redact') {
    style.background = '#000'
  }
  return <div className="eo-shape" style={style} />
}
