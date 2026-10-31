import { Popover } from '@base-ui/react/popover'
import { CalendarDays } from 'lucide-react'
import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Calendar } from '@/components/ui/calendar'
import { cn } from '@/lib/utils'
import { formatDateTime } from './format'

export const INPUT_CLASS =
  'min-h-11 w-full min-w-0 rounded-md border border-input bg-background px-3 py-2 text-sm leading-5 outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50'

// В API дата без зоны, а календарь работает с местным временем: день не должен съехать при переводе.
function parseDate(value: string) {
  const [year, month, day] = value.split('-').map(Number)
  return new Date(year, month - 1, day)
}

function toIsoDate(date: Date) {
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  return `${date.getFullYear()}-${month}-${day}`
}

interface DateFieldProps {
  value: string
  onChange: (value: string) => void
  placeholder: string
  required?: boolean
  // Раньше этой даты выбрать нельзя.
  min?: string
  clearLabel?: string
}

export function DateField({ value, onChange, placeholder, required, min, clearLabel }: DateFieldProps) {
  const [open, setOpen] = useState(false)
  const selected = value ? parseDate(value) : undefined

  return (
    <div className="relative">
      <Popover.Root open={open} onOpenChange={setOpen}>
        <Popover.Trigger className={cn(INPUT_CLASS, 'flex cursor-pointer items-center justify-between gap-2 text-left', !value && 'text-muted-foreground')}>
          <span className="min-w-0 wrap-anywhere">{value ? formatDateTime(value) : placeholder}</span>
          <CalendarDays className="size-4 shrink-0 text-muted-foreground" aria-hidden="true" />
        </Popover.Trigger>
        <Popover.Portal>
          <Popover.Positioner side="bottom" align="start" sideOffset={8} className="z-50">
            <Popover.Popup className="flex origin-[var(--transform-origin)] flex-col gap-2 rounded-lg border bg-popover p-2 text-popover-foreground shadow-lg outline-none transition-[opacity,transform] duration-150 data-ending-style:scale-95 data-ending-style:opacity-0 data-starting-style:scale-95 data-starting-style:opacity-0">
              <Calendar
                mode="single"
                autoFocus
                required={false}
                selected={selected}
                defaultMonth={selected ?? (min ? parseDate(min) : undefined)}
                disabled={min ? { before: parseDate(min) } : undefined}
                onSelect={(date) => {
                  // Повторный клик по выбранному дню снимает выбор. Обязательную дату так не сбрасываем.
                  if (date) onChange(toIsoDate(date))
                  else if (clearLabel) onChange('')
                  setOpen(false)
                }}
              />
              {clearLabel && value && (
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => {
                    onChange('')
                    setOpen(false)
                  }}
                >
                  {clearLabel}
                </Button>
              )}
            </Popover.Popup>
          </Popover.Positioner>
        </Popover.Portal>
      </Popover.Root>
      {/* Кнопка не участвует в проверке формы, поэтому обязательность держит скрытое поле. */}
      {required && <input tabIndex={-1} aria-hidden="true" required value={value} onChange={() => {}} className="pointer-events-none absolute inset-x-0 bottom-0 h-px opacity-0" />}
    </div>
  )
}

function maskTime(raw: string) {
  const digits = raw.replace(/\D/g, '').slice(0, 4)
  return digits.length > 2 ? `${digits.slice(0, 2)}:${digits.slice(2)}` : digits
}

interface TimeFieldProps {
  value: string
  onChange: (value: string) => void
  required?: boolean
  disabled?: boolean
}

export function TimeField({ value, onChange, required, disabled }: TimeFieldProps) {
  return (
    <input
      inputMode="numeric"
      placeholder="ЧЧ:ММ"
      pattern="([01][0-9]|2[0-3]):[0-5][0-9]"
      title="Время в формате ЧЧ:ММ, например 09:30"
      required={required}
      disabled={disabled}
      value={value}
      onChange={(event) => onChange(maskTime(event.target.value))}
      className={cn(INPUT_CLASS, 'tabular-nums')}
    />
  )
}
