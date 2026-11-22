import { useEffect, useState } from 'react'
import { ErrorNotice } from '../components/ErrorNotice'
import { JobProgressBar } from '../components/JobProgressBar'
import { BoxLayer, type Rect } from '../editing/BoxLayer'
import { call, toError, type AiModelStatus, type FaceBox, type ImageInfo, type RenderedImage, type SavedImage } from '../lib/bridge'
import { cls } from '../lib/cls'
import { useJob } from '../lib/useJob'
import { useToolRequest } from '../lib/workspace'
import { ResultCard } from '../pdf/components'
import { useSaveFlow } from '../pdf/useSaveFlow'
import { CompareSlider, FormatSelect, ImageGate, ImageStage, ModelNotice, QualityField } from './components'
import { outputExt, useImageDoc } from './context'
import { useDebounced, useImagePreview, useRendered } from './hooks'

function useModel(key: 'upscale' | 'background') {
  const [model, setModel] = useState<AiModelStatus | null>(null)
  const [tick, setTick] = useState(0)
  useEffect(() => {
    call('ai_models').then((m) => setModel(m[key]), () => {})
  }, [key, tick])
  return { model, refresh: () => setTick((t) => t + 1) }
}

function AiShell({ tool, title, intro, children }: { tool: 'img-upscale' | 'img-remove-bg' | 'img-blur-faces'; title: string; intro: string; children: (image: ImageInfo) => React.ReactNode }) {
  const doc = useImageDoc()
  useToolRequest(tool, (path) => void doc.open(path))
  return (
    <section className="tool tool-wide">
      <header className="tool-header">
        <h1>{title}</h1>
        <p>{intro}</p>
      </header>
      <ImageGate>{children}</ImageGate>
    </section>
  )
}

// --- Upscale ------------------------------------------------------------------------------

export function UpscaleImage() {
  return (
    <AiShell
      tool="img-upscale"
      title="Upscale Image"
      intro="Double or quadruple the resolution with Real-ESRGAN, an AI super-resolution model that rebuilds sharp detail instead of just stretching pixels. Runs on your graphics card when it can."
    >
      {(image) => <UpscaleBody key={`${image.path}|${image.mtime}`} image={image} />}
    </AiShell>
  )
}

function UpscaleBody({ image }: { image: ImageInfo }) {
  const doc = useImageDoc()
  const flow = useSaveFlow()
  const job = useJob()
  const { model, refresh } = useModel('upscale')
  const { url } = useImagePreview(image)
  const [scale, setScale] = useState<2 | 4>(4)
  const [sharpen, setSharpen] = useState(false)
  const [format, setFormat] = useState('png')
  const [quality, setQuality] = useState(92)
  const [limits, setLimits] = useState<Record<number, number>>({})
  const [after, setAfter] = useState<string | null>(null)
  const [zoom, setZoom] = useState(3)
  const [device, setDevice] = useState<string | null>(null)

  useEffect(() => {
    Promise.all([call('ai_upscale_limit', 2), call('ai_upscale_limit', 4)]).then(([two, four]) => setLimits({ 2: two, 4: four }), () => {})
  }, [])

  const pixels = image.width * image.height
  const tooBig = limits[scale] !== undefined && pixels > limits[scale]
  const ext = outputExt(image.path, format)

  async function run() {
    setAfter(null)
    const res = await flow.saveTo(
      () => call('image_suggest', image.path, `_x${scale}`, format),
      (out) => job.run((id) => call('ai_upscale', image.path, out, scale, { format, quality, sharpen }, id)),
      { label: 'Image', extensions: [ext] },
    )
    refresh()
    if (res) {
      setDevice((res as SavedImage).device ?? null)
      try {
        setAfter((await call('image_preview', res.path, Math.max(image.width, image.height) * 2)).data_url)
      } catch {
        /* saved anyway */
      }
    }
  }

  return (
    <div className="split-layout">
      <div className="split-main">
        {after && url ? (
          <>
            <CompareSlider before={url} after={after} width={image.width} height={image.height} zoom={zoom} />
            <div className="segmented">
              {[1, 2, 3, 4].map((z) => (
                <button key={z} type="button" className={cls('segment', zoom === z && 'is-on')} onClick={() => setZoom(z)}>
                  {z === 1 ? 'Fit' : `${z}× zoom`}
                </button>
              ))}
            </div>
            <p className="muted small center">Drag the divider to compare. When zoomed, move the pointer to look around.</p>
          </>
        ) : (
          <ImageStage src={url} width={image.width} height={image.height} checker={image.alpha} busy={job.busy} />
        )}
      </div>
      <aside className="side-panel">
        <ModelNotice model={model} />
        <h2 className="panel-title">Scale</h2>
        <div className="level-cards two">
          {([2, 4] as const).map((s) => (
            <button key={s} type="button" className={cls('card level-card', scale === s && 'is-on')} onClick={() => setScale(s)}>
              <strong>{s}×</strong>
              <span className="muted small">
                {image.width * s} × {image.height * s} px
              </span>
            </button>
          ))}
        </div>
        {tooBig && <p className="field-error small">This image is {(pixels / 1e6).toFixed(1)} MP; {scale}× works up to {((limits[scale] ?? 0) / 1e6).toFixed(1)} MP. Try 2×, or crop it first.</p>}
        <label className="check">
          <input type="checkbox" checked={sharpen} onChange={(e) => setSharpen(e.target.checked)} /> Extra sharpening
        </label>
        <div className="field-stack">
          <FormatSelect value={format} onChange={setFormat} formats={['png', 'jpg', 'webp', 'avif']} />
          {ext !== 'png' && <QualityField value={quality} onChange={setQuality} />}
        </div>
        <JobProgressBar busy={job.busy} progress={job.progress} label="Loading the model…" />
        <button type="button" className="btn btn-primary" disabled={flow.busy || job.busy || tooBig} onClick={run}>
          {job.busy ? 'Upscaling…' : `Upscale ${scale}× and save…`}
        </button>
        {device && <p className="muted small">Ran on the {device}.</p>}
        <ErrorNotice error={flow.error} />
        {flow.saved && <ResultCard files={flow.saved} onDismiss={flow.dismiss} onContinue={(f) => void doc.open(f.path)} />}
      </aside>
    </div>
  )
}

