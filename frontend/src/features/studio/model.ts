import type { StudioDocument, StudioLayer } from '@/api/studio'
import type { Banner, BannerType, Content, PromoComponent } from '@/types/api'

export type StudioSource = { kind: 'banner'; item: Banner; type: BannerType } | { kind: 'content'; item: Content }
export interface StudioVariant { id: string; label: string; document: StudioDocument }
export type PromoButton = Extract<PromoComponent, { role: 'button' }>

export function newLayer(kind: StudioLayer['kind'], values: Partial<StudioLayer> = {}): StudioLayer {
  return { id: crypto.randomUUID(), name: kind === 'text' ? 'Текст' : kind === 'image' ? 'Изображение' : 'Фигура', kind, role: kind === 'text' ? 'body' : 'decoration', x: 24, y: 24, width: 220, height: 64, rotation: 0, opacity: 1, hidden: false, locked: false, text: kind === 'text' ? 'Ваш текст' : '', fontSize: 24, fontWeight: 600, textAlign: 'left', fill: '#ffffff', shape: 'rect', radius: 0, src: '', fit: 'cover', ...values }
}

const color = (value?: string | null, fallback = '#3155ff') => /^#[\da-f]{6}([\da-f]{2})?$/i.test(value ?? '') ? value! : fallback
function plain(text: string) { return text.replace(/<[^>]*>/g, '') }

export function importSource(source: StudioSource): StudioDocument {
  const document: StudioDocument = { version: 1, name: source.item.name, format: source.kind === 'banner' ? source.type.code as 'STORY' | 'SMART_BANNER' : 'PROMO', width: 300, height: source.kind === 'banner' && source.type.code === 'SMART_BANNER' ? 160 : 600, background: '#3155ff', layers: [] }
  if (source.kind === 'banner') {
    const data = source.item.content
    const story = document.format === 'STORY'
    document.background = color(data.background?.color)
    if (data.image) document.layers.push(newLayer('image', { name: 'Изображение исходного креатива', src: data.image.url, x: 0, y: 0, width: 300, height: document.height }))
    if (data.title) document.layers.push(newLayer('text', { name: 'Заголовок', role: 'title', text: data.title, x: 24, y: story ? 36 : 18, width: 252, height: story ? 120 : 46, fontSize: data.titleStyle?.fontSize ?? (story ? 32 : 20), fontWeight: 700, fill: color(data.titleStyle?.textColor, '#ffffff') }))
    if (data.text) document.layers.push(newLayer('text', { name: 'Описание', text: data.text, x: 24, y: story ? 176 : 68, width: 252, height: story ? 130 : 48, fontSize: data.textStyle?.fontSize ?? (story ? 18 : 14), fill: color(data.textStyle?.textColor, '#ffffff') }))
    if (data.buttonName) {
      const y = document.height - (story ? 62 : 36)
      document.layers.push(newLayer('shape', { name: 'Подложка кнопки', x: 24, y, width: 252, height: story ? 42 : 28, fill: '#ffffff', radius: 14 }))
      document.layers.push(newLayer('text', { name: 'Текст кнопки', role: 'button', text: data.buttonName, x: 32, y: y + (story ? 12 : 6), width: 236, height: 24, fontSize: story ? 15 : 12, textAlign: 'center', fill: document.background }))
    }
  } else {
    const container = source.item.content.component
    document.background = color(container.style?.backgroundColor, '#ffffff')
    let y = 24
    for (const item of container.components) {
      if (item.role === 'button') continue
      if (item.role === 'image') {
        const height = Math.min(200, 252 / (item.aspectRatio ?? 1.5))
        document.layers.push(newLayer('image', { src: item.url, x: 24, y, width: 252, height }))
        y += height + 20
      } else {
        const size = item.textStyle?.fontSize ?? 20
        const height = Math.max(50, Math.ceil(plain(item.text).length * size * .55 / 252) * size * 1.15)
        document.layers.push(newLayer('text', { name: y < 100 ? 'Заголовок' : 'Текст', role: y < 100 ? 'title' : 'body', text: plain(item.text), x: 24, y, width: 252, height, fontSize: Math.min(120, Math.max(8, size)), fill: color(item.textStyle?.textColor, '#172033') }))
        y += height + 20
      }
    }
    document.height = Math.max(400, Math.min(1000, y + 24))
  }
  return document
}

export function validateDocument(document: StudioDocument): string[] {
  const errors: string[] = []
  if (document.layers.length > 40) errors.push('В макете может быть не больше 40 слоёв.')
  if (document.format !== 'PROMO') {
    const title = document.layers.filter(x => x.kind === 'text' && x.role === 'title').map(x => x.text).join(' ')
    const body = document.layers.filter(x => x.kind === 'text' && x.role !== 'title').map(x => x.text).join(' ')
    const limits = document.format === 'STORY' ? [100, 500] : [250, 1000]
    if (title.length > limits[0]) errors.push(`Заголовок: ${title.length} символов из ${limits[0]}.`)
    if (body.length > limits[1]) errors.push(`Остальные тексты: ${body.length} символов из ${limits[1]}.`)
  }
  if (document.layers.some(x => x.kind === 'text' && !x.hidden && x.height < x.fontSize * 1.15)) errors.push('Некоторые текстовые блоки ниже одной строки — увеличьте их высоту.')
  return errors
}

export function makeLayoutVariants(base: StudioDocument): StudioDocument[] {
  return ['Плакат', 'Редакционный', 'Контраст'].map((name, index) => {
    const document = structuredClone(base)
    document.name = name
    const tall = document.height > 300
    const palettes = [['#3155ff', '#ffffff', '#d6f45b'], ['#f4eadb', '#23283c', '#ff714e'], ['#d6f45b', '#222b59', '#8060dd']]
    const [background, ink, accent] = palettes[index]
    document.background = background
    document.layers = document.layers.filter(x => x.kind !== 'shape')
    document.layers.unshift(newLayer('shape', { name: 'Цветная плоскость', x: index === 1 ? 180 : -60, y: tall ? document.height * .48 : 75, width: 380, height: tall ? 270 : 120, rotation: index === 1 ? 12 : -12, fill: accent, radius: index === 2 ? 120 : 0 }))
    let textY = 24
    document.layers = document.layers.map(layer => {
      if (layer.kind === 'image') return { ...layer, x: 24, y: tall ? document.height * .54 : 70, width: 252, height: tall ? document.height * .29 : 72, rotation: index === 1 ? -4 : 0, opacity: .9 }
      if (layer.kind !== 'text') return layer
      if (layer.role === 'button') return { ...layer, x: 24, y: document.height - 40, width: 252, height: 24, fill: ink, fontSize: 15, textAlign: 'left' as const }
      const title = layer.role === 'title'
      const size = title ? (tall ? 36 : 22) : (tall ? 18 : 13)
      const height = Math.ceil(layer.text.length * size * .56 / 252) * size * 1.15 + 8
      const next = { ...layer, x: 24, y: textY, width: 252, height, fontSize: size, fill: ink, fontWeight: (title ? 800 : 500) as 800 | 500 }
      textY += height + 14
      return next
    })
    return document
  })
}
