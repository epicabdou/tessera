/** Drag-and-drop payload type for a folder path (tree → pinned list, pin → pin). */
export const DND_PATH = 'application/x-toolbox-path'
/** Drag-and-drop payload type for a file path (tree → tools, e.g. Merge PDF). */
export const DND_FILE = 'application/x-toolbox-file'

export type FileKind = 'code' | 'image' | 'archive' | 'app' | 'doc' | 'media' | 'other'

const KINDS: [FileKind, string[]][] = [
  ['code', ['py', 'ts', 'tsx', 'js', 'jsx', 'mjs', 'json', 'css', 'scss', 'html', 'toml', 'yml', 'yaml', 'ini', 'cfg', 'sh', 'ps1', 'bat', 'cmd', 'c', 'h', 'cpp', 'cs', 'java', 'go', 'rs', 'rb', 'php', 'sql', 'xml']],
  ['image', ['png', 'jpg', 'jpeg', 'gif', 'svg', 'webp', 'ico', 'bmp', 'tif', 'tiff', 'heic']],
  ['archive', ['zip', '7z', 'rar', 'tar', 'gz', 'tgz', 'bz2', 'xz']],
  ['app', ['exe', 'msi', 'dll', 'lnk', 'appx', 'msix']],
  ['doc', ['pdf', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx', 'txt', 'md', 'rtf', 'csv', 'odt', 'ods', 'log']],
  ['media', ['mp3', 'wav', 'flac', 'ogg', 'm4a', 'mp4', 'mov', 'mkv', 'avi', 'webm']],
]

const BY_EXT = new Map<string, FileKind>(KINDS.flatMap(([kind, exts]) => exts.map((e) => [e, kind] as const)))

export function fileKind(ext: string): FileKind {
  return BY_EXT.get(ext) ?? 'other'
}
