import type { components } from './openapi'

// Типы API кампаний генерируются из openapi.json: npm run gen:api. Здесь только короткие имена для них.
type Schemas = components['schemas']

export type FontWeight = Schemas['FontWeight']
export type TextStyle = Schemas['TextStyle']
export type BannerContent = Schemas['BannerContent']
export type BannerType = Schemas['BannerTypeDto']
export type PromoContent = Schemas['PromoContent']
export type PromoComponent = PromoContent['component']['components'][number]
export type CampaignState = Schemas['CampaignState']
export type CampaignListItem = Schemas['CampaignListItem']
type SavedCampaign = Schemas['CampaignDetails']
export type CampaignInfo = Schemas['CampaignInfo']
export type BannerCreate = Schemas['BannerCreate']
export type ContentCreate = Schemas['ContentCreate']
export type CreativeCreate = Schemas['CreativeCreate']
export type CampaignRef = Schemas['CampaignRef']
export type Segments = Schemas['Segments']
export type ApiError = Schemas['ApiError']
export type CampaignValidation = Schemas['ValidationReport']
export type Segment = Schemas['SegmentDto']
export type Place = Schemas['PlaceDto']
export type Tag = Schemas['TagDto']
export type Topic = Schemas['TopicDto']

// В черновике чата id баннеров, контента и креативов временные: "tmp-1". У сохранённых они числовые.
export type EntityId = number | string

// В ответах API content описан как произвольный объект: ему соответствуют схемы BannerContent и PromoContent.
export type Banner = Omit<Schemas['BannerDto'], 'id' | 'campaignId' | 'content'> & { id: EntityId; campaignId?: number; content: BannerContent }
export type Content = Omit<Schemas['ContentDto'], 'id' | 'campaignId' | 'content'> & { id: EntityId; campaignId?: number; content: PromoContent }
export type Creative = Omit<Schemas['CreativeDto'], 'id' | 'campaignId' | 'bannerId' | 'contentId'> & {
  id: EntityId
  campaignId?: number
  bannerId: EntityId
  contentId?: EntityId | null
}

export type CampaignDetails = Omit<SavedCampaign, 'banners' | 'contents' | 'creatives'> & {
  banners: Banner[]
  contents: Content[]
  creatives: Creative[]
}

export interface Dictionaries {
  segments: Segment[]
  places: Place[]
  tags: Tag[]
  bannerTypes: BannerType[]
  topics: Topic[]
}

// Контракт чата: docs/ours/chat-api.md. Схемы событий тоже в openapi.json, руками собираем только их объединение по типу.

export type UserRole = 'campaignManager' | 'campaignModerator'

export interface User {
  login: string
  role: UserRole
}

// Пока собирается бриф, части полей ещё нет, поэтому всё необязательно. В схеме черновик описан как произвольный объект.
export type CampaignDraft = Partial<
  Omit<SavedCampaign, 'id' | 'state' | 'published' | 'author' | 'lastEditAuthor' | 'banners' | 'contents' | 'creatives'>
> & {
  banners?: Banner[]
  contents?: Content[]
  creatives?: Creative[]
}

export type Confirmation = Schemas['ChatEventConfirmationRequired']
export type ConfirmationChange = Schemas['ConfirmationChange']
export type ChatStep = Schemas['ChatEventStep']
export type ChatWarning = Schemas['ChatEventWarning']
export type Suggestion = Schemas['SuggestionItem']
export type ConfirmationAnswer = Schemas['ConfirmationBody']
export type DraftValidation = Schemas['DraftValidation']

type DraftUpdated = { draft: CampaignDraft; validation: DraftValidation }

export type ChatEvent =
  | { event: 'message_delta'; data: Schemas['ChatEventMessageDelta'] }
  | { event: 'step'; data: ChatStep }
  | { event: 'suggestions'; data: Schemas['ChatEventSuggestions'] }
  | { event: 'confirmation_required'; data: Confirmation }
  | { event: 'draft_updated'; data: DraftUpdated }
  | { event: 'campaign_updated'; data: Schemas['ChatEventCampaignUpdated'] }
  | { event: 'warning'; data: ChatWarning }
  | { event: 'error'; data: Schemas['ChatEventError'] }
  | { event: 'done'; data: Schemas['ChatEventDone'] }

export type ChatSession = Omit<Schemas['SessionSnapshot'], 'draft'> & { draft: CampaignDraft | null }
