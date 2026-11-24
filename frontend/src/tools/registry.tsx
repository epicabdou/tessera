import type { ComponentType, ReactNode } from 'react'
import {
  BrushIcon,
  CollageIcon,
  CompressIcon,
  ConvertIcon,
  CutoutIcon,
  FaceIcon,
  ResizeIcon,
  SlidersIcon,
  SparkleIcon,
  UpscaleIcon,
  CropIcon,
  DocumentsIcon,
  FileInIcon,
  FileOutIcon,
  FormIcon,
  GlobeIcon,
  ImageIcon,
  LockIcon,
  MarkdownIcon,
  MergeIcon,
  NumbersIcon,
  PagesIcon,
  PencilIcon,
  PrinterIcon,
  RotateCwIcon,
  ScanTextIcon,
  SheetIcon,
  ShieldIcon,
  SigmaIcon,
  SignatureIcon,
  SlidesIcon,
  SplitIcon,
  StampIcon,
  WordIcon,
  WrenchIcon,
} from '../components/icons'
import { HtmlToPdf } from '../convert/HtmlToPdf'
import { ImagesToPdf } from '../convert/ImagesToPdf'
import { MarkdownToPdf } from '../convert/MarkdownToPdf'
import { ExcelToPdf, PowerPointToPdf, WordToPdf } from '../convert/OfficeToPdf'
import '../convert/convert.css'
import { EditPdf } from '../editing/EditPdf'
import { OcrPdf } from '../editing/OcrPdf'
import { PdfForms } from '../editing/PdfForms'
import { Watermark } from '../editing/Watermark'
import '../editing/editing.css'
import { BlurFaces, RemoveBackground, UpscaleImage } from '../images/AiTools'
import { PhotoEditor, WatermarkImage } from '../images/EditTools'
import { PhotoCollage } from '../images/CollageTool'
import { CropImage, HtmlToImage, RotateImage } from '../images/FrameTools'
import '../images/images.css'
import { CompressImage, ConvertFromJpg, ConvertToJpg, ResizeImage } from '../images/OptimizeTools'
import { PdfToExcel, PdfToImages, PdfToMarkdown, PdfToPowerPoint, PdfToWord } from '../frompdf/FromPdfTools'
import { LatexEditor } from '../latex/LatexEditor'
import '../latex/latex.css'
import type { CategoryId, ToolId } from '../lib/workspace'
import { CropPdf } from '../pdf/tools/CropPdf'
import { MergePdf } from '../pdf/tools/MergePdf'
import { OrganizePdf } from '../pdf/tools/OrganizePdf'
import { PageNumbers } from '../pdf/tools/PageNumbers'
import { RotatePdf } from '../pdf/tools/RotatePdf'
import { SplitPdf } from '../pdf/tools/SplitPdf'
import { PrintPdf } from '../print/PrintPdf'
import { CompressPdf } from '../security/CompressPdf'
import { ProtectPdf } from '../security/ProtectPdf'
import { RepairPdf } from '../security/RepairPdf'
import { SignPdf } from '../security/SignPdf'

export interface ToolDef {
  id: ToolId
  label: string
  icon: ReactNode
  component: ComponentType
  /** One line for the command palette. */
  hint: string
}

export type SectionId = 'docs' | 'images'

export interface SectionDef {
  id: SectionId
  label: string
  icon: ReactNode
}

/** Top-level switch in the top bar: each category belongs to one section. */
export const SECTIONS: SectionDef[] = [
  { id: 'docs', label: 'Documents', icon: <DocumentsIcon size={15} /> },
  { id: 'images', label: 'Images', icon: <ImageIcon size={15} /> },
]

export interface CategoryDef {
  id: CategoryId
  section: SectionId
  /** Full name (tooltip, tool strip). */
  label: string
  /** Tab label. */
  short: string
  icon: ReactNode
  tools: ToolDef[]
}

