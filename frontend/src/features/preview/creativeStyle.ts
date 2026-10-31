import type { CSSProperties } from 'react'
import type { FontWeight, PromoComponent, TextStyle } from '@/types/api'

const FONT_WEIGHTS: Record<FontWeight, number> = {
  thin: 100,
  light: 300,
  regular: 400,
  medium: 500,
  'semi-bold': 600,
  bold: 700,
}

// В схеме PROMO вес шрифта — произвольная строка, неизвестное значение просто не применяем.
type AnyTextStyle = TextStyle | Extract<PromoComponent, { role: 'text' }>['textStyle']

export function textStyleToCss(style?: AnyTextStyle): CSSProperties {
  return {
    fontSize: style?.fontSize ?? undefined,
    fontWeight: style?.fontWeight ? FONT_WEIGHTS[style.fontWeight as FontWeight] : undefined,
    color: style?.textColor ?? undefined,
  }
}

// Сгенерированные картинки бэкенд раздаёт сам: они идут через тот же прокси /api (docs/ours/chat-api.md, раздел 8).
const MEDIA_PREFIX = '/api/media/'

export function isImageUrl(url?: string | null): url is string {
  if (!url) return false
  if (url.startsWith(MEDIA_PREFIX)) return true
  try {
    return new URL(url).protocol === 'https:'
  } catch {
    return false
  }
}

export interface RichTextPart {
  text: string
  bold: boolean
}

// Текст приходит от LLM, поэтому HTML не вставляем как разметку: понимаем только <b>, остальные теги убираем.
export function parseRichText(html: string): RichTextPart[] {
  return html
    .split(/(<b>.*?<\/b>)/gis)
    .filter(Boolean)
    .map((part) => {
      const bold = /^<b>.*<\/b>$/is.test(part)
      return { text: part.replace(/<[^>]*>/g, ''), bold }
    })
    .filter((part) => part.text)
}
