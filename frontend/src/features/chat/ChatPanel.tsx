import { Check, CircleAlert, LoaderCircle, SendHorizontal, X } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import type { KeyboardEvent, SyntheticEvent } from 'react'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'
import type { ChatStep } from '@/types/api'
import { ConfirmationCard } from './ConfirmationCard'
import type { ChatMessage, useChat } from './useChat'

// Бриф из §9 задания: с него начинается демо.
const EXAMPLE_BRIEF = 'Кампания по вкладу для клиентов 26–45 в Москве и СПб, промо на главном, ставка 16%, с 5 ноября до конца года'

const STICK_THRESHOLD_PX = 48

function Step({ step }: { step: ChatStep }) {
  return (
    <li className={cn('flex items-center gap-2 text-[13px] leading-[18px] text-muted-foreground', step.status === 'failed' && 'text-destructive')}>
      {step.status === 'running' && <LoaderCircle className="size-4 shrink-0 animate-spin" aria-hidden="true" />}
      {step.status === 'done' && <Check className="size-4 shrink-0" aria-hidden="true" />}
      {step.status === 'failed' && <X className="size-4 shrink-0" aria-hidden="true" />}
      <span className="min-w-0 wrap-anywhere">
        {step.label}
        {step.status === 'failed' && ': не удалось'}
      </span>
    </li>
  )
}

function Message({ message, thinking }: { message: ChatMessage; thinking: boolean }) {
  if (message.role === 'user') {
    return <p className="m-0 max-w-[85%] self-end rounded-lg bg-secondary px-3 py-2 text-sm leading-5 wrap-anywhere whitespace-pre-wrap text-secondary-foreground">{message.text}</p>
  }

  return (
    <div className="flex flex-col gap-2">
      {message.steps.length > 0 && (
        <ul className="m-0 flex list-none flex-col gap-1 p-0">
          {message.steps.map((step) => (
            <Step key={step.id} step={step} />
          ))}
        </ul>
      )}
      {/* Текст приходит от LLM, поэтому выводим его только как текст */}
      {message.text && <p className="m-0 text-sm leading-5 wrap-anywhere whitespace-pre-wrap">{message.text}</p>}
      {thinking && <p className="m-0 text-[13px] leading-[18px] text-muted-foreground">Ассистент думает…</p>}
    </div>
  )
}

function SuggestionButton({ children, onClick }: { children: string; onClick: () => void }) {
  return (
    <Button variant="outline" className="h-auto min-h-11 py-2 text-left whitespace-normal" onClick={onClick}>
      {children}
    </Button>
  )
}

export function ChatPanel({ chat }: { chat: ReturnType<typeof useChat> }) {
  const { busy, messages, suggestions, confirmation, error, send, answer, retry } = chat
  const [text, setText] = useState('')
  const log = useRef<HTMLDivElement>(null)
  const stickToBottom = useRef(true)

  useEffect(() => {
    if (log.current && stickToBottom.current) log.current.scrollTop = log.current.scrollHeight
  }, [messages, suggestions, confirmation, error])

  function submit(value: string) {
    const trimmed = value.trim()
    if (!trimmed || busy) return
    stickToBottom.current = true
    setText('')
    void send(trimmed)
  }

  function handleKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === 'Enter' && !event.shiftKey && !event.nativeEvent.isComposing) {
      event.preventDefault()
      submit(text)
    }
  }

  function handleScroll(event: SyntheticEvent<HTMLDivElement>) {
    const { scrollTop, scrollHeight, clientHeight } = event.currentTarget
    stickToBottom.current = scrollHeight - scrollTop - clientHeight < STICK_THRESHOLD_PX
  }

  const last = messages.at(-1)
  const thinking = busy && last?.role === 'assistant' && !last.text && last.steps.every((step) => step.status !== 'running')

  return (
    <div className="flex h-full flex-col">
      <div ref={log} role="log" aria-label="Сообщения" onScroll={handleScroll} className="flex min-h-0 flex-1 flex-col gap-4 overflow-y-auto p-4">
        {messages.length === 0 && !busy && (
          <div className="flex flex-col gap-3">
            <p className="m-0 text-sm leading-5">Опишите кампанию своими словами: продукт, аудиторию, сроки. Я соберу черновик и покажу его перед сохранением.</p>
            <SuggestionButton onClick={() => submit(EXAMPLE_BRIEF)}>{EXAMPLE_BRIEF}</SuggestionButton>
          </div>
        )}
        {messages.map((message, index) => (
          <Message key={index} message={message} thinking={thinking && index === messages.length - 1} />
        ))}
        {suggestions.length > 0 && !busy && (
          <div className="flex flex-wrap gap-2">
            {suggestions.map((item) => (
              <SuggestionButton key={item.value} onClick={() => submit(item.value)}>
                {item.label}
              </SuggestionButton>
            ))}
          </div>
        )}
        {confirmation && !busy && (
          <ConfirmationCard
            confirmation={confirmation}
            onApprove={() => {
              stickToBottom.current = true
              void answer(confirmation.id, { approved: true })
            }}
            onReject={() => {
              stickToBottom.current = true
              void answer(confirmation.id, { approved: false })
            }}
          />
        )}
        {error && (
          <div role="alert" className="flex flex-col gap-2 rounded-md bg-error px-3 py-2 text-[13px] leading-[18px] text-error-foreground">
            <p className="m-0 flex items-start gap-2">
              <CircleAlert className="mt-px size-4 shrink-0" aria-hidden="true" />
              {error.message}
            </p>
            {error.retryable && (
              <Button variant="outline" className="self-start" onClick={() => void retry()}>
                Повторить
              </Button>
            )}
          </div>
        )}
      </div>

      <form
        className="flex items-end gap-2 border-t p-3"
        onSubmit={(event) => {
          event.preventDefault()
          submit(text)
        }}
      >
        <textarea
          aria-label="Сообщение ассистенту"
          rows={2}
          value={text}
          placeholder={confirmation ? 'Что изменить?' : 'Напишите сообщение'}
          onChange={(event) => setText(event.target.value)}
          onKeyDown={handleKeyDown}
          className="min-h-11 min-w-0 flex-1 resize-none rounded-md border border-input bg-background px-3 py-2 text-sm leading-5 outline-none placeholder:text-muted-foreground focus-visible:ring-2 focus-visible:ring-ring"
        />
        <Button type="submit" size="icon" aria-label="Отправить" disabled={busy || !text.trim()}>
          <SendHorizontal aria-hidden="true" />
        </Button>
      </form>
    </div>
  )
}
