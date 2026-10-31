import type { CampaignState } from '@/types/api'

export interface NextStep {
  title: string
  actions: { label: string; message: string }[]
}

const TO_MODERATION = 'Отправь кампанию на модерацию'

// Кнопки только формулируют просьбу к агенту: запись всё равно идёт через карточку подтверждения.
export function managerNextStep(state: CampaignState, hasErrors: boolean): NextStep | null {
  switch (state) {
    case 'DRAFT':
    case 'ACTIVE_EDITING':
      return hasErrors
        ? { title: 'В кампании есть ошибки', actions: [{ label: 'Исправить ошибки', message: 'Помоги исправить ошибки проверки кампании' }] }
        : { title: 'Кампания готова к проверке', actions: [{ label: 'Отправить на модерацию', message: TO_MODERATION }] }
    case 'NEEDS_WORK':
      return {
        title: 'Модератор вернул кампанию на правки',
        actions: [
          { label: 'Исправить по комментарию', message: 'Исправь кампанию по комментарию модератора' },
          ...(hasErrors ? [] : [{ label: 'Отправить повторно', message: TO_MODERATION }]),
        ],
      }
    case 'APPROVED':
      return { title: 'Кампания одобрена', actions: [{ label: 'Запустить показ', message: 'Запусти показ кампании' }] }
    default:
      return null
  }
}
