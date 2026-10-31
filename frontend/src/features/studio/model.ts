import type { StudioDocument, StudioLayer } from '@/api/studio'
import type { Banner, BannerType, Content, PromoComponent } from '@/types/api'

export type StudioSource = { kind: 'banner'; item: Banner; type: BannerType } | { kind: 'content'; item: Content }
export interface StudioVariant { id: string; label: string; document: StudioDocument }
export type PromoButton = Extract<PromoComponent, { role: 'button' }>
export const buttonActionLabel = (action: PromoButton['actionType']) => ({ default: 'Основное действие', externalLink: 'Открыть ссылку', openSmartLink: 'Открыть ссылку приложения', closeCampaign: 'Закрыть кампанию', doneCampaign: 'Завершить кампанию' })[action]

export function newLayer(kind: StudioLayer['kind'], values: Partial<StudioLayer> = {}): StudioLayer {
  return { id: crypto.randomUUID(), name: kind === 'text' ? 'Текст' : kind === 'image' ? 'Изображение' : 'Фигура', kind, role: kind === 'text' ? 'body' : 'decoration', x: 24, y: 24, width: 220, height: 64, rotation: 0, opacity: 1, hidden: false, locked: false, text: kind === 'text' ? 'Ваш текст' : '', fontSize: 24, fontWeight: 600, textAlign: 'left', fill: '#ffffff', shape: 'rect', radius: 0, src: '', fit: 'cover', ...values }
}

const color = (value?: string | null, fallback = '#3155ff') => /^#[\da-f]{6}([\da-f]{2})?$/i.test(value ?? '') ? value! : fallback
export function contrastingText(background: string): string {
  const rgb = [1, 3, 5].map(index => parseInt(background.slice(index, index + 2), 16) / 255).map(value => value <= .04045 ? value / 12.92 : ((value + .055) / 1.055) ** 2.4)
  return rgb[0] * .2126 + rgb[1] * .7152 + rgb[2] * .0722 > .179 ? '#17223d' : '#ffffff'
}
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
      document.layers.push(newLayer('shape', { name: 'Подложка кнопки', x: 24, y, width: 252, height: story ? 42 : 28, fill: color(data.titleStyle?.textColor, contrastingText(document.background)), radius: 14 }))
      document.layers.push(newLayer('text', { name: 'Текст кнопки', role: 'button', text: data.buttonName, x: 32, y: y + (story ? 12 : 6), width: 236, height: 24, fontSize: story ? 15 : 12, textAlign: 'center', fill: document.background }))
    }
  } else {
    const container = source.item.content.component
    document.background = color(container.style?.backgroundColor, '#ffffff')
    let y = 24
    let textIndex = 0
    for (const item of container.components) {
      if (item.role === 'button') continue
      if (item.role === 'image') {
        const height = Math.min(200, 252 / (item.aspectRatio ?? 1.5))
        document.layers.push(newLayer('image', { src: item.url, x: 24, y, width: 252, height }))
        y += height + 20
      } else {
        const title = textIndex++ === 0
        const size = item.textStyle?.fontSize ?? 20
        const height = Math.max(50, Math.ceil(plain(item.text).length * size * .55 / 252) * size * 1.15)
        document.layers.push(newLayer('text', { name: title ? 'Заголовок' : 'Текст', role: title ? 'title' : 'body', text: plain(item.text), x: 24, y, width: 252, height, fontSize: Math.min(120, Math.max(8, size)), fill: color(item.textStyle?.textColor, '#172033') }))
        y += height + 20
      }
    }
    document.height = Math.max(400, Math.min(1000, y + 24))
  }
  return document
}

export function validateDocument(document: StudioDocument): string[] {
  const errors: string[] = []
  if (![document.background, ...document.layers.map(x => x.fill)].every(value => /^#[\da-f]{6}([\da-f]{2})?$/i.test(value))) errors.push('Цвет должен содержать # и 6 или 8 шестнадцатеричных символов.')
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

export { makeLayoutVariants } from './layouts.ts'
