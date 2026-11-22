/**
 * Every tool in the app, grouped as the app groups them (frontend/src/tools/registry.tsx).
 * Used by the home page and to link into the docs: each category has a docs page, and each
 * tool is a "## <label>" section on it, so its anchor is slug(label).
 */

export interface Tool {
  /** Same id as in the app's registry. */
  id: string
  label: string
  hint: string
}

export interface Category {
  /** Docs page: /docs/<id>. Same id as the app's category. */
  id: string
  label: string
  section: 'Documents' | 'Images'
  tools: Tool[]
}

export const CATEGORIES: Category[] = [
  {
    id: 'pdf-pages',
    label: 'Combine, split & pages',
    section: 'Documents',
    tools: [
      { id: 'pdf-merge', label: 'Merge PDF', hint: 'Combine several PDFs into one' },
      { id: 'pdf-split', label: 'Split PDF', hint: 'Split by ranges, every N pages, or extract pages' },
      { id: 'pdf-organize', label: 'Organize PDF', hint: 'Reorder, rotate, delete or insert pages' },
      { id: 'pdf-rotate', label: 'Rotate PDF', hint: 'Turn some or all pages' },
      { id: 'pdf-crop', label: 'Crop PDF', hint: 'Trim margins or crop to a box' },
      { id: 'pdf-numbers', label: 'Page numbers', hint: 'Add and format page numbering' },
    ],
  },
  {
    id: 'to-pdf',
    label: 'Convert to PDF',
    section: 'Documents',
    tools: [
      { id: 'to-pdf-word', label: 'Word to PDF', hint: 'DOC, DOCX, RTF, ODT' },
      { id: 'to-pdf-powerpoint', label: 'PowerPoint to PDF', hint: 'Slides, notes pages or handouts' },
      { id: 'to-pdf-excel', label: 'Excel to PDF', hint: 'XLS, XLSX, CSV, ODS' },
      { id: 'to-pdf-images', label: 'JPG to PDF', hint: 'JPG, PNG, TIFF and more into a PDF' },
      { id: 'to-pdf-html', label: 'HTML to PDF', hint: 'A web page, an HTML file or pasted code' },
      { id: 'to-pdf-markdown', label: 'Markdown to PDF', hint: 'Markdown with tables, code and images' },
    ],
  },
  {
    id: 'from-pdf',
    label: 'Convert from PDF',
    section: 'Documents',
    tools: [
      { id: 'from-pdf-word', label: 'PDF to Word', hint: 'Editable DOCX or DOC' },
      { id: 'from-pdf-powerpoint', label: 'PDF to PowerPoint', hint: 'One slide per page' },
      { id: 'from-pdf-excel', label: 'PDF to Excel', hint: 'Tables into spreadsheets' },
      { id: 'from-pdf-images', label: 'PDF to JPG', hint: 'Pages or embedded images as files' },
      { id: 'from-pdf-markdown', label: 'PDF to Markdown', hint: 'Headings, lists and tables as .md' },
    ],
  },
  {
    id: 'edit',
    label: 'Edit, forms & OCR',
    section: 'Documents',
    tools: [
      { id: 'edit-pdf', label: 'Edit PDF', hint: 'Change text; add images, shapes; redact' },
      { id: 'ocr-pdf', label: 'OCR PDF', hint: 'Make scans searchable and selectable' },
      { id: 'pdf-forms', label: 'PDF Forms', hint: 'Fill in forms or design new fields' },
      { id: 'watermark', label: 'Watermark PDF', hint: 'Stamp text or an image on pages' },
    ],
  },
  {
    id: 'security',
    label: 'Security, signing & size',
    section: 'Documents',
    tools: [
      { id: 'protect-pdf', label: 'Protect PDF', hint: 'Passwords, restrictions, or unlock' },
      { id: 'sign-pdf', label: 'Sign PDF', hint: 'Handwritten or certificate signatures' },
      { id: 'compress-pdf', label: 'Compress PDF', hint: 'Make the file smaller' },
      { id: 'repair-pdf', label: 'Repair PDF', hint: 'Recover damaged files' },
    ],
  },
  {
    id: 'print',
    label: 'Printing',
    section: 'Documents',
    tools: [{ id: 'print-pdf', label: 'Advanced Print', hint: 'Duplex, booklets, n-up, crop marks' }],
  },
  {
    id: 'latex',
    label: 'LaTeX',
    section: 'Documents',
    tools: [{ id: 'latex', label: 'LaTeX editor', hint: 'Write LaTeX with a live PDF preview' }],
  },
  {
    id: 'img-optimize',
    label: 'Format & size',
    section: 'Images',
    tools: [
      { id: 'img-compress', label: 'Compress Image', hint: 'Smaller files for web, email or storage' },
      { id: 'img-resize', label: 'Resize Image', hint: 'Scale by pixels, percentage or longest side' },
      { id: 'img-to-jpg', label: 'Convert to JPG', hint: 'PNG, WebP, HEIC and more into JPG' },
      { id: 'img-from-jpg', label: 'Convert from JPG', hint: 'JPG into PNG, WebP, AVIF or PDF' },
    ],
  },
  {
    id: 'img-layout',
    label: 'Crop, rotate & capture',
    section: 'Images',
    tools: [
      { id: 'img-crop', label: 'Crop Image', hint: 'Trim edges or frame an aspect ratio' },
      { id: 'img-rotate', label: 'Rotate Image', hint: 'Rotate or flip, one or many images' },
      { id: 'html-to-image', label: 'HTML to Image', hint: 'Screenshot a web page or HTML/CSS' },
    ],
  },
  {
    id: 'img-ai',
    label: 'AI enhancements',
    section: 'Images',
    tools: [
      { id: 'img-upscale', label: 'Upscale Image', hint: 'AI super-resolution, 2× or 4×' },
      { id: 'img-remove-bg', label: 'Remove background', hint: 'Transparent or new background' },
      { id: 'img-blur-faces', label: 'Blur face', hint: 'Find and blur faces for privacy' },
    ],
  },
  {
    id: 'img-edit',
    label: 'Edit & brand',
    section: 'Images',
    tools: [
      { id: 'photo-editor', label: 'Photo editor', hint: 'Light, colour, filters, text, drawing, logos' },
      { id: 'img-watermark', label: 'Watermark Image', hint: 'Text or logo on many images' },
    ],
  },
]

export const TOOL_COUNT = CATEGORIES.reduce((n, c) => n + c.tools.length, 0)

/** VitePress's heading anchor for a tool's "## <label>" section. */
export function slug(label: string): string {
  return label
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-|-$/g, '')
}

export const docsLink = (c: Category, t?: Tool) => `/docs/${c.id}${t ? `#${slug(t.label)}` : ''}`
