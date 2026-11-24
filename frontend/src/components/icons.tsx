import type { ReactNode, SVGProps } from 'react'

type IconProps = SVGProps<SVGSVGElement> & { size?: number }

function Svg({ size = 16, children, ...rest }: IconProps & { children: ReactNode }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.8}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      {...rest}
    >
      {children}
    </svg>
  )
}

export const ChevronIcon = (p: IconProps) => (
  <Svg {...p}>
    <path d="m9 6 6 6-6 6" />
  </Svg>
)

export const CollageIcon = (p: IconProps) => (
  <Svg {...p}>
    <rect x="3" y="3" width="10" height="11" rx="1.5" />
    <rect x="15" y="3" width="6" height="7" rx="1.5" />
    <rect x="15" y="12" width="6" height="9" rx="1.5" />
    <rect x="3" y="16" width="10" height="5" rx="1.5" />
  </Svg>
)

export const FolderIcon = (p: IconProps) => (
  <Svg {...p}>
    <path d="M3 7.5A2.5 2.5 0 0 1 5.5 5H9l2 2.2h7.5A2.5 2.5 0 0 1 21 9.7v7.8a2.5 2.5 0 0 1-2.5 2.5h-13A2.5 2.5 0 0 1 3 17.5z" />
  </Svg>
)

export const FolderOpenIcon = (p: IconProps) => (
  <Svg {...p}>
    <path d="M4 18.5V7.5A2.5 2.5 0 0 1 6.5 5H9l2 2.2h6.5A2.5 2.5 0 0 1 20 9.7V11" />
    <path d="M4 19h13.6a1.5 1.5 0 0 0 1.45-1.1L21 12H6.4a1.5 1.5 0 0 0-1.45 1.1z" />
  </Svg>
)

export const FileIcon = (p: IconProps) => (
  <Svg {...p}>
    <path d="M14 3H7.5A2.5 2.5 0 0 0 5 5.5v13A2.5 2.5 0 0 0 7.5 21h9a2.5 2.5 0 0 0 2.5-2.5V8z" />
    <path d="M14 3v5h5" />
  </Svg>
)

export const PinIcon = (p: IconProps) => (
  <Svg {...p}>
    <path d="M9 3.5h6l-.8 6.2 3.3 3.3h-11l3.3-3.3z" />
    <path d="M12 13v7.5" />
  </Svg>
)

export const HomeIcon = (p: IconProps) => (
  <Svg {...p}>
    <path d="M3.5 11 12 4l8.5 7" />
    <path d="M5.5 9.5V20h13V9.5" />
    <path d="M10 20v-5h4v5" />
  </Svg>
)

export const DesktopIcon = (p: IconProps) => (
  <Svg {...p}>
    <rect x="3" y="4" width="18" height="12" rx="2" />
    <path d="M8 20h8M12 16v4" />
  </Svg>
)

export const DocumentsIcon = (p: IconProps) => (
  <Svg {...p}>
    <path d="M14 3H7.5A2.5 2.5 0 0 0 5 5.5v13A2.5 2.5 0 0 0 7.5 21h9a2.5 2.5 0 0 0 2.5-2.5V8z" />
    <path d="M14 3v5h5M9 13h6M9 17h4" />
  </Svg>
)

export const DownloadIcon = (p: IconProps) => (
  <Svg {...p}>
    <path d="M12 4v11M7 10l5 5 5-5M5 20h14" />
  </Svg>
)

export const DriveIcon = (p: IconProps) => (
  <Svg {...p}>
    <rect x="3" y="13" width="18" height="7" rx="2" />
    <path d="M5 13 7.5 5h9L19 13M7.5 16.5h.01M11 16.5h.01" />
  </Svg>
)

export const ArrowLeftIcon = (p: IconProps) => (
  <Svg {...p}>
    <path d="M19 12H5M11 6l-6 6 6 6" />
  </Svg>
)

export const ArrowRightIcon = (p: IconProps) => (
  <Svg {...p}>
    <path d="M5 12h14M13 6l6 6-6 6" />
  </Svg>
)

export const ArrowUpIcon = (p: IconProps) => (
  <Svg {...p}>
    <path d="M12 19V5M6 11l6-6 6 6" />
  </Svg>
)

export const RefreshIcon = (p: IconProps) => (
  <Svg {...p}>
    <path d="M20 12a8 8 0 1 1-2.34-5.66" />
    <path d="M20 4v5h-5" />
  </Svg>
)

export const EyeIcon = (p: IconProps) => (
  <Svg {...p}>
    <path d="M2.5 12S6 5.5 12 5.5 21.5 12 21.5 12 18 18.5 12 18.5 2.5 12 2.5 12z" />
    <circle cx="12" cy="12" r="3" />
  </Svg>
)

