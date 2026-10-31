import { useCallback, useEffect, useRef, useState } from 'react'
import { ApiRequestError } from '@/api/http'
import { LiveSession } from './liveSession'
import type { LiveEvent } from './liveSession'
import { voiceAudio } from './voiceAudio'

// connecting: ждём соединение; live: говорим с GPT-Live; fallback: работает прежняя схема с ходом по нажатию.
export type LiveStatus = 'connecting' | 'live' | 'fallback'

export const LIVE_ENABLED = import.meta.env.VITE_VOICE_ENGINE !== 'press' && typeof RTCPeerConnection !== 'undefined'

// Распознанный текст приходит позже звука, а событие передачи работы его не содержит: ждём затишья в тексте.
const TRANSCRIPT_SETTLE_MS = 700
const TRANSCRIPT_WAIT_MAX_MS = 3000
// Забытая вкладка не должна оплачиваться до двухчасового предела сессии.
const MAX_SESSION_MS = 20 * 60 * 1000

const NOT_HEARD = 'Запрос не расслышан. Попроси человека повторить.'
const GREETING = 'Коротко поприветствуй человека и спроси, что будем рекламировать.'
const TRANSCRIPT_TAIL_CHARS = 160
const SESSION_LOST = 'Связь с GPT-Live прервалась, дальше по нажатию'

function startFailure(error: unknown): string | null {
  // Ключ не задан намеренно: прежняя схема здесь не сбой.
  if (error instanceof ApiRequestError && error.status === 503) return null
  if (error instanceof DOMException && error.name === 'NotAllowedError') return 'Нет доступа к микрофону: разрешите его в браузере'
  if (error instanceof DOMException && error.name === 'NotFoundError') return 'Микрофон не найден'
  return 'GPT-Live не подключился, дальше по нажатию'
}

interface LiveVoiceOptions {
  // Агент занят: сказанное копим и передадим следующим ходом.
  busy: boolean
  // Открыта карточка или анкета: сообщение от случайной фразы отклонило бы карточку.
  acceptsRequests: boolean
  greet: boolean
  microphoneEnabled: boolean
  volume: number
  onRequest: (text: string) => void
}

