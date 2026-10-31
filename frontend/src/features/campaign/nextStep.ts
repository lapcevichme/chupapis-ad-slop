import type { CampaignState } from '@/types/api'

export interface NextStep {
  title: string
  actions: { label: string; message: string }[]
}

export const TO_MODERATION = 'Отправь кампанию на модерацию'
const MAKE_CREATIVE = { label: 'Сделать креатив', message: 'Сделай креатив для кампании' }

// Кнопки только формулируют просьбу к агенту: запись всё равно идёт через карточку подтверждения.
// Без креативов API модерацию не блокирует (только warning), но предлагать отправку такой кампании рано.
export function managerNextStep(state: CampaignState, errorCount: number, hasCreatives: boolean): NextStep | null {
  switch (state) {
    case 'DRAFT':
    case 'ACTIVE_EDITING':
      if (errorCount > 0) {
        return { title: `Отправить нельзя, ошибок в проверке: ${errorCount}`, actions: [{ label: 'Исправить ошибки', message: 'Помоги исправить ошибки проверки кампании' }] }
      }
      return hasCreatives
        ? { title: 'Ошибок нет, можно отправлять', actions: [{ label: 'Отправить на модерацию', message: TO_MODERATION }] }
        : { title: 'Креативов пока нет', actions: [MAKE_CREATIVE] }
    case 'NEEDS_WORK':
      return {
        title: 'Модератор вернул кампанию на правки',
        actions: [
          { label: 'Исправить по комментарию', message: 'Исправь кампанию по комментарию модератора' },
          ...(errorCount > 0 || !hasCreatives ? [] : [{ label: 'Отправить повторно', message: TO_MODERATION }]),
        ],
      }
    case 'APPROVED':
      return { title: 'Кампания одобрена', actions: [{ label: 'Запустить показ', message: 'Запусти показ кампании' }] }
    default:
      return null
  }
}
