import { onMounted, ref } from 'vue'

export const REPO = 'https://github.com/epicabdou/tessera'
/** The release workflow always uploads the installer under this name too, so this link never changes. */
export const MSI_LATEST = `${REPO}/releases/latest/download/Tessera-x64.msi`
export const RELEASES = `${REPO}/releases`
export const SOURCE_MAIN = `${REPO}/archive/refs/heads/main.zip`

export interface Release {
  version: string
  date: string
  msiUrl: string
  msiSize: number | null
  sourceZip: string
  notesUrl: string
  sumsUrl: string | null
}

let cached: Promise<Release | null> | null = null

/** The latest GitHub release, read in the visitor's browser. Null until there is one (or offline). */
export function useLatestRelease() {
  const release = ref<Release | null>(null)
  onMounted(async () => {
    cached ??= fetch('https://api.github.com/repos/epicabdou/tessera/releases/latest', { headers: { Accept: 'application/vnd.github+json' } })
      .then((r) => (r.ok ? r.json() : null))
      .then((r) => {
        if (!r) return null
        const msi = r.assets?.find((a: { name: string }) => a.name === 'Tessera-x64.msi')
        const sums = r.assets?.find((a: { name: string }) => a.name === 'SHA256SUMS.txt')
        return {
          version: String(r.tag_name).replace(/^v/, ''),
          date: new Date(r.published_at).toLocaleDateString(undefined, { dateStyle: 'medium' }),
          msiUrl: msi?.browser_download_url ?? MSI_LATEST,
          msiSize: msi?.size ?? null,
          sourceZip: `${REPO}/archive/refs/tags/${r.tag_name}.zip`,
          notesUrl: r.html_url,
          sumsUrl: sums?.browser_download_url ?? null,
        } satisfies Release
      })
      .catch(() => null)
    release.value = await cached
  })
  return release
}

export function megabytes(bytes: number | null): string {
  return bytes ? `${(bytes / 1024 / 1024).toFixed(0)} MB` : ''
}
