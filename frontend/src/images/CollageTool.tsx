import { useState, type ReactNode } from 'react'
import { ErrorNotice } from '../components/ErrorNotice'
import { ArrowDownIcon, ArrowUpIcon } from '../components/icons'
import { JobProgressBar } from '../components/JobProgressBar'
import { call } from '../lib/bridge'
import { cls } from '../lib/cls'
import { dirname } from '../lib/format'
import { useJob } from '../lib/useJob'
import { useWorkspace } from '../lib/workspace'
import { ResultCard } from '../pdf/components'
import { useSaveFlow } from '../pdf/useSaveFlow'
import { FormatSelect, ImageListView, ImageStage, QualityField } from './components'
import { useImageList, useRendered } from './hooks'

type Layout = 'grid' | 'mosaic' | 'featured'
type Side = 'left' | 'right' | 'top' | 'bottom'

const SHAPES: [string, string][] = [
  ['square', 'Square (1:1)'],
  ['portrait', 'Portrait (4:5)'],
  ['landscape', 'Landscape (3:2)'],
  ['wide', 'Wide (16:9)'],
  ['story', 'Story (9:16)'],
  ['a4', 'A4 portrait'],
  ['a4-landscape', 'A4 landscape'],
]
const WIDTHS = [1200, 2400, 3600, 4800]

/** Little drawings of each layout, for the picker. */
const LAYOUT_ICONS: Record<Layout, ReactNode> = {
  grid: (
    <svg viewBox="0 0 30 22" aria-hidden="true">
      <rect x="1" y="1" width="8.5" height="9.5" rx="1.2" />
      <rect x="10.75" y="1" width="8.5" height="9.5" rx="1.2" />
      <rect x="20.5" y="1" width="8.5" height="9.5" rx="1.2" />
      <rect x="1" y="11.5" width="8.5" height="9.5" rx="1.2" />
      <rect x="10.75" y="11.5" width="8.5" height="9.5" rx="1.2" />
      <rect x="20.5" y="11.5" width="8.5" height="9.5" rx="1.2" />
    </svg>
  ),
  mosaic: (
    <svg viewBox="0 0 30 22" aria-hidden="true">
      <rect x="1" y="1" width="12" height="9.5" rx="1.2" />
      <rect x="14" y="1" width="6" height="9.5" rx="1.2" />
      <rect x="21" y="1" width="8" height="9.5" rx="1.2" />
      <rect x="1" y="11.5" width="7" height="9.5" rx="1.2" />
      <rect x="9" y="11.5" width="20" height="9.5" rx="1.2" />
    </svg>
  ),
  featured: (
    <svg viewBox="0 0 30 22" aria-hidden="true">
      <rect x="1" y="1" width="17" height="20" rx="1.2" />
      <rect x="19" y="1" width="10" height="6" rx="1.2" />
      <rect x="19" y="8" width="10" height="6" rx="1.2" />
      <rect x="19" y="15" width="10" height="6" rx="1.2" />
    </svg>
  ),
}

const LAYOUTS: { id: Layout; label: string; hint: string }[] = [
  { id: 'grid', label: 'Grid', hint: 'Equal cells' },
  { id: 'mosaic', label: 'Mosaic', hint: 'Rows, no cropping' },
  { id: 'featured', label: 'Featured', hint: 'One big photo' },
]

