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

// Контракт чата: docs/ours/chat-api.md.

export type UserRole = 'campaignManager' | 'campaignModerator'

export interface User {
  login: string
  role: UserRole
}

// Типы чата написаны руками: схем ChatEvent* в openapi.json пока нет. Появятся — заменяем сгенерированными.

// Пока собирается бриф, части полей ещё нет, поэтому всё необязательно.
export type CampaignDraft = Partial<
  Omit<SavedCampaign, 'id' | 'state' | 'published' | 'author' | 'lastEditAuthor' | 'banners' | 'contents' | 'creatives'>
> & {
  banners?: Banner[]
  contents?: Content[]
  creatives?: Creative[]
}

export type OperationKind =
  | 'create_campaign'
  | 'update_campaign'
  | 'set_segments'
  | 'create_banner'
  | 'update_banner'
  | 'delete_banner'
  | 'create_content'
  | 'update_content'
  | 'delete_content'
  | 'create_creative'
  | 'update_creative'
  | 'delete_creative'
  | 'create_place'
  | 'create_tag'
  | 'to_moderation'
  | 'approve'
  | 'decline'
  | 'activate'
  | 'stop'
  | 'delete_campaign'

export interface ConfirmationChange {
  field: string
  label: string
  from: unknown
  to: unknown
}

export interface Confirmation {
  id: string
  title: string
  operations: { kind: OperationKind; label: string }[]
  changes: ConfirmationChange[]
}

export interface ChatStep {
  id: string
  label: string
  status: 'running' | 'done' | 'failed'
}

export interface Suggestion {
  label: string
  value: string
}

export type ChatEvent =
  | { event: 'message_delta'; data: { text: string } }
  | { event: 'step'; data: ChatStep }
  | { event: 'suggestions'; data: { items: Suggestion[] } }
  | { event: 'confirmation_required'; data: Confirmation }
  | { event: 'draft_updated'; data: { draft: CampaignDraft; validation: CampaignValidation } }
  | { event: 'campaign_updated'; data: { campaignId: number } }
  | { event: 'error'; data: { code: string; message: string } }
  | { event: 'done'; data: Record<string, never> }

export interface StoredChatMessage {
  role: 'user' | 'assistant'
  text: string
}

export interface ChatSession {
  campaignId: number | null
  messages: StoredChatMessage[]
  draft: CampaignDraft | null
  validation: CampaignValidation | null
  pendingConfirmation: Confirmation | null
}

export type ConfirmationAnswer = { approved: true } | { approved: false; comment?: string }
