/**
 * Typed bridge to the Python backend (backend/toolbox/api.py).
 *
 * pywebview injects `window.pywebview.api` and fires `pywebviewready` once
 * every Python method is callable. Each method returns a Promise; a Python
 * exception rejects it with the exception message.
 *
 * When you add a public method to `Api` in api.py, add it to `PyApi` here.
 */

export type BridgeState = 'connecting' | 'connected' | 'unavailable'

export interface SystemInfo {
  app_name: string
  app_version: string
  os: string
  os_version: string
  machine: string
  cpu_count: number
  python_version: string
  python_implementation: string
  frozen: boolean
}

export interface FsEntry {
  name: string
  path: string
  is_dir: boolean
  size: number | null
  /** Seconds since the epoch. */
  modified: number | null
  hidden: boolean
  ext: string
}

export interface Crumb {
  name: string
  path: string
}

export interface DirListing {
  path: string
  name: string
  parent: string | null
  crumbs: Crumb[]
  entries: FsEntry[]
  truncated: boolean
}

export interface QuickLocation {
  kind: 'home' | 'desktop' | 'documents' | 'downloads' | 'drive'
  label: string
  path: string
}

export interface PinnedFolder {
  path: string
  name: string
  exists: boolean
}

export interface Preferences {
  show_hidden: boolean
  browser_root: string | null
  sidebar_width: number
  preview_open: boolean
  preview_width: number
  /** Record each tool run in the activity history. */
  history_enabled: boolean
}

/** One tool run in the activity history (backend/toolbox/services/history.py). */
export interface HistoryEntry {
  id: number
  /** Unix time, seconds. */
  started_at: number
  duration_ms: number
  /** API method, e.g. "pdf_merge". */
  action: string
  /** The tool's name, e.g. "Merge PDF". */
  label: string
  status: 'ok' | 'error'
  error: string | null
  inputs: { path: string; name: string }[]
  /** `exists` is false once the file has been moved or deleted. */
  outputs: { path: string; name: string; size: number | null; exists: boolean }[]
}

export interface HistoryPage {
  entries: HistoryEntry[]
  /** More, older entries: ask again with `before_id` = the last entry's id. */
  more: boolean
  enabled: boolean
}

export interface FolderSummary {
  folders: number
  files: number
  /** Bytes in the files directly inside (not recursive). */
  total_size: number
  types: { ext: string; count: number }[]
  latest: { name: string; modified: number } | null
  truncated: boolean
}

export interface ImagePreview {
  data_url: string
  width: number | null
  height: number | null
  format: string | null
  mode: string | null
  frames: number
}

export interface TextPreview {
  content: string
  truncated: boolean
  encoding: string
  line_endings: 'CRLF' | 'LF'
  lines: number
}

export interface TablePreview {
  rows: string[][]
  columns: number
  truncated: boolean
  delimiter: string
  encoding: string
}

export interface FilePreview {
  path: string
  name: string
  is_dir: boolean
  size: number | null
  modified: number
  created: number
  ext: string
  kind: 'folder' | 'pdf' | 'image' | 'text' | 'table' | 'file'
  error?: string
  folder?: FolderSummary
  pdf?: PdfInfo
  image?: ImagePreview
  text?: TextPreview
  table?: TablePreview
}

export interface AppSettings extends Preferences {
  pinned: PinnedFolder[]
}

export interface TextFile {
  path: string
  name: string
  text: string
}

export interface PdfPageInfo {
  /** Points, as displayed (after the page's own rotation). */
  width: number
  height: number
  rotation: number
}

export interface PdfInfo {
  path: string
  name: string
  size: number
  mtime: number
  page_count: number
  pages: PdfPageInfo[]
  title: string | null
}

export interface SavedPdf {
  path: string
  name: string
  size: number
  page_count: number
}

export interface Margins {
  top: number
  right: number
  bottom: number
  left: number
}

export type SplitMode = 'ranges' | 'every' | 'extract' | 'extract_each'

export interface OrganizeItem {
  source?: string
  index?: number
  rotate?: number
  blank?: boolean
  width?: number
  height?: number
}

export interface PageNumberOptions {
  position: string
  template: string
  start: number
  first_page: number
  last_page: number | null
  font_size: number
  margin: number
  color: string
  mirror: boolean
}

export type OfficeKind = 'word' | 'excel' | 'powerpoint'

export interface ConversionEngines {
  office: Record<OfficeKind, boolean>
  /** Path to soffice, or null. */
  libreoffice: string | null
}

