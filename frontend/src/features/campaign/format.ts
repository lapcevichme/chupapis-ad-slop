const DATE_FORMAT = new Intl.DateTimeFormat('ru-RU', { day: 'numeric', month: 'long', year: 'numeric', timeZone: 'UTC' })
const COUNT_FORMAT = new Intl.NumberFormat('ru-RU')

export function formatDateTime(date: string, time?: string) {
  const formatted = DATE_FORMAT.format(new Date(`${date}T00:00:00Z`)).replace(' г.', '')
  return time ? `${formatted}, ${time}` : formatted
}

export function formatCount(count: number) {
  return COUNT_FORMAT.format(count)
}
