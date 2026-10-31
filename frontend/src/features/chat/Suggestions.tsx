import { Check } from 'lucide-react'
import { useState } from 'react'
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
}

function QuestionBlock({ question, answer, onPick, onOwn, onSubmitOwn }: QuestionProps) {
  const ownActive = answer.own.trim() !== ''

  return (
    <fieldset className="m-0 flex min-w-0 flex-col gap-2 border-0 p-0">
      <legend className="flex flex-col gap-1 p-0">
        <span className="w-fit rounded-md bg-muted px-2 py-0.5 text-xs leading-4 font-medium text-muted-foreground">{question.header}</span>
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

export function Suggestions({ questions, onSend }: SuggestionsProps) {
  const [answers, setAnswers] = useState<Record<number, Answer>>({})
  const single = questions.length === 1 && !questions[0].multiSelect

  const texts = questions.map((question, index) => answerText(question, answers[index] ?? EMPTY))
  const answered = texts.filter(Boolean).length

  function submit() {
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
    update(index, (answer) => {
      if (questions[index].multiSelect) {
        const picked = answer.picked.includes(value) ? answer.picked.filter((v) => v !== value) : [...answer.picked, value]
        return { ...answer, picked }
      }
      return { picked: answer.picked[0] === value && !answer.own.trim() ? [] : [value], own: '' }
    })
  }

  return (
    <section aria-label="Вопросы ассистента" className="flex flex-col gap-4 rounded-lg border border-border bg-card p-4">
      {questions.map((question, index) => (
        <QuestionBlock
          key={`${question.header}-${question.question}`}
          question={question}
          answer={answers[index] ?? EMPTY}
          onPick={(value) => pick(index, value)}
          onOwn={(own) => update(index, (answer) => ({ ...answer, own }))}
          onSubmitOwn={submit}
        />
      ))}
      {!single && (
        <div className="flex flex-wrap items-center gap-3">
          <Button disabled={answered === 0} onClick={submit}>
            Отправить {questions.length > 1 ? 'ответы' : 'ответ'}
          </Button>
          {questions.length > 1 && (
            <span className="text-[13px] leading-[18px] text-muted-foreground tabular-nums">
              Отвечено {answered} из {questions.length}
            </span>
          )}
        </div>
      )}
    </section>
  )
}