export interface ConvertedPdf extends SavedPdf {
  engine?: 'office' | 'libreoffice'
}

export interface ImageThumb {
  path: string
  name: string
  data_url?: string
  width?: number
  height?: number
  /** Frames in a multi-page TIFF. */
  pages?: number
  /** File size in bytes. */
  size?: number
  error?: string
}

export interface ImageInfo {
  path: string
  name: string
  size: number
  mtime: number
  /** Upright (EXIF-rotated) pixel size. */
  width: number
  height: number
  format: string
  mode: string
  alpha: boolean
  frames: number
}

export interface ImageView extends ImageInfo {
  data_url: string
}

/** A rendered preview (data URL) and its pixel size. */
export interface RenderedImage {
  data_url: string
  width: number
  height: number
  device?: string
}

export interface SavedImage extends SavedFile {
  before?: number
  after?: number
  kept_original?: boolean
  device?: string
  faces?: number
  truncated?: boolean
}

export type ImageFormat = 'jpg' | 'png' | 'webp' | 'avif' | 'gif' | 'bmp' | 'tiff'

export interface AiModelStatus {
  title: string
  size: number
  license: string
  source: string
  installed: boolean
}

export interface FaceBox {
  x: number
  y: number
  w: number
  h: number
}

export interface ImagePdfOptions {
  page_size: 'fit' | 'a4' | 'letter' | 'legal' | 'a3' | 'a5'
  orientation: 'auto' | 'portrait' | 'landscape'
  margin: 'none' | 'small' | 'large'
  fit: 'contain' | 'fill'
}

export interface WebPrintOptions {
  page_size: 'a4' | 'letter' | 'legal' | 'a3' | 'a5'
  orientation: 'portrait' | 'landscape'
  margin: 'none' | 'narrow' | 'normal' | 'wide'
  /** Percent, 10-200. */
  scale: number
  backgrounds: boolean
  header_footer: boolean
  /** Seconds to wait after loading (web pages). */
  wait: number
  /** Scroll through the page first so lazy content loads. */
  scroll: boolean
}

/** A file written by a tool (PDF or not). */
export interface SavedFile {
  path: string
  name: string
  size: number
  page_count?: number
  /** Images: pixel size. */
  width?: number
  height?: number
}

export interface JobProgress {
  done: number
  total: number
  message: string
}

export interface LatexMessage {
  kind: 'error' | 'warning'
  message: string
  line: number | null
  file: string
}

export interface LatexResult {
  ok: boolean
  pdf: string | null
  engine: string
  seconds: number
  messages: LatexMessage[]
  log: string
}

export interface LatexStatus {
  state: 'unknown' | 'missing' | 'downloading' | 'installing' | 'warming' | 'ready' | 'error'
  progress: number
  error: string | null
  engine: string | null
  engines: Record<string, string | null>
}

export interface LatexDoc {
  path: string
  text: string
  untitled: boolean
}

export interface TextLine {
  text: string
  x: number
  y: number
  w: number
  h: number
  size: number
  bold: boolean
  family: 'sans' | 'serif' | 'mono'
}

export interface FormWidget {
  page: number
  x: number
  y: number
  w: number
  h: number
  state: string | null
}

export interface FormField {
  name: string
  type: 'text' | 'multiline' | 'checkbox' | 'radio' | 'dropdown' | 'listbox' | 'signature' | 'button'
  value: string
  options: string[]
  required: boolean
  readonly: boolean
  widgets: FormWidget[]
}

export interface OcrEngines {
  tesseract: { path: string | null; languages: string[] }
  windows: { languages: string[] }
}

export interface SecurityInfo {
  path: string
  name: string
  size: number
  encrypted: boolean
  needs_password: boolean
  permissions: Record<string, boolean>
  page_count?: number
}

export interface CertInfo {
  subject: string
  issuer: string
  self_signed: boolean
  valid_from: string
  valid_until: string
  expired: boolean
}

export interface SignatureStatus {
  field: string
  /** Common name of the signing certificate. */
  signer: string | null
  /** Full subject, e.g. "Common Name: …, Country: …". */
  signer_details?: string | null
  signed_at: string | null
  intact: boolean
  valid: boolean
  trusted: boolean
  covers_whole_file: boolean
  reason?: string | null
  location?: string | null
  error: string | null
}

export interface PdfHealth {
  path: string
  name: string
  size: number
  healthy: boolean
  pages: number | null
  issues: string[]
}

