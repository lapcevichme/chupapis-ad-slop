import { useQueryClient } from '@tanstack/react-query'
import { useCallback, useEffect, useReducer, useRef } from 'react'
import { answerChatConfirmation, createChatSession, getChatSession, sendChatMessage } from '@/api/chat'
import type { CampaignDraft, CampaignValidation, ChatEvent, ChatSession, ChatStep, Confirmation, ConfirmationAnswer, Suggestion } from '@/types/api'

const SESSION_KEY = 'adpilot.chat.session'
const CONNECTION_ERROR = 'Не удалось получить ответ. Проверьте соединение и попробуйте ещё раз.'

export interface ChatMessage {
  role: 'user' | 'assistant'
  text: string
  steps: ChatStep[]
}

interface ChatError {
  message: string
  retryable: boolean
}

interface ChatState {
  busy: boolean
  campaignId: number | null
  messages: ChatMessage[]
  suggestions: Suggestion[]
  confirmation: Confirmation | null
  draft: CampaignDraft | null
  validation: CampaignValidation | null
  error: ChatError | null
}

type ChatAction =
  | { type: 'restore'; session: ChatSession | null }
  | { type: 'reset'; campaignId: number | null }
  | { type: 'start'; userText?: string; retry?: boolean }
  | { type: 'event'; event: ChatEvent }
  | { type: 'fail'; error: ChatError }

const EMPTY: Omit<ChatState, 'busy'> = {
  campaignId: null,
  messages: [],
  suggestions: [],
  confirmation: null,
  draft: null,
  validation: null,
  error: null,
}

function settleSteps(messages: ChatMessage[], status: ChatStep['status']) {
  return messages.map((message) => ({
    ...message,
    steps: message.steps.map((step) => (step.status === 'running' ? { ...step, status } : step)),
  }))
}

function updateAnswer(messages: ChatMessage[], update: (answer: ChatMessage) => ChatMessage) {
  const last = messages.at(-1)
  return last?.role === 'assistant' ? [...messages.slice(0, -1), update(last)] : messages
}

function applyEvent(state: ChatState, event: ChatEvent): ChatState {
  switch (event.event) {
    case 'message_delta':
      return { ...state, messages: updateAnswer(state.messages, (answer) => ({ ...answer, text: answer.text + event.data.text })) }
    case 'step':
      return {
        ...state,
        messages: updateAnswer(state.messages, (answer) => ({
          ...answer,
          steps: answer.steps.some((step) => step.id === event.data.id)
            ? answer.steps.map((step) => (step.id === event.data.id ? event.data : step))
            : [...answer.steps, event.data],
        })),
      }
    case 'suggestions':
      return { ...state, suggestions: event.data.items }
    case 'confirmation_required':
      return { ...state, confirmation: event.data }
    case 'draft_updated':
      return { ...state, draft: event.data.draft, validation: event.data.validation }
    case 'campaign_updated':
      // Запись прошла: источник правды теперь API. Неподтверждённые правки придут следующим draft_updated.
      return { ...state, campaignId: event.data.campaignId, draft: null, validation: null }
    case 'error':
      return {
        ...state,
        busy: false,
        messages: settleSteps(state.messages, 'failed'),
        error: { message: event.data.message, retryable: true },
      }
    case 'done':
      return { ...state, busy: false, messages: settleSteps(state.messages, 'done') }
    default:
      // Событие из более новой версии контракта не должно ронять экран.
      return state
  }
}

