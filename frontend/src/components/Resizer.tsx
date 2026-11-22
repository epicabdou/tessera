import { useEffect, useState } from 'react'
import { cls } from '../lib/cls'

interface Props {
  label: string
  /** Which side of the window the panel being resized sits on. */
  panel: 'left' | 'right'
  width: number
  min: number
  max: number
  defaultWidth: number
  onResize: (width: number) => void
  /** Called when a drag or key press finishes, with the final width. */
  onCommit: (width: number) => void
}

const STEP = 16

/** Vertical drag handle between a side panel and the main area. Also keyboard-resizable. */
export function Resizer({ label, panel, width, min, max, defaultWidth, onResize, onCommit }: Props) {
  const [dragging, setDragging] = useState(false)
  const clamp = (w: number) => Math.round(Math.min(max, Math.max(min, w)))
  const widthAt = (clientX: number) => clamp(panel === 'left' ? clientX : window.innerWidth - clientX)

  useEffect(() => {
    document.body.classList.toggle('is-resizing', dragging)
    return () => document.body.classList.remove('is-resizing')
  }, [dragging])

  return (
    <div
      className={cls('resizer', dragging && 'is-dragging')}
      role="separator"
      aria-orientation="vertical"
      aria-label={label}
      aria-valuemin={min}
      aria-valuemax={max}
      aria-valuenow={width}
      tabIndex={0}
      onPointerDown={(e) => {
        e.preventDefault()
        e.currentTarget.setPointerCapture(e.pointerId)
        setDragging(true)
      }}
      onPointerMove={(e) => {
        if (dragging) onResize(widthAt(e.clientX))
      }}
      onPointerUp={(e) => {
        if (!dragging) return
        setDragging(false)
        onCommit(widthAt(e.clientX))
      }}
      onDoubleClick={() => {
        onResize(defaultWidth)
        onCommit(defaultWidth)
      }}
      onKeyDown={(e) => {
        if (e.key !== 'ArrowLeft' && e.key !== 'ArrowRight') return
        e.preventDefault()
        const grow = (e.key === 'ArrowRight') === (panel === 'left')
        const next = clamp(width + (grow ? STEP : -STEP))
        onResize(next)
        onCommit(next)
      }}
    />
  )
}
