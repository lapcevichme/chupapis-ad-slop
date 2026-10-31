import type { Banner, BannerCreate, CampaignDraft, CampaignInfo, CampaignRef, CampaignValidation, ChatEvent, ChatSession, Confirmation, ConfirmationAnswer, Content, ContentCreate, Creative, CreativeCreate, Segments, Suggestion } from '@/types/api'
import { getCampaignWarnings } from './campaigns'
import { apiRequest, ApiRequestError } from './http'

// Имитация агента по сценарию §9 task.md, пока в бэкенде нет чата. Диалог заскриптован и бриф не читает, а записи идут
// через настоящий API кампаний, поэтому переходы, роли и валидацию проверяет бэкенд. Удаляется вместе с появлением агента.
// Слово «сбой» в сообщении один раз вызывает событие error.

const STORAGE_KEY = 'adpilot.mock.sessions'

type Stage = 'brief' | 'tag' | 'create' | 'moderation' | 'sent'

interface MockSession extends ChatSession {
  stage: Stage
  failed?: boolean
}

function readSessions(): Record<string, MockSession> {
  return JSON.parse(localStorage.getItem(STORAGE_KEY) ?? '{}') as Record<string, MockSession>
}

function writeSession(id: string, session: MockSession) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify({ ...readSessions(), [id]: session }))
}

function wait(ms: number) {
  return new Promise((resolve) => setTimeout(resolve, ms))
}

const OK: CampaignValidation = { errors: [], warnings: [] }
const NO_TAGS: CampaignValidation = { errors: [], warnings: ['У кампании отсутствуют теги'] }

const BANNER: Banner = {
  id: 'tmp-1',
  name: 'Сторис: вклад 16%',
  bannerTypeId: 1,
  content: {
    title: 'Вклад под 16% годовых',
    titleStyle: { fontSize: 26, fontWeight: 'bold', textColor: '#FFFFFFFF' },
    text: 'Откройте вклад в приложении до конца года',
    textStyle: { fontSize: 15, fontWeight: 'regular', textColor: '#FFFFFFCC' },
    background: { color: '#123D32FF' },
    buttonName: 'Открыть вклад',
    actionType: 'openSmartLink',
    link: { iOS: 'mobilebank://products/deposit', android: 'mobilebank://products/deposit' },
    voiceOver: 'История: вклад под 16 процентов годовых',
  },
}

const CONTENT: Content = {
  id: 'tmp-2',
  name: 'Промо-экран: вклад 16%',
  contentType: 'PROMO',
  content: {
    role: 'promo',
    component: {
      role: 'linearContainer',
      axis: 'v',
      aligns: 'lt',
      style: { backgroundColor: '#FFFFFFFF' },
      components: [
        { role: 'text', format: 'html', text: '<b>16% годовых</b> на вклад', textStyle: { fontSize: 24, fontWeight: 'semi-bold', textColor: '#000014FF' } },
        { role: 'text', format: 'none', text: 'Откройте вклад в приложении с 5 ноября до 31 декабря', textStyle: { fontSize: 15, fontWeight: 'regular', textColor: '#00001499' } },
        { role: 'button', text: 'Открыть вклад', actionType: 'openSmartLink', link: { iOS: 'mobilebank://products/deposit', android: 'mobilebank://products/deposit' }, textStyle: { fontSize: 15, fontWeight: 'medium', textColor: '#FFFFFFFF' }, style: { backgroundColor: '#123D32FF' } },
      ],
    },
  },
}

const CREATIVE: Creative = { id: 'tmp-3', name: 'Креатив Android', bannerId: 'tmp-1', contentId: 'tmp-2', channelCode: 'ANDROID' }

const INFO: CampaignDraft = {
  name: 'Вклад 16%',
  startDate: '2026-11-05',
  startTime: '10:00',
  endDate: '2026-12-31',
  endTime: '23:59',
  topic: 'SALES',
  audienceType: 'SEGMENTED',
  weight: 0,
  initialCtr: 15,
}