export interface PrinterInfo {
  name: string
  default: boolean
  /** False while a slow (e.g. network) printer's capabilities are still being read. */
  ready: boolean
  duplex: boolean
  color: boolean
  papers: { id: number; name: string; w_mm: number; h_mm: number }[]
}

export interface PyApi {
  ping(): Promise<string>
  get_system_info(): Promise<SystemInfo>

  get_settings(): Promise<AppSettings>
  set_preference(key: keyof Preferences, value: Preferences[keyof Preferences]): Promise<void>
  pin_folder(path: string, index: number | null): Promise<PinnedFolder[]>
  unpin_folder(path: string): Promise<PinnedFolder[]>

  history_list(query: string, limit: number, beforeId: number | null): Promise<HistoryPage>
  history_delete(ids: number[]): Promise<void>
  history_clear(): Promise<void>

  get_locations(): Promise<QuickLocation[]>
  resolve_dir(path: string): Promise<string>
  list_dir(path: string, showHidden: boolean): Promise<DirListing>
  open_path(path: string): Promise<void>
  /** One of the project's pages, in the default browser (backend/toolbox/__init__.py LINKS). */
  open_link(name: 'website' | 'docs' | 'source' | 'issues' | 'license'): Promise<void>
  reveal_path(path: string): Promise<void>
  read_text_file(path: string): Promise<TextFile>
  preview_file(path: string): Promise<FilePreview>
  pick_file(): Promise<string | null>
  pick_folder(directory: string): Promise<string | null>
  pick_pdfs(multiple: boolean): Promise<string[]>
  pick_files(label: string, extensions: string[], multiple: boolean): Promise<string[]>
  save_pdf_dialog(suggestedPath: string): Promise<string | null>

  pdf_info(path: string): Promise<PdfInfo>
  pdf_thumbnails(path: string, indexes: number[], width: number): Promise<(string | null)[]>
  pdf_detect_margins(path: string, index: number): Promise<Margins>
  pdf_split_plan(pageCount: number, mode: SplitMode, value: string): Promise<number[][]>
  pdf_suggest_output(path: string, suffix: string): Promise<string>
  pdf_merge(items: { path: string; pages: string }[], output: string, bookmarks: boolean): Promise<SavedPdf>
  pdf_split(path: string, outputDir: string, mode: SplitMode, value: string): Promise<{ files: SavedPdf[]; folder: string }>
  pdf_organize(output: string, sources: Record<string, string>, pages: OrganizeItem[]): Promise<SavedPdf>
  pdf_rotate(path: string, output: string, rotations: number[]): Promise<SavedPdf>
  pdf_crop(path: string, output: string, margins: Margins, pages: number[] | null): Promise<SavedPdf>
  pdf_number_pages(path: string, output: string, options: PageNumberOptions): Promise<SavedPdf>

  conversion_engines(): Promise<ConversionEngines>
  convert_office(
    kind: OfficeKind,
    path: string,
    outputDir: string | null,
    engine: 'auto' | 'office' | 'libreoffice',
    options: Record<string, unknown>,
  ): Promise<ConvertedPdf>
  suggest_pdf_path(source: string | null, hint: string): Promise<string>
  /** Like suggest_pdf_path, for any extension; `source` is a local file, never a web address. */
  suggest_output_path(source: string | null, hint: string, ext: string): Promise<string>
  image_thumbnails(paths: string[], size: number): Promise<ImageThumb[]>
  images_to_pdf(items: { path: string; rotate: number }[], output: string, options: ImagePdfOptions): Promise<SavedPdf>
  images_to_pdfs(items: { path: string; rotate: number }[], outputDir: string | null, options: ImagePdfOptions): Promise<SavedPdf[]>
  markdown_html(text: string, baseDir: string | null, theme: string, title: string): Promise<string>
  markdown_to_pdf(
    text: string,
    baseDir: string | null,
    theme: string,
    title: string,
    output: string,
    options: WebPrintOptions,
  ): Promise<SavedPdf>
  html_to_pdf(kind: 'url' | 'file' | 'code', value: string, output: string, options: WebPrintOptions): Promise<SavedPdf>

  save_file_dialog(suggestedPath: string, label: string, extensions: string[]): Promise<string | null>
  job_progress(jobId: string): Promise<JobProgress | null>
  components_status(): Promise<{ latex: LatexStatus }>
  components_retry(): Promise<void>

