import type { PhotoTone } from './palette'

const URL_LINE =/^Загружено фото: (\/api\/media\/upload-[\w-]+\.(?:jpg|png))$/
const COLOR = /#[0-9A-F]{6}/g

export interface ImageMessage {
  url: string
  colors: string[]
}

// Обычное сообщение чата: правило для него — в prompts/chat.md. История сессии хранит только текст, поэтому формат строгий.
export function imageMessage(url: string, colors: string[], tone: PhotoTone, banner?: { id: unknown; name: string }): string {
  return [
    `Загружено фото: ${url}`,
    ...(banner ? [`Баннер: ${String(banner.id)} «${banner.name}»`] : []),
    `Цвета фото: ${colors.join(', ')}`,
    `Яркость фото: ${tone === 'dark' ? 'тёмное, текст поверх него светлый' : 'светлое, текст поверх него тёмный'}`,
    'Поставь фото в креатив и подстрой под него цвета.',
  ].join('\n')
}

export function parseImageMessage(text: string): ImageMessage | null {
  const [first, ...rest] = text.split('\n')
  const url = URL_LINE.exec(first)?.[1]
  if (!url) return null
  const colors = rest.find((line) => line.startsWith('Цвета фото: '))?.match(COLOR) ?? []
  return { url, colors: [...colors] }
}

// Как показать сообщение там, где важен только смысл.
export function userMessageSummary(text: string): string {
  return parseImageMessage(text) ? 'Загружено фото' : text
}