const AUDIENCE: CampaignDraft = {
  ...INFO,
  places: [1],
  segments: { included: ['AGE_26_45', 'CITY_MSK', 'CITY_SPB'], excluded: ['EXC_UNSUBSCRIBED'] },
}

const FULL: CampaignDraft = { ...AUDIENCE, banners: [BANNER], contents: [CONTENT], creatives: [CREATIVE] }

const TAG_SUGGESTIONS: Suggestion[] = [
  { label: 'Добавить тег «Вклад»', value: 'Добавь тег «Вклад»' },
  { label: 'Оставить без тегов', value: 'Оставь без тегов' },
]

const CREATE_CONFIRMATION: Omit<Confirmation, 'changes'> = {
  id: 'conf-create',
  title: 'Создать кампанию «Вклад 16%»',
  operations: [
    { kind: 'create_campaign', label: 'Кампания «Вклад 16%»' },
    { kind: 'set_segments', label: 'Сегменты: 3 включить, 1 исключить' },
    { kind: 'create_banner', label: 'Баннер STORY «Сторис: вклад 16%»' },
    { kind: 'create_content', label: 'Контент PROMO «Промо-экран: вклад 16%»' },
    { kind: 'create_creative', label: 'Креатив ANDROID' },
  ],
}

const MODERATION_CONFIRMATION: Confirmation = {
  id: 'conf-moderation',
  title: 'Отправить «Вклад 16%» на модерацию',
  operations: [{ kind: 'to_moderation', label: 'Кампания «Вклад 16%»' }],
  changes: [{ field: 'state', label: 'Статус', from: 'Черновик', to: 'На модерации' }],
}

const APPROVE_CONFIRMATION: Confirmation = {
  id: 'conf-approve',
  title: 'Одобрить кампанию «Вклад 16%»',
  operations: [{ kind: 'approve', label: 'Кампания «Вклад 16%»' }],
  changes: [{ field: 'state', label: 'Статус', from: 'На модерации', to: 'Одобрена' }],
}

function createConfirmation(draft: CampaignDraft | null): Confirmation {
  return {
    ...CREATE_CONFIRMATION,
    changes: [
      { field: 'startDate', label: 'Дата начала', from: null, to: '2026-11-05' },
      { field: 'endDate', label: 'Дата конца', from: null, to: '2026-12-31' },
      { field: 'tags', label: 'Теги', from: null, to: draft?.tags?.length ? ['Вклад'] : 'Без тегов' },
    ],
  }
}

function post<T>(path: string, body?: unknown) {
  return apiRequest<T>(path, { method: 'POST', body })
}

// Тот же порядок вызовов, что у узла записи в графе: кампания, сегменты, баннер, контент, креатив.
async function saveCampaign(draft: CampaignDraft): Promise<number> {
  const info = {
    // Имена кампаний уникальны, а сценарий имитации повторяется.
    name: `${draft.name} ${Date.now() % 100000}`,
    startDate: draft.startDate,
    startTime: draft.startTime,
    endDate: draft.endDate,
    endTime: draft.endTime,
    topic: { value: draft.topic },
    tags: draft.tags?.map((value) => ({ value })) ?? [],
    audienceType: draft.audienceType,
    weight: draft.weight,
    initialCtr: draft.initialCtr,
    places: draft.places?.map((value) => ({ value })),
  } as CampaignInfo
  const { id } = await post<CampaignRef>('/campaigns', info)

  await apiRequest(`/campaigns/${id}/segments`, { method: 'PUT', body: draft.segments as Segments })
  const banner = await post<{ id: number }>(`/campaigns/${id}/banners`, { name: BANNER.name, bannerTypeId: BANNER.bannerTypeId, content: BANNER.content } as BannerCreate)
  const content = await post<{ id: number }>(`/campaigns/${id}/contents`, { name: CONTENT.name, contentType: CONTENT.contentType, content: CONTENT.content } as ContentCreate)
  await post(`/campaigns/${id}/creatives`, { name: CREATIVE.name, bannerId: banner.id, contentId: content.id, channelCode: CREATIVE.channelCode } as CreativeCreate)
  return id
}

