import { photoTone, pickPalette, type PhotoTone } from './palette'

const ACCEPTED_TYPES = ['image/jpeg', 'image/png']
// Исходник большой только до сжатия: на сервер уходит файл намного меньше.
const MAX_SOURCE_BYTES = 20 * 1024 * 1024
const MAX_SIDE_PX = 1600
const PALETTE_SIDE_PX = 64
const JPEG_QUALITY = 0.85

export const IMAGE_ACCEPT = ACCEPTED_TYPES.join(',')
export const IMAGE_LIMITS_HINT = 'JPEG или PNG, до 20 МБ'

export interface PreparedImage {
  blob: Blob
  previewUrl: string
  colors: string[]
  tone: PhotoTone
}

export class ImageRejected extends Error {}

function draw(bitmap: ImageBitmap, maxSide: number) {
  const scale = Math.min(1, maxSide / Math.max(bitmap.width, bitmap.height))
  const canvas = document.createElement('canvas')
  canvas.width = Math.max(1, Math.round(bitmap.width * scale))
  canvas.height = Math.max(1, Math.round(bitmap.height * scale))
  const context = canvas.getContext('2d')
  if (!context) throw new ImageRejected('Браузер не смог обработать фото.')
  // JPEG без прозрачности: у PNG она иначе станет чёрной.
  context.fillStyle = '#FFFFFF'
  context.fillRect(0, 0, canvas.width, canvas.height)
  context.drawImage(bitmap, 0, 0, canvas.width, canvas.height)
  return { canvas, context }
}

// Перекодирование заодно убирает из снимка метаданные, в том числе геопозицию.
export async function prepareImage(file: File): Promise<PreparedImage> {
  if (!ACCEPTED_TYPES.includes(file.type)) throw new ImageRejected('Подойдёт только JPEG или PNG.')
  if (file.size > MAX_SOURCE_BYTES) throw new ImageRejected('Файл больше 20 МБ, выберите поменьше.')

  let bitmap: ImageBitmap
  try {
    bitmap = await createImageBitmap(file, { imageOrientation: 'from-image' })
  } catch {
    throw new ImageRejected('Не получилось открыть файл: возможно, он повреждён.')
  }
  try {
    const small = draw(bitmap, PALETTE_SIDE_PX)
    const pixels = small.context.getImageData(0, 0, small.canvas.width, small.canvas.height).data
    const colors = pickPalette(pixels)
    const tone = photoTone(pixels)
    const { canvas } = draw(bitmap, MAX_SIDE_PX)
    const blob = await new Promise<Blob | null>((resolve) => canvas.toBlob(resolve, 'image/jpeg', JPEG_QUALITY))
    if (!blob) throw new ImageRejected('Браузер не смог обработать фото.')
    return { blob, previewUrl: URL.createObjectURL(blob), colors, tone }
  } finally {
    bitmap.close()
  }
}
