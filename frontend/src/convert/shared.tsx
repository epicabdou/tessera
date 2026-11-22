import { useState, type ReactNode } from 'react'
import { call, toError, type WebPrintOptions } from '../lib/bridge'
import { cls } from '../lib/cls'

const PAGE_SIZES: [WebPrintOptions['page_size'], string][] = [
  ['a4', 'A4'],
  ['letter', 'Letter'],
  ['legal', 'Legal'],
  ['a3', 'A3'],
  ['a5', 'A5'],
]

const MARGINS: [WebPrintOptions['margin'], string][] = [
  ['none', 'None'],
  ['narrow', 'Narrow (6 mm)'],
  ['normal', 'Normal (12 mm)'],
  ['wide', 'Wide (25 mm)'],
]

/** Page setup for HTML and Markdown printing. `web` adds the options that only matter for live pages. */
export function PrintOptions({
  value,
  onChange,
  web = false,
}: {
  value: WebPrintOptions
  onChange: (v: WebPrintOptions) => void
  web?: boolean
}) {
  const set = (patch: Partial<WebPrintOptions>) => onChange({ ...value, ...patch })
  return (
    <div className="opt-grid">
      <label>
        Page size
        <select className="text-input" value={value.page_size} onChange={(e) => set({ page_size: e.target.value as WebPrintOptions['page_size'] })}>
          {PAGE_SIZES.map(([id, label]) => (
            <option key={id} value={id}>
              {label}
            </option>
          ))}
        </select>
      </label>
      <label>
        Orientation
        <select className="text-input" value={value.orientation} onChange={(e) => set({ orientation: e.target.value as WebPrintOptions['orientation'] })}>
          <option value="portrait">Portrait</option>
          <option value="landscape">Landscape</option>
        </select>
      </label>
      <label>
        Margins
        <select className="text-input" value={value.margin} onChange={(e) => set({ margin: e.target.value as WebPrintOptions['margin'] })}>
          {MARGINS.map(([id, label]) => (
            <option key={id} value={id}>
              {label}
            </option>
          ))}
        </select>
      </label>
      <label>
        Scale (%)
        <input
          className="text-input num"
          type="number"
          min={10}
          max={200}
          step={5}
          value={value.scale}
          onChange={(e) => set({ scale: Number(e.target.value) })}
        />
      </label>
      {web && (
        <label>
          Wait after loading (s)
          <input className="text-input num" type="number" min={0} max={30} value={value.wait} onChange={(e) => set({ wait: Number(e.target.value) })} />
        </label>
      )}
      <label className="check span-2">
        <input type="checkbox" checked={value.backgrounds} onChange={(e) => set({ backgrounds: e.target.checked })} />
        Print background colours and images
      </label>
      <label className="check span-2">
        <input type="checkbox" checked={value.header_footer} onChange={(e) => set({ header_footer: e.target.checked })} />
        Header and footer (title, date, page numbers)
      </label>
      {web && (
        <label className="check span-2">
          <input type="checkbox" checked={value.scroll} onChange={(e) => set({ scroll: e.target.checked })} />
          Scroll through the page first, so lazy-loaded images appear
        </label>
      )}
    </div>
  )
}

/** "Next to each file" or "In this folder: …". `folder` is null for next-to-each. */
export function OutputChooser({
  folder,
  onChange,
  what = 'file',
}: {
  folder: string | null
  onChange: (folder: string | null) => void
  what?: string
}) {
  const [error, setError] = useState<string | null>(null)
  async function choose() {
    try {
      const picked = await call('pick_folder', folder ?? '')
      if (picked) onChange(picked)
    } catch (err) {
      setError(toError(err).message)
    }
  }
  return (
    <div className="output-chooser" role="radiogroup" aria-label="Where to save">
      <label className="check">
        <input type="radio" checked={folder === null} onChange={() => onChange(null)} /> Save next to each {what}
      </label>
      <label className="check">
        <input type="radio" checked={folder !== null} onChange={choose} /> Save in a folder
        {folder !== null && (
          <span className="mono small output-folder" title={folder}>
            {folder}
          </span>
        )}
        <button type="button" className="btn btn-ghost btn-sm" onClick={choose}>
          Choose…
        </button>
      </label>
      {error && <span className="field-error small">{error}</span>}
    </div>
  )
}

export function EmptyDrop({ icon, children, over }: { icon: ReactNode; children: ReactNode; over?: boolean }) {
  return (
    <div className={cls('conv-empty', over && 'is-over')}>
      {icon}
      <span>{children}</span>
    </div>
  )
}