function describeFailure(error: unknown) {
  if (error instanceof ApiRequestError) return `API отказал: ${error.errors.map((item) => `${item.message} (${item.code})`).join('; ')}`
  throw error
}

async function* say(text: string): AsyncGenerator<ChatEvent> {
  for (const chunk of text.match(/\S+\s*/g) ?? []) {
    await wait(18)
    yield { event: 'message_delta', data: { text: chunk } }
  }
}

async function* step(id: string, label: string, ms = 350): AsyncGenerator<ChatEvent> {
  yield { event: 'step', data: { id, label, status: 'running' } }
  await wait(ms)
  yield { event: 'step', data: { id, label, status: 'done' } }
}

async function* reply(session: MockSession, text: string): AsyncGenerator<ChatEvent> {
  if (/сбой/i.test(text) && !session.failed) {
    session.failed = true
    yield* step('llm', 'Обращаюсь к модели', 200)
    yield { event: 'error', data: { code: 'LLM_UNAVAILABLE', message: 'Модель не ответила. Попробуйте ещё раз.' } }
    return
  }

  if (/одобр/i.test(text)) {
    if (session.stage === 'sent') {
      yield* say('Проверьте паспорт и превью справа. Решение за вами.')
      yield { event: 'confirmation_required', data: APPROVE_CONFIRMATION }
    } else {
      yield* say('Кампания ещё не на модерации, одобрять пока нечего.')
    }
    return
  }

  if (session.stage === 'brief') {
    if (session.campaignId) {
      yield* say(`Кампания ${session.campaignId} открыта. Имитация умеет только сценарий создания новой кампании: настоящие правки появятся вместе с агентом.`)
      return
    }
    yield* step('brief', 'Разбираю бриф')
    yield { event: 'draft_updated', data: { draft: INFO, validation: NO_TAGS } }
    yield* step('places', 'Подбираю места показа')
    yield* step('segments', 'Ищу сегменты')
    yield { event: 'draft_updated', data: { draft: AUDIENCE, validation: NO_TAGS } }
    yield* step('creative', 'Собираю креатив', 200)
    const title = BANNER.content.title ?? ''
    for (const end of [8, 15, title.length]) {
      const banner = { ...BANNER, content: { ...BANNER.content, title: title.slice(0, end) } }
      yield { event: 'draft_updated', data: { draft: { ...FULL, banners: [banner] }, validation: NO_TAGS } }
      await wait(150)
    }
    yield* say('Черновик готов: сторис на главном экране для клиентов 26–45 в Москве и Санкт-Петербурге, без отписавшихся, с 5 ноября до 31 декабря. Время начала в брифе не указано, поэтому в черновике 10:00.\n\nВ брифе нет тегов, без них будет предупреждение. Добавить тег «Вклад»?')
    yield { event: 'suggestions', data: { items: TAG_SUGGESTIONS } }
    session.stage = 'tag'
    return
  }

  if (session.stage === 'tag' || session.stage === 'create') {
    if (session.stage === 'tag' && !/без тег/i.test(text)) {
      const draft = { ...FULL, tags: [5] }
      yield { event: 'draft_updated', data: { draft, validation: OK } }
    }
    session.stage = 'create'
    yield* say('Проверьте превью справа. Если всё верно, подтвердите создание кампании.')
    yield { event: 'confirmation_required', data: createConfirmation(session.draft) }
    return
  }

  if (session.stage === 'moderation') {
    yield* say('Подтвердите отправку, когда будете готовы.')
    yield { event: 'confirmation_required', data: MODERATION_CONFIRMATION }
    return
  }

  yield* say('Кампания уже на модерации. Дальше модератор одобрит её или вернёт на правки.')
}