  frompdf_suggest(path: string, ext: string): Promise<string>
  pdf_to_word(path: string, output: string, engine: string, fmt: string, jobId: string): Promise<SavedFile & { engine: string }>
  pdf_to_powerpoint(path: string, output: string, dpi: number, notes: boolean, jobId: string): Promise<SavedFile & { slides: number }>
  pdf_to_excel(path: string, output: string, pages: string, detection: string, jobId: string): Promise<SavedFile & { tables: number }>
  pdf_to_images(
    path: string,
    outputDir: string | null,
    pages: string,
    fmt: string,
    dpi: number,
    quality: number,
    mode: string,
    jobId: string,
  ): Promise<{ files: SavedFile[]; folder: string }>
  pdf_to_markdown(path: string, output: string, pages: string, pageBreaks: boolean, jobId: string): Promise<SavedFile>
  pdf_markdown_preview(path: string, pages: string): Promise<string>

  pdf_text_lines(path: string, page: number): Promise<TextLine[]>
  pdf_apply_edits(path: string, output: string, objects: Record<string, unknown>[]): Promise<SavedPdf>
  ocr_engines(): Promise<OcrEngines>
  ocr_pdf(
    path: string,
    output: string,
    engine: string,
    language: string,
    dpi: number,
    skipText: boolean,
    pages: string,
    jobId: string,
  ): Promise<SavedPdf & { engine: string; pages_recognised: number; pages_skipped: number; words: number }>
  form_fields(path: string): Promise<FormField[]>
  form_fill(path: string, output: string, values: Record<string, string | boolean>, flatten: boolean): Promise<SavedPdf>
  form_add_fields(path: string, output: string, specs: Record<string, unknown>[]): Promise<SavedPdf>
  pdf_watermark(path: string, output: string, options: Record<string, unknown>): Promise<SavedPdf>
  pdf_watermark_preview(path: string, options: Record<string, unknown>, page: number): Promise<PdfInfo>

  pdf_security_info(path: string): Promise<SecurityInfo>
  pdf_protect(
    path: string,
    output: string,
    userPassword: string,
    ownerPassword: string,
    permissions: Record<string, boolean>,
    algorithm: string,
  ): Promise<SavedPdf>
  pdf_unlock(path: string, output: string, password: string): Promise<SavedPdf>
  cert_suggest_path(name: string): Promise<string>
  cert_create(output: string, password: string, name: string, email: string, organization: string, country: string): Promise<{ path: string; name: string; subject: string; valid_until: string }>
  cert_info(path: string, password: string): Promise<CertInfo>
  pdf_sign(
    path: string,
    output: string,
    certificate: string,
    password: string,
    reason: string,
    location: string,
    contact: string,
    visible: { page: number; x: number; y: number; w: number; h: number } | null,
  ): Promise<SavedPdf & { signer: string }>
  pdf_verify_signatures(path: string): Promise<SignatureStatus[]>
  pdf_compress(path: string, output: string, level: string, stripMetadata: boolean, jobId: string): Promise<SavedPdf & { before: number; after: number; images_recompressed: number; already_optimal?: boolean }>
  pdf_analyze(path: string): Promise<PdfHealth>
  pdf_repair(path: string, output: string): Promise<SavedPdf & { method: string }>

  printers(): Promise<PrinterInfo[]>
  print_preview(path: string, options: Record<string, unknown>): Promise<PdfInfo & { sheets: number; source_pages: number }>
  print_pdf(path: string, printer: string, options: Record<string, unknown>, jobId: string): Promise<{ printer: string; sheets: number; copies: number }>
  print_save_pdf(path: string, output: string, options: Record<string, unknown>): Promise<SavedPdf>

  latex_status(): Promise<LatexStatus>
  latex_templates(): Promise<Record<string, string>>
  latex_new_document(template: string): Promise<LatexDoc>
  latex_read(path: string): Promise<LatexDoc>
  latex_save(path: string, text: string): Promise<{ path: string; saved: boolean }>
  latex_compile(path: string, engine: string): Promise<LatexResult>

