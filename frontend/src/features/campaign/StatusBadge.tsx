import { cn } from '@/lib/utils'
import type { CampaignState } from '@/types/api'
import { STATE_LABELS } from './format'

// Подпись обязательна: цвет сам по себе статус не передаёт.
const STATE_CLASSES: Record<CampaignState, string> = {
  DRAFT: 'bg-muted text-foreground',
  ON_MODERATION: 'bg-info text-info-foreground',
  NEEDS_WORK: 'bg-warning text-warning-foreground',
  APPROVED: 'bg-success text-success-foreground',
  ACTIVE: 'bg-primary text-primary-foreground',
  ACTIVE_EDITING: 'bg-warning text-warning-foreground',
  STOPPED: 'bg-error text-error-foreground',
  ARCHIVED: 'bg-muted text-foreground',
}

export function StatusBadge({ state }: { state: CampaignState }) {
  return <span className={cn('inline-flex rounded-sm px-2.5 py-1 text-[13px] leading-[18px] font-medium', STATE_CLASSES[state])}>{STATE_LABELS[state]}</span>
}