async function* confirm(session: MockSession, confirmationId: string, answer: ConfirmationAnswer): AsyncGenerator<ChatEvent> {
  if (!answer.approved) {
    yield* say(answer.comment ? 'Учту правку.' : 'Хорошо, ничего не записываю. Что изменить?')
    return
  }

  try {
    if (confirmationId === 'conf-create' && session.draft) {
      yield* step('save', 'Создаю кампанию, баннер, контент и креатив', 100)
      const campaignId = await saveCampaign(session.draft)
      yield { event: 'campaign_updated', data: { campaignId } }
      session.stage = 'moderation'
      const { warnings } = await getCampaignWarnings(campaignId)
      yield* say(`Кампания ${campaignId} создана. ${warnings.length > 0 ? `Предупреждения: ${warnings.join('; ')}.` : 'Предупреждений нет.'} Отправляем на модерацию?`)
      yield { event: 'confirmation_required', data: MODERATION_CONFIRMATION }
    }

    if (confirmationId === 'conf-moderation' && session.campaignId) {
      yield* step('moderation', 'Отправляю на модерацию', 100)
      await post(`/campaigns/${session.campaignId}/to-moderation`)
      yield { event: 'campaign_updated', data: { campaignId: session.campaignId } }
      session.stage = 'sent'
      yield* say('Кампания на модерации. Дальше модератор одобрит её или вернёт на правки; после одобрения её можно будет активировать.')
    }

    if (confirmationId === 'conf-approve' && session.campaignId) {
      yield* step('approve', 'Одобряю кампанию', 100)
      await post(`/campaigns/${session.campaignId}/approve`)
      yield { event: 'campaign_updated', data: { campaignId: session.campaignId } }
      yield* say('Кампания одобрена. Менеджер может её активировать.')
    }
  } catch (error) {
    yield* say(describeFailure(error))
  }
}

// Ведёт историю сессии так, как это делал бы checkpointer: перезагрузка страницы восстанавливает диалог.
async function* record(sessionId: string, events: (session: MockSession) => AsyncGenerator<ChatEvent>, userText?: string): AsyncGenerator<ChatEvent> {
  const session = readSessions()[sessionId]
  session.pendingConfirmation = null
  if (userText) session.messages.push({ role: 'user', text: userText })
  const answer = { role: 'assistant' as const, text: '' }
  session.messages.push(answer)

  for await (const event of events(session)) {
    if (event.event === 'message_delta') answer.text += event.data.text
    if (event.event === 'draft_updated') Object.assign(session, event.data)
    if (event.event === 'confirmation_required') session.pendingConfirmation = event.data
    if (event.event === 'campaign_updated') Object.assign(session, { campaignId: event.data.campaignId, draft: null, validation: null })
    writeSession(sessionId, session)
    yield event
  }
  writeSession(sessionId, session)
  yield { event: 'done', data: {} }
}

export async function mockCreateSession(campaignId?: number): Promise<string> {
  const id = crypto.randomUUID()
  writeSession(id, { campaignId: campaignId ?? null, messages: [], draft: null, validation: null, pendingConfirmation: null, stage: 'brief' })
  return id
}

export async function mockGetSession(sessionId: string): Promise<ChatSession | null> {
  return readSessions()[sessionId] ?? null
}

export function mockSendMessage(sessionId: string, text: string, onOpen: () => void) {
  onOpen()
  return record(sessionId, (session) => reply(session, text), text)
}

export function mockAnswerConfirmation(sessionId: string, confirmationId: string, answer: ConfirmationAnswer, onOpen: () => void) {
  onOpen()
  return record(sessionId, (session) => confirm(session, confirmationId, answer))
}

export function mockRetry(sessionId: string, onOpen: () => void) {
  onOpen()
  const session = readSessions()[sessionId]
  if (session.messages.at(-1)?.role === 'assistant') session.messages.pop()
  writeSession(sessionId, session)
  const text = session.messages.findLast((message) => message.role === 'user')?.text ?? ''
  return record(sessionId, (current) => reply(current, text))
}
