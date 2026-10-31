import { useCallback, useEffect, useRef, useState } from 'react'
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
        case 'error':
          console.warn('GPT-Live:', event.error)
          break
      }
    },
    [say, settle],
  )

  useEffect(() => {
    if (!LIVE_ENABLED) return
    const live = new LiveSession({
      onEvent: handleEvent,
      onLost: () => fallBack(),
      onInputStream: (stream) => voiceAudio.attachMicrophone(stream),
      onOutputStream: (stream) => voiceAudio.attachLiveOutput(stream),
    })
    session.current = live
    const limit = setTimeout(() => fallBack(), MAX_SESSION_MS)
    function fallBack() {
      // Закрытая сессия может упасть уже после открытия новой (StrictMode), на новую это не влияет.
      if (session.current !== live) return
      live.close()
      voiceAudio.detachLive()
      session.current = null
      setStatus('fallback')
    }
    // Нет ключа, сбой провайдера или запрет микрофона: режим продолжает работать по прежней схеме.
    live.start().catch(() => fallBack())
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

  return { status, active: status === 'live', report }
}
