import { ArrowLeft, Mic } from 'lucide-react'
import { useEffect, useRef } from 'react'
import { Button } from '@/components/ui/button'
import { ChatMarkdown } from '@/features/chat/ChatMarkdown'
import { SuggestionButton } from '@/features/chat/Suggestions'
import { cn } from '@/lib/utils'
import { formatAnswers } from './questionnaire'
import type { Answer, Answers, QuestionPage } from './questionnaire'

// Пауза даёт увидеть отмеченный вариант перед переходом на следующую страницу.
const ADVANCE_DELAY_MS = 220

interface QuestionnaireProps {
  pages: QuestionPage[]
  answers: Answers
  page: number
  intro?: string
  introPage: number
  notes: string[]
  onAnswer: (group: string, answer: Answer | null) => void
  onPage: (page: number) => void
  onDiscuss: (group: string) => void
  onSubmit: () => void
}

export function Questionnaire({ pages, answers, page, intro, introPage, notes, onAnswer, onPage, onDiscuss, onSubmit }: QuestionnaireProps) {
  const current = pages[Math.min(page, pages.length - 1)]
  const index = pages.indexOf(current)
  const last = index === pages.length - 1
  const answer = answers[current.group]
  const heading = useRef<HTMLHeadingElement>(null)
  const advance = useRef<ReturnType<typeof setTimeout> | undefined>(undefined)
  const canSubmit = formatAnswers(pages, answers) !== ''

  useEffect(() => () => clearTimeout(advance.current), [])
  useEffect(() => {
    clearTimeout(advance.current)
    heading.current?.focus({ preventScroll: true })
  }, [index])

  function choose(value: string) {
    clearTimeout(advance.current)
    if (answer?.value === value && !answer.custom) {
      onAnswer(current.group, null)
      return
    }
    onAnswer(current.group, { value, custom: false })
    if (!last) advance.current = setTimeout(() => onPage(index + 1), ADVANCE_DELAY_MS)
  }

  return (
    <div className="flex flex-col gap-4">
      {pages.length > 1 && (
        <div className="flex flex-col gap-2">
          <span className="text-[13px] leading-[18px] text-muted-foreground">
            Вопрос {index + 1} из {pages.length}
          </span>
          <div className="flex gap-1">
            {pages.map((item, position) => (
              <button
                key={item.group}
                type="button"
                aria-label={`Вопрос ${position + 1}: ${item.group}`}
                aria-current={position === index ? 'step' : undefined}
                onClick={() => onPage(position)}
                // Полоска тонкая, а нажимать удобно по всей высоте кнопки.
                className="group flex h-6 min-w-0 flex-1 items-center rounded-sm focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none"
              >
                <span className={cn('h-1 w-full rounded-full transition-colors', position === index ? 'bg-primary' : answers[item.group] ? 'bg-primary/40' : 'bg-secondary group-hover:bg-secondary-hover')} />
              </button>
            ))}
          </div>
        </div>
      )}

      {index === introPage && intro && (
        <div className="max-h-40 overflow-y-auto text-sm leading-5 text-muted-foreground">
          <ChatMarkdown text={intro} />
        </div>
      )}
      {index === introPage && notes.map((note) => (
        <p key={note} className="m-0 rounded-md bg-warning px-3 py-2 text-[13px] leading-[18px] text-warning-foreground">
          {note}
        </p>
      ))}

      <div key={current.group} className="flex animate-rise flex-col gap-3">
        <h2 ref={heading} tabIndex={-1} className="m-0 text-xl leading-7 font-semibold text-balance outline-none">
          {current.group || 'Выберите вариант'}
        </h2>
        {current.question && current.question !== current.group && <p className="m-0 -mt-1 text-sm leading-5 text-muted-foreground">{current.question}</p>}
        <div className="flex flex-col gap-2">
          {current.options.map((option) => (
            <SuggestionButton key={option.value} pressed={answer?.value === option.value && !answer.custom} onClick={() => choose(option.value)}>
              {option.label}
            </SuggestionButton>
          ))}
        </div>
        <input
          type="text"
          aria-label="Свой вариант"
          placeholder="Свой вариант"
          value={answer?.custom ? answer.value : ''}
          onChange={(event) => {
            clearTimeout(advance.current)
            onAnswer(current.group, event.target.value ? { value: event.target.value, custom: true } : null)
          }}
          onKeyDown={(event) => {
            if (event.key !== 'Enter' || event.nativeEvent.isComposing) return
            if (!last) onPage(index + 1)
            else if (canSubmit) onSubmit()
          }}
          className="h-11 min-w-0 rounded-md border border-input bg-background px-3 text-sm outline-none placeholder:text-muted-foreground focus-visible:ring-2 focus-visible:ring-ring"
        />
        <Button variant="secondary" onClick={() => onDiscuss(current.group)}>
          <Mic aria-hidden="true" />
          Обсудить голосом
        </Button>
      </div>

      <div className="flex items-center gap-2">
        {index > 0 && (
          <Button variant="ghost" onClick={() => onPage(index - 1)}>
            <ArrowLeft aria-hidden="true" />
            Назад
          </Button>
        )}
        {last ? (
          <Button className="flex-1" disabled={!canSubmit} onClick={onSubmit}>
            Отправить ответы
          </Button>
        ) : (
          <Button variant={answer ? 'default' : 'outline'} className="flex-1" onClick={() => onPage(index + 1)}>
            {answer ? 'Далее' : 'Пропустить'}
          </Button>
        )}
      </div>
    </div>
  )
}