export function useLiveVoice({ busy, acceptsRequests, greet, microphoneEnabled, volume, onRequest }: LiveVoiceOptions) {
  const [status, setStatus] = useState<LiveStatus>(LIVE_ENABLED ? 'connecting' : 'fallback')
  const [notice, setNotice] = useState<string | null>(null)
  const [playbackBlocked, setPlaybackBlocked] = useState(false)
  // Что модель услышала и что сказала: сразу видно, где обрыв, в микрофоне или в звуке.
  const [transcript, setTranscript] = useState({ heard: '', said: '' })
  const lastSpeaker = useRef<'heard' | 'said' | null>(null)
  const session = useRef<LiveSession | null>(null)
  const heard = useRef('')
  const delegation = useRef<string | null>(null)
  const requested = useRef(false)
  const settleTimer = useRef<ReturnType<typeof setTimeout> | undefined>(undefined)
  const waitingSince = useRef(0)
  const latest = useRef({ busy, acceptsRequests, greet, onRequest })
  useEffect(() => {
    latest.current = { busy, acceptsRequests, greet, onRequest }
  })

  const say = useCallback((content: string, delegationId: string | null) => {
    session.current?.send({ type: 'session.commentary.append', delegation_id: delegationId, content })
  }, [])

  const flush = useCallback(() => {
    clearTimeout(settleTimer.current)
    if (!requested.current) return
    const { busy, acceptsRequests, onRequest } = latest.current
    if (busy) return
    requested.current = false
    const text = heard.current.trim()
    heard.current = ''
    if (!acceptsRequests) return
    if (text) onRequest(text)
    else say(NOT_HEARD, delegation.current)
  }, [say])

  const settle = useCallback(() => {
    clearTimeout(settleTimer.current)
    const waited = Date.now() - waitingSince.current
    const delay = heard.current.trim() ? TRANSCRIPT_SETTLE_MS : TRANSCRIPT_WAIT_MAX_MS - waited
    settleTimer.current = setTimeout(flush, Math.max(0, delay))
  }, [flush])

  const handleEvent = useCallback(
    (event: LiveEvent) => {
      if (event.type === 'error') console.warn('[GPT-Live]', event.error)
      else if (!event.type.endsWith('transcript.delta')) console.info('[GPT-Live]', event.type, event.type === 'session.closed' ? event.reason : '')
      if (event.type.endsWith('transcript.delta')) {
        const speaker = event.type === 'session.input_transcript.delta' ? 'heard' : 'said'
        const fresh = lastSpeaker.current !== speaker
        lastSpeaker.current = speaker
        const delta = String(event.delta ?? '')
        setTranscript((current) => ({ ...current, [speaker]: `${fresh ? '' : current[speaker]}${delta}`.slice(-TRANSCRIPT_TAIL_CHARS) }))
      }
      switch (event.type) {
        case 'session.started':
          setStatus('live')
          if (latest.current.greet) say(GREETING, null)
          break
        case 'session.input_transcript.delta':
          heard.current += String(event.delta ?? '')
          if (requested.current) settle()
          break
        case 'session.delegation.created': {
          const { id, target } = event.delegation as { id: string; target: string }
          if (target !== 'client') break
          delegation.current = id
          requested.current = true
          waitingSince.current = Date.now()
          settle()
          break
        }
      }
    },
    [say, settle],
  )

  useEffect(() => {
    if (!LIVE_ENABLED) return
    const live = new LiveSession({
      onEvent: handleEvent,
      onLost: () => fallBack(SESSION_LOST),
      onPlayback: (allowed) => setPlaybackBlocked(!allowed),
      onInputStream: (stream) => voiceAudio.attachMicrophone(stream),
      onOutputStream: (stream) => voiceAudio.attachLiveOutput(stream),
    })
    session.current = live
    const limit = setTimeout(() => fallBack(SESSION_LOST), MAX_SESSION_MS)
    function fallBack(reason: string | null) {
      // Закрытая сессия может упасть уже после открытия новой (StrictMode), на новую это не влияет.
      if (session.current !== live) return
      live.close()
      voiceAudio.detachLive()
      session.current = null
      setNotice(reason)
      setStatus('fallback')
    }
    // Нет ключа, сбой провайдера или запрет микрофона: режим продолжает работать по прежней схеме.
    live.start().catch((error: unknown) => {
      console.warn('[GPT-Live] не удалось подключиться', error)
      fallBack(startFailure(error))
    })
    return () => {
      clearTimeout(limit)
      clearTimeout(settleTimer.current)
      live.close()
      voiceAudio.detachLive()
      if (session.current === live) session.current = null
    }
  }, [handleEvent])

  useEffect(() => {
    if (session.current) session.current.microphoneEnabled = microphoneEnabled
  }, [microphoneEnabled, status])

  useEffect(() => {
    if (session.current) session.current.volume = volume
  }, [volume, status])

  // Ход агента закончился: отдаём то, что пришло за время его работы.
  useEffect(() => {
    if (!busy) flush()
  }, [busy, flush])

  // Сказанное до появления карточки к ней не относится.
  useEffect(() => {
    if (acceptsRequests) return
    clearTimeout(settleTimer.current)
    heard.current = ''
    requested.current = false
  }, [acceptsRequests])

  // final закрывает работу: следующий ответ, например после кнопки на карточке, к этой передаче уже не относится.
  const report = useCallback((content: string, final = true) => {
    say(content, delegation.current)
    if (final) delegation.current = null
  }, [say])

  return { status, active: status === 'live', notice, playbackBlocked, transcript, report }
}
