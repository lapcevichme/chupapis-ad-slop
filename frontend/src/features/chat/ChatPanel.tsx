import { ArrowDown, ArrowUp, AudioLines, Check, ChevronDown, CircleAlert, Info, LoaderCircle, TriangleAlert, X } from 'lucide-react'
import { useEffect, useLayoutEffect, useRef, useState } from 'react'
import type { KeyboardEvent, ReactNode, SyntheticEvent } from 'react'
import { Button } from '@/components/ui/button'
import type { NextStep } from '@/features/campaign/nextStep'
import { parseImageMessage } from '@/features/imageUpload/imageMessage'
import { cn } from '@/lib/utils'
import type { CampaignListItem, ChatStep, ChatWarning, Dictionaries, UserRole } from '@/types/api'
import { AnimatedAnswer } from './AnimatedAnswer'
import { ConfirmationCard } from './ConfirmationCard'
import { MicButton } from './MicButton'
import { ModerationBar } from './ModerationBar'
import { ModerationQueue } from './ModerationQueue'
import { NextStepBar } from './NextStepBar'
import { Suggestions } from './Suggestions'
import { WelcomeTitle } from './WelcomeTitle'
import type { ChatMessage, useChat } from './useChat'
import { useDictation } from './useDictation'

// Первый бриф из §9 задания: с него начинается демо.
const EXAMPLE_BRIEFS = [
  { label: 'Вклад под 16%', prompt: 'Кампания по вкладу для клиентов 26–45 в Москве и СПб, промо на главном, ставка 16%, с 5 ноября до конца года' },
  { label: 'Кэшбэк по карте', prompt: 'Смарт-баннер про кэшбэк по карте для всех пользователей на главном экране, с 10 ноября по 10 декабря' },
  { label: 'Страхование путешествий', prompt: 'Сторис про страхование путешествий для клиентов из Москвы, с 1 по 31 декабря' },
]

const STICK_THRESHOLD_PX = 48

