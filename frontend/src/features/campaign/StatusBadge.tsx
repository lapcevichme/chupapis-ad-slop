import { cn } from '@/lib/utils'
import type { CampaignState } from '@/types/api'

// Таблица из docs/ours/design.md. Подпись обязательна: цвет сам по себе статус не передаёт.
const STATES: Record<CampaignState, { label: string; className: string }> = {
  DRAFT: { label: 'Черновик', className: 'bg-muted text-foreground' },
  ON_MODERATION: { label: 'На модерации', className: 'bg-info text-info-foreground' },
  NEEDS_WORK: { label: 'Нужны правки', className: 'bg-warning text-warning-foreground' },
  APPROVED: { label: 'Одобрена', className: 'bg-success text-success-foreground' },
  ACTIVE: { label: 'Активна', className: 'bg-primary text-primary-foreground' },
  ACTIVE_EDITING: { label: 'Активна, есть правки', className: 'bg-warning text-warning-foreground' },
  STOPPED: { label: 'Остановлена', className: 'bg-error text-error-foreground' },
  ARCHIVED: { label: 'В архиве', className: 'bg-muted text-foreground' },
}

export function StatusBadge({ state }: { state: CampaignState }) {
  const { label, className } = STATES[state]
  return <span className={cn('inline-flex rounded-sm px-2.5 py-1 text-[13px] leading-[18px] font-medium', className)}>{label}</span>
}
