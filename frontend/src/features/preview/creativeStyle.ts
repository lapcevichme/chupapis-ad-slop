import type { CSSProperties } from 'react'
import type { FontWeight, TextStyle } from '@/types/api'

const FONT_WEIGHTS: Record<FontWeight, number> = {
  thin: 100,
  light: 300,
  regular: 400,
  medium: 500,
  'semi-bold': 600,
  bold: 700,
}

export function textStyleToCss(style?: TextStyle): CSSProperties {
  return {
    fontSize: style?.fontSize,
    fontWeight: style?.fontWeight ? FONT_WEIGHTS[style.fontWeight] : undefined,
    color: style?.textColor,
  }
}

export function isHttpsUrl(url?: string): url is string {
  if (!url) return false
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
