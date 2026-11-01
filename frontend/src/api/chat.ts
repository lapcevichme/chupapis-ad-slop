import type { ChatEvent, ChatSession, ConfirmationAnswer } from '@/types/api'
import { userHeaders } from './currentUser'
import { apiRequest } from './http'
import type { components } from '@/types/openapi'

export type ChatSummary = components['schemas']['SessionSummary']
export const listChatSessions = (archived = false) => apiRequest<ChatSummary[]>(`/chat?archived=${archived}`)
export const archiveChatSession = (id: string) => apiRequest(`/chat/${id}`, { method: 'DELETE' })
export const restoreChatSession = (id: string) => apiRequest(`/chat/${id}/restore`, { method: 'POST' })

// Контракт: docs/contracts/chat.md.
const SILENCE_TIMEOUT_MS = 90_000

async function postJson(path: string, body: unknown, init?: RequestInit) {
  return fetch(`/api${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...userHeaders() },
    body: body === undefined ? undefined : JSON.stringify(body),
    ...init,
  })
}

export async function createChatSession(campaignId?: number): Promise<string> {
  const response = await postJson('/chat', campaignId === undefined ? {} : { campaignId })
  if (!response.ok) throw new Error(`POST /chat: ${response.status}`)
  const { sessionId } = (await response.json()) as { sessionId: string }
  return sessionId
}

// null значит, что такой сессии на сервере больше нет.
export async function getChatSession(sessionId: string): Promise<ChatSession | null> {
  const response = await fetch(`/api/chat/${sessionId}`, { headers: userHeaders() })
  if (response.status === 404) return null
  if (!response.ok) throw new Error(`GET /chat: ${response.status}`)
  return (await response.json()) as ChatSession
}

function parseEvent(block: string): ChatEvent | null {
  let event = ''
  const data: string[] = []
  for (const line of block.split('\n')) {
    if (line.startsWith('event:')) event = line.slice(6).trim()
    if (line.startsWith('data:')) data.push(line.slice(5).trimStart())
  }
  if (!event) return null
  return { event, data: data.length > 0 ? JSON.parse(data.join('\n')) : {} } as ChatEvent
}

async function* readStream(path: string, body: unknown, onOpen: () => void): AsyncGenerator<ChatEvent> {
  const controller = new AbortController()
  let timer = setTimeout(() => controller.abort(), SILENCE_TIMEOUT_MS)
  const resetTimer = () => {
    clearTimeout(timer)
    timer = setTimeout(() => controller.abort(), SILENCE_TIMEOUT_MS)
  }

  try {
    const response = await postJson(path, body, { signal: controller.signal })
    if (!response.ok || !response.body) throw new Error(`POST ${path}: ${response.status}`)
    onOpen()

    const reader = response.body.pipeThrough(new TextDecoderStream()).getReader()
    let buffer = ''
    let finished = false
    while (true) {
      const { value, done } = await reader.read()
      if (done) break
      resetTimer()
      buffer += value.replaceAll('\r\n', '\n')
      const blocks = buffer.split('\n\n')
      buffer = blocks.pop() ?? ''
      for (const block of blocks) {
        const event = parseEvent(block)
        if (!event) continue
        if (event.event === 'done' || event.event === 'error') finished = true
        yield event
      }
    }
    if (!finished) throw new Error('Поток оборвался до конца ответа')
  } finally {
    clearTimeout(timer)
  }
}

export function sendChatMessage(sessionId: string, text: string, voice: boolean, onOpen: () => void): AsyncIterable<ChatEvent> {
  return readStream(`/chat/${sessionId}/messages`, { text, voice }, onOpen)
}

export function answerChatConfirmation(sessionId: string, confirmationId: string, answer: ConfirmationAnswer, onOpen: () => void): AsyncIterable<ChatEvent> {
  return readStream(`/chat/${sessionId}/confirmations/${confirmationId}`, answer, onOpen)
}

export function retryChat(sessionId: string, onOpen: () => void): AsyncIterable<ChatEvent> {
  return readStream(`/chat/${sessionId}/retry`, undefined, onOpen)
}
