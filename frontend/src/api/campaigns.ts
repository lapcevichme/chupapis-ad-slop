import type { AuditRecord, BannerType, CampaignDetails, CampaignListItem, CampaignValidation, Dictionaries, Place, Segment, Tag, Topic } from '@/types/api'
import { apiRequest } from './http'

export function listCampaigns() {
  return apiRequest<CampaignListItem[]>('/campaigns')
}

export function getCampaign(id: number) {
  return apiRequest<CampaignDetails>(`/campaigns/${id}`)
}

export function getCampaignWarnings(id: number) {
  return apiRequest<CampaignValidation>(`/campaigns/${id}/warnings`)
}

export function getCampaignAudit(id: number) {
  return apiRequest<AuditRecord[]>(`/campaigns/${id}/audit`)
}

export async function getDictionaries(): Promise<Dictionaries> {
  const [segments, places, tags, bannerTypes, topics] = await Promise.all([
    apiRequest<Segment[]>('/segments'),
    apiRequest<Place[]>('/places'),
    apiRequest<Tag[]>('/tags'),
    apiRequest<BannerType[]>('/banner-types'),
    apiRequest<Topic[]>('/topics'),
  ])
  return { segments, places, tags, bannerTypes, topics }
}
