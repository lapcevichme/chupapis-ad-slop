import type { CampaignState } from '@/types/api'

export const STATE_LABELS: Record<CampaignState, string> = {
  DRAFT: 'Черновик',
  ON_MODERATION: 'На модерации',
  NEEDS_WORK: 'Нужны правки',
  APPROVED: 'Одобрена',
  ACTIVE: 'Активна',
  ACTIVE_EDITING: 'Активна, есть правки',
  STOPPED: 'Остановлена',
  ARCHIVED: 'В архиве',
}

const DATE_FORMAT = new Intl.DateTimeFormat('ru-RU', { day: 'numeric', month: 'long', year: 'numeric', timeZone: 'UTC' })
const TIMESTAMP_FORMAT = new Intl.DateTimeFormat('ru-RU', { day: 'numeric', month: 'long', hour: '2-digit', minute: '2-digit', timeZone: 'UTC' })
const COUNT_FORMAT = new Intl.NumberFormat('ru-RU')

export function formatDateTime(date: string, time?: string | null) {
  const formatted = DATE_FORMAT.format(new Date(`${date}T00:00:00Z`)).replace(' г.', '')
  return time ? `${formatted}, ${time}` : formatted
}

// Время в API в UTC, но без указания зоны.
export function formatTimestamp(at: string) {
  const zoned = /(Z|[+-]\d{2}:?\d{2})$/.test(at) ? at : `${at}Z`
  return `${TIMESTAMP_FORMAT.format(new Date(zoned))} UTC`
}

export function formatCount(count: number) {
  return COUNT_FORMAT.format(count)
}
