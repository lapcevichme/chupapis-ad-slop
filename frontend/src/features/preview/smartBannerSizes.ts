// Один и тот же смарт-баннер на разных экранах приложения: карточка на главной, плитка в каталоге, полоса в платежах.
export type SmartBannerSize = 'card' | 'tile' | 'strip'

export const SMART_BANNER_SIZES: { value: SmartBannerSize; label: string }[] = [
  { value: 'card', label: 'Главная' },
  { value: 'tile', label: 'Каталог' },
  { value: 'strip', label: 'Платежи' },
]
