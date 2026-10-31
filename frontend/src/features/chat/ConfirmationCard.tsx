import { CircleAlert } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { formatDateTime } from '@/features/campaign/format'
import type { Confirmation, ConfirmationChange, Dictionaries } from '@/types/api'

// Глагол на кнопке называет действие. Опасные действия контурные: цвет сам по себе их не отличает.
const ACTIONS: Record<string, { label: string; danger?: boolean }> = {
  delete_campaign: { label: 'Удалить кампанию', danger: true },
  stop: { label: 'Остановить показ', danger: true },
  decline: { label: 'Вернуть на правки', danger: true },
  delete_banner: { label: 'Удалить', danger: true },
  delete_content: { label: 'Удалить', danger: true },
  delete_creative: { label: 'Удалить', danger: true },
  activate: { label: 'Запустить показ' },
  approve: { label: 'Одобрить' },
  to_moderation: { label: 'Отправить на модерацию' },
}

function primaryAction(confirmation: Confirmation) {
  const kinds = confirmation.operations.map((operation) => operation.kind)
  const known = Object.entries(ACTIONS).find(([kind]) => kinds.includes(kind))
  return known?.[1] ?? { label: 'Подтвердить', danger: false }
}

const AUDIENCE_LABELS: Record<string, string> = { ALL_USERS: 'Все пользователи', SEGMENTED: 'По сегментам' }

function isEmpty(value: unknown) {
  return value === null || value === undefined || value === '' || (Array.isArray(value) && value.length === 0)
}

// В changes приходят сырые значения полей: человек подтверждает запись, поэтому показываем ему названия из справочников.
function formatValue(field: string, value: unknown, dictionaries?: Dictionaries): string {
  if (isEmpty(value)) return 'не задано'
  if (Array.isArray(value)) return value.map((item) => formatValue(field, item, dictionaries)).join(', ')
  if (field === 'audienceType') return AUDIENCE_LABELS[String(value)] ?? String(value)
  if (field === 'startDate' || field === 'endDate') return formatDateTime(String(value))
  if (field === 'topic') return dictionaries?.topics.find((item) => item.value === value)?.label ?? String(value)
  if (field === 'tags') return dictionaries?.tags.find((item) => item.id === value)?.name ?? String(value)
  if (field === 'places') return dictionaries?.places.find((item) => item.id === value)?.description ?? String(value)
  if (field.startsWith('segments.')) return dictionaries?.segments.find((item) => item.code === value)?.name ?? String(value)
  return typeof value === 'object' ? JSON.stringify(value) : String(value)
}

function Change({ change, dictionaries }: { change: ConfirmationChange; dictionaries?: Dictionaries }) {
  const to = formatValue(change.field, change.to, dictionaries)
  return (
    <div className="text-[13px] leading-[18px] wrap-anywhere">
      <dt className="inline opacity-80">{change.label}: </dt>
      <dd className="m-0 inline">
        {!isEmpty(change.from) && <>{formatValue(change.field, change.from, dictionaries)} → </>}
        <span className="font-medium">{to}</span>
      </dd>
    </div>
  )
}

interface ConfirmationCardProps {
  confirmation: Confirmation
  dictionaries?: Dictionaries
  onApprove: () => void
  onReject: () => void
}

export function ConfirmationCard({ confirmation, dictionaries, onApprove, onReject }: ConfirmationCardProps) {
  const action = primaryAction(confirmation)
  const changes = confirmation.changes.filter((change) => !isEmpty(change.from) || !isEmpty(change.to))
  const toModeration = confirmation.operations.some((operation) => operation.kind === 'to_moderation')

  return (
    <section aria-label="Подтверждение записи" className="flex animate-rise flex-col gap-3 rounded-lg border border-accent-foreground/30 bg-accent p-4 text-accent-foreground">
      <h3 className="m-0 text-sm leading-5 font-semibold wrap-anywhere">{confirmation.title}</h3>
      {confirmation.operations.length > 0 && (
        <ul className="m-0 flex list-disc flex-col gap-1 pl-5 text-[13px] leading-[18px]">
          {confirmation.operations.map((operation) => (
            <li key={`${operation.kind}-${operation.label}`} className="wrap-anywhere">
              {operation.label}
            </li>
          ))}
        </ul>
      )}
      {changes.length > 0 && (
        <dl className="m-0 flex flex-col gap-1 border-t border-accent-foreground/30 pt-3">
          {changes.map((change) => (
            <Change key={change.field} change={change} dictionaries={dictionaries} />
          ))}
        </dl>
      )}
      {toModeration && (
        <p className="m-0 flex items-start gap-2 text-[13px] leading-[18px]">
          <CircleAlert className="mt-px size-4 shrink-0" aria-hidden="true" />
          Перед отправкой проверьте превью справа.
        </p>
      )}
      <div className="flex flex-wrap gap-2">
        <Button variant={action.danger ? 'destructive' : 'default'} className="flex-1" onClick={onApprove}>
          {action.label}
        </Button>
        <Button variant="outline" className="flex-1" onClick={onReject}>
          Не подтверждать
        </Button>
      </div>
      <p className="m-0 text-xs leading-4 opacity-80">Или напишите ниже, что изменить: это отменит предложение.</p>
    </section>
  )
}
