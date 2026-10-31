import { Check } from 'lucide-react'
import { useState } from 'react'
import type { ReactNode } from 'react'
import { Button } from '@/components/ui/button'
import type { Suggestion } from '@/types/api'

interface SuggestionButtonProps {
  children: ReactNode
  pressed?: boolean
  onClick: () => void
}

export function SuggestionButton({ children, pressed, onClick }: SuggestionButtonProps) {
  return (
    <Button variant={pressed ? 'default' : 'outline'} aria-pressed={pressed} className="h-auto min-h-11 py-2 text-left whitespace-normal" onClick={onClick}>
      {pressed && <Check aria-hidden="true" />}
      {children}
    </Button>
  )
}

interface SuggestionsProps {
  items: Suggestion[]
  onSend: (text: string) => void
}

export function Suggestions({ items, onSend }: SuggestionsProps) {
  const [selected, setSelected] = useState<Record<string, string>>({})
  const groups = [...new Set(items.map((item) => item.group ?? ''))]

  if (groups.length < 2) {
    return (
      <div className="flex flex-wrap gap-2">
        {items.map((item) => (
          <SuggestionButton key={item.value} onClick={() => onSend(item.value)}>
            {item.label}
          </SuggestionButton>
        ))}
      </div>
    )
  }

  // Несколько тем сразу: по варианту в каждой, отправляем одним сообщением.
  function toggle(group: string, value: string) {
    setSelected((current) => {
      const next = { ...current }
      if (next[group] === value) delete next[group]
      else next[group] = value
      return next
    })
  }

  const answers = groups.flatMap((group) => selected[group] ?? [])

  return (
    <div className="flex flex-col gap-3">
      {groups.map((group) => (
        <div key={group} role="group" aria-label={group || 'Варианты'} className="flex flex-col gap-2">
          {group && <span className="text-[13px] leading-[18px] font-medium">{group}</span>}
          <div className="flex flex-wrap gap-2">
            {items
              .filter((item) => (item.group ?? '') === group)
              .map((item) => (
                <SuggestionButton key={item.value} pressed={selected[group] === item.value} onClick={() => toggle(group, item.value)}>
                  {item.label}
                </SuggestionButton>
              ))}
          </div>
        </div>
      ))}
      <div className="flex flex-wrap items-center gap-3">
        <Button variant="secondary" disabled={answers.length === 0} onClick={() => onSend(answers.join('\n'))}>
          Отправить ответы
        </Button>
        <span className="text-[13px] leading-[18px] text-muted-foreground tabular-nums">
          Выбрано {answers.length} из {groups.length}
        </span>
      </div>
    </div>
  )
}
