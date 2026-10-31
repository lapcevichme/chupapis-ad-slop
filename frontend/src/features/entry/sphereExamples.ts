import type { SmartBannerSize } from '@/features/preview/smartBannerSizes'
import type { BannerContent, PromoContent } from '@/types/api'

// Примеры акций на сфере: все типы креативов сервиса. Тексты, размеры и цвета без изменений взяты из выданных моков
// (case/Кейс1/mocks/campaign_banners.json и campaign_contents.json, id в поле source). Адреса картинок в моках не открываются,
// поэтому картинки сгенерированы моделью IMAGE_MODEL по правилам prompts/design.md и лежат в frontend/public/entry.
interface ExampleBase {
  source: number
  label: string
  title: string
  background: string
  titleColor: string
  image: string
  // Долгота и широта точки крепления на сфере, в градусах.
  longitude: number
  latitude: number
}

export type SphereExample = ExampleBase &
  (
    | { kind: 'story'; banner: BannerContent }
    | { kind: SmartBannerSize; banner: BannerContent }
    | { kind: 'promo'; promo: PromoContent }
  )

// Соседние по долготе карточки чередуются по широте: высокие истории и промо сверху, низкие баннеры снизу, поэтому они не наезжают друг на друга.
const LATITUDES = { upper: 48, lower: -24 }
const SMART_BANNER = 'Смарт-баннер'

export const SPHERE_EXAMPLES: SphereExample[] = [
  {
    source: 205,
    kind: 'story',
    label: 'История',
    title: 'Кэшбэк 5% на отели',
    background: '#7A00E6FF',
    titleColor: '#FFFFFFFF',
    image: '/entry/hotels.webp',
    longitude: 58,
    latitude: LATITUDES.upper,
    banner: {
      title: 'Кэшбэк 5% на отели',
      titleStyle: { fontSize: 22, fontWeight: 'bold', textColor: '#FFFFFFFF' },
      text: 'Бронируйте путешествия в приложении до 15 ноября',
      textStyle: { fontSize: 14, fontWeight: 'regular', textColor: '#FFFFFFFF' },
      background: { color: '#7A00E6FF' },
      image: { url: '/entry/hotels.webp' },
      buttonName: 'Выбрать отель',
      actionType: 'externalLink',
      voiceOver: 'История: кэшбэк пять процентов на отели',
    },
  },
  {
    source: 214,
    kind: 'strip',
    label: `${SMART_BANNER}, платежи`,
    title: 'Переводы без комиссии',
    background: '#E8FAFFFF',
    titleColor: '#000014FF',
    image: '/entry/transfers.webp',
    longitude: 118,
    latitude: LATITUDES.lower,
    banner: {
      title: 'Переводы без комиссии',
      titleStyle: { fontSize: 15, fontWeight: 'medium', textColor: '#000014FF' },
      text: 'До 100 000 ₽ в месяц на любые карты',
      textStyle: { fontSize: 13, fontWeight: 'regular', textColor: '#00001499' },
      background: { color: '#E8FAFFFF' },
      image: { url: '/entry/transfers.webp' },
      buttonName: 'Перевести',
      actionType: 'externalLink',
    },
  },
  {
    source: 307,
    kind: 'promo',
    label: 'Промо-экран',
    title: 'Автокредит: ставка от 7,9%',
    background: '#F0F4FFFF',
    titleColor: '#000014FF',
    image: '/entry/car.webp',
    longitude: 178,
    latitude: LATITUDES.upper,
    promo: {
      role: 'promo',
      component: {
        role: 'linearContainer',
        axis: 'v',
        aligns: 'lt',
        style: { backgroundColor: '#F0F4FFFF' },
        components: [
          { role: 'text', format: 'none', text: 'Автокредит: ставка от 7,9%', textStyle: { fontSize: 22, fontWeight: 'bold', textColor: '#000014FF' } },
          { role: 'text', format: 'none', text: 'Одобрение за 2 минуты, первый взнос от 10%, срок до 7 лет', textStyle: { fontSize: 14, fontWeight: 'regular', textColor: '#00001499' } },
          { role: 'image', url: '/entry/car.webp', aspectRatio: 1.8 },
          { role: 'button', text: 'Рассчитать кредит', actionType: 'externalLink', textStyle: { fontSize: 15, fontWeight: 'medium', textColor: '#FFFFFFFF' }, style: { backgroundColor: '#003BF8FF' } },
        ],
      },
    },
  },
  {
    source: 215,
    kind: 'tile',
    label: `${SMART_BANNER}, каталог`,
    title: 'Подписка на фильмы',
    background: '#F3E8FFFF',
    titleColor: '#000014FF',
    image: '/entry/movies.webp',
    longitude: 238,
    latitude: LATITUDES.lower,
    banner: {
      title: 'Подписка на фильмы',
      titleStyle: { fontSize: 15, fontWeight: 'medium', textColor: '#000014FF' },
      text: 'Первый месяц за 1 ₽ — тысячи фильмов и сериалов',
      textStyle: { fontSize: 13, fontWeight: 'regular', textColor: '#00001499' },
      background: { color: '#F3E8FFFF' },
      image: { url: '/entry/movies.webp' },
      actionType: 'default',
    },
  },
  {
    source: 211,
    kind: 'story',
    label: 'История',
    title: 'Зимний марафон скидок',
    background: '#24009EFF',
    titleColor: '#FFFFFFFF',
    image: '/entry/marathon.webp',
    longitude: 298,
    latitude: LATITUDES.upper,
    banner: {
      title: 'Зимний марафон скидок',
      titleStyle: { fontSize: 26, fontWeight: 'bold', textColor: '#FFFFFFFF' },
      text: '12 дней, новые категории каждый день',
      textStyle: { fontSize: 14, fontWeight: 'medium', textColor: '#FFFFFFFF' },
      background: { color: '#24009EFF' },
      image: { url: '/entry/marathon.webp' },
      buttonName: 'Участвовать',
      actionType: 'externalLink',
      voiceOver: 'История: зимний марафон скидок, двенадцать дней',
    },
  },
  {
    source: 207,
    kind: 'card',
    label: `${SMART_BANNER}, главная`,
    title: 'Страховка в поездку',
    background: '#E6F7EEFF',
    titleColor: '#000014FF',
    image: '/entry/insurance.webp',
    longitude: 358,
    latitude: LATITUDES.lower,
    banner: {
      title: 'Страховка в поездку',
      titleStyle: { fontSize: 16, fontWeight: 'medium', textColor: '#000014FF' },
      text: 'Оформите полис за 2 минуты перед отпуском',
      textStyle: { fontSize: 13, fontWeight: 'regular', textColor: '#00001499' },
      background: { color: '#E6F7EEFF' },
      image: { url: '/entry/insurance.webp' },
      buttonName: 'Оформить',
      actionType: 'externalLink',
    },
  },
]
