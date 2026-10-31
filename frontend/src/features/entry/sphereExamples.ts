// Примеры акций на сфере. Тексты и цвета без изменений взяты из выданных моков:
// case/Кейс1/mocks/campaign_banners.json, id в поле source. Картинки не берём: их адреса синтетические и не открываются.
export interface SphereExample {
  source: number
  title: string
  text: string
  buttonName?: string
  background: string
  titleColor: string
  textColor: string
  // Долгота и широта точки крепления на сфере, в градусах.
  longitude: number
  latitude: number
}

// Три уровня широты: соседние по долготе карточки не наезжают друг на друга, даже когда сфера маленькая.
const LATITUDES = { upper: 48, middle: 8, lower: -32 }

export const SPHERE_EXAMPLES: SphereExample[] = [
  {
    source: 205,
    title: 'Кэшбэк 5% на отели',
    text: 'Бронируйте путешествия в приложении до 15 ноября',
    buttonName: 'Выбрать отель',
    background: '#7A00E6FF',
    titleColor: '#FFFFFFFF',
    textColor: '#FFFFFFFF',
    longitude: 50,
    latitude: LATITUDES.upper,
  },
  {
    source: 207,
    title: 'Страховка в поездку',
    text: 'Оформите полис за 2 минуты перед отпуском',
    buttonName: 'Оформить',
    background: '#E6F7EEFF',
    titleColor: '#000014FF',
    textColor: '#00001499',
    longitude: 110,
    latitude: LATITUDES.middle,
  },
  {
    source: 210,
    title: 'Автокредит от 7,9%',
    text: 'Одобрение за 2 минуты, первый взнос от 10%',
    background: '#003BF8FF',
    titleColor: '#FFFFFFFF',
    textColor: '#FFFFFFFF',
    longitude: 170,
    latitude: LATITUDES.lower,
  },
  {
    source: 214,
    title: 'Переводы без комиссии',
    text: 'До 100 000 ₽ в месяц на любые карты',
    buttonName: 'Перевести',
    background: '#E8FAFFFF',
    titleColor: '#000014FF',
    textColor: '#00001499',
    longitude: 230,
    latitude: LATITUDES.upper,
  },
  {
    source: 211,
    title: 'Зимний марафон скидок',
    text: '12 дней, новые категории каждый день',
    buttonName: 'Участвовать',
    background: '#24009EFF',
    titleColor: '#FFFFFFFF',
    textColor: '#FFFFFFFF',
    longitude: 290,
    latitude: LATITUDES.middle,
  },
  {
    source: 215,
    title: 'Подписка на фильмы',
    text: 'Первый месяц за 1 ₽ — тысячи фильмов и сериалов',
    background: '#F3E8FFFF',
    titleColor: '#000014FF',
    textColor: '#00001499',
    longitude: 350,
    latitude: LATITUDES.lower,
  },
]
