import { useEffect, useMemo, useState } from 'react'
import { ErrorNotice } from '../components/ErrorNotice'
import { call, toError, type ImagePdfOptions, type SavedImage } from '../lib/bridge'
import { cls } from '../lib/cls'
import { useJob } from '../lib/useJob'
import { IMAGE_EXTS, JPEG_EXTS } from '../lib/workspace'
import { ResultCard } from '../pdf/components'
import { useSaveFlow } from '../pdf/useSaveFlow'
import { BatchRun, FormatSelect, ImageListView, QualityField } from './components'
import { formatBytesShort } from './context'
import { useDebounced, useImageList, type ListItem } from './hooks'
import { targetSize, type ResizeOptions } from './resize'

const NON_JPEG = IMAGE_EXTS.filter((e) => !JPEG_EXTS.includes(e))

function Shell({ title, intro, children }: { title: string; intro: string; children: React.ReactNode }) {
  return (
    <section className="tool">
      <header className="tool-header">
        <h1>{title}</h1>
        <p>{intro}</p>
      </header>
      {children}
    </section>
  )
}

/** Run a batch call and keep each source's result for its row. */
function useBatch() {
  const flow = useSaveFlow()
  const job = useJob()
  const [folder, setFolder] = useState<string | null>(null)
  const [results, setResults] = useState<Record<string, SavedImage>>({})
  async function run(paths: string[], work: (paths: string[], folder: string | null, jobId: string) => Promise<SavedImage[]>) {
    setResults({})
    await flow.runSave(async () => {
      const files = await job.run((id) => work(paths, folder, id))
      if (files.length === paths.length) setResults(Object.fromEntries(paths.map((p, i) => [p, files[i]])))
      return files
    })
  }
  return { flow, job, folder, setFolder, results, run }
}

// --- Compress -----------------------------------------------------------------------------

const PRESETS = [
  { id: 'high', label: 'High quality', quality: 85 },
  { id: 'balanced', label: 'Balanced', quality: 72 },
  { id: 'small', label: 'Smallest', quality: 55 },
] as const
const MAX_SIDES = [0, 3840, 2560, 1920, 1600, 1280, 1024, 800]

