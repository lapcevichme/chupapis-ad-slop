import type { StudioLayer } from '@/api/studio'

export const ILLUSTRATIONS = [
  { symbol: 'coffee', label: 'Кофе', src: '/studio/coffee.png' },
  { symbol: 'card', label: 'Банковская карта', src: '/studio/card.png' },
  { symbol: 'travel', label: 'Путешествия', src: '/studio/travel.png' },
  { symbol: 'car', label: 'Автомобиль', src: '/studio/car.png' },
] as const

export function illustrationSource(symbol: StudioLayer['symbol']) {
  return ILLUSTRATIONS.find(item => item.symbol === symbol)?.src ?? ILLUSTRATIONS[0].src
}
