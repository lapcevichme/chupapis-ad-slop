import { useQueryClient } from '@tanstack/react-query'
import { useCallback, useEffect, useReducer, useRef } from 'react'
import { answerChatConfirmation, createChatSession, getChatSession, retryChat, sendChatMessage } from '@/api/chat'
import type { CampaignDraft, ChatEvent, ChatSession, ChatStep, ChatWarning, Confirmation, ConfirmationAnswer, DraftValidation, Suggestion } from '@/types/api'

const SESSION_KEY = 'adpilot.chat.session'
const CONNECTION_ERROR = 'Не удалось получить ответ. Проверьте соединение и попробуйте ещё раз.'

export interface ChatMessage {
  role: 'user' | 'assistant'
  text: string
  steps: ChatStep[]
  warnings: ChatWarning[]
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
  validation: DraftValidation | null
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
          // Агент работает циклом: текст после шага — это уже следующий ответ модели.
          text: answer.text && !answer.text.endsWith('\n') ? `${answer.text}\n\n` : answer.text,
          steps: answer.steps.some((step) => step.id === event.data.id)
            ? answer.steps.map((step) => (step.id === event.data.id ? event.data : step))
            : [...answer.steps, event.data],
        })),
      }
    case 'warning':
      return { ...state, messages: updateAnswer(state.messages, (answer) => ({ ...answer, warnings: [...answer.warnings, event.data] })) }
    case 'suggestions':
      // За один ход агент может вызвать suggest_options несколько раз, поэтому варианты копим.
      return {
        ...state,
        suggestions: [...state.suggestions, ...event.data.items.filter((item) => !state.suggestions.some((known) => known.value === item.value))],
      }
    case 'confirmation_required':
      return { ...state, confirmation: event.data }
    case 'draft_updated':
      return { ...state, draft: event.data.draft, validation: event.data.validation }
    case 'campaign_updated':
      // Запись прошла: источник правды теперь API. Неподтверждённые правки придут следующим draft_updated.
      return { ...state, campaignId: event.data.campaignId ?? null, draft: null, validation: null }
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
        messages: action.session.messages.map((message) => ({ role: message.role, text: message.text, steps: [], warnings: [] })),
        confirmation: action.session.pendingConfirmation,
        draft: action.session.draft,
        validation: action.session.validation,
      }
    case 'reset':
      return { ...EMPTY, busy: false, campaignId: action.campaignId }
    case 'start': {
      // При повторе ответ, оборвавшийся на ошибке, заменяется новым.
      const previous = action.retry && state.messages.at(-1)?.role === 'assistant' ? state.messages.slice(0, -1) : state.messages
      const messages: ChatMessage[] = action.userText ? [...previous, { role: 'user', text: action.userText, steps: [], warnings: [] }] : previous
      return {
        ...state,
        busy: true,
        error: null,
        suggestions: [],
        confirmation: null,
        messages: [...messages, { role: 'assistant', text: '', steps: [], warnings: [] }],
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
  // Сервер ответил потоком, значит, сообщение уже в истории: повторять его нельзя, нужен /retry.
  const streamOpened = useRef(false)
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
            void queryClient.invalidateQueries({ queryKey: ['campaign'] })
          }
        }
      } catch {
        dispatch({ type: 'fail', error: { message: CONNECTION_ERROR, retryable: true } })
      }
    },
    [queryClient],
  )

  const markOpened = useCallback(() => {
    streamOpened.current = true
  }, [])

  const send = useCallback(
    (text: string) => {
      streamOpened.current = false
      dispatch({ type: 'start', userText: text })
      return run(async function* () {
        if (!sessionId.current) {
          sessionId.current = await createChatSession()
          localStorage.setItem(SESSION_KEY, sessionId.current)
        }
        yield* sendChatMessage(sessionId.current, text, markOpened)
      })
    },
    [run, markOpened],
  )

  const answer = useCallback(
    (confirmationId: string, value: ConfirmationAnswer) => {
      const id = sessionId.current
      if (!id) return
      streamOpened.current = false
      dispatch({ type: 'start' })
      return run(() => answerChatConfirmation(id, confirmationId, value, markOpened))
    },
    [run, markOpened],
  )

  const retry = useCallback(() => {
    const id = sessionId.current
    const request = streamOpened.current && id ? () => retryChat(id, markOpened) : lastRequest.current
    if (!request) return
    dispatch({ type: 'start', retry: true })
    return run(request)
  }, [run, markOpened])

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