export function CompressImage() {
  const list = useImageList('img-compress')
  const batch = useBatch()
  const [format, setFormat] = useState('keep')
  const [quality, setQuality] = useState(72)
  const [maxSide, setMaxSide] = useState(0)
  const [pngColors, setPngColors] = useState(0)
  const [keepMeta, setKeepMeta] = useState(false)
  const options = useMemo(() => ({ format, quality, max_side: maxSide, png_colors: pngColors, keep_metadata: keepMeta }), [format, quality, maxSide, pngColors, keepMeta])
  const pathsKey = list.good.map((i) => i.path).join('|')
  const settled = useDebounced(options, 450)
  const settledPaths = useDebounced(pathsKey, 450)
  const [estimates, setEstimates] = useState<Record<string, { before: number; after: number } | string>>({})

  // Measure each file's new size (compressed in memory, nothing written), one at a time.
  useEffect(() => {
    let active = true
    const paths = settledPaths ? settledPaths.split('|').slice(0, 60) : []
    ;(async () => {
      for (const path of paths) {
        try {
          const e = await call('image_compress_estimate', path, settled)
          if (!active) return
          setEstimates((m) => ({ ...m, [path]: e }))
        } catch (err) {
          if (!active) return
          setEstimates((m) => ({ ...m, [path]: toError(err).message }))
        }
      }
    })()
    return () => {
      active = false
    }
  }, [settled, settledPaths])

  const totals = list.good.reduce(
    (acc, i) => {
      const e = estimates[i.path]
      return typeof e === 'object' ? { before: acc.before + e.before, after: acc.after + Math.min(e.after, e.before) } : acc
    },
    { before: 0, after: 0 },
  )
  const pngOut = format === 'png' || (format === 'keep' && list.good.some((i) => i.path.toLowerCase().endsWith('.png')))

  return (
    <Shell title="Compress Image" intro="Make images smaller for the web, email or storage. Sizes below are measured, not guessed: each image is compressed in memory with your settings.">
      <div className="level-cards" role="radiogroup">
        {PRESETS.map((p) => (
          <button key={p.id} type="button" role="radio" aria-checked={quality === p.quality} className={cls('card level-card', quality === p.quality && 'is-on')} onClick={() => setQuality(p.quality)}>
            <strong>{p.label}</strong>
            <span className="muted small">Quality {p.quality}</span>
          </button>
        ))}
      </div>
      <div className="card conv-options">
        <div className="opt-grid">
          <FormatSelect value={format} onChange={setFormat} formats={['jpg', 'webp', 'avif', 'png']} />
          <QualityField value={quality} onChange={setQuality} />
          <label>
            Limit the size
            <select className="text-input" value={maxSide} onChange={(e) => setMaxSide(Number(e.target.value))}>
              {MAX_SIDES.map((s) => (
                <option key={s} value={s}>
                  {s ? `Longest side ${s} px` : 'Keep the pixel size'}
                </option>
              ))}
            </select>
          </label>
          {pngOut && (
            <label>
              PNG colours
              <select className="text-input" value={pngColors} onChange={(e) => setPngColors(Number(e.target.value))}>
                <option value={0}>All (lossless)</option>
                <option value={256}>256 colours (much smaller)</option>
                <option value={128}>128 colours</option>
                <option value={64}>64 colours (smallest)</option>
              </select>
            </label>
          )}
          <label className="check span-2">
            <input type="checkbox" checked={keepMeta} onChange={(e) => setKeepMeta(e.target.checked)} /> Keep metadata (camera details, location)
          </label>
        </div>
      </div>
      <ImageListView
        list={list}
        extra={(item) => {
          const e = estimates[item.path]
          if (!e) return <span className="muted small">Measuring…</span>
          if (typeof e === 'string') return <span className="field-error small">{e}</span>
          const saved = 1 - e.after / e.before
          return (
            <span className={cls('small', saved > 0 ? 'est-good' : 'muted')}>
              → {formatBytesShort(Math.min(e.after, e.before))} {saved > 0 ? `(−${Math.round(saved * 100)}%)` : '(already small)'}
            </span>
          )
        }}
        results={Object.fromEntries(Object.entries(batch.results).map(([p, r]) => [p, r.kept_original ? 'Kept original' : `Saved ${formatBytesShort(r.after ?? r.size)}`]))}
      />
      <ErrorNotice error={list.error} />
      <BatchRun
        count={list.good.length}
        label="Compress"
        folder={batch.folder}
        onFolder={batch.setFolder}
        flow={batch.flow}
        job={batch.job}
        note={totals.before > 0 ? <span className="small">Estimated total: {formatBytesShort(totals.before)} → <strong>{formatBytesShort(totals.after)}</strong></span> : undefined}
        onRun={() => batch.run(list.good.map((i) => i.path), (paths, folder, id) => call('image_compress', paths, folder, options, id))}
      />
    </Shell>
  )
}

// --- Resize -------------------------------------------------------------------------------