  image_info(path: string): Promise<ImageInfo>
  image_preview(path: string, maxSide: number): Promise<ImageView>
  image_formats(): Promise<{ inputs: string[]; outputs: Record<ImageFormat, { ext: string; alpha: boolean; lossy: boolean }>; heif: boolean }>
  image_suggest(path: string, suffix: string, fmt: string): Promise<string>
  image_compress(paths: string[], folder: string | null, options: Record<string, unknown>, jobId: string): Promise<SavedImage[]>
  image_compress_estimate(path: string, options: Record<string, unknown>): Promise<{ before: number; after: number; format: string; width: number; height: number }>
  image_resize(paths: string[], folder: string | null, options: Record<string, unknown>, jobId: string): Promise<SavedImage[]>
  image_convert(paths: string[], folder: string | null, options: Record<string, unknown>, jobId: string): Promise<SavedImage[]>
  image_crop(path: string, output: string, rect: { x: number; y: number; w: number; h: number }, options: Record<string, unknown>): Promise<SavedImage>
  image_rotate(items: { path: string; turns: number; flip_h: boolean; flip_v: boolean }[], folder: string | null, options: Record<string, unknown>, jobId: string): Promise<SavedImage[]>
  html_to_image(kind: 'url' | 'file' | 'code', value: string, output: string, options: Record<string, unknown>): Promise<SavedImage>
  ai_models(): Promise<Record<'upscale' | 'background', AiModelStatus>>
  ai_upscale(path: string, output: string, scale: number, options: Record<string, unknown>, jobId: string): Promise<SavedImage>
  ai_upscale_limit(scale: number): Promise<number>
  ai_remove_bg_preview(path: string, options: Record<string, unknown>, jobId: string): Promise<RenderedImage>
  ai_remove_bg(path: string, output: string, options: Record<string, unknown>, jobId: string): Promise<SavedImage>
  faces_detect(path: string): Promise<FaceBox[]>
  faces_preview(path: string, faces: FaceBox[], options: Record<string, unknown>): Promise<RenderedImage>
  faces_blur(path: string, output: string, faces: FaceBox[], options: Record<string, unknown>): Promise<SavedImage>
  photo_preview(path: string, edits: Record<string, unknown>, maxSide: number): Promise<RenderedImage>
  photo_save(path: string, output: string, edits: Record<string, unknown>, options: Record<string, unknown>): Promise<SavedImage>
  image_watermark_preview(path: string, options: Record<string, unknown>, maxSide: number): Promise<RenderedImage>
  image_watermark(paths: string[], folder: string | null, options: Record<string, unknown>, jobId: string): Promise<SavedImage[]>
}

/** Typed wrapper so the value must match the preference's type. */
export function setPreference<K extends keyof Preferences>(key: K, value: Preferences[K]): Promise<void> {
  return call('set_preference', key, value)
}

declare global {
  interface Window {
    pywebview?: { api: PyApi }
  }
  interface WindowEventMap {
    pywebviewready: Event
  }
}

export class BridgeUnavailableError extends Error {
  constructor() {
    super(
      'The Python backend is not connected. Start the app with `python scripts/dev.py` ' +
        'rather than opening the Vite URL in a regular browser.',
    )
    this.name = 'BridgeUnavailableError'
  }
}

const READY_TIMEOUT_MS = 4000

let apiPromise: Promise<PyApi> | undefined

function injectedApi(): PyApi | undefined {
  const api = window.pywebview?.api
  return typeof api?.ping === 'function' ? api : undefined
}

/** Resolves once pywebview has injected the API; rejects if it never does. */
export function getApi(): Promise<PyApi> {
  apiPromise ??= new Promise<PyApi>((resolve, reject) => {
    const ready = injectedApi()
    if (ready) {
      resolve(ready)
      return
    }
    const onReady = () => {
      window.clearTimeout(timer)
      resolve(window.pywebview!.api)
    }
    const timer = window.setTimeout(() => {
      window.removeEventListener('pywebviewready', onReady)
      reject(new BridgeUnavailableError())
    }, READY_TIMEOUT_MS)
    window.addEventListener('pywebviewready', onReady, { once: true })
  })
  return apiPromise
}

/** Call a Python method by name, with typed arguments and result. */
export async function call<K extends keyof PyApi>(
  method: K,
  ...args: Parameters<PyApi[K]>
): Promise<Awaited<ReturnType<PyApi[K]>>> {
  const api = await getApi()
  const fn = api[method] as (...a: Parameters<PyApi[K]>) => ReturnType<PyApi[K]>
  try {
    return await fn(...args)
  } catch (err) {
    throw toError(err)
  }
}

export function toError(err: unknown): Error {
  if (err instanceof Error) return err
  if (err && typeof err === 'object' && 'message' in err) return new Error(String(err.message))
  return new Error(String(err))
}
