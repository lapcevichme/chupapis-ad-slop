import type { ApiError } from '@/types/api'
import { userHeaders } from './currentUser'
import { ApiRequestError } from './http'

// Сервер сам ограничен двумя попытками по 30 секунд; это страховка от зависшего соединения.
const TRANSCRIBE_TIMEOUT_MS = 90_000

export async function transcribeSpeech(audio: Blob): Promise<string> {
  const body = new FormData()
  body.append('file', audio, 'speech')
  const response = await fetch('/api/speech/transcriptions', {
    method: 'POST',
    headers: userHeaders(),
    body,
    signal: AbortSignal.timeout(TRANSCRIBE_TIMEOUT_MS),
  })
  if (!response.ok) {
    const payload = (await response.json().catch(() => null)) as { errors?: ApiError[] } | null
    throw new ApiRequestError(response.status, payload?.errors ?? [])
  }
  const { text } = (await response.json()) as { text: string }
  return text
}

export async function synthesizeSpeech(text: string, signal?: AbortSignal): Promise<ArrayBuffer> {
  const response = await fetch('/api/speech/synthesis', {
    method: 'POST',
    headers: { ...userHeaders(), 'Content-Type': 'application/json' },
    body: JSON.stringify({ text }),
    signal,
  })
  if (!response.ok) throw new Error(`POST /speech/synthesis: ${response.status}`)
  return response.arrayBuffer()
}