export const EyeOffIcon = (p: IconProps) => (
  <Svg {...p}>
    <path d="M2.5 12S6 5.5 12 5.5 21.5 12 21.5 12 18 18.5 12 18.5 2.5 12 2.5 12z" />
    <circle cx="12" cy="12" r="3" />
    <path d="M4 4l16 16" />
  </Svg>
)

export const SearchIcon = (p: IconProps) => (
  <Svg {...p}>
    <circle cx="11" cy="11" r="6.5" />
    <path d="m20 20-4.2-4.2" />
  </Svg>
)

export const PlusIcon = (p: IconProps) => (
  <Svg {...p}>
    <path d="M12 5v14M5 12h14" />
  </Svg>
)

export const HistoryIcon = (p: IconProps) => (
  <Svg {...p}>
    <path d="M3.5 12a8.5 8.5 0 1 0 2.5-6" />
    <path d="M3.5 4v4h4" />
    <path d="M12 7.5V12l3 2" />
  </Svg>
)

export const CloseIcon = (p: IconProps) => (
  <Svg {...p}>
    <path d="M6 6l12 12M18 6 6 18" />
  </Svg>
)

export const MergeIcon = (p: IconProps) => (
  <Svg {...p}>
    <path d="M7 4v5a3 3 0 0 0 3 3h4a3 3 0 0 1 3 3v5M17 4v5a3 3 0 0 1-3 3" />
    <path d="m14 17 3 3 3-3" />
  </Svg>
)

export const SplitIcon = (p: IconProps) => (
  <Svg {...p}>
    <rect x="4" y="3" width="16" height="7" rx="1.5" />
    <rect x="4" y="14" width="16" height="7" rx="1.5" />
    <path d="M2 12h3M9 12h2M14 12h2M19 12h3" />
  </Svg>
)

export const PagesIcon = (p: IconProps) => (
  <Svg {...p}>
    <rect x="3" y="4" width="7" height="9" rx="1.2" />
    <rect x="14" y="4" width="7" height="9" rx="1.2" />
    <path d="M3 17h7M14 17h7M3 20.5h7M14 20.5h7" />
  </Svg>
)

export const RotateCwIcon = (p: IconProps) => (
  <Svg {...p}>
    <path d="M20 12a8 8 0 1 1-2.34-5.66L20 8.5" />
    <path d="M20 3.5v5h-5" />
  </Svg>
)

export const RotateCcwIcon = (p: IconProps) => (
  <Svg {...p}>
    <path d="M4 12a8 8 0 1 0 2.34-5.66L4 8.5" />
    <path d="M4 3.5v5h5" />
  </Svg>
)

export const CropIcon = (p: IconProps) => (
  <Svg {...p}>
    <path d="M6 2v14a2 2 0 0 0 2 2h14" />
    <path d="M18 22V8a2 2 0 0 0-2-2H2" />
  </Svg>
)

export const NumbersIcon = (p: IconProps) => (
  <Svg {...p}>
    <rect x="4" y="3" width="16" height="18" rx="2" />
    <path d="M10.5 17h3M12 17v-4.5l-1.2.8" />
  </Svg>
)

export const TrashIcon = (p: IconProps) => (
  <Svg {...p}>
    <path d="M4 7h16M10 11v6M14 11v6M6 7l1 12.5A1.5 1.5 0 0 0 8.5 21h7a1.5 1.5 0 0 0 1.5-1.5L18 7M9 7V4.5A1.5 1.5 0 0 1 10.5 3h3A1.5 1.5 0 0 1 15 4.5V7" />
  </Svg>
)

export const DuplicateIcon = (p: IconProps) => (
  <Svg {...p}>
    <rect x="8" y="8" width="12" height="13" rx="2" />
    <path d="M16 8V5a2 2 0 0 0-2-2H6a2 2 0 0 0-2 2v10a2 2 0 0 0 2 2h2" />
  </Svg>
)

export const UndoIcon = (p: IconProps) => (
  <Svg {...p}>
    <path d="M9 14 4 9l5-5" />
    <path d="M4 9h10.5a5.5 5.5 0 0 1 0 11H11" />
  </Svg>
)

export const RedoIcon = (p: IconProps) => (
  <Svg {...p}>
    <path d="m15 14 5-5-5-5" />
    <path d="M20 9H9.5a5.5 5.5 0 0 0 0 11H13" />
  </Svg>
)

