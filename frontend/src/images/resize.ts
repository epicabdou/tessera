/** Sizing maths shared by the image tools. */

/** Resize options, and the size they produce (mirrors images/basic.py target_size). */
export interface ResizeOptions {
  mode: 'percent' | 'pixels' | 'longest'
  percent: number
  width: number
  height: number
  longest: number
  keep_aspect: boolean
  fit: 'contain' | 'cover'
  no_enlarge: boolean
  resample: 'lanczos' | 'bicubic' | 'nearest'
}

export function targetSize(width: number, height: number, o: ResizeOptions): { width: number; height: number; unchanged: boolean } {
  let w: number
  let h: number
  let crop: [number, number] | null = null
  if (o.mode === 'percent') {
    w = (width * o.percent) / 100
    h = (height * o.percent) / 100
  } else if (o.mode === 'longest') {
    const k = o.longest / Math.max(width, height)
    w = width * k
    h = height * k
  } else if (!o.keep_aspect && o.width && o.height) {
    w = o.width
    h = o.height
  } else if (o.width && o.height) {
    const k = o.fit === 'cover' ? Math.max(o.width / width, o.height / height) : Math.min(o.width / width, o.height / height)
    w = width * k
    h = height * k
    if (o.fit === 'cover') crop = [o.width, o.height]
  } else {
    const k = o.width ? o.width / width : o.height / height
    w = width * k
    h = height * k
  }
  w = Math.max(1, Math.round(w))
  h = Math.max(1, Math.round(h))
  if (o.no_enlarge && (w > width || h > height)) return { width, height, unchanged: true }
  if (crop) return { width: Math.min(crop[0], w), height: Math.min(crop[1], h), unchanged: false }
  return { width: w, height: h, unchanged: w === width && h === height }
}

/** Largest rectangle with this aspect ratio (w / h), centred in a width × height image. */
export function fitAspect(width: number, height: number, aspect: number) {
  const w = Math.min(width, height * aspect)
  const h = w / aspect
  return { x: Math.round((width - w) / 2), y: Math.round((height - h) / 2), w: Math.round(w), h: Math.round(h) }
}
