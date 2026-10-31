const MAX_COLORS = 4
// Цвета ближе этого расстояния в RGB человек воспринимает как один.
const MIN_DISTANCE = 56
const BUCKET_BITS = 4

type Rgb = [number, number, number]

function saturation([red, green, blue]: Rgb) {
  const max = Math.max(red, green, blue)
  return max === 0 ? 0 : (max - Math.min(red, green, blue)) / max
}

function distance(a: Rgb, b: Rgb) {
  return Math.hypot(a[0] - b[0], a[1] - b[1], a[2] - b[2])
}

function toHex(color: Rgb) {
  return `#${color.map((part) => Math.round(part).toString(16).padStart(2, '0')).join('')}`.toUpperCase()
}

export type PhotoTone = 'dark' | 'light'

// Средняя яркость снимка. Фото лежит под текстом баннера, поэтому контраст зависит от него, а не от цвета фона.
export function photoTone(pixels: Uint8ClampedArray): PhotoTone {
  let sum = 0
  let count = 0
  for (let index = 0; index + 3 < pixels.length; index += 4) {
    if (pixels[index + 3] < 128) continue
    sum += 0.299 * pixels[index] + 0.587 * pixels[index + 1] + 0.114 * pixels[index + 2]
    count += 1
  }
  return count > 0 && sum / count >= 140 ? 'light' : 'dark'
}

// Основные цвета по пикселям RGBA. Насыщенные получают больший вес: иначе в палитру попадёт только фон фото.
export function pickPalette(pixels: Uint8ClampedArray): string[] {
  const buckets = new Map<number, { sum: Rgb; count: number }>()
  const shift = 8 - BUCKET_BITS
  for (let index = 0; index + 3 < pixels.length; index += 4) {
    if (pixels[index + 3] < 128) continue
    const [red, green, blue] = [pixels[index], pixels[index + 1], pixels[index + 2]]
    const key = ((red >> shift) << (BUCKET_BITS * 2)) | ((green >> shift) << BUCKET_BITS) | (blue >> shift)
    const bucket = buckets.get(key) ?? { sum: [0, 0, 0] as Rgb, count: 0 }
    bucket.sum = [bucket.sum[0] + red, bucket.sum[1] + green, bucket.sum[2] + blue]
    bucket.count += 1
    buckets.set(key, bucket)
  }

  const ranked = [...buckets.values()]
    .map(({ sum, count }) => {
      const color: Rgb = [sum[0] / count, sum[1] / count, sum[2] / count]
      return { color, weight: count * (1 + 3 * saturation(color)) }
    })
    .sort((a, b) => b.weight - a.weight)

  const picked: Rgb[] = []
  for (const { color } of ranked) {
    if (picked.every((known) => distance(known, color) >= MIN_DISTANCE)) picked.push(color)
    if (picked.length === MAX_COLORS) break
  }
  return picked.map(toHex)
}
