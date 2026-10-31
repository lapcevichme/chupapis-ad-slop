import { CircleAlert } from 'lucide-react'
import { Button } from '@/components/ui/button'
import type { Confirmation, ConfirmationChange, OperationKind } from '@/types/api'

// Глагол на кнопке называет действие. Опасные действия контурные: цвет сам по себе их не отличает.
const ACTIONS: Partial<Record<OperationKind, { label: string; danger?: boolean }>> = {
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
  const known = Object.entries(ACTIONS).find(([kind]) => kinds.includes(kind as OperationKind))
  return known?.[1] ?? { label: 'Подтвердить', danger: false }
}

function formatValue(value: unknown) {
  if (value === null || value === undefined || value === '') return 'не задано'
  if (Array.isArray(value)) return value.join(', ')
  return typeof value === 'object' ? JSON.stringify(value) : String(value)
}

function Change({ change }: { change: ConfirmationChange }) {
  return (
    <div className="flex flex-col gap-0.5">
      <dt className="text-xs leading-4 opacity-80">{change.label}</dt>
      <dd className="m-0 text-[13px] leading-[18px] wrap-anywhere">
        {formatValue(change.from)} → <span className="font-medium">{formatValue(change.to)}</span>
      </dd>
    </div>
  )
}

interface ConfirmationCardProps {
  confirmation: Confirmation
  onApprove: () => void
  onReject: () => void
}

export function ConfirmationCard({ confirmation, onApprove, onReject }: ConfirmationCardProps) {
  const action = primaryAction(confirmation)
  const toModeration = confirmation.operations.some((operation) => operation.kind === 'to_moderation')

  return (
    <section aria-label="Подтверждение записи" className="flex flex-col gap-3 rounded-lg border border-accent-foreground/30 bg-accent p-4 text-accent-foreground">
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
      {confirmation.changes.length > 0 && (
        <dl className="m-0 flex flex-col gap-2 border-t border-accent-foreground/30 pt-3">
          {confirmation.changes.map((change) => (
            <Change key={change.field} change={change} />
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