function Step({ step }: { step: ChatStep }) {
  return (
    <li className={cn('animate-rise flex items-center gap-2 text-[13px] leading-[18px] text-muted-foreground', step.status === 'failed' && 'text-destructive')}>
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

function Warning({ warning }: { warning: ChatWarning }) {
  const info = warning.severity === 'info'
  const Icon = info ? Info : TriangleAlert
  return (
    <p className={cn('m-0 flex items-start gap-2 rounded-md px-3 py-2 text-[13px] leading-[18px] wrap-anywhere', info ? 'bg-info text-info-foreground' : 'bg-warning text-warning-foreground')}>
      <Icon className="mt-px size-4 shrink-0" aria-hidden="true" />
      <span>
        <span className="font-medium">{info ? 'На заметку: ' : 'Предупреждение: '}</span>
        {warning.message}
      </span>
    </p>
  )
}

function Message({ message, thinking, active }: { message: ChatMessage; thinking: boolean; active: boolean }) {
  if (message.role === 'user') {
    const image = parseImageMessage(message.text)
    if (image) {
      return (
        <figure className="chat-user-message flex flex-col gap-2">
          <img src={image.url} alt="Загруженное фото" className="max-h-40 rounded-md object-contain" />
          <figcaption className="flex items-center gap-1.5 px-1">
            Загружено фото
            {image.colors.map((color) => (
              <span key={color} className="size-3.5 rounded-full border" style={{ backgroundColor: color }} aria-hidden="true" />
            ))}
          </figcaption>
        </figure>
      )
    }
    return <p className="chat-user-message">{message.text}</p>
  }

  const running = message.steps.findLast((step) => step.status === 'running')
  const failed = message.steps.some((step) => step.status === 'failed')
  return (
    <article className="assistant-message" aria-label="Ответ AdPilot">
      <div className="message-author"><span className="message-avatar" aria-hidden="true">a</span><strong>AdPilot</strong>{active && <span className="message-state">{message.text ? 'Пишет' : 'Работает'}</span>}</div>
      {active && running && <ul className="m-0 list-none p-0"><Step step={running} /></ul>}
      {!active && message.steps.length > 0 && (
        <details className={cn('message-steps', failed && 'has-failed-steps')}>
          <summary>{failed ? <CircleAlert size={14} aria-hidden="true" /> : <Check size={14} aria-hidden="true" />}Ход работы · {message.steps.length}<ChevronDown size={14} aria-hidden="true" /></summary>
        <ul className="m-0 flex list-none flex-col gap-1 p-0">
          {message.steps.map((step) => (
            <Step key={step.id} step={step} />
          ))}
        </ul>
        </details>
      )}
      {message.text && <AnimatedAnswer text={message.text} active={active} />}
      {message.warnings.map((warning) => (
        <Warning key={warning.message} warning={warning} />
      ))}
      {thinking && <span className="typing-indicator" role="status"><span aria-hidden="true"><i /><i /><i /></span>Готовлю ответ</span>}
    </article>
  )
}

interface ChatPanelProps {
  chat: ReturnType<typeof useChat>
  dictionaries?: Dictionaries
  awaitsModeration: boolean
  nextStep: NextStep | null
  role?: UserRole
  moderationQueue: CampaignListItem[]
  onOpenCampaign: (id: number) => void
  onOpenVoiceMode?: () => void
  imageAction?: ReactNode
}

export function ChatPanel({ chat, dictionaries, awaitsModeration, nextStep, role, moderationQueue, onOpenCampaign, onOpenVoiceMode, imageAction }: ChatPanelProps) {
  const { busy, campaignId, messages, suggestions, confirmation, error, send, answer, retry } = chat
  const [text, setText] = useState('')
  const log = useRef<HTMLDivElement>(null)
  const transcript = useRef<HTMLDivElement>(null)
  const [awayFromBottom, setAwayFromBottom] = useState(false)
  const input = useRef<HTMLTextAreaElement>(null)
  const stickToBottom = useRef(true)
  // Распознанное попадает в поле, а не уходит сразу: Whisper ошибается, и текст должен увидеть человек.
  const dictation = useDictation((spoken) => setText((current) => (current.trim() ? `${current.trimEnd()} ${spoken}` : spoken)))

  useEffect(() => {
    if (!transcript.current) return
    const observer = new ResizeObserver(() => {
      if (log.current && stickToBottom.current) log.current.scrollTop = log.current.scrollHeight
    })
    observer.observe(transcript.current)
    return () => observer.disconnect()
  }, [])

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
    setAwayFromBottom(!stickToBottom.current)
  }

  const last = messages.at(-1)
  const thinking = busy && last?.role === 'assistant' && !last.text && last.steps.every((step) => step.status !== 'running')
  const moderator = role === 'campaignModerator'
  const empty = messages.length === 0 && !busy
  // Агент задал вопрос текстом и ждёт ответа: подсказку следующего шага не показываем.
  const asking = last?.role === 'assistant' && last.text.trim().endsWith('?')
  // Модератору без кампании обсуждать с агентом нечего: кампании создаёт менеджер.
  const showQueue = empty && moderator && campaignId === null
  const voiceAction = !text.trim() && Boolean(onOpenVoiceMode)

  useLayoutEffect(() => {
    const field = input.current
    if (!field) return
    field.style.height = 'auto'
    field.style.height = `${field.scrollHeight}px`
  }, [text, showQueue])

  useEffect(() => {
    const field = input.current
    if (!field) return
    let width = field.clientWidth
    const observer = new ResizeObserver(() => {
      if (field.clientWidth === width) return
      width = field.clientWidth
      field.style.height = 'auto'
      field.style.height = `${field.scrollHeight}px`
    })
    observer.observe(field)
    return () => observer.disconnect()
  }, [showQueue])

  return (
    <div className="chat-panel flex h-full flex-col">
      <div className="chat-log-shell">
      <div ref={log} role="log" aria-label="Сообщения" onScroll={handleScroll} className="flex min-h-0 flex-1 flex-col gap-4 overflow-y-auto p-4">
        <div ref={transcript} className="chat-transcript">
        {showQueue && <ModerationQueue campaigns={moderationQueue} onOpen={onOpenCampaign} />}
        {empty && !moderator && campaignId === null && (
          <div className="chat-welcome my-auto flex animate-rise flex-col gap-4">
            <WelcomeTitle text="Давайте создадим яркую кампанию." />
            <div className="welcome-prompts" aria-label="Быстрые промпты">
              {EXAMPLE_BRIEFS.map(({ label, prompt }) => (
                <Button key={label} variant="outline" title={prompt} onClick={() => submit(prompt)}>
                  {label}
                </Button>
              ))}
            </div>
          </div>
        )}
        {empty && !moderator && campaignId !== null && (
          <p className="m-0 animate-rise text-sm leading-5">Что поменять в кампании? Могу поправить поля и креативы, объяснить статус или ошибки проверки.</p>
        )}
        {empty && moderator && campaignId !== null && (
          <p className="m-0 animate-rise text-sm leading-5">Проверьте кампанию в рабочей области и примите решение. Можно спросить меня, что с ней не так.</p>
        )}
        {messages.map((message, index) => (
          // Анимируем только новый ход, иначе при открытии истории дёрнется вся лента.
          <div key={index} className={cn('flex flex-col', index >= messages.length - 2 && 'animate-rise')}>
            <Message message={message} thinking={thinking && index === messages.length - 1} active={busy && index === messages.length - 1} />
          </div>
        ))}
        {suggestions.length > 0 && !busy && (
          <div className="animate-rise">
            <Suggestions key={suggestions.map((item) => item.question).join()} questions={suggestions} onSend={submit} />
          </div>
        )}
        {confirmation && !busy && (
          <ConfirmationCard
            confirmation={confirmation}
            dictionaries={dictionaries}
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
          <div role="alert" className="flex animate-rise flex-col gap-2 rounded-md bg-error px-3 py-2 text-[13px] leading-[18px] text-error-foreground">
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
      </div>
      {awayFromBottom && <Button className="chat-jump" size="icon" variant="secondary" aria-label="К последним сообщениям" title="К последним сообщениям" onClick={() => {stickToBottom.current = true; setAwayFromBottom(false); if (log.current) log.current.scrollTop = log.current.scrollHeight}}><ArrowDown aria-hidden="true" /></Button>}
      </div>

      {awaitsModeration && !confirmation && !busy && (
        <div className="max-h-[60%] shrink-0 animate-rise overflow-y-auto border-t p-3">
          <ModerationBar onSend={submit} />
        </div>
      )}
      {/* Пока агент ждёт ответа на свой вопрос, не предлагаем другое действие. */}
      {nextStep && !confirmation && !busy && suggestions.length === 0 && !asking && (
        <div className="shrink-0 animate-rise border-t p-3">
          <NextStepBar step={nextStep} onSend={submit} />
        </div>
      )}
      {imageAction && messages.length > 0 && !confirmation && !showQueue && <div className="shrink-0 border-t p-3">{imageAction}</div>}
      {dictation.error && !showQueue && (
        <p role="alert" className="m-0 flex shrink-0 items-start gap-2 border-t bg-error px-3 py-2 text-[13px] leading-[18px] text-error-foreground">
          <CircleAlert className="mt-px size-4 shrink-0" aria-hidden="true" />
          {dictation.error}
        </p>
      )}
      {!showQueue && (
        <form
          className="chat-composer flex items-end gap-2 border-t p-3"
          onSubmit={(event) => {
            event.preventDefault()
            submit(text)
          }}
        >
          <textarea
            ref={input}
            aria-label="Сообщение ассистенту"
            rows={1}
            value={text}
            placeholder={dictation.status === 'recording' ? 'Говорите…' : confirmation ? 'Что изменить?' : 'Сообщение…'}
            onChange={(event) => setText(event.target.value)}
            onKeyDown={handleKeyDown}
            className="min-w-0 flex-1 resize-none outline-none placeholder:text-muted-foreground"
          />
          <MicButton status={dictation.status} onToggle={dictation.toggle} />
          <Button
            type={voiceAction ? 'button' : 'submit'}
            size="icon"
            className="composer-action"
            data-mode={voiceAction ? 'voice' : 'send'}
            aria-label={voiceAction ? 'Открыть голосовой режим' : 'Отправить'}
            title={voiceAction ? 'Голосовой режим' : 'Отправить'}
            disabled={voiceAction ? dictation.status !== 'idle' : busy || !text.trim()}
            onClick={voiceAction ? onOpenVoiceMode : undefined}
          >
            <span className="action-voice" aria-hidden="true"><AudioLines /></span>
            <span className="action-send" aria-hidden="true"><ArrowUp /></span>
          </Button>
        </form>
      )}
    </div>
  )
}
