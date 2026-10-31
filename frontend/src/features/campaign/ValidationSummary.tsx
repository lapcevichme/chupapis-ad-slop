import { CircleAlert, CircleCheck, TriangleAlert } from 'lucide-react'
import type { CampaignValidation } from '@/types/api'

export function ValidationSummary({ validation }: { validation: CampaignValidation }) {
  const { errors, warnings } = validation

  if (errors.length === 0 && warnings.length === 0) {
    return (
      <p className="m-0 flex items-center gap-2 rounded-md bg-success px-3 py-2 text-[13px] leading-[18px] text-success-foreground">
        <CircleCheck className="size-4 shrink-0" aria-hidden="true" />
        Ошибок и предупреждений нет
      </p>
    )
  }

  return (
    <ul className="m-0 flex list-none flex-col gap-2 p-0">
      {errors.map((error) => (
        <li
          key={`${error.code}-${error.field ?? ''}`}
          className="flex items-start gap-2 rounded-md bg-error px-3 py-2 text-[13px] leading-[18px] text-error-foreground"
        >
          <CircleAlert className="mt-px size-4 shrink-0" aria-hidden="true" />
          <span>
            <span className="font-medium">Ошибка: </span>
            {error.message}
          </span>
        </li>
      ))}
      {warnings.map((warning) => (
        <li
          key={warning}
          className="flex items-start gap-2 rounded-md bg-warning px-3 py-2 text-[13px] leading-[18px] text-warning-foreground"
        >
          <TriangleAlert className="mt-px size-4 shrink-0" aria-hidden="true" />
          <span>
            <span className="font-medium">Предупреждение: </span>
            {warning}
          </span>
        </li>
      ))}
    </ul>
  )
}
