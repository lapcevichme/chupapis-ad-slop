import { Check, Circle, CircleDot, MessageSquareWarning } from 'lucide-react'
import { cn } from '@/lib/utils'
import type { AuditRecord, CampaignState, CampaignValidation } from '@/types/api'
import { Flash } from './Flash'
import { formatTimestamp, STATE_LABELS } from './format'
import { ValidationSummary } from './ValidationSummary'

// Основной поток из §2.3 задания. Возвраты и остановка занимают тот же шаг под своей подписью.
const STEPS: CampaignState[][] = [['DRAFT', 'NEEDS_WORK'], ['ON_MODERATION'], ['APPROVED'], ['ACTIVE', 'ACTIVE_EDITING', 'STOPPED', 'ARCHIVED']]

const LIFECYCLE_ACTIONS: Record<string, string> = {
  TO_MODERATION: 'Отправка на модерацию',
  DECLINE: 'Возврат на правки',
  APPROVE: 'Одобрение',
  ACTIVATE: 'Запуск показа',
  STOP: 'Остановка показа',
}

const EDIT_ACTIONS: Record<string, string> = { CREATE: 'Создание', UPDATE: 'Изменение', DELETE: 'Удаление' }

const ENTITIES: Record<string, string> = {
  CAMPAIGN: 'кампании',
  BANNER: 'баннера',
  CONTENT: 'промо-экрана',
  CREATIVE: 'креатива',
  SEGMENTS: 'сегментов',
}

function recordTitle({ action, entity, entityId }: AuditRecord) {
  if (LIFECYCLE_ACTIONS[action]) return LIFECYCLE_ACTIONS[action]
  const subject = ENTITIES[entity] ?? entity
  const id = entity === 'CAMPAIGN' || entity === 'SEGMENTS' ? '' : ` ${entityId}`
  return `${EDIT_ACTIONS[action] ?? action} ${subject}${id}`
}

function Steps({ state }: { state: CampaignState }) {
  const current = STEPS.findIndex((states) => states.includes(state))

  return (
    <ol className="m-0 flex list-none flex-wrap gap-x-3 gap-y-1 p-0 text-[13px] leading-[18px]">
      {STEPS.map((states, index) => {
        const active = index === current
        const Icon = active ? CircleDot : index < current ? Check : Circle
        return (
          <li
            key={states[0]}
            aria-current={active ? 'step' : undefined}
            className={cn('flex items-center gap-1.5 rounded-md py-1 text-muted-foreground', active && 'bg-accent px-2 font-semibold text-accent-foreground')}
          >
            <Icon key={String(active)} className={cn('size-4 shrink-0', active && 'animate-pop')} aria-hidden="true" />
            {STATE_LABELS[active ? state : states[0]]}
          </li>
        )
      })}
    </ol>
  )
}

interface CampaignLifecycleProps {
  state: CampaignState
  audit?: AuditRecord[]
  validation?: CampaignValidation
}

export function CampaignLifecycle({ state, audit = [], validation }: CampaignLifecycleProps) {
  // Сервер отдаёт журнал от старых записей к новым, а записи одного пакета могут совпасть по времени.
  // Номер в журнале не меняется при появлении новых записей, поэтому годится как ключ.
  const records = audit
    .map((record, order) => ({ ...record, order }))
    .reverse()
    .sort((a, b) => b.at.localeCompare(a.at))
  const decline = state === 'NEEDS_WORK' ? records.find((record) => record.action === 'DECLINE') : undefined

  return (
    <section className="flex flex-col gap-3 rounded-lg border bg-card p-4 text-card-foreground">
      <h2 className="m-0 text-sm leading-5 font-semibold">Ход кампании</h2>
      <Flash value={state}>
        <Steps state={state} />
      </Flash>
      {decline && (
        <div className="flex animate-rise items-start gap-2 rounded-md bg-warning px-3 py-2 text-[13px] leading-[18px] text-warning-foreground">
          <MessageSquareWarning className="mt-px size-4 shrink-0" aria-hidden="true" />
          <div className="flex min-w-0 flex-col gap-0.5">
            <span className="font-semibold">Комментарий модератора</span>
            <span className="wrap-anywhere whitespace-pre-wrap">{decline.comment}</span>
            <span className="text-xs leading-4">
              {decline.actor}, {formatTimestamp(decline.at)}
            </span>
          </div>
        </div>
      )}
      {validation && (
        <Flash value={JSON.stringify(validation)}>
          <ValidationSummary validation={validation} />
        </Flash>
      )}
      {records.length > 0 && (
        <details>
          <summary className="flex min-h-11 cursor-pointer items-center rounded-md text-[13px] leading-[18px] font-medium outline-none focus-visible:ring-2 focus-visible:ring-ring">
            Журнал действий: {records.length}
          </summary>
          <ol className="m-0 flex list-none flex-col p-0">
            {records.map((record) => (
              <li key={record.order} className="flex animate-rise flex-col gap-0.5 border-t py-2 last:pb-0">
                <span className="text-[13px] leading-[18px] font-medium">{recordTitle(record)}</span>
                <span className="text-xs leading-4 text-muted-foreground">
                  {record.actor}, {formatTimestamp(record.at)}
                </span>
                {record.comment && <span className="text-[13px] leading-[18px] wrap-anywhere whitespace-pre-wrap">{record.comment}</span>}
              </li>
            ))}
          </ol>
        </details>
      )}
    </section>
  )
}