export function ResizeImage() {
  const list = useImageList('img-resize')
  const batch = useBatch()
  const [opts, setOpts] = useState<ResizeOptions>({ mode: 'percent', percent: 50, width: 1920, height: 0, longest: 1920, keep_aspect: true, fit: 'contain', no_enlarge: true, resample: 'lanczos' })
  const [format, setFormat] = useState('keep')
  const [quality, setQuality] = useState(90)
  const set = (patch: Partial<ResizeOptions>) => setOpts((o) => ({ ...o, ...patch }))
  const valid = opts.mode !== 'pixels' || opts.width > 0 || opts.height > 0

  const describe = (item: ListItem) => {
    if (!item.width || !item.height || !valid) return null
    const t = targetSize(item.width, item.height, opts)
    return (
      <span className="small">
        → {t.width} × {t.height} px{t.unchanged ? ' (kept)' : ''}
      </span>
    )
  }

  return (
    <Shell title="Resize Image" intro="Scale images by percentage, to exact pixels, or so the longest side fits. High-quality Lanczos resampling; aspect ratio kept unless you say otherwise.">
      <div className="card conv-options">
        <div className="segmented" role="radiogroup">
          {(
            [
              ['percent', 'Percentage'],
              ['pixels', 'Pixels'],
              ['longest', 'Longest side'],
            ] as const
          ).map(([id, label]) => (
            <button key={id} type="button" role="radio" aria-checked={opts.mode === id} className={cls('segment', opts.mode === id && 'is-on')} onClick={() => set({ mode: id })}>
              {label}
            </button>
          ))}
        </div>
        <div className="opt-grid">
          {opts.mode === 'percent' && (
            <label className="range-field span-2">
              Scale ({opts.percent}%)
              <input type="range" min={5} max={400} step={5} value={opts.percent} onChange={(e) => set({ percent: Number(e.target.value) })} />
            </label>
          )}
          {opts.mode === 'longest' && (
            <label>
              Longest side (px)
              <input className="text-input num" type="number" min={16} max={20000} value={opts.longest} onChange={(e) => set({ longest: Number(e.target.value) || 0 })} />
            </label>
          )}
          {opts.mode === 'pixels' && (
            <>
              <label>
                Width (px)
                <input className="text-input num" type="number" min={0} max={20000} value={opts.width || ''} placeholder="auto" onChange={(e) => set({ width: Number(e.target.value) || 0 })} />
              </label>
              <label>
                Height (px)
                <input className="text-input num" type="number" min={0} max={20000} value={opts.height || ''} placeholder="auto" onChange={(e) => set({ height: Number(e.target.value) || 0 })} />
              </label>
              <label className="check">
                <input type="checkbox" checked={opts.keep_aspect} onChange={(e) => set({ keep_aspect: e.target.checked })} /> Keep proportions
              </label>
              {opts.keep_aspect && opts.width > 0 && opts.height > 0 && (
                <label>
                  When both are set
                  <select className="text-input" value={opts.fit} onChange={(e) => set({ fit: e.target.value as ResizeOptions['fit'] })}>
                    <option value="contain">Fit inside (no cropping)</option>
                    <option value="cover">Fill exactly (crop the overflow)</option>
                  </select>
                </label>
              )}
            </>
          )}
          <label>
            Resampling
            <select className="text-input" value={opts.resample} onChange={(e) => set({ resample: e.target.value as ResizeOptions['resample'] })}>
              <option value="lanczos">Lanczos (sharpest)</option>
              <option value="bicubic">Bicubic (smooth)</option>
              <option value="nearest">Nearest (pixel art)</option>
            </select>
          </label>
          <FormatSelect value={format} onChange={setFormat} formats={['jpg', 'png', 'webp', 'avif']} />
          {format !== 'png' && <QualityField value={quality} onChange={setQuality} />}
          <label className="check span-2">
            <input type="checkbox" checked={opts.no_enlarge} onChange={(e) => set({ no_enlarge: e.target.checked })} /> Never enlarge (images already smaller are kept as they are)
          </label>
        </div>
      </div>
      <ImageListView list={list} extra={describe} results={Object.fromEntries(Object.entries(batch.results).map(([p, r]) => [p, `Saved ${r.width} × ${r.height}`]))} />
      <ErrorNotice error={list.error} />
      <BatchRun
        count={list.good.length}
        label="Resize"
        folder={batch.folder}
        onFolder={batch.setFolder}
        flow={batch.flow}
        job={batch.job}
        disabled={!valid}
        onRun={() => batch.run(list.good.map((i) => i.path), (paths, folder, id) => call('image_resize', paths, folder, { ...opts, format, quality }, id))}
      />
    </Shell>
  )
}

// --- Convert to JPG -------------------------------------------------------------------------

export function ConvertToJpg() {
  const list = useImageList('img-to-jpg', NON_JPEG)
  const batch = useBatch()
  const [quality, setQuality] = useState(90)
  const [background, setBackground] = useState('#ffffff')
  const [keepMeta, setKeepMeta] = useState(true)
  const [allFrames, setAllFrames] = useState(false)
  const multi = list.good.some((i) => (i.pages ?? 1) > 1) || list.good.some((i) => /\.(gif|tiff?)$/i.test(i.path))

  return (
    <Shell title="Convert to JPG" intro="Turn PNG, WebP, HEIC (iPhone), AVIF, GIF, BMP, TIFF and ICO images into JPG. Transparent areas get the background colour you choose.">
      <div className="card conv-options">
        <div className="opt-grid">
          <QualityField value={quality} onChange={setQuality} />
          <label>
            Background for transparency
            <input type="color" value={background} onChange={(e) => setBackground(e.target.value)} />
          </label>
          <label className="check span-2">
            <input type="checkbox" checked={keepMeta} onChange={(e) => setKeepMeta(e.target.checked)} /> Keep metadata and colour profile
          </label>
          {multi && (
            <label className="check span-2">
              <input type="checkbox" checked={allFrames} onChange={(e) => setAllFrames(e.target.checked)} /> Every page / frame as its own JPG (multi-page TIFF, animated GIF)
            </label>
          )}
        </div>
      </div>
      <ImageListView list={list} hint="Drag PNG, WebP, HEIC and other images here, or add them." results={Object.fromEntries(Object.entries(batch.results).map(([p, r]) => [p, `→ ${r.name}`]))} />
      <ErrorNotice error={list.error} />
      <BatchRun
        count={list.good.length}
        label="Convert"
        folder={batch.folder}
        onFolder={batch.setFolder}
        flow={batch.flow}
        job={batch.job}
        onRun={() => batch.run(list.good.map((i) => i.path), (paths, folder, id) => call('image_convert', paths, folder, { format: 'jpg', quality, background, keep_metadata: keepMeta, all_frames: allFrames }, id))}
      />
    </Shell>
  )
}

