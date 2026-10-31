import { useEffect, useRef, useState } from 'react'
import { ApiRequestError } from '@/api/http'
import { transcribeSpeech } from '@/api/speech'

// Первым подходящим станет Opus в WebM (Chrome, Firefox), запасной MP4 нужен Safari.
const MIME_TYPES = ['audio/webm;codecs=opus', 'audio/mp4', 'audio/ogg;codecs=opus']
const AUDIO_BITS_PER_SECOND = 64_000
// Запись длиннее брифа — скорее всего забытый микрофон, а распознавание платное.
const MAX_RECORDING_MS = 120_000

export type DictationStatus = 'idle' | 'starting' | 'recording' | 'transcribing'

export const dictationSupported = () =>
  typeof MediaRecorder !== 'undefined' && Boolean(navigator.mediaDevices?.getUserMedia)

function microphoneError(error: unknown): string {
  const name = error instanceof DOMException ? error.name : ''
  if (name === 'NotAllowedError') return 'Нет доступа к микрофону: разрешите его в настройках браузера.'
  if (name === 'NotFoundError') return 'Микрофон не найден.'
  return 'Не удалось включить микрофон.'
}

function transcriptionError(error: unknown): string {
  if (error instanceof ApiRequestError && error.errors.length > 0) return error.message
  return 'Не удалось распознать запись, попробуйте ещё раз.'
}

// onStream нужен голосовому режиму: сфера реагирует на громкость микрофона.
export function useDictation(onText: (text: string) => void, onStream?: (stream: MediaStream) => void) {
  const [status, setStatus] = useState<DictationStatus>('idle')
  const [error, setError] = useState<string | null>(null)
  const recorder = useRef<MediaRecorder | null>(null)
  const timer = useRef<ReturnType<typeof setTimeout> | undefined>(undefined)
  const mounted = useRef(true)
  const latestOnText = useRef(onText)

  useEffect(() => {
    latestOnText.current = onText
  }, [onText])

  useEffect(() => {
    mounted.current = true
    return () => {
      mounted.current = false
      clearTimeout(timer.current)
      // Микрофон нельзя оставлять включённым, а запись покинутого экрана распознавать незачем.
      if (recorder.current?.state === 'recording') recorder.current.stop()
    }
  }, [])

  async function finish(chunks: Blob[], mimeType: string) {
    const audio = new Blob(chunks, { type: mimeType })
    if (audio.size === 0) {
      setError('Запись пустая, попробуйте ещё раз.')
      setStatus('idle')
      return
    }
    setStatus('transcribing')
    try {
      const text = await transcribeSpeech(audio)
      if (!mounted.current) return
      if (text) latestOnText.current(text)
      else setError('Не удалось разобрать речь, попробуйте ещё раз.')
    } catch (failure) {
      if (mounted.current) setError(transcriptionError(failure))
    } finally {
      if (mounted.current) setStatus('idle')
    }
  }

  async function start() {
    setError(null)
    setStatus('starting')
    let stream: MediaStream
    try {
      stream = await navigator.mediaDevices.getUserMedia({ audio: true })
    } catch (failure) {
      if (mounted.current) {
        setError(microphoneError(failure))
        setStatus('idle')
      }
      return
    }
    if (!mounted.current) {
      stream.getTracks().forEach((track) => track.stop())
      return
    }

    const mimeType = MIME_TYPES.find((type) => MediaRecorder.isTypeSupported(type))
    let next: MediaRecorder
    try {
      next = new MediaRecorder(stream, { mimeType, audioBitsPerSecond: AUDIO_BITS_PER_SECOND })
    } catch {
      stream.getTracks().forEach((track) => track.stop())
      setError('Браузер не умеет записывать звук.')
      setStatus('idle')
      return
    }
    const chunks: Blob[] = []
    next.ondataavailable = (event) => {
      if (event.data.size > 0) chunks.push(event.data)
    }
    next.onstop = () => {
      clearTimeout(timer.current)
      stream.getTracks().forEach((track) => track.stop())
      recorder.current = null
      if (mounted.current) void finish(chunks, next.mimeType || (mimeType ?? ''))
    }
    recorder.current = next
    onStream?.(stream)
    next.start()
    timer.current = setTimeout(() => next.stop(), MAX_RECORDING_MS)
    setStatus('recording')
  }

  function toggle() {
    if (status === 'idle') void start()
    else if (status === 'recording') recorder.current?.stop()
  }

  return { status, error, toggle }
}
