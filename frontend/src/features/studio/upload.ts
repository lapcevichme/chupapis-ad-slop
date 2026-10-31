import { uploadImage } from '@/api/media'
import { canvasBlob, readImage } from './render'

const SVG_TAGS = new Set(['svg', 'g', 'path', 'rect', 'circle', 'ellipse', 'polygon', 'polyline', 'line', 'text', 'tspan', 'defs', 'linearGradient', 'radialGradient', 'stop', 'clipPath', 'mask', 'pattern', 'use', 'symbol', 'title', 'desc'])

function cleanSvg(raw: string): Blob {
  const xml = new DOMParser().parseFromString(raw, 'image/svg+xml')
  if (xml.querySelector('parsererror') || xml.documentElement.localName !== 'svg') throw new Error('Не удалось прочитать SVG.')
  for (const element of Array.from(xml.querySelectorAll('*'))) {
    if (!SVG_TAGS.has(element.localName)) { element.remove(); continue }
    for (const attribute of Array.from(element.attributes)) {
      const value = attribute.value.trim()
      if (/^on/i.test(attribute.name) || (/href$/i.test(attribute.name) && !value.startsWith('#')) || (/url\s*\(/i.test(value) && !/^url\(\s*["']?#[\w-]+["']?\s*\)$/i.test(value))) element.removeAttribute(attribute.name)
    }
  }
  xml.documentElement.setAttribute('xmlns', 'http://www.w3.org/2000/svg')
  return new Blob([new XMLSerializer().serializeToString(xml)], { type: 'image/svg+xml' })
}

export async function uploadStudioImage(file: File): Promise<{ url: string; aspect: number }> {
  if (file.size > 20 * 1024 * 1024) throw new Error('Файл больше 20 МБ. Выберите изображение поменьше.')
  const svg = file.type === 'image/svg+xml' || /\.svg$/i.test(file.name)
  const blob = svg ? cleanSvg(await file.text()) : file
  const local = URL.createObjectURL(blob)
  try {
    const image = await readImage(local)
    const canvas = document.createElement('canvas')
    const scale = Math.min(1, 1400 / Math.max(image.naturalWidth, image.naturalHeight))
    canvas.width = Math.max(1, Math.round(image.naturalWidth * scale))
    canvas.height = Math.max(1, Math.round(image.naturalHeight * scale))
    canvas.getContext('2d')!.drawImage(image, 0, 0, canvas.width, canvas.height)
    let png = await canvasBlob(canvas)
    if (png.size > 5 * 1024 * 1024) {
      const smaller = document.createElement('canvas')
      const factor = 1000 / Math.max(canvas.width, canvas.height)
      smaller.width = Math.round(canvas.width * factor); smaller.height = Math.round(canvas.height * factor)
      smaller.getContext('2d')!.drawImage(canvas, 0, 0, smaller.width, smaller.height)
      png = await canvasBlob(smaller)
    }
    return { url: await uploadImage(png), aspect: image.naturalWidth / image.naturalHeight }
  } finally { URL.revokeObjectURL(local) }
}
