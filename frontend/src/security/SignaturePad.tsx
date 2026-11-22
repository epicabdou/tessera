import { useEffect, useRef, useState, type PointerEvent } from 'react'
import { ErrorNotice } from '../components/ErrorNotice'
import { call, toError } from '../lib/bridge'
import { cls } from '../lib/cls'
import { CONVERT_EXTS } from '../lib/workspace'

/** A finished signature: a PNG (data URL or image path) and its aspect ratio (w / h). */
export interface Signature {
  src: string
  preview: string
  ratio: number
}

const FONTS = ['Segoe Script', 'Lucida Handwriting', 'Ink Free', 'Segoe Print', 'Brush Script MT']
const INKS = ['#111111', '#1a3d8f', '#0b6e4f']
const PAD_W = 520
const PAD_H = 170

/** Crop a canvas to its inked pixels (plus a little padding) and return it as PNG. */
function trimmed(canvas: HTMLCanvasElement): Signature | null {
  const ctx = canvas.getContext('2d')!
  const { width, height } = canvas
  const data = ctx.getImageData(0, 0, width, height).data
  let x0 = width
  let y0 = height
  let x1 = -1
  let y1 = -1
  for (let y = 0; y < height; y++) {
    for (let x = 0; x < width; x++) {
      if (data[(y * width + x) * 4 + 3] > 8) {
        if (x < x0) x0 = x
        if (x > x1) x1 = x
        if (y < y0) y0 = y
        if (y > y1) y1 = y
      }
    }
  }
  if (x1 < 0) return null
  const pad = Math.round(width * 0.015)
  x0 = Math.max(0, x0 - pad)
  y0 = Math.max(0, y0 - pad)
  x1 = Math.min(width - 1, x1 + pad)
  y1 = Math.min(height - 1, y1 + pad)
  const out = document.createElement('canvas')
  out.width = x1 - x0 + 1
  out.height = y1 - y0 + 1
  out.getContext('2d')!.drawImage(canvas, x0, y0, out.width, out.height, 0, 0, out.width, out.height)
  const url = out.toDataURL('image/png')
  return { src: url, preview: url, ratio: out.width / out.height }
}

