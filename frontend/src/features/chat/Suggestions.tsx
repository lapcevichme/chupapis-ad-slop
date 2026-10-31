import { ArrowLeft, Check } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import type { ReactNode } from 'react'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'
import type { SuggestionQuestion } from '@/types/api'

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

interface Answer {
  picked: string[]
  own: string
}

const EMPTY: Answer = { picked: [], own: '' }

function answerText(question: SuggestionQuestion, answer: Answer): string {
  const own = answer.own.trim()
  // В одиночном выборе своё значение заменяет вариант, в множественном добавляется к ним.
  if (!question.multiSelect) return own || answer.picked[0] || ''
  return [...answer.picked, ...(own ? [own] : [])].join(', ')
}

interface QuestionProps {
  question: SuggestionQuestion
  answer: Answer
  onPick: (value: string) => void
  onOwn: (text: string) => void
  onSubmitOwn: () => void
  // В пошаговом блоке тема уже видна в переключателе вопросов.
  showHeader: boolean
}

function QuestionBlock({ question, answer, onPick, onOwn, onSubmitOwn, showHeader }: QuestionProps) {
  const ownActive = answer.own.trim() !== ''

  return (
    <fieldset className="m-0 flex min-w-0 flex-col gap-2 border-0 p-0">
      <legend className="flex flex-col gap-1 p-0">
        {showHeader && <span className="w-fit rounded-md bg-muted px-2 py-0.5 text-xs leading-4 font-medium text-muted-foreground">{question.header}</span>}
        <span className="text-sm leading-5 font-semibold wrap-anywhere">{question.question}</span>
      </legend>
      <div className="flex flex-col gap-1.5">
        {question.options.map((option) => {
          const checked = answer.picked.includes(option.value) && (question.multiSelect || !ownActive)
          return (
            <button
              key={option.value}
              type="button"
              role={question.multiSelect ? 'checkbox' : 'radio'}
              aria-checked={checked}
              onClick={() => onPick(option.value)}
              className={cn(
                'flex min-h-11 w-full cursor-pointer items-start gap-3 rounded-lg border px-3 py-2 text-left transition-colors outline-none focus-visible:ring-2 focus-visible:ring-ring',
                checked ? 'border-primary bg-primary/10' : 'border-border bg-background hover:bg-muted',
              )}
            >
              <span
                aria-hidden="true"
                className={cn(
                  'mt-0.5 flex size-4 shrink-0 items-center justify-center border',
                  question.multiSelect ? 'rounded-sm' : 'rounded-full',
                  checked ? 'border-primary bg-primary text-primary-foreground' : 'border-input',
                )}
              >
                {checked && <Check className="size-3" />}
              </span>
              <span className="flex min-w-0 flex-col gap-0.5">
                <span className="text-sm leading-5 font-medium wrap-anywhere">{option.label}</span>
                {option.description && <span className="text-[13px] leading-[18px] text-muted-foreground wrap-anywhere">{option.description}</span>}
              </span>
            </button>
          )
        })}
        <input
          type="text"
          value={answer.own}
          onChange={(event) => onOwn(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === 'Enter' && !event.nativeEvent.isComposing) {
              event.preventDefault()
              onSubmitOwn()
            }
          }}
          placeholder="Свой вариант"
          aria-label={`${question.header}: свой вариант`}
          className={cn(
            'min-h-11 w-full rounded-lg border bg-background px-3 py-2 text-sm leading-5 outline-none placeholder:text-muted-foreground focus-visible:ring-2 focus-visible:ring-ring',
            ownActive ? 'border-primary' : 'border-border',
          )}
        />
      </div>
    </fieldset>
  )
}

interface SuggestionsProps {
  questions: SuggestionQuestion[]
  onSend: (text: string) => void
}

// Пауза даёт увидеть отмеченный вариант перед переходом к следующему вопросу.
const ADVANCE_DELAY_MS = 220

