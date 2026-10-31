import type { StudioDocument, StudioLayer } from '@/api/studio'

export function readImage(src: string): Promise<HTMLImageElement> {
  return new Promise((resolve, reject) => {
    const image = new Image()
    if (!src.startsWith('blob:')) image.crossOrigin = 'anonymous'
    image.onload = () => resolve(image)
    image.onerror = () => reject(new Error('Изображение недоступно для экспорта. Загрузите его файлом или замените в макете.'))
    image.src = src
  })
}

export function canvasBlob(canvas: HTMLCanvasElement): Promise<Blob> {
  return new Promise((resolve, reject) => canvas.toBlob(blob => blob ? resolve(blob) : reject(new Error('Не удалось собрать PNG.')), 'image/png'))
}

function textLines(context: CanvasRenderingContext2D, text: string, width: number) {
  const lines: string[] = []
  for (const paragraph of text.split('\n')) {
    let current = ''
    for (const word of paragraph.split(/(\s+)/)) {
      if (context.measureText(current + word).width <= width) { current += word; continue }
      if (current) lines.push(current.trimEnd())
      current = ''
      for (const char of word.trimStart()) {
        if (current && context.measureText(current + char).width > width) { lines.push(current); current = '' }
        current += char
      }
    }
    lines.push(current)
  }
  return lines
}

function drawLayer(context: CanvasRenderingContext2D, layer: StudioLayer, image?: HTMLImageElement) {
  context.save()
  context.translate(layer.x + layer.width / 2, layer.y + layer.height / 2)
  context.rotate(layer.rotation * Math.PI / 180)
  context.translate(-layer.width / 2, -layer.height / 2)
  context.globalAlpha = layer.opacity
  context.beginPath()
  context.rect(0, 0, layer.width, layer.height)
  context.clip()
  context.fillStyle = layer.fill
  if (layer.kind === 'shape') {
    context.beginPath()
    if (layer.shape === 'ellipse') context.ellipse(layer.width / 2, layer.height / 2, layer.width / 2, layer.height / 2, 0, 0, Math.PI * 2)
    else context.roundRect(0, 0, layer.width, layer.height, Math.min(layer.radius, layer.width / 2, layer.height / 2))
    context.fill()
  } else if (layer.kind === 'text') {
    context.font = `${layer.fontWeight} ${layer.fontSize}px "Onest Variable"`
    context.textAlign = layer.textAlign
    context.textBaseline = 'top'
    const x = layer.textAlign === 'center' ? layer.width / 2 : layer.textAlign === 'right' ? layer.width : 0
    textLines(context, layer.text, layer.width).forEach((line, index) => context.fillText(line, x, index * layer.fontSize * 1.15))
  } else if (image) {
    const scale = (layer.fit === 'contain' ? Math.min : Math.max)(layer.width / image.naturalWidth, layer.height / image.naturalHeight)
    const w = image.naturalWidth * scale, h = image.naturalHeight * scale
    context.drawImage(image, (layer.width - w) / 2, (layer.height - h) / 2, w, h)
  }
  context.restore()
}

export async function renderDocument(document: StudioDocument): Promise<Blob> {
  await window.document.fonts.ready
  const canvas = window.document.createElement('canvas')
  canvas.width = document.width * 2
  canvas.height = document.height * 2
  const context = canvas.getContext('2d')!
  context.scale(2, 2)
  context.fillStyle = document.background
  context.fillRect(0, 0, document.width, document.height)
  const layers = document.layers.filter(x => !x.hidden)
  const images = await Promise.all(layers.map(layer => layer.kind === 'image' ? readImage(layer.src) : undefined))
  layers.forEach((layer, i) => drawLayer(context, layer, images[i]))
  return canvasBlob(canvas)
}

export function downloadBlob(blob: Blob, name: string) {
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url; link.download = name; link.click()
  setTimeout(() => URL.revokeObjectURL(url), 1000)
}
