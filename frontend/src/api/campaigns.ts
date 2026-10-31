import bannerTypes from '@/fixtures/banner_types.json'
import banners from '@/fixtures/campaign_banners.json'
import contents from '@/fixtures/campaign_contents.json'
import creatives from '@/fixtures/campaign_creatives.json'
import campaignPlaces from '@/fixtures/campaign_places.json'
import campaignSegments from '@/fixtures/campaign_segments.json'
import campaignWarnings from '@/fixtures/campaign_warnings.json'
import campaigns from '@/fixtures/campaigns.json'
import places from '@/fixtures/places.json'
import segments from '@/fixtures/segments.json'
import tags from '@/fixtures/tags.json'
import type { Banner, BannerType, Campaign, CampaignDetails, CampaignValidation, Content, Creative, Dictionaries, Place, Segment } from '@/types/api'

// Пока бэкенда нет, функции собирают ответы §3 task.md из моков. Когда он появится, тела заменяем
// на fetch('/api/...'), а сигнатуры оставляем: компоненты и запросы менять не придётся.

export async function listCampaigns(): Promise<Campaign[]> {
  return campaigns as Campaign[]
}

export async function getCampaign(id: number): Promise<CampaignDetails> {
  const campaign = (campaigns as Campaign[]).find((item) => item.id === id)
  if (!campaign) throw new Error(`Кампания ${id} не найдена`)

  const segmentLists = campaignSegments.find((item) => item.campaignId === id)
  return {
    ...campaign,
    places: campaignPlaces.find((item) => item.campaignId === id)?.placeIds ?? [],
    segments: { included: segmentLists?.included ?? [], excluded: segmentLists?.excluded ?? [] },
    banners: (banners as Banner[]).filter((item) => item.campaignId === id),
    contents: (contents as Content[]).filter((item) => item.campaignId === id),
    creatives: (creatives as Creative[]).filter((item) => item.campaignId === id),
  }
}

export async function getCampaignWarnings(id: number): Promise<CampaignValidation> {
  return { errors: [], warnings: campaignWarnings.find((item) => item.campaignId === id)?.warnings ?? [] }
}

export async function getDictionaries(): Promise<Dictionaries> {
  return {
    segments: segments as Segment[],
    places: places as Place[],
    tags,
    bannerTypes: bannerTypes as BannerType[],
  }
}
