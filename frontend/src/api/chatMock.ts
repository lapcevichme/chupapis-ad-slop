import type { Banner, CampaignDetails, CampaignDraft, CampaignState, CampaignValidation, ChatEvent, ChatSession, Confirmation, ConfirmationAnswer, Content, Creative, Suggestion } from '@/types/api'
import { getCurrentUser } from './currentUser'
import { getMockCampaign, saveMockCampaign } from './mockStore'

// Имитация агента по сценарию §9 task.md, чтобы писать и проверять чат без бэкенда. Удаляется, когда появится настоящий API.
// Значения взяты из моков; слово «сбой» в сообщении один раз вызывает событие error.

const STORAGE_KEY = 'adpilot.mock.sessions'
const FIRST_CAMPAIGN_ID = 1001

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
        { role: 'button', text: 'Открыть вклад', actionType: 'openSmartLink', textStyle: { fontSize: 15, fontWeight: 'medium', textColor: '#FFFFFFFF' }, style: { backgroundColor: '#123D32FF' } },
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

function saveCampaign(draft: CampaignDraft): number {
  const id = FIRST_CAMPAIGN_ID + Math.floor(Math.random() * 8000)
  const { login } = getCurrentUser()
  const banner = { ...BANNER, id: id * 10 + 1, campaignId: id }
  const content = { ...CONTENT, id: id * 10 + 2, campaignId: id }
  saveMockCampaign({
    ...(draft as CampaignDetails),
    id,
    state: 'DRAFT',
    published: false,
    author: login,
    lastEditAuthor: login,
    banners: [banner],
    contents: [content],
    creatives: [{ ...CREATIVE, id: id * 10 + 3, campaignId: id, bannerId: banner.id, contentId: content.id }],
  })
  return id
}

function setState(id: number, state: CampaignState) {
  const campaign = getMockCampaign(id)
  if (campaign) saveMockCampaign({ ...campaign, state, lastEditAuthor: getCurrentUser().login })
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
    if (getCurrentUser().role !== 'campaignModerator') {
      yield* say('Одобрить кампанию может только модератор: API вернул ROLE_FORBIDDEN. Переключитесь на пользователя с этой ролью или дождитесь решения модератора.')
    } else if (session.stage === 'sent') {
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
    yield* say('Собрала черновик: сторис на главном экране для клиентов 26–45 в Москве и Санкт-Петербурге, без отписавшихся, с 5 ноября до 31 декабря. Время начала в брифе не указано, поставила 10:00.\n\nВ брифе нет тегов, без них будет предупреждение. Добавить тег «Вклад»?')
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

  if (confirmationId === 'conf-create' && session.draft) {
    yield* step('save', 'Создаю кампанию, баннер, контент и креатив', 500)
    const campaignId = saveCampaign(session.draft)
    yield { event: 'campaign_updated', data: { campaignId } }
    session.stage = 'moderation'
    yield* say(`Кампания ${campaignId} создана, предупреждений нет. Отправляем на модерацию?`)
    yield { event: 'confirmation_required', data: MODERATION_CONFIRMATION }
    return
  }

  if (confirmationId === 'conf-moderation' && session.campaignId) {
    yield* step('moderation', 'Отправляю на модерацию')
    setState(session.campaignId, 'ON_MODERATION')
    yield { event: 'campaign_updated', data: { campaignId: session.campaignId } }
    session.stage = 'sent'
    yield* say('Кампания на модерации. Дальше модератор одобрит её или вернёт на правки; после одобрения её можно будет активировать.')
    return
  }

  if (confirmationId === 'conf-approve' && session.campaignId) {
    yield* step('approve', 'Одобряю кампанию')
    setState(session.campaignId, 'APPROVED')
    yield { event: 'campaign_updated', data: { campaignId: session.campaignId } }
    yield* say('Кампания одобрена. Менеджер может её активировать.')
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

export function mockSendMessage(sessionId: string, text: string) {
  return record(sessionId, (session) => reply(session, text), text)
}

export function mockAnswerConfirmation(sessionId: string, confirmationId: string, answer: ConfirmationAnswer) {
  return record(sessionId, (session) => confirm(session, confirmationId, answer))
}
