import { CircleAlert, LoaderCircle, Mic, MicOff, Square, Volume2, VolumeX, X } from 'lucide-react'
import { useCallback, useEffect, useRef, useState } from 'react'
import type { ReactNode } from 'react'
import { Button } from '@/components/ui/button'
import { TO_MODERATION } from '@/features/campaign/nextStep'
import type { NextStep } from '@/features/campaign/nextStep'
import { ChatMarkdown } from '@/features/chat/ChatMarkdown'
import { ConfirmationCard } from '@/features/chat/ConfirmationCard'
import { NextStepBar } from '@/features/chat/NextStepBar'
import type { useChat } from '@/features/chat/useChat'
import { useDictation } from '@/features/chat/useDictation'
import { ImageUploadMenu } from '@/features/imageUpload/ImageUploadMenu'
import { userMessageSummary } from '@/features/imageUpload/imageMessage'
import { cn } from '@/lib/utils'
import type { CampaignState, Dictionaries } from '@/types/api'
import { Orb } from './Orb'
import type { OrbMode } from './Orb'
import { Questionnaire } from './VoiceQuestionnaire'
import { VoiceSummary } from './VoiceSummary'
import { buildPages, discussionMessage, formatAnswers, mergeOptions } from './questionnaire'
import type { Answers, QuestionPage } from './questionnaire'
import { spokenText } from './spokenText'
import { useLiveNarration } from './useLiveNarration'
import { useLiveVoice } from './useLiveVoice'
import { voiceAudio } from './voiceAudio'

const MORE_CUE_DELAY_MS = 6000
const NO_WARNINGS: { message: string }[] = []
const LIVE_FAILED_REPORT = 'Бэкенд не ответил, ничего не записано. Предложи повторить.'

// Состав передаём дословно: без него модель додумывает содержимое карточки.
function liveCardReport(title: string, operations: string[]) {
  return `На экране карточка «${title}». В ней только это: ${operations.join('; ')}. Ничего другого о её содержимом не говори. Одной фразой попроси проверить и нажать кнопку на карточке.`
}

function liveFormReport(topics: string[]) {
  return `На экране вопросы: ${topics.join(', ')}. Коротко назови эти темы и попроси ответить на экране или нажать «Обсудить голосом».`
}
const PILL_ORB_PX = 36
const PILL_WIDTH_PX = 340
const PILL_TOP_PX = 12
const PILL_HEIGHT_PX = 52
const ORB_TOP_PX = 64
const PILL_BUTTON = 'h-9 shrink-0 rounded-full bg-background/15 px-3 text-[13px] font-medium whitespace-nowrap focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none dark:bg-foreground/15'

function useViewport() {
  const [viewport, setViewport] = useState(() => ({ width: innerWidth, height: innerHeight }))
  useEffect(() => {
    const update = () => setViewport({ width: innerWidth, height: innerHeight })
    addEventListener('resize', update)
    return () => removeEventListener('resize', update)
  }, [])
  return viewport
}

interface QuestionnaireState {
  pages: QuestionPage[]
  answers: Answers
  page: number
  // На какой странице показать последний ответ агента: после обсуждения он относится к этому пункту.
  introPage: number
}

interface VoiceModeProps {
  chat: ReturnType<typeof useChat>
  dictionaries?: Dictionaries
  nextStep: NextStep | null
  campaignState?: CampaignState
  imageUpload?: { banner?: { id: unknown; name: string } }
  preview?: ReactNode
  onClose: () => void
}