/** Add a category or tool here; App builds the navigation (and tool search) from this list. */
export const CATEGORIES: CategoryDef[] = [
  {
    id: 'pdf-pages',
    section: 'docs',
    label: 'Combine, Split & Page Management',
    short: 'Pages',
    icon: <PagesIcon size={15} />,
    tools: [
      { id: 'pdf-merge', label: 'Merge PDF', icon: <MergeIcon size={15} />, component: MergePdf, hint: 'Combine several PDFs into one' },
      { id: 'pdf-split', label: 'Split PDF', icon: <SplitIcon size={15} />, component: SplitPdf, hint: 'Split by ranges, every N pages, or extract pages' },
      { id: 'pdf-organize', label: 'Organize PDF', icon: <PagesIcon size={15} />, component: OrganizePdf, hint: 'Reorder, rotate, delete or insert pages' },
      { id: 'pdf-rotate', label: 'Rotate PDF', icon: <RotateCwIcon size={15} />, component: RotatePdf, hint: 'Turn some or all pages' },
      { id: 'pdf-crop', label: 'Crop', icon: <CropIcon size={15} />, component: CropPdf, hint: 'Trim margins or crop to a box' },
      { id: 'pdf-numbers', label: 'Page numbers', icon: <NumbersIcon size={15} />, component: PageNumbers, hint: 'Add and format page numbering' },
    ],
  },
  {
    id: 'to-pdf',
    section: 'docs',
    label: 'Conversion: To PDF',
    short: 'To PDF',
    icon: <FileInIcon size={15} />,
    tools: [
      { id: 'to-pdf-word', label: 'Word to PDF', icon: <DocumentsIcon size={15} />, component: WordToPdf, hint: 'DOC, DOCX, RTF, ODT' },
      { id: 'to-pdf-powerpoint', label: 'PowerPoint to PDF', icon: <SlidesIcon size={15} />, component: PowerPointToPdf, hint: 'Slides, notes pages or handouts' },
      { id: 'to-pdf-excel', label: 'Excel to PDF', icon: <SheetIcon size={15} />, component: ExcelToPdf, hint: 'XLS, XLSX, CSV, ODS' },
      { id: 'to-pdf-images', label: 'JPG to PDF', icon: <ImageIcon size={15} />, component: ImagesToPdf, hint: 'JPG, PNG, TIFF and more into a PDF' },
      { id: 'to-pdf-html', label: 'HTML to PDF', icon: <GlobeIcon size={15} />, component: HtmlToPdf, hint: 'A web page, an HTML file or pasted code' },
      { id: 'to-pdf-markdown', label: 'Markdown to PDF', icon: <MarkdownIcon size={15} />, component: MarkdownToPdf, hint: 'Markdown with tables, code and images' },
    ],
  },
  {
    id: 'from-pdf',
    section: 'docs',
    label: 'Conversion: From PDF',
    short: 'From PDF',
    icon: <FileOutIcon size={15} />,
    tools: [
      { id: 'from-pdf-word', label: 'PDF to Word', icon: <WordIcon size={15} />, component: PdfToWord, hint: 'Editable DOCX or DOC' },
      { id: 'from-pdf-powerpoint', label: 'PDF to PowerPoint', icon: <SlidesIcon size={15} />, component: PdfToPowerPoint, hint: 'One slide per page' },
      { id: 'from-pdf-excel', label: 'PDF to Excel', icon: <SheetIcon size={15} />, component: PdfToExcel, hint: 'Tables into spreadsheets' },
      { id: 'from-pdf-images', label: 'PDF to JPG', icon: <ImageIcon size={15} />, component: PdfToImages, hint: 'Pages or embedded images as files' },
      { id: 'from-pdf-markdown', label: 'PDF to Markdown', icon: <MarkdownIcon size={15} />, component: PdfToMarkdown, hint: 'Headings, lists and tables as .md' },
    ],
  },
  {
    id: 'edit',
    section: 'docs',
    label: 'Editing, Forms & Text Recognition',
    short: 'Edit & Forms',
    icon: <PencilIcon size={15} />,
    tools: [
      { id: 'edit-pdf', label: 'Edit PDF', icon: <PencilIcon size={15} />, component: EditPdf, hint: 'Change text; add images, shapes; redact' },
      { id: 'ocr-pdf', label: 'OCR PDF', icon: <ScanTextIcon size={15} />, component: OcrPdf, hint: 'Make scans searchable and selectable' },
      { id: 'pdf-forms', label: 'PDF Forms', icon: <FormIcon size={15} />, component: PdfForms, hint: 'Fill in forms or design new fields' },
      { id: 'watermark', label: 'Watermark', icon: <StampIcon size={15} />, component: Watermark, hint: 'Stamp text or an image on pages' },
    ],
  },
  {
    id: 'security',
    section: 'docs',
    label: 'Security, Signatures & Optimization',
    short: 'Security',
    icon: <ShieldIcon size={15} />,
    tools: [
      { id: 'protect-pdf', label: 'Protect PDF', icon: <LockIcon size={15} />, component: ProtectPdf, hint: 'Passwords, restrictions, or unlock' },
      { id: 'sign-pdf', label: 'Sign PDF', icon: <SignatureIcon size={15} />, component: SignPdf, hint: 'Handwritten or certificate signatures' },
      { id: 'compress-pdf', label: 'Compress PDF', icon: <CompressIcon size={15} />, component: CompressPdf, hint: 'Make the file smaller' },
      { id: 'repair-pdf', label: 'Repair PDF', icon: <WrenchIcon size={15} />, component: RepairPdf, hint: 'Recover damaged files' },
    ],
  },
  {
    id: 'print',
    section: 'docs',
    label: 'Printing & Output',
    short: 'Print',
    icon: <PrinterIcon size={15} />,
    tools: [
      { id: 'print-pdf', label: 'Advanced Print', icon: <PrinterIcon size={15} />, component: PrintPdf, hint: 'Duplex, booklets, n-up, crop marks' },
    ],
  },
  {
    id: 'latex',
    section: 'docs',
    label: 'LaTeX',
    short: 'LaTeX',
    icon: <SigmaIcon size={15} />,
    tools: [
      { id: 'latex', label: 'LaTeX editor', icon: <SigmaIcon size={15} />, component: LatexEditor, hint: 'Write LaTeX with a live PDF preview' },
    ],
  },
  {
    id: 'img-optimize',
    section: 'images',
    label: 'Format & Size Optimization',
    short: 'Optimize',
    icon: <CompressIcon size={15} />,
    tools: [
      { id: 'img-compress', label: 'Compress Image', icon: <CompressIcon size={15} />, component: CompressImage, hint: 'Smaller files for web, email or storage' },
      { id: 'img-resize', label: 'Resize Image', icon: <ResizeIcon size={15} />, component: ResizeImage, hint: 'Scale by pixels, percentage or longest side' },
      { id: 'img-to-jpg', label: 'Convert to JPG', icon: <ConvertIcon size={15} />, component: ConvertToJpg, hint: 'PNG, WebP, HEIC and more into JPG' },
      { id: 'img-from-jpg', label: 'Convert from JPG', icon: <ConvertIcon size={15} />, component: ConvertFromJpg, hint: 'JPG into PNG, WebP, AVIF or PDF' },
    ],
  },
  {
    id: 'img-layout',
    section: 'images',
    label: 'Framing, Layout & Generation',
    short: 'Frame',
    icon: <CropIcon size={15} />,
    tools: [
      { id: 'img-crop', label: 'Crop Image', icon: <CropIcon size={15} />, component: CropImage, hint: 'Trim edges or frame an aspect ratio' },
      { id: 'img-rotate', label: 'Rotate Image', icon: <RotateCwIcon size={15} />, component: RotateImage, hint: 'Rotate or flip, one or many images' },
      { id: 'img-collage', label: 'Photo collage', icon: <CollageIcon size={15} />, component: PhotoCollage, hint: 'Arrange photos in a grid, mosaic or featured layout' },
      { id: 'html-to-image', label: 'HTML to Image', icon: <GlobeIcon size={15} />, component: HtmlToImage, hint: 'Screenshot a web page or HTML/CSS' },
    ],
  },
  {
    id: 'img-ai',
    section: 'images',
    label: 'AI & Smart Enhancements',
    short: 'AI',
    icon: <SparkleIcon size={15} />,
    tools: [
      { id: 'img-upscale', label: 'Upscale Image', icon: <UpscaleIcon size={15} />, component: UpscaleImage, hint: 'AI super-resolution, 2× or 4×' },
      { id: 'img-remove-bg', label: 'Remove background', icon: <CutoutIcon size={15} />, component: RemoveBackground, hint: 'Transparent or new background' },
      { id: 'img-blur-faces', label: 'Blur face', icon: <FaceIcon size={15} />, component: BlurFaces, hint: 'Find and blur faces for privacy' },
    ],
  },
  {
    id: 'img-edit',
    section: 'images',
    label: 'Editing & Branding',
    short: 'Edit & Brand',
    icon: <BrushIcon size={15} />,
    tools: [
      { id: 'photo-editor', label: 'Photo editor', icon: <SlidersIcon size={15} />, component: PhotoEditor, hint: 'Light, colour, filters, text, drawing, logos' },
      { id: 'img-watermark', label: 'Watermark Image', icon: <StampIcon size={15} />, component: WatermarkImage, hint: 'Text or logo on many images' },
    ],
  },
]

export function categoryOf(tool: ToolId): CategoryDef {
  return CATEGORIES.find((c) => c.tools.some((t) => t.id === tool)) ?? CATEGORIES[0]
}