export const ArrowDownIcon = (p: IconProps) => (
  <Svg {...p}>
    <path d="M12 5v14M6 13l6 6 6-6" />
  </Svg>
)

export const FilePdfIcon = (p: IconProps) => (
  <Svg {...p}>
    <path d="M14 3H7.5A2.5 2.5 0 0 0 5 5.5v13A2.5 2.5 0 0 0 7.5 21h9a2.5 2.5 0 0 0 2.5-2.5V8z" />
    <path d="M14 3v5h5M8.5 15.5h1.2a1.3 1.3 0 0 0 0-2.6H8.5V18M13 12.9V18h1a2 2 0 0 0 2-2v-1.1a2 2 0 0 0-2-2z" />
  </Svg>
)

export const BlankPageIcon = (p: IconProps) => (
  <Svg {...p}>
    <path d="M14 3H7.5A2.5 2.5 0 0 0 5 5.5v13A2.5 2.5 0 0 0 7.5 21h9a2.5 2.5 0 0 0 2.5-2.5V8z" />
    <path d="M14 3v5h5M12 11v6M9 14h6" />
  </Svg>
)

export const PanelRightIcon = (p: IconProps) => (
  <Svg {...p}>
    <rect x="3" y="4" width="18" height="16" rx="2" />
    <path d="M15 4v16" />
  </Svg>
)

export const SlidesIcon = (p: IconProps) => (
  <Svg {...p}>
    <rect x="3" y="4" width="18" height="12" rx="1.5" />
    <path d="M12 16v4M8 20h8M7 8h6M7 11h10" />
  </Svg>
)

export const SheetIcon = (p: IconProps) => (
  <Svg {...p}>
    <rect x="3.5" y="4" width="17" height="16" rx="2" />
    <path d="M3.5 9.5h17M3.5 15h17M9.5 4v16" />
  </Svg>
)

export const ImageIcon = (p: IconProps) => (
  <Svg {...p}>
    <rect x="3" y="4" width="18" height="16" rx="2" />
    <circle cx="9" cy="9.5" r="1.8" />
    <path d="m21 16-5.5-5.5L5 20" />
  </Svg>
)

export const GlobeIcon = (p: IconProps) => (
  <Svg {...p}>
    <circle cx="12" cy="12" r="9" />
    <path d="M3 12h18M12 3a14 14 0 0 1 0 18M12 3a14 14 0 0 0 0 18" />
  </Svg>
)

export const MarkdownIcon = (p: IconProps) => (
  <Svg {...p}>
    <rect x="2.5" y="5" width="19" height="14" rx="2" />
    <path d="M6 15V9l2.5 3L11 9v6M15.5 9v6M13.5 13l2 2 2-2" />
  </Svg>
)

export const PencilIcon = (p: IconProps) => (
  <Svg {...p}>
    <path d="M4 20h4L19 9a2.8 2.8 0 0 0-4-4L4 16z" />
    <path d="m13.5 6.5 4 4" />
  </Svg>
)

export const ScanTextIcon = (p: IconProps) => (
  <Svg {...p}>
    <path d="M4 8V6a2 2 0 0 1 2-2h2M16 4h2a2 2 0 0 1 2 2v2M20 16v2a2 2 0 0 1-2 2h-2M8 20H6a2 2 0 0 1-2-2v-2" />
    <path d="M8 9h8M8 12h8M8 15h5" />
  </Svg>
)

export const FormIcon = (p: IconProps) => (
  <Svg {...p}>
    <rect x="4" y="4" width="16" height="16" rx="2" />
    <rect x="7" y="7.5" width="10" height="3" rx="0.8" />
    <path d="m7.5 15 1.5 1.5 3-3M14 15.5h3" />
  </Svg>
)

export const StampIcon = (p: IconProps) => (
  <Svg {...p}>
    <path d="M9.5 13.5 8.5 9a3.5 3.5 0 1 1 7 0l-1 4.5" />
    <path d="M5 13.5h14v3H5zM6 20h12" />
  </Svg>
)

export const LockIcon = (p: IconProps) => (
  <Svg {...p}>
    <rect x="5" y="10.5" width="14" height="10" rx="2" />
    <path d="M8 10.5V7.5a4 4 0 0 1 8 0v3M12 14.5v2" />
  </Svg>
)

export const SignatureIcon = (p: IconProps) => (
  <Svg {...p}>
    <path d="M3 17c3-1 4-9 6.5-9S9 16 11 16s2-4 3.5-4 1 3 2.5 3 2.5-2 4-2" />
    <path d="M3 21h18" />
  </Svg>
)