export function PhotoCollage() {
  const list = useImageList('img-collage')
  const flow = useSaveFlow()
  const job = useJob()
  const { openInTool } = useWorkspace()
  const [layout, setLayout] = useState<Layout>('grid')
  const [aspect, setAspect] = useState('square')
  const [columns, setColumns] = useState(0)
  const [perRow, setPerRow] = useState(3)
  const [side, setSide] = useState<Side>('left')
  const [share, setShare] = useState(60)
  const [fit, setFit] = useState<'fill' | 'fit'>('fill')
  const [spacing, setSpacing] = useState(1)
  const [margin, setMargin] = useState(2)
  const [radius, setRadius] = useState(0)
  const [background, setBackground] = useState('#ffffff')
  const [transparent, setTransparent] = useState(false)
  const [width, setWidth] = useState(2400)
  const [format, setFormat] = useState('jpg')
  const [quality, setQuality] = useState(90)

  const paths = list.good.map((i) => i.path)
  const look = {
    layout,
    aspect,
    columns,
    per_row: perRow,
    side,
    share: share / 100,
    fit,
    spacing: spacing / 100,
    margin: margin / 100,
    radius: radius / 100,
    background: transparent ? 'transparent' : background,
    width,
  }
  const options = { ...look, format, quality }
  const enough = paths.length >= 2
  // The preview depends on the layout, not on the file format.
  const { result: preview, busy, error: previewError } = useRendered(enough ? JSON.stringify([paths, look]) : null, () => call('collage_preview', paths, look, 900))

  const move = (from: number, to: number) =>
    list.setItems((items) => {
      if (to < 0 || to >= items.length) return items
      const next = [...items]
      const [item] = next.splice(from, 1)
      next.splice(to, 0, item)
      return next
    })

  const shuffle = () =>
    list.setItems((items) => {
      const next = [...items]
      for (let i = next.length - 1; i > 0; i--) {
        const j = Math.floor(Math.random() * (i + 1))
        ;[next[i], next[j]] = [next[j], next[i]]
      }
      return next
    })

  function toggleTransparent(on: boolean) {
    setTransparent(on)
    if (on && format === 'jpg') setFormat('png') // JPG has no transparency
  }

  const save = () => {
    const ext = format
    return flow.saveTo(
      () => call('suggest_output_path', `${dirname(paths[0])}/collage.${ext}`, 'collage', ext),
      (out) => job.run((id) => call('collage_save', paths, out, options, id)),
      { label: 'Image', extensions: [ext] },
    )
  }

  return (
    <section className="tool tool-wide">
      <header className="tool-header">
        <h1>Photo collage</h1>
        <p>Arrange photos on one canvas: a grid, a mosaic that keeps every photo whole, or one featured photo with the rest beside it. The preview is the real result.</p>
      </header>
      <div className="split-layout">
        <div className="split-main">
          {enough && preview ? (
            <ImageStage src={preview.data_url} width={preview.width} height={preview.height} busy={busy} maxHeight={520} checker={transparent} />
          ) : (
            <div className="stage-empty muted">{list.items.length === 1 ? 'Add one more photo to see the collage.' : enough ? 'Preparing the preview…' : 'Add at least two photos below.'}</div>
          )}
          <ErrorNotice error={previewError} />
          <ImageListView
            list={list}
            hint="Drag photos here from the Explorer, or add them. The order here is the order in the collage."
            extra={(item) => {
              const i = list.items.findIndex((x) => x.path === item.path)
              return (
                <span className="collage-order">
                  {layout === 'featured' && i === 0 && <span className="collage-badge">Big</span>}
                  <button type="button" className="icon-btn" aria-label={`Move ${item.name} up`} disabled={i <= 0} onClick={() => move(i, i - 1)}>
                    <ArrowUpIcon size={13} />
                  </button>
                  <button type="button" className="icon-btn" aria-label={`Move ${item.name} down`} disabled={i >= list.items.length - 1} onClick={() => move(i, i + 1)}>
                    <ArrowDownIcon size={13} />
                  </button>
                </span>
              )
            }}
          />
          <ErrorNotice error={list.error} />
        </div>

        <aside className="side-panel">
          <div className="collage-layouts" role="radiogroup" aria-label="Layout">
            {LAYOUTS.map((l) => (
              <button key={l.id} type="button" role="radio" aria-checked={layout === l.id} className={cls('card level-card collage-layout', layout === l.id && 'is-on')} onClick={() => setLayout(l.id)}>
                {LAYOUT_ICONS[l.id]}
                <strong>{l.label}</strong>
                <span className="muted small">{l.hint}</span>
              </button>
            ))}
          </div>

          <div className="field-stack">
            {layout === 'mosaic' ? (
              <>
                <label className="range-field">
                  Photos per row (about {perRow})
                  <input type="range" min={1} max={6} value={perRow} onChange={(e) => setPerRow(Number(e.target.value))} />
                </label>
                <p className="muted small">The height follows from the photos; none is cropped.</p>
              </>
            ) : (
              <label>
                Shape
                <select className="text-input" value={aspect} onChange={(e) => setAspect(e.target.value)}>
                  {SHAPES.map(([id, label]) => (
                    <option key={id} value={id}>
                      {label}
                    </option>
                  ))}
                </select>
              </label>
            )}
            {layout === 'grid' && (
              <label>
                Columns
                <select className="text-input" value={columns} onChange={(e) => setColumns(Number(e.target.value))}>
                  <option value={0}>Automatic</option>
                  {[1, 2, 3, 4, 5, 6, 7, 8].map((n) => (
                    <option key={n} value={n}>
                      {n}
                    </option>
                  ))}
                </select>
              </label>
            )}
            {layout === 'featured' && (
              <>
                <div className="segmented" role="radiogroup" aria-label="Big photo on the">
                  {(['left', 'top', 'right', 'bottom'] as const).map((s) => (
                    <button key={s} type="button" role="radio" aria-checked={side === s} className={cls('segment', side === s && 'is-on')} onClick={() => setSide(s)}>
                      {s[0].toUpperCase() + s.slice(1)}
                    </button>
                  ))}
                </div>
                <label className="range-field">
                  Big photo ({share}% of the space)
                  <input type="range" min={35} max={80} value={share} onChange={(e) => setShare(Number(e.target.value))} />
                </label>
                <p className="muted small">The first photo in the list is the big one.</p>
              </>
            )}
            {layout !== 'mosaic' && (
              <div className="segmented" role="radiogroup" aria-label="Photos in their cells">
                <button type="button" role="radio" aria-checked={fit === 'fill'} className={cls('segment', fit === 'fill' && 'is-on')} onClick={() => setFit('fill')}>
                  Fill (crop)
                </button>
                <button type="button" role="radio" aria-checked={fit === 'fit'} className={cls('segment', fit === 'fit' && 'is-on')} onClick={() => setFit('fit')}>
                  Whole photo
                </button>
              </div>
            )}
          </div>

          <h2 className="panel-title">Spacing and style</h2>
          <label className="range-field">
            Spacing ({spacing}%)
            <input type="range" min={0} max={6} step={0.5} value={spacing} onChange={(e) => setSpacing(Number(e.target.value))} />
          </label>
          <label className="range-field">
            Border ({margin}%)
            <input type="range" min={0} max={10} step={0.5} value={margin} onChange={(e) => setMargin(Number(e.target.value))} />
          </label>
          <label className="range-field">
            Rounded corners ({radius}%)
            <input type="range" min={0} max={8} step={0.5} value={radius} onChange={(e) => setRadius(Number(e.target.value))} />
          </label>
          <div className="field-grid">
            <label>
              Background
              <input type="color" value={background} disabled={transparent} onChange={(e) => setBackground(e.target.value)} />
            </label>
            <label className="check">
              <input type="checkbox" checked={transparent} onChange={(e) => toggleTransparent(e.target.checked)} /> Transparent
            </label>
          </div>
          <button type="button" className="btn btn-ghost btn-sm" disabled={list.items.length < 2} onClick={shuffle}>
            Shuffle the photos
          </button>

          <h2 className="panel-title">Output</h2>
          <div className="field-stack">
            <label>
              Width
              <select className="text-input" value={width} onChange={(e) => setWidth(Number(e.target.value))}>
                {WIDTHS.map((w) => (
                  <option key={w} value={w}>
                    {w} px
                  </option>
                ))}
              </select>
            </label>
            <FormatSelect value={format} onChange={setFormat} keep={false} formats={transparent ? ['png', 'webp', 'avif'] : ['jpg', 'png', 'webp', 'avif']} />
            {format !== 'png' && <QualityField value={quality} onChange={setQuality} />}
          </div>
        </aside>
      </div>

      <ErrorNotice error={flow.error} />
      {flow.saved && <ResultCard files={flow.saved} onDismiss={flow.dismiss} onContinue={(f) => openInTool('photo-editor', f.path)} />}
      <div className="action-bar">
        <span className="muted small">{enough && preview ? `${paths.length} photos · ${preview.full_width} × ${preview.full_height} px` : ''}</span>
        <JobProgressBar busy={job.busy} progress={job.progress} label="Making the collage…" />
        <button type="button" className="btn btn-primary" disabled={!enough || flow.busy || job.busy} onClick={save}>
          {job.busy ? 'Saving…' : 'Save collage…'}
        </button>
      </div>
    </section>
  )
}