// --- Convert from JPG -----------------------------------------------------------------------

const PDF_OPTIONS: ImagePdfOptions = { page_size: 'fit', orientation: 'auto', margin: 'none', fit: 'contain' }

export function ConvertFromJpg() {
  const list = useImageList('img-from-jpg', JPEG_EXTS)
  const batch = useBatch()
  const [target, setTarget] = useState<'png' | 'webp' | 'avif' | 'gif' | 'bmp' | 'tiff' | 'pdf'>('png')
  const [quality, setQuality] = useState(90)
  const [pdfMode, setPdfMode] = useState<'one' | 'each'>('one')
  const [pageSize, setPageSize] = useState<ImagePdfOptions['page_size']>('fit')
  const lossy = target === 'webp' || target === 'avif'

  function run() {
    const paths = list.good.map((i) => i.path)
    const items = paths.map((path) => ({ path, rotate: 0 }))
    const options = { ...PDF_OPTIONS, page_size: pageSize, margin: pageSize === 'fit' ? 'none' : 'small' } as ImagePdfOptions
    if (target === 'pdf' && pdfMode === 'one') {
      return batch.flow.saveTo(
        () => call('suggest_pdf_path', paths[0], 'images'),
        (out) => call('images_to_pdf', items, out, options),
      )
    }
    if (target === 'pdf') return batch.flow.runSave(() => call('images_to_pdfs', items, batch.folder, options))
    return batch.run(paths, (p, folder, id) => call('image_convert', p, folder, { format: target, quality }, id))
  }

  return (
    <Shell title="Convert from JPG" intro="Export JPG photos as PNG, WebP, AVIF, GIF, BMP or TIFF, or put them into a PDF (one document, or one per photo).">
      <div className="card conv-options">
        <div className="segmented" role="radiogroup">
          {(['png', 'webp', 'avif', 'gif', 'bmp', 'tiff', 'pdf'] as const).map((f) => (
            <button key={f} type="button" role="radio" aria-checked={target === f} className={cls('segment', target === f && 'is-on')} onClick={() => setTarget(f)}>
              {f === 'tiff' ? 'TIFF' : f === 'webp' ? 'WebP' : f.toUpperCase()}
            </button>
          ))}
        </div>
        <div className="opt-grid">
          {lossy && <QualityField value={quality} onChange={setQuality} />}
          {target === 'pdf' && (
            <>
              <label>
                PDF
                <select className="text-input" value={pdfMode} onChange={(e) => setPdfMode(e.target.value as 'one' | 'each')}>
                  <option value="one">All photos in one PDF (list order)</option>
                  <option value="each">One PDF per photo</option>
                </select>
              </label>
              <label>
                Page size
                <select className="text-input" value={pageSize} onChange={(e) => setPageSize(e.target.value as ImagePdfOptions['page_size'])}>
                  <option value="fit">Same as the photo</option>
                  <option value="a4">A4</option>
                  <option value="letter">Letter</option>
                </select>
              </label>
            </>
          )}
          {target === 'png' && <p className="muted small span-2">PNG is lossless: the file is usually bigger than the JPG, but nothing more is lost.</p>}
        </div>
      </div>
      <ImageListView list={list} hint="Drag JPG photos here, or add them." results={Object.fromEntries(Object.entries(batch.results).map(([p, r]) => [p, `→ ${r.name}`]))} />
      <ErrorNotice error={list.error} />
      {target === 'pdf' && pdfMode === 'one' ? (
        <>
          <ErrorNotice error={batch.flow.error} />
          {batch.flow.saved && <ResultCard files={batch.flow.saved} onDismiss={batch.flow.dismiss} />}
          <div className="action-bar">
            <span />
            <button type="button" className="btn btn-primary" disabled={!list.good.length || batch.flow.busy} onClick={run}>
              {batch.flow.busy ? 'Working…' : 'Create PDF…'}
            </button>
          </div>
        </>
      ) : (
        <BatchRun count={list.good.length} label="Convert" folder={batch.folder} onFolder={batch.setFolder} flow={batch.flow} job={batch.job} onRun={run} />
      )}
    </Shell>
  )
}