export function VoiceMode({ chat, dictionaries, nextStep, campaignState, imageUpload, preview, onClose }: VoiceModeProps) {
  const { busy, messages, suggestions, confirmation, error, send, answer, retry } = chat
  const [speaking, setSpeaking] = useState(false)
  const [muted, setMuted] = useState(voiceAudio.muted)
  const [volume, setVolume] = useState(voiceAudio.volume)
  const [textOnly, setTextOnly] = useState(false)
  const [startState] = useState(campaignState)
  const [startedFresh] = useState(messages.length === 0)
  const startedAt = useRef<number | null>(null)
  const [elapsedMs, setElapsedMs] = useState<number | null>(null)
  const [questionsAsked, setQuestionsAsked] = useState(0)
  const [confirmations, setConfirmations] = useState(0)
  // На телефоне лист закрывает макет, а перед подтверждением его нужно видеть целиком.
  const [sheetHidden, setSheetHidden] = useState(false)
  const dark = document.documentElement.classList.contains('dark')
  const { width, height } = useViewport()

  const [questionnaire, setQuestionnaire] = useState<QuestionnaireState | null>(null)
  // Какой пункт анкеты сейчас обсуждают. Анкета живёт здесь, а не в чате: новый ход агента очищает его варианты.
  const [discussing, setDiscussing] = useState<string | null>(null)
  const discussingRef = useRef<string | null>(null)
  const startDiscussion = useCallback((group: string | null) => {
    discussingRef.current = group
    setDiscussing(group)
  }, [])

  const handleText = useCallback((text: string) => void send(discussionMessage(discussingRef.current ?? '', text), true), [send])
  const dictation = useDictation(handleText, (stream) => voiceAudio.attachMicrophone(stream))
  const recording = dictation.status === 'starting' || dictation.status === 'recording'
  const transcribing = dictation.status === 'transcribing'

  const [micOpen, setMicOpen] = useState(true)
  // «Сказать правку» убирает карточку только на время речи: сама карточка отклоняется, когда агент получит правку.
  const [editing, setEditing] = useState(false)
  const hasSheetContent = confirmation !== null || (questionnaire !== null && discussing === null)
  const finished = campaignState === 'ON_MODERATION' && startState !== 'ON_MODERATION'
  const acceptsSpeech = !finished && (!hasSheetContent || editing)
  const handleLiveRequest = useCallback(
    (text: string) => {
      startedAt.current ??= Date.now()
      setEditing(false)
      handleText(text)
    },
    [handleText],
  )
  const live = useLiveVoice({
    busy,
    acceptsRequests: acceptsSpeech,
    greet: messages.length === 0,
    microphoneEnabled: micOpen && acceptsSpeech,
    volume: muted ? 0 : volume,
    onRequest: handleLiveRequest,
  })
  const { report: liveReport } = live
  const liveActive = useRef(live.active)
  useEffect(() => {
    liveActive.current = live.active
  })

  useEffect(() => {
    if (!recording && !live.active && live.status !== 'connecting') voiceAudio.detachMicrophone()
  }, [recording, live.active, live.status])

  const lastAnswer = messages.findLast((message) => message.role === 'assistant')
  const lastHeard = messages.findLast((message) => message.role === 'user')
  useLiveNarration({
    active: live.active,
    busy,
    step: lastAnswer?.steps.filter((step) => step.status === 'running').at(-1)?.label,
    warnings: lastAnswer?.warnings ?? NO_WARNINGS,
    request: lastHeard ? userMessageSummary(lastHeard.text) : '',
    report: liveReport,
  })
  const startedEmpty = useRef(messages.length === 0)
  const waitCuePlayed = useRef(false)
  const wasBusy = useRef(busy)
  const latest = useRef({ text: lastAnswer?.text ?? '', hasConfirmation: confirmation !== null, hasSuggestions: suggestions.length > 0, failed: error !== null, cardTitle: confirmation?.title ?? '', cardOperations: confirmation?.operations.map((operation) => operation.label) ?? [], topics: suggestions.map((question) => question.header) })
  useEffect(() => {
    latest.current = { text: lastAnswer?.text ?? '', hasConfirmation: confirmation !== null, hasSuggestions: suggestions.length > 0, failed: error !== null, cardTitle: confirmation?.title ?? '', cardOperations: confirmation?.operations.map((operation) => operation.label) ?? [], topics: suggestions.map((question) => question.header) }
  })

  useEffect(() => {
    if (suggestions.length === 0 || busy) return
    const group = discussingRef.current
    // Варианты из обсуждения пункта дополняют уже заданный вопрос.
    if (group === null) setQuestionsAsked((count) => count + buildPages(suggestions).length)
    setQuestionnaire((current) => {
      if (group === null || !current) return { pages: buildPages(suggestions), answers: {}, page: 0, introPage: 0 }
      // Ход обсуждения касается одного пункта, как бы модель ни назвала тему.
      const options = suggestions.flatMap((question) => question.options)
      const pages = mergeOptions(current.pages, options, group)
      // Единственный вариант агента — это и есть итог обсуждения, его сразу отмечаем.
      const decided = options.length === 1
      return {
        ...current,
        pages,
        answers: decided ? { ...current.answers, [group]: { value: options[0].value, custom: false } } : current.answers,
      }
    })
    if (group !== null) startDiscussion(null)
  }, [suggestions, busy, startDiscussion])

  useEffect(() => {
    if (campaignState !== 'ON_MODERATION' || startState === 'ON_MODERATION' || startedAt.current === null) return
    const finishedAt = Date.now()
    setElapsedMs((current) => current ?? finishedAt - (startedAt.current as number))
  }, [campaignState, startState])

  useEffect(() => {
    // В уже начатом диалоге приветствие не к месту. GPT-Live здоровается сам, заготовка нужна только прежней схеме.
    if (live.status === 'fallback' && startedEmpty.current) void voiceAudio.cue('greet')
  }, [live.status])

  useEffect(() => () => voiceAudio.stop(), [])

  useEffect(() => {
    if (busy === wasBusy.current) return
    wasBusy.current = busy
    // В разговоре с GPT-Live говорит только модель: заготовка и озвучка наложились бы на её голос.
    if (liveActive.current) {
      if (busy) return
      const { text, hasConfirmation, hasSuggestions, failed, cardTitle, cardOperations, topics } = latest.current
      const spoken = spokenText(text)
      const next = hasConfirmation ? liveCardReport(cardTitle, cardOperations) : hasSuggestions ? liveFormReport(topics) : ''
      const content = [spoken, next].filter(Boolean).join(' ')
      if (failed) liveReport(LIVE_FAILED_REPORT)
      else if (content) liveReport(content)
      return
    }
    // Legacy: ход по нажатию, заготовки и озвучка. Только запасной путь, новое поведение сюда не добавляем.
    if (busy) {
      if (!waitCuePlayed.current) void voiceAudio.cue('wait')
      waitCuePlayed.current = true
      const timer = setTimeout(() => {
        if (!voiceAudio.isPlaying) void voiceAudio.cue('more')
      }, MORE_CUE_DELAY_MS)
      return () => clearTimeout(timer)
    }
    waitCuePlayed.current = false
    const { text, hasConfirmation, hasSuggestions } = latest.current
    const spoken = spokenText(text)
    if (spoken) {
      setTextOnly(false)
      setSpeaking(true)
      voiceAudio
        .speak(spoken)
        .catch(() => setTextOnly(true))
        .finally(() => setSpeaking(false))
    } else if (hasConfirmation) {
      void voiceAudio.cue('confirm')
    } else if (hasSuggestions) {
      void voiceAudio.cue('form')
    } else {
      voiceAudio.stop()
    }
  }, [busy, liveReport])

  function talk() {
    if (live.status === 'connecting') return
    setSheetHidden(false)
    startedAt.current ??= Date.now()
    if (live.active) {
      setEditing(false)
      setMicOpen(!micOpen || editing)
      return
    }
    if (dictation.status === 'recording') {
      // Заглушка звучит сразу по нажатию: распознавание и агент займут ещё секунды.
      waitCuePlayed.current = true
      void voiceAudio.cue('wait')
    } else {
      voiceAudio.stop()
      setSpeaking(false)
      setTextOnly(false)
    }
    dictation.toggle()
  }

  useEffect(() => {
    function handleKey(event: KeyboardEvent) {
      if (event.key === 'Escape') onClose()
    }
    addEventListener('keydown', handleKey)
    return () => removeEventListener('keydown', handleKey)
  }, [onClose])

  // Открыть микрофон для правки или обсуждения пункта: в разговоре с GPT-Live запись уже идёт, поэтому не переключаем его.
  function speakUp() {
    if (!live.active) return talk()
    setSheetHidden(false)
    startedAt.current ??= Date.now()
    setEditing(true)
    setMicOpen(true)
  }

  const connecting = live.status === 'connecting'
  const waiting = busy || transcribing
  const liveListening = live.active && micOpen && !busy
  const mode: OrbMode = recording || liveListening ? 'listen' : waiting ? 'think' : speaking ? 'speak' : 'idle'
  const settled = !recording && !waiting && !speaking
  const onModeration = settled && campaignState === 'ON_MODERATION' && startState !== 'ON_MODERATION'
  const sheet = !settled || onModeration || editing ? null : confirmation ? 'confirm' : questionnaire && discussing === null ? 'form' : null
  const showPreview = settled && !onModeration && preview !== undefined
  const collapsed = sheet !== null || showPreview

  const desktop = width >= 900
  const orbSize = Math.round(desktop ? Math.min(height * 0.38, 380) : Math.min(width * 0.76, height * 0.4, 440))
  const pillWidth = Math.min(width - 24, PILL_WIDTH_PX)
  const pillLeft = (width - pillWidth) / 2
  const orbTransform = collapsed
    ? `translate(${pillLeft + 8 + PILL_ORB_PX / 2 - orbSize / 2}px, ${PILL_TOP_PX + PILL_HEIGHT_PX / 2 - orbSize / 2}px) scale(${PILL_ORB_PX / orbSize})`
    : `translate(${(width - orbSize) / 2}px, ${ORB_TOP_PX}px) scale(${onModeration ? 0.7 : 1})`

  const running = lastAnswer?.steps.filter((step) => step.status === 'running').at(-1)
  const status = dictation.error
    ? dictation.error
    : error
      ? error.message
      : connecting
        ? 'Подключаю голос, разрешите микрофон'
      : recording || (liveListening && !discussing)
        ? discussing
          ? `Слушаю: ${discussing}`
          : 'Слушаю'
        : transcribing
          ? 'Распознаю'
          : busy
            ? (running?.label ?? 'Думаю')
            : onModeration
              ? 'На модерации'
              : speaking
                ? 'Говорю'
                : textOnly
                  ? 'Звук недоступен, отвечаю текстом'
                  : discussing
                    ? `Обсуждаем: ${discussing}`
                    : live.active
                      ? 'Микрофон выключен'
                      : (live.notice ?? 'Можно говорить')
  const failed = Boolean(dictation.error || error)
  const pillText = sheet === 'confirm' ? 'Проверьте и подтвердите' : sheet === 'form' ? (live.active ? 'Микрофон выключен, ответьте здесь' : 'Жду ответы') : 'Можно говорить правки'
  const talkLabel = live.active
    ? micOpen ? 'Выключить микрофон' : 'Включить микрофон'
    : connecting ? 'Подключаю' : dictation.status === 'starting' ? 'Включаю микрофон' : recording ? 'Закончить' : waiting ? 'Думаю…' : speaking ? 'Перебить' : 'Говорить'
  const talkBlocked = connecting || (!live.active && (waiting || dictation.status === 'starting'))

  const reply = lastAnswer?.text.trim()
  // Остальные шаги в разговоре ведёт агент, а кнопка рядом с его вопросом только сбивает.
  const askNext = nextStep && !confirmation && !questionnaire && nextStep.actions.some((action) => action.message === TO_MODERATION)

  // Фото заменяет ответ анкеты, поэтому уже отмеченные ответы уходят вместе с ним, а сама анкета закрывается.
  const sendImage = (message: string) => {
    const answers = questionnaire ? formatAnswers(questionnaire.pages, questionnaire.answers) : ''
    setQuestionnaire(null)
    startDiscussion(null)
    void send(answers ? `${message}\n${answers}` : message, true)
  }
  const imageMenu = imageUpload && <ImageUploadMenu banner={imageUpload.banner} disabled={busy} onSend={sendImage} />

  return (
    <div role="dialog" aria-modal="true" aria-label="Голосовой режим" className="fixed inset-0 z-50 overflow-hidden bg-background text-foreground">
      {showPreview && (
        <div className="absolute inset-0 flex flex-col items-center gap-3 overflow-y-auto px-4 pt-20 data-[sheet=true]:min-[900px]:right-1/2 data-[sheet=true]:min-[900px]:items-end data-[sheet=true]:min-[900px]:pr-6" data-sheet={sheet !== null}>
          <div className="flex flex-none justify-center">{preview}</div>
          <div className="sticky bottom-0 mt-auto flex w-full max-w-110 shrink-0 flex-col gap-2 bg-background py-3 data-[sheet=true]:min-[900px]:hidden" data-sheet={sheet !== null}>
            {sheet === null &&
              lastAnswer?.warnings.map((warning) => (
                <p key={warning.message} className="m-0 rounded-md bg-warning px-3 py-2 text-left text-[13px] leading-[18px] text-warning-foreground">
                  {warning.message}
                </p>
              ))}
            {askNext && <NextStepBar step={nextStep} onSend={handleText} />}
            <Button variant="secondary" className="w-full" onClick={talk}>
              {live.active && micOpen ? <MicOff aria-hidden="true" /> : <Mic aria-hidden="true" />}
              {live.active && micOpen ? 'Выключить микрофон' : 'Сказать правку'}
            </Button>
          </div>
        </div>
      )}

      {!collapsed && (
        <div className="absolute inset-0 flex flex-col items-center px-6 pb-7 text-center" style={{ paddingTop: ORB_TOP_PX + orbSize }}>
          <div aria-live="polite" className="flex min-h-0 w-full max-w-140 flex-1 flex-col justify-end gap-2 overflow-y-auto py-3">
            <p role={failed ? 'alert' : undefined} className={cn('m-0 flex items-center justify-center gap-2 text-sm font-medium', failed ? 'text-destructive' : 'text-muted-foreground')}>
              {failed && <CircleAlert className="size-4 shrink-0" aria-hidden="true" />}
              {status}
            </p>
            {live.playbackBlocked && <p role="alert" className="m-0 text-sm font-medium text-destructive">Браузер не дал включить звук: нажмите на экран</p>}
            {live.active && live.transcript.heard && <p aria-hidden="true" className="m-0 line-clamp-2 text-left text-[13px] leading-[18px] text-muted-foreground">Слышу: {live.transcript.heard}</p>}
            {live.active && live.transcript.said && <p aria-hidden="true" className="m-0 line-clamp-2 text-left text-[13px] leading-[18px] text-muted-foreground">Говорю: {live.transcript.said}</p>}
            {lastHeard && waiting && <p className="m-0 line-clamp-2 text-[15px] leading-5 text-muted-foreground">«{userMessageSummary(lastHeard.text)}»</p>}
            {onModeration ? (
              <VoiceSummary elapsedMs={elapsedMs} startedFresh={startedFresh} questions={questionsAsked} confirmations={confirmations} />
            ) : (
              !waiting ? reply && <div className="text-left text-[15px] leading-6"><ChatMarkdown text={reply} /></div> : null
            )}
            {!messages.length && !waiting && !speaking && !onModeration && <p className="m-0 text-xl leading-7 font-medium text-balance">Здравствуйте! Расскажите, что будем рекламировать.</p>}
            {!waiting &&
              lastAnswer?.warnings.map((warning) => (
                <p key={warning.message} className="m-0 rounded-md bg-warning px-3 py-2 text-left text-[13px] leading-[18px] text-warning-foreground">
                  {warning.message}
                </p>
              ))}
          </div>
          <div className="flex w-full max-w-110 shrink-0 flex-col items-center gap-3">
            {error?.retryable && !waiting && (
              <Button variant="outline" onClick={() => void retry()}>
                Повторить
              </Button>
            )}
            {settled && discussing !== null && !confirmation && (
              <Button variant="secondary" onClick={() => startDiscussion(null)}>
                Вернуться к анкете
              </Button>
            )}
            {settled && !onModeration && imageMenu}
            {settled && !onModeration && askNext && <div className="w-full text-left"><NextStepBar step={nextStep} onSend={handleText} /></div>}
            {onModeration ? (
              <Button className="h-16 min-w-44 rounded-full px-7 font-semibold" onClick={onClose}>
                Завершить разговор
              </Button>
            ) : (
              <Button
                autoFocus
                variant={recording ? 'destructive' : 'default'}
                className={cn('h-16 min-w-44 rounded-full px-7 font-semibold', recording && 'bg-destructive text-destructive-foreground hover:bg-destructive-hover')}
                disabled={talkBlocked}
                onClick={talk}
              >
                {talkBlocked ? <LoaderCircle className="animate-spin" aria-hidden="true" /> : live.active && micOpen ? <MicOff aria-hidden="true" /> : recording ? <Square className="fill-current" aria-hidden="true" /> : <Mic aria-hidden="true" />}
                {talkLabel}
              </Button>
            )}
          </div>
        </div>
      )}

      {collapsed && (
        <div role="status" className="absolute z-10 flex items-center gap-2 rounded-full bg-foreground pr-2 pl-[52px] text-background shadow-lg dark:bg-secondary dark:text-secondary-foreground" style={{ left: pillLeft, top: PILL_TOP_PX, width: pillWidth, height: PILL_HEIGHT_PX }}>
          <span className="min-w-0 flex-1 truncate text-sm font-medium">{pillText}</span>
          {sheet && preview !== undefined && (
            <button type="button" onClick={() => setSheetHidden(!sheetHidden)} className={cn(PILL_BUTTON, 'min-[900px]:hidden')}>
              {sheetHidden ? (sheet === 'confirm' ? 'К карточке' : 'К вопросам') : 'Макет'}
            </button>
          )}
          {sheet === null && (
            <button type="button" onClick={talk} className={PILL_BUTTON}>
              {live.active ? (micOpen ? 'Выкл. микрофон' : 'Вкл. микрофон') : 'Говорить'}
            </button>
          )}
        </div>
      )}

      {sheet && !(sheetHidden && width < 900) && (
        <section aria-label={sheet === 'confirm' ? 'Подтверждение' : 'Уточнения'} className="absolute inset-x-0 bottom-0 z-[5] flex max-h-[calc(100%-76px)] animate-rise flex-col gap-4 overflow-y-auto rounded-t-3xl bg-card p-5 shadow-[0_-14px_40px_rgb(10_25_18/.12)] min-[900px]:inset-x-auto min-[900px]:top-[calc(50%+32px)] min-[900px]:bottom-auto min-[900px]:max-h-[calc(100%-104px)] min-[900px]:w-120 min-[900px]:-translate-y-1/2 min-[900px]:rounded-3xl data-[beside=true]:min-[900px]:left-[calc(50%+24px)] data-[beside=false]:min-[900px]:left-1/2 data-[beside=false]:min-[900px]:-translate-x-1/2" data-beside={preview !== undefined}>
          {sheet === 'confirm' && reply && <div className="text-sm leading-5"><ChatMarkdown text={reply} /></div>}
          {sheet === 'confirm' &&
            lastAnswer?.warnings.map((warning) => (
              <p key={warning.message} className="m-0 rounded-md bg-warning px-3 py-2 text-[13px] leading-[18px] text-warning-foreground">
                {warning.message}
              </p>
            ))}
          {sheet === 'form' && questionnaire && (
            <Questionnaire
              pages={questionnaire.pages}
              answers={questionnaire.answers}
              page={questionnaire.page}
              intro={reply}
              introPage={questionnaire.introPage}
              notes={lastAnswer?.warnings.map((warning) => warning.message) ?? []}
              onAnswer={(group, answer) =>
                setQuestionnaire((current) => {
                  if (!current) return current
                  const answers = { ...current.answers }
                  if (answer) answers[group] = answer
                  else delete answers[group]
                  return { ...current, answers }
                })
              }
              onPage={(page) => setQuestionnaire((current) => current && { ...current, page })}
              onDiscuss={(group) => {
                setQuestionnaire((current) => current && { ...current, introPage: current.page })
                startDiscussion(group)
                speakUp()
              }}
              onSubmit={() => {
                const text = formatAnswers(questionnaire.pages, questionnaire.answers)
                setQuestionnaire(null)
                startDiscussion(null)
                handleText(text)
              }}
            />
          )}
          {/* На ПК рядом виден макет со своей кнопкой, на телефоне анкета его закрывает. */}
          {sheet === 'form' && (preview === undefined || width < 900) && imageMenu}
          {sheet === 'confirm' && confirmation && (
            <>
              <ConfirmationCard
                confirmation={confirmation}
                dictionaries={dictionaries}
                onApprove={() => {
                  setConfirmations((count) => count + 1)
                  void answer(confirmation.id, { approved: true, voice: true })
                }}
                onReject={() => void answer(confirmation.id, { approved: false, voice: true })}
                hideEditHint
              />
              <Button variant="secondary" onClick={speakUp}>
                <Mic aria-hidden="true" />
                Сказать правку
              </Button>
              <p className="m-0 text-center text-[13px] leading-[18px] text-muted-foreground">Записывает только кнопка на карточке. Голосом можно внести правку, это отменит предложение.</p>
            </>
          )}
        </section>
      )}

      <div
        aria-hidden="true"
        className="pointer-events-none absolute top-0 left-0 z-20 origin-center transition-transform duration-[440ms] ease-[cubic-bezier(.22,1,.36,1)] motion-reduce:transition-none"
        style={{ width: orbSize, height: orbSize, transform: orbTransform }}
      >
        <Orb key={String(dark)} mode={mode} dark={dark} compact={collapsed} size={orbSize} getLevel={voiceAudio.level.bind(voiceAudio)} />
      </div>

      {!collapsed && (
        <div className="absolute inset-x-0 top-3 z-30 flex justify-between px-4">
          <Button variant="secondary" size="icon" className="rounded-full" aria-label="Выйти из голосового режима" onClick={onClose}>
            <X aria-hidden="true" />
          </Button>
          <div className="flex items-center gap-1 rounded-full bg-secondary pr-4">
            <Button
              variant="secondary"
              size="icon"
              className="rounded-full"
              aria-label="Звук ответов"
              aria-pressed={!muted}
              onClick={() => {
                voiceAudio.muted = !muted
                if (!muted) voiceAudio.stop()
                setMuted(!muted)
              }}
            >
              {muted || volume === 0 ? <VolumeX aria-hidden="true" /> : <Volume2 aria-hidden="true" />}
            </Button>
            <input
              type="range"
              min={0}
              max={100}
              step={5}
              aria-label="Громкость ответов"
              aria-valuetext={`${Math.round(volume * 100)}%`}
              value={muted ? 0 : Math.round(volume * 100)}
              onChange={(event) => {
                const next = Number(event.target.value) / 100
                voiceAudio.volume = next
                setVolume(next)
                // Движение ползунка значит, что звук снова нужен.
                if (muted && next > 0) {
                  voiceAudio.muted = false
                  setMuted(false)
                }
              }}
              className="h-11 w-24 cursor-pointer accent-primary sm:w-32"
            />
          </div>
        </div>
      )}
    </div>
  )
}