function reducer(state: ChatState, action: ChatAction): ChatState {
  switch (action.type) {
    case 'restore':
      if (!action.session) return { ...EMPTY, busy: false }
      return {
        ...EMPTY,
        busy: false,
        campaignId: action.session.campaignId,
        messages: action.session.messages.map((message) => ({ role: message.role, text: message.text, steps: [] })),
        confirmation: action.session.pendingConfirmation,
        draft: action.session.draft,
        validation: action.session.validation,
      }
    case 'reset':
      return { ...EMPTY, busy: false, campaignId: action.campaignId }
    case 'start': {
      // При повторе ответ, оборвавшийся на ошибке, заменяется новым.
      const previous = action.retry && state.messages.at(-1)?.role === 'assistant' ? state.messages.slice(0, -1) : state.messages
      const messages: ChatMessage[] = action.userText ? [...previous, { role: 'user', text: action.userText, steps: [] }] : previous
      return {
        ...state,
        busy: true,
        error: null,
        suggestions: [],
        confirmation: null,
        messages: [...messages, { role: 'assistant', text: '', steps: [] }],
      }
    }
    case 'event':
      return applyEvent(state, action.event)
    case 'fail':
      return { ...state, busy: false, messages: settleSteps(state.messages, 'failed'), error: action.error }
  }
}

export function useChat() {
  const queryClient = useQueryClient()
  const sessionId = useRef(localStorage.getItem(SESSION_KEY))
  const lastRequest = useRef<() => AsyncIterable<ChatEvent>>(null)
  const [state, dispatch] = useReducer(reducer, null, () => ({ ...EMPTY, busy: localStorage.getItem(SESSION_KEY) !== null }))

  useEffect(() => {
    const stored = sessionId.current
    if (!stored) return
    let ignore = false
    getChatSession(stored)
      .then((session) => {
        if (ignore) return
        if (!session) {
          localStorage.removeItem(SESSION_KEY)
          sessionId.current = null
        }
        dispatch({ type: 'restore', session })
      })
      .catch(() => {
        if (!ignore) dispatch({ type: 'fail', error: { message: 'Не удалось восстановить диалог. Обновите страницу.', retryable: false } })
      })
    return () => {
      ignore = true
    }
  }, [])

  const run = useCallback(
    async (request: () => AsyncIterable<ChatEvent>) => {
      lastRequest.current = request
      try {
        for await (const event of request()) {
          dispatch({ type: 'event', event })
          if (event.event === 'campaign_updated') {
            void queryClient.invalidateQueries({ queryKey: ['campaigns'] })
            void queryClient.invalidateQueries({ queryKey: ['campaign', event.data.campaignId] })
          }
        }
      } catch {
        dispatch({ type: 'fail', error: { message: CONNECTION_ERROR, retryable: true } })
      }
    },
    [queryClient],
  )

  const send = useCallback(
    (text: string) => {
      dispatch({ type: 'start', userText: text })
      return run(async function* () {
        if (!sessionId.current) {
          sessionId.current = await createChatSession()
          localStorage.setItem(SESSION_KEY, sessionId.current)
        }
        yield* sendChatMessage(sessionId.current, text)
      })
    },
    [run],
  )

  const answer = useCallback(
    (confirmationId: string, value: ConfirmationAnswer) => {
      const id = sessionId.current
      if (!id) return
      dispatch({ type: 'start' })
      return run(() => answerChatConfirmation(id, confirmationId, value))
    },
    [run],
  )

  const retry = useCallback(() => {
    if (!lastRequest.current) return
    dispatch({ type: 'start', retry: true })
    return run(lastRequest.current)
  }, [run])

  // Открыть кампанию или, если campaignId === null, начать новый диалог. Сессию новой кампании создаст первое сообщение.
  const open = useCallback(async (campaignId: number | null) => {
    lastRequest.current = null
    try {
      const id = campaignId === null ? null : await createChatSession(campaignId)
      sessionId.current = id
      if (id) localStorage.setItem(SESSION_KEY, id)
      else localStorage.removeItem(SESSION_KEY)
      dispatch({ type: 'reset', campaignId })
    } catch {
      dispatch({ type: 'fail', error: { message: 'Не удалось открыть кампанию. Попробуйте ещё раз.', retryable: false } })
    }
  }, [])

  return { ...state, send, answer, retry, open }
}
