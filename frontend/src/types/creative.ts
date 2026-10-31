// Временные типы по §2.6–2.8 task.md. Заменить сгенерированными из OpenAPI, когда он появится.

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

export interface Banner {
  id: number
  campaignId: number
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
  id: number
  campaignId: number
  name: string
  contentType: 'PROMO'
  content: PromoContent
}

export interface Creative {
  id: number
  campaignId: number
  name: string
  bannerId: number
  contentId?: number | null
  channelCode: string
}