export function Suggestions({ questions, onSend }: SuggestionsProps) {
  const [answers, setAnswers] = useState<Record<number, Answer>>({})
  const [page, setPage] = useState(0)
  const advance = useRef<ReturnType<typeof setTimeout> | undefined>(undefined)
  const single = questions.length === 1 && !questions[0].multiSelect
  const paged = questions.length > 1
  const last = page === questions.length - 1

  const texts = questions.map((question, index) => answerText(question, answers[index] ?? EMPTY))
  const answered = texts.filter(Boolean).length

  useEffect(() => () => clearTimeout(advance.current), [])

  function goTo(index: number) {
    clearTimeout(advance.current)
    setPage(index)
  }

  function submit() {
    clearTimeout(advance.current)
    if (answered === 0) return
    if (questions.length === 1) {
      onSend(texts[0])
      return
    }
    onSend(
      questions
        .map((question, index) => texts[index] && `${question.header}: ${texts[index]}`)
        .filter(Boolean)
        .join('\n'),
    )
  }

  function update(index: number, change: (answer: Answer) => Answer) {
    setAnswers((current) => ({ ...current, [index]: change(current[index] ?? EMPTY) }))
  }

  function pick(index: number, value: string) {
    // Один вопрос с одним выбором: клик сразу отвечает, как раньше кнопка.
    if (single) {
      onSend(value)
      return
    }
    const question = questions[index]
    const current = answers[index] ?? EMPTY
    if (question.multiSelect) {
      const picked = current.picked.includes(value) ? current.picked.filter((v) => v !== value) : [...current.picked, value]
      update(index, () => ({ ...current, picked }))
      return
    }
    const unpick = current.picked[0] === value && !current.own.trim()
    update(index, () => ({ picked: unpick ? [] : [value], own: '' }))
    // Одиночный выбор отвечает на вопрос целиком: сразу показываем следующий.
    if (!unpick && paged && !last) {
      clearTimeout(advance.current)
      advance.current = setTimeout(() => setPage(index + 1), ADVANCE_DELAY_MS)
    }
  }

  const question = questions[page]

  return (
    <section aria-label="Вопросы ассистента" className="flex flex-col gap-4 rounded-lg border border-border bg-card p-4">
      {paged && (
        <nav aria-label="Вопросы" className="flex flex-wrap gap-1.5">
          {questions.map((item, index) => {
            const done = Boolean(texts[index])
            return (
              <button
                key={`${item.header}-${item.question}`}
                type="button"
                aria-current={index === page ? 'step' : undefined}
                aria-label={`Вопрос ${index + 1} из ${questions.length}: ${item.header}${done ? ', отвечен' : ''}`}
                onClick={() => goTo(index)}
                className={cn(
                  'flex min-h-8 cursor-pointer items-center gap-1 rounded-md px-2.5 text-xs leading-4 font-medium transition-colors outline-none focus-visible:ring-2 focus-visible:ring-ring',
                  index === page ? 'bg-primary text-primary-foreground' : done ? 'bg-primary/15 text-foreground hover:bg-primary/25' : 'bg-muted text-muted-foreground hover:bg-secondary',
                )}
              >
                {done && index !== page && <Check aria-hidden="true" className="size-3" />}
                {item.header}
              </button>
            )
          })}
        </nav>
      )}

      <div key={page} className="animate-rise">
        <QuestionBlock
          question={question}
          answer={answers[page] ?? EMPTY}
          onPick={(value) => pick(page, value)}
          onOwn={(own) => {
            clearTimeout(advance.current)
            update(page, (answer) => ({ ...answer, own }))
          }}
          onSubmitOwn={() => (paged && !last ? goTo(page + 1) : submit())}
          showHeader={!paged}
        />
      </div>

      {!single && (
        <div className="flex flex-wrap items-center gap-2">
          {paged && page > 0 && (
            <Button variant="ghost" onClick={() => goTo(page - 1)}>
              <ArrowLeft aria-hidden="true" />
              Назад
            </Button>
          )}
          {paged && !last ? (
            <Button variant={texts[page] ? 'default' : 'outline'} onClick={() => goTo(page + 1)}>
              {texts[page] ? 'Далее' : 'Пропустить'}
            </Button>
          ) : (
            <Button disabled={answered === 0} onClick={submit}>
              Отправить {paged ? 'ответы' : 'ответ'}
            </Button>
          )}
          {paged && (
            <span className="ml-auto text-[13px] leading-[18px] text-muted-foreground tabular-nums">
              Отвечено {answered} из {questions.length}
            </span>
          )}
        </div>
      )}
    </section>
  )
}