/** Draw, type or upload a handwritten-style signature. */
export function SignaturePad({ onDone }: { onDone: (sig: Signature) => void }) {
  const [mode, setMode] = useState<'draw' | 'type' | 'upload'>('draw')
  const [ink, setInk] = useState(INKS[0])
  const [name, setName] = useState('')
  const [font, setFont] = useState(FONTS[0])
  const [drawn, setDrawn] = useState(false)
  const [error, setError] = useState<Error | null>(null)
  const empty = mode === 'type' ? !name.trim() : !drawn
  const canvas = useRef<HTMLCanvasElement>(null)
  const last = useRef<{ x: number; y: number } | null>(null)
  const dpr = 2

  // Typed signatures are drawn on the same canvas, so "Use" works the same way.
  useEffect(() => {
    const c = canvas.current
    if (!c || mode !== 'type') return
    const ctx = c.getContext('2d')!
    ctx.clearRect(0, 0, c.width, c.height)
    if (!name.trim()) return
    let size = 64 * dpr
    ctx.font = `${size}px "${font}", cursive`
    while (ctx.measureText(name).width > c.width * 0.92 && size > 16) {
      size -= 4
      ctx.font = `${size}px "${font}", cursive`
    }
    ctx.fillStyle = ink
    ctx.textAlign = 'center'
    ctx.textBaseline = 'middle'
    ctx.fillText(name, c.width / 2, c.height / 2)
  }, [mode, name, font, ink])

  function clear() {
    const c = canvas.current
    c?.getContext('2d')!.clearRect(0, 0, c.width, c.height)
    setDrawn(false)
  }

  function pos(e: PointerEvent<HTMLCanvasElement>) {
    const r = e.currentTarget.getBoundingClientRect()
    return { x: ((e.clientX - r.left) / r.width) * e.currentTarget.width, y: ((e.clientY - r.top) / r.height) * e.currentTarget.height }
  }

  function stroke(e: PointerEvent<HTMLCanvasElement>) {
    if (!last.current) return
    const p = pos(e)
    const ctx = e.currentTarget.getContext('2d')!
    ctx.strokeStyle = ink
    ctx.lineWidth = 2.6 * dpr * (e.pressure && e.pointerType === 'pen' ? 0.5 + e.pressure : 1)
    ctx.lineCap = 'round'
    ctx.lineJoin = 'round'
    ctx.beginPath()
    ctx.moveTo(last.current.x, last.current.y)
    ctx.lineTo(p.x, p.y)
    ctx.stroke()
    last.current = p
    setDrawn(true)
  }

  async function upload() {
    try {
      const [path] = await call('pick_files', 'Images', CONVERT_EXTS['to-pdf-images'] ?? [], false)
      if (!path) return
      const [thumb] = await call('image_thumbnails', [path], 600)
      if (thumb.error || !thumb.data_url) throw new Error(thumb.error ?? 'Unreadable image')
      onDone({ src: path, preview: thumb.data_url, ratio: (thumb.width ?? 3) / (thumb.height ?? 1) })
    } catch (err) {
      setError(toError(err))
    }
  }

  return (
    <div className="card sig-pad">
      <div className="segmented" role="radiogroup">
        {(
          [
            ['draw', 'Draw'],
            ['type', 'Type'],
            ['upload', 'Upload image'],
          ] as const
        ).map(([id, label]) => (
          <button
            key={id}
            type="button"
            role="radio"
            aria-checked={mode === id}
            className={cls('segment', mode === id && 'is-on')}
            onClick={() => {
              clear()
              setMode(id)
            }}
          >
            {label}
          </button>
        ))}
      </div>
      {mode === 'upload' ? (
        <div className="button-row">
          <button type="button" className="btn btn-secondary" onClick={upload}>
            Choose a signature image…
          </button>
          <span className="muted small">A PNG with a transparent background looks best.</span>
        </div>
      ) : (
        <>
          {mode === 'type' && (
            <div className="button-row">
              <input className="text-input" value={name} placeholder="Your name" onChange={(e) => setName(e.target.value)} aria-label="Name" />
              <select className="text-input" value={font} onChange={(e) => setFont(e.target.value)} aria-label="Style">
                {FONTS.map((f) => (
                  <option key={f} value={f} style={{ fontFamily: f }}>
                    {f}
                  </option>
                ))}
              </select>
            </div>
          )}
          <canvas
            ref={canvas}
            className={cls('sig-canvas', mode === 'draw' && 'is-draw')}
            width={PAD_W * dpr}
            height={PAD_H * dpr}
            onPointerDown={(e) => {
              if (mode !== 'draw') return
              e.currentTarget.setPointerCapture(e.pointerId)
              last.current = pos(e)
            }}
            onPointerMove={stroke}
            onPointerUp={() => {
              last.current = null
            }}
            onPointerCancel={() => {
              last.current = null
            }}
          />
          <div className="button-row">
            <span className="muted small">Ink</span>
            {INKS.map((c) => (
              <button key={c} type="button" className={cls('swatch', ink === c && 'is-on')} style={{ background: c }} aria-label={`Ink ${c}`} onClick={() => setInk(c)} />
            ))}
            <span className="toolbar-spacer" />
            <button type="button" className="btn btn-ghost btn-sm" onClick={clear} disabled={empty}>
              Clear
            </button>
            <button
              type="button"
              className="btn btn-primary btn-sm"
              disabled={empty}
              onClick={() => {
                const sig = canvas.current && trimmed(canvas.current)
                if (sig) onDone(sig)
              }}
            >
              Use this signature
            </button>
          </div>
          {mode === 'draw' && <p className="muted small">Sign in the box with your mouse, pen or finger.</p>}
        </>
      )}
      <ErrorNotice error={error} />
    </div>
  )
}