export const CompressIcon = (p: IconProps) => (
  <Svg {...p}>
    <path d="M12 3v6m0 0-3-3m3 3 3-3M12 21v-6m0 0-3 3m3-3 3 3M4 12h16" />
  </Svg>
)

export const WrenchIcon = (p: IconProps) => (
  <Svg {...p}>
    <path d="M14.7 6.3a4 4 0 0 0-5.4 5.2L4 16.8V20h3.2l5.3-5.3a4 4 0 0 0 5.2-5.4l-2.6 2.6-2.8-.6-.6-2.8z" />
  </Svg>
)

export const PrinterIcon = (p: IconProps) => (
  <Svg {...p}>
    <path d="M7 9V4h10v5" />
    <rect x="4" y="9" width="16" height="8" rx="2" />
    <path d="M7 14h10v6H7z" />
  </Svg>
)

export const SigmaIcon = (p: IconProps) => (
  <Svg {...p}>
    <path d="M18 7V5H6l6 7-6 7h12v-2" />
  </Svg>
)

export const WordIcon = (p: IconProps) => (
  <Svg {...p}>
    <rect x="4" y="3" width="16" height="18" rx="2" />
    <path d="m7.5 8 1.8 8 2.7-6 2.7 6 1.8-8" />
  </Svg>
)

export const ShieldIcon = (p: IconProps) => (
  <Svg {...p}>
    <path d="M12 3 5 6v5.5c0 4.4 3 8 7 9.5 4-1.5 7-5.1 7-9.5V6z" />
    <path d="m9 12 2 2 4-4" />
  </Svg>
)

export const FileInIcon = (p: IconProps) => (
  <Svg {...p}>
    <path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z" />
    <path d="M14 3v5h5M12 11v6m0 0-2.5-2.5M12 17l2.5-2.5" />
  </Svg>
)

export const FileOutIcon = (p: IconProps) => (
  <Svg {...p}>
    <path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z" />
    <path d="M14 3v5h5M12 17v-6m0 0-2.5 2.5M12 11l2.5 2.5" />
  </Svg>
)


export const SparkleIcon = (p: IconProps) => (
  <Svg {...p}>
    <path d="M12 3.5 13.8 9a2 2 0 0 0 1.2 1.2l5.5 1.8-5.5 1.8a2 2 0 0 0-1.2 1.2L12 20.5 10.2 15A2 2 0 0 0 9 13.8L3.5 12 9 10.2A2 2 0 0 0 10.2 9z" />
    <path d="M19 3v3M17.5 4.5h3" />
  </Svg>
)

export const ResizeIcon = (p: IconProps) => (
  <Svg {...p}>
    <rect x="3.5" y="9.5" width="11" height="11" rx="1.5" />
    <path d="M14 4h6v6M20 4l-7 7" />
  </Svg>
)

export const ConvertIcon = (p: IconProps) => (
  <Svg {...p}>
    <path d="M4 8h13l-3.5-3.5M20 16H7l3.5 3.5" />
  </Svg>
)

export const UpscaleIcon = (p: IconProps) => (
  <Svg {...p}>
    <rect x="3.5" y="3.5" width="17" height="17" rx="2" />
    <rect x="6.5" y="12.5" width="5" height="5" rx="0.8" />
    <path d="M11.5 12.5 17 7m0 0h-3.5M17 7v3.5" />
  </Svg>
)

export const CutoutIcon = (p: IconProps) => (
  <Svg {...p}>
    <path d="M4 4h2M9 4h2M14 4h2M19 4v2M20 9v2M20 14v2M18 20h2M13 20h2M8 20h2M4 18v2M4 13v2M4 8v2" />
    <circle cx="12" cy="10" r="2.6" />
    <path d="M7 18a5 5 0 0 1 10 0" />
  </Svg>
)

export const FaceIcon = (p: IconProps) => (
  <Svg {...p}>
    <circle cx="12" cy="12" r="8.5" />
    <path d="M9 10h.01M15 10h.01M8.8 14.5a4 4 0 0 0 6.4 0" />
  </Svg>
)

export const SlidersIcon = (p: IconProps) => (
  <Svg {...p}>
    <path d="M5 21v-7M5 10V3M12 21v-9M12 8V3M19 21v-5M19 12V3M2.5 14h5M9.5 8h5M16.5 16h5" />
  </Svg>
)

export const BrushIcon = (p: IconProps) => (
  <Svg {...p}>
    <path d="M18.5 3.5a2.1 2.1 0 0 1 3 3L12 16l-3-3z" />
    <path d="M9 13c-2.5 0-4 1.7-4 4 0 1.5-.8 2.5-2 3 4 1 8-.5 8-4.5z" />
  </Svg>
)
