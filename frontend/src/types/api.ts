// Временные типы по §2 и §3 task.md. Заменить сгенерированными из OpenAPI, когда он появится.

export type FontWeight = 'thin' | 'light' | 'regular' | 'medium' | 'semi-bold' | 'bold'

export type ActionType = 'default' | 'externalLink' | 'openSmartLink' | 'closeCampaign' | 'doneCampaign'

export interface TextStyle {
  fontSize?: number
  fontWeight?: FontWeight
  textColor?: string
}

export interface ActionLink {
  iOS?: string
  android?: string
  web?: string
}

export interface BannerContent {
  title?: string
  titleStyle?: TextStyle
  text?: string
  textStyle?: TextStyle
  background?: { color?: string }
  image?: { url?: string }
  buttonName?: string
  actionType: ActionType
  link?: ActionLink
  voiceOver?: string
}

// До сохранения в API id баннеров, контента и креативов временные: "tmp-1".
export type EntityId = number | string

export interface Banner {
  id: EntityId
  campaignId?: number
  name: string
  bannerTypeId: number
  content: BannerContent
}

export interface BannerType {
  id: number
  code: 'STORY' | 'SMART_BANNER'
  description: string
  titleMaxLength: number
  textMaxLength: number
  channels: string[]
}

export interface PromoText {
  role: 'text'
  format: 'none' | 'html'
  text: string
  textStyle?: TextStyle
}

export interface PromoImage {
  role: 'image'
  url: string
  aspectRatio?: number
}

export interface PromoButton {
  role: 'button'
  text: string
  actionType: ActionType
  link?: ActionLink
  textStyle?: TextStyle
  style?: { backgroundColor?: string }
}

export type PromoComponent = PromoText | PromoImage | PromoButton

export interface PromoContent {
  role: 'promo'
  component: {
    role: 'linearContainer'
    axis: 'v'
    aligns?: string
    style?: { backgroundColor?: string }
    components: PromoComponent[]
  }
}

export interface Content {
  id: EntityId
  campaignId?: number
  name: string
  contentType: 'PROMO'
  content: PromoContent
}

export interface Creative {
  id: EntityId
  campaignId?: number
  name: string
  bannerId: EntityId
  contentId?: EntityId | null
  channelCode: string
}

export type CampaignState =
  | 'DRAFT'
  | 'ON_MODERATION'
  | 'NEEDS_WORK'
  | 'APPROVED'
  | 'ACTIVE'
  | 'ACTIVE_EDITING'
  | 'STOPPED'
  | 'ARCHIVED'

export type AudienceType = 'ALL_USERS' | 'SEGMENTED'

export interface Campaign {
  id: number
  name: string
  marketingName?: string
  startDate: string
  startTime: string
  endDate?: string
  endTime?: string
  topic: string
  tags?: number[]
  keywords?: string
  state: CampaignState
  published: boolean
  audienceType: AudienceType
  weight: number
  initialCtr: number
  author?: string
  lastEditAuthor?: string
}

export interface CampaignSegments {
  included: string[]
  excluded: string[]
}

export interface CampaignDetails extends Campaign {
  places: number[]
  segments: CampaignSegments
  banners: Banner[]
  contents: Content[]
  creatives: Creative[]
}

export interface ApiError {
  code: string
  message: string
  field?: string
}

export interface CampaignValidation {
  errors: ApiError[]
  warnings: string[]
}

export interface Segment {
  code: string
  name: string
  type: string
  state: 'ACTIVE' | 'NEW'
  count: number
}

export interface Place {
  id: number
  code: string
  description: string
  defaultBanner: BannerType['code']
  state: 'ACTIVE' | 'INACTIVE'
}

export interface Tag {
  id: number
  name: string
}

export interface Dictionaries {
  segments: Segment[]
  places: Place[]
  tags: Tag[]
  bannerTypes: BannerType[]
}

// Контракт чата: docs/ours/chat-api.md.

export type UserRole = 'campaignManager' | 'campaignModerator'

export interface User {
  login: string
  role: UserRole
}

// Пока собирается бриф, части полей ещё нет, поэтому всё необязательно.
export type CampaignDraft = Partial<Omit<CampaignDetails, 'id' | 'state' | 'published' | 'author' | 'lastEditAuthor'>>

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