// --- Remove background --------------------------------------------------------------------

export function RemoveBackground() {
  return (
    <AiShell
      tool="img-remove-bg"
      title="Remove Background"
      intro="Find the subject with an AI segmentation model (ISNet) and make the background transparent, or replace it with a colour or a blurred version of itself."
    >
      {(image) => <RemoveBgBody key={`${image.path}|${image.mtime}`} image={image} />}
    </AiShell>
  )
}

function RemoveBgBody({ image }: { image: ImageInfo }) {
  const doc = useImageDoc()
  const flow = useSaveFlow()
  const job = useJob()
  const { model, refresh } = useModel('background')
  const { url } = useImagePreview(image)
  const [background, setBackground] = useState<'transparent' | 'color' | 'blur'>('transparent')
  const [color, setColor] = useState('#ffffff')
  const [blur, setBlur] = useState(50)
  const [cleanup, setCleanup] = useState(40)
  const [feather, setFeather] = useState(0)
  const [trim, setTrim] = useState(false)
  const [format, setFormat] = useState('png')
  const [compare, setCompare] = useState(false)
  const [preview, setPreview] = useState<RenderedImage | null>(null)
  const [error, setError] = useState<Error | null>(null)
  const [started, setStarted] = useState(false)
  const options = { background, color, blur, cleanup, feather, trim }
  const settled = useDebounced(JSON.stringify(options), 250)
  const outFormat = background === 'transparent' && format === 'jpg' ? 'png' : format
  const ext = outputExt(image.path, outFormat)

  // The first preview runs the model (and may download it); later ones reuse its mask.
  useEffect(() => {
    if (!started) return
    let active = true
    job
      .run((id) => call('ai_remove_bg_preview', image.path, JSON.parse(settled), id))
      .then(
        (r) => {
          if (!active) return
          setPreview(r)
          setError(null)
          refresh()
        },
        (err) => active && setError(toError(err)),
      )
    return () => {
      active = false
    }
    // job and refresh are stable enough; re-running on their identity would loop
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [settled, started, image.path])

  return (
    <div className="split-layout">
      <div className="split-main">
        {preview && compare && url ? (
          <CompareSlider before={url} after={preview.data_url} width={preview.width} height={preview.height} checker />
        ) : (
          <ImageStage src={preview?.data_url ?? url} width={preview?.width ?? image.width} height={preview?.height ?? image.height} checker={!!preview} busy={job.busy} />
        )}
        {!started && (
          <button type="button" className="btn btn-primary" onClick={() => setStarted(true)}>
            Remove the background
          </button>
        )}
        <JobProgressBar busy={job.busy} progress={job.progress} label="Finding the subject…" />
        <ErrorNotice error={error} />
      </div>
      <aside className="side-panel">
        <ModelNotice model={model} />
        <h2 className="panel-title">Background</h2>
        <div className="segmented">
          {(
            [
              ['transparent', 'Transparent'],
              ['color', 'Colour'],
              ['blur', 'Blurred'],
            ] as const
          ).map(([id, label]) => (
            <button key={id} type="button" className={cls('segment', background === id && 'is-on')} onClick={() => setBackground(id)}>
              {label}
            </button>
          ))}
        </div>
        {background === 'color' && (
          <div className="swatch-row">
            {['#ffffff', '#000000', '#f2f2f2', '#1e88e5', '#43a047', '#e53935', '#fdd835'].map((c) => (
              <button key={c} type="button" className={cls('swatch', color === c && 'is-on')} style={{ background: c }} aria-label={c} onClick={() => setColor(c)} />
            ))}
            <input type="color" value={color} onChange={(e) => setColor(e.target.value)} aria-label="Custom colour" />
          </div>
        )}
        {background === 'blur' && (
          <label className="range-field">
            Blur ({blur})
            <input type="range" min={5} max={100} value={blur} onChange={(e) => setBlur(Number(e.target.value))} />
          </label>
        )}
        <h2 className="panel-title">Edges</h2>
        <label className="range-field">
          Clean-up ({cleanup}) – firmer edges, less haze
          <input type="range" min={0} max={90} value={cleanup} onChange={(e) => setCleanup(Number(e.target.value))} />
        </label>
        <label className="range-field">
          Soften ({feather} px)
          <input type="range" min={0} max={12} step={0.5} value={feather} onChange={(e) => setFeather(Number(e.target.value))} />
        </label>
        {background === 'transparent' && (
          <label className="check">
            <input type="checkbox" checked={trim} onChange={(e) => setTrim(e.target.checked)} /> Trim to the subject
          </label>
        )}
        {preview && (
          <label className="check">
            <input type="checkbox" checked={compare} onChange={(e) => setCompare(e.target.checked)} /> Compare with the original
          </label>
        )}
        <div className="field-stack">
          <FormatSelect value={format} onChange={setFormat} keep={false} formats={background === 'transparent' ? ['png', 'webp', 'avif'] : ['png', 'jpg', 'webp', 'avif']} />
        </div>
        <button
          type="button"
          className="btn btn-primary"
          disabled={flow.busy || job.busy}
          onClick={() =>
            flow.saveTo(
              () => call('image_suggest', image.path, '_no_bg', outFormat),
              (out) => job.run((id) => call('ai_remove_bg', image.path, out, { ...options, format: outFormat, quality: 92 }, id)),
              { label: 'Image', extensions: [ext] },
            )
          }
        >
          {flow.busy ? 'Saving…' : 'Save…'}
        </button>
        <ErrorNotice error={flow.error} />
        {flow.saved && <ResultCard files={flow.saved} onDismiss={flow.dismiss} onContinue={(f) => void doc.open(f.path)} />}
      </aside>
    </div>
  )
}

// --- Blur faces ---------------------------------------------------------------------------

interface Face extends FaceBox {
  id: string
}

let faceSeq = 0
const faceId = () => `f${++faceSeq}`

export function BlurFaces() {
  return (
    <AiShell
      tool="img-blur-faces"
      title="Blur Face"
      intro="Faces are found automatically with the face detector built into Windows. Check the boxes, add any it missed, remove any you want to keep, then blur, pixelate or cover them."
    >
      {(image) => <BlurBody key={`${image.path}|${image.mtime}`} image={image} />}
    </AiShell>
  )
}

function BlurBody({ image }: { image: ImageInfo }) {
  const doc = useImageDoc()
  const flow = useSaveFlow()
  const { url } = useImagePreview(image)
  const [faces, setFaces] = useState<Face[] | null>(null)
  const [detectError, setDetectError] = useState<Error | null>(null)
  const [selected, setSelected] = useState<string | null>(null)
  const [adding, setAdding] = useState(false)
  const [showBoxes, setShowBoxes] = useState(true)
  const [style, setStyle] = useState<'blur' | 'pixelate' | 'solid'>('blur')
  const [strength, setStrength] = useState(60)
  const [shape, setShape] = useState<'ellipse' | 'rect'>('ellipse')
  const [padding, setPadding] = useState(15)
  const [color, setColor] = useState('#000000')
  const [format, setFormat] = useState('keep')
  const options = { style, strength, shape, padding, color }
  const boxes = (faces ?? []).map(({ x, y, w, h }) => ({ x, y, w, h }))
  const { result: rendered, busy } = useRendered(faces ? JSON.stringify([boxes, options]) : null, () => call('faces_preview', image.path, boxes, options))

  function detect() {
    setFaces(null)
    setDetectError(null)
    call('faces_detect', image.path).then(
      (found) => setFaces(found.map((f) => ({ ...f, id: faceId() }))),
      (err) => {
        setDetectError(toError(err))
        setFaces([])
      },
    )
  }
  // Detect once when the photo opens.
  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(detect, [image.path])

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const t = e.target as HTMLElement
      if (selected && (e.key === 'Delete' || e.key === 'Backspace') && !['INPUT', 'TEXTAREA', 'SELECT'].includes(t.tagName)) {
        setFaces((l) => l?.filter((f) => f.id !== selected) ?? null)
        setSelected(null)
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [selected])

  function add(r: Rect) {
    const size = Math.max(40, Math.min(image.width, image.height) * 0.12)
    const box = r.w > 6 ? r : { x: r.x - size / 2, y: r.y - size / 2, w: size, h: size }
    const face = { ...box, id: faceId() }
    setFaces((l) => [...(l ?? []), face])
    setSelected(face.id)
    setAdding(false)
  }

  const shown = rendered && faces?.length ? rendered : null

  return (
    <div className="split-layout">
      <div className="split-main">
        <ImageStage
          src={shown?.data_url ?? url}
          width={image.width}
          height={image.height}
          busy={busy || faces === null}
          overlay={(scale) =>
            showBoxes || adding ? (
              <BoxLayer
                page={{ width: image.width, height: image.height }}
                scale={scale}
                boxes={(faces ?? []).map((f) => ({ ...f, className: 'lbox-face' }))}
                selected={selected}
                onSelect={setSelected}
                onChange={(id, r) => setFaces((l) => l?.map((f) => (f.id === id ? { ...f, ...r } : f)) ?? null)}
                onCreate={adding ? add : undefined}
              />
            ) : null
          }
        />
      </div>
      <aside className="side-panel">
        <h2 className="panel-title">Faces</h2>
        <p className="small">
          {faces === null ? 'Looking for faces…' : faces.length === 0 ? 'No faces found. Draw boxes over anything you want hidden.' : `${faces.length} box${faces.length === 1 ? '' : 'es'} to blur.`}
        </p>
        <ErrorNotice error={detectError} />
        <div className="button-row">
          <button type="button" className={cls('btn btn-secondary btn-sm', adding && 'is-tool')} onClick={() => setAdding((a) => !a)}>
            {adding ? 'Click or drag on the photo…' : '+ Add a box'}
          </button>
          {selected && (
            <button
              type="button"
              className="btn btn-ghost btn-sm"
              onClick={() => {
                setFaces((l) => l?.filter((f) => f.id !== selected) ?? null)
                setSelected(null)
              }}
            >
              Remove selected
            </button>
          )}
          <button type="button" className="btn btn-ghost btn-sm" onClick={detect}>
            Detect again
          </button>
        </div>
        <label className="check">
          <input type="checkbox" checked={showBoxes} onChange={(e) => setShowBoxes(e.target.checked)} /> Show boxes
        </label>
        <h2 className="panel-title">Effect</h2>
        <div className="segmented">
          {(
            [
              ['blur', 'Blur'],
              ['pixelate', 'Pixelate'],
              ['solid', 'Cover'],
            ] as const
          ).map(([id, label]) => (
            <button key={id} type="button" className={cls('segment', style === id && 'is-on')} onClick={() => setStyle(id)}>
              {label}
            </button>
          ))}
        </div>
        {style === 'solid' ? (
          <label className="inline-field">
            Colour <input type="color" value={color} onChange={(e) => setColor(e.target.value)} />
          </label>
        ) : (
          <label className="range-field">
            Strength ({strength})
            <input type="range" min={10} max={100} value={strength} onChange={(e) => setStrength(Number(e.target.value))} />
          </label>
        )}
        <label className="range-field">
          Grow boxes ({padding}%)
          <input type="range" min={0} max={60} value={padding} onChange={(e) => setPadding(Number(e.target.value))} />
        </label>
        <div className="segmented">
          {(['ellipse', 'rect'] as const).map((s) => (
            <button key={s} type="button" className={cls('segment', shape === s && 'is-on')} onClick={() => setShape(s)}>
              {s === 'ellipse' ? 'Oval' : 'Rectangle'}
            </button>
          ))}
        </div>
        <div className="field-stack">
          <FormatSelect value={format} onChange={setFormat} formats={['jpg', 'png', 'webp']} />
        </div>
        <p className="muted small">Saved copies leave out the photo's metadata (camera, location) by default.</p>
        <button
          type="button"
          className="btn btn-primary"
          disabled={flow.busy || !faces?.length}
          onClick={() =>
            flow.saveTo(
              () => call('image_suggest', image.path, '_blurred', format),
              (out) => call('faces_blur', image.path, out, boxes, { ...options, format, quality: 92 }),
              { label: 'Image', extensions: [outputExt(image.path, format)] },
            )
          }
        >
          {flow.busy ? 'Saving…' : 'Blur and save…'}
        </button>
        <ErrorNotice error={flow.error} />
        {flow.saved && <ResultCard files={flow.saved} onDismiss={flow.dismiss} onContinue={(f) => void doc.open(f.path)} />}
      </aside>
    </div>
  )
}
