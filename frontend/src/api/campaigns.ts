import type { AuditRecord, BannerType, CampaignDetails, CampaignListItem, CampaignValidation, Dictionaries, Place, Segment, Segments, Tag, Topic } from '@/types/api'
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

export type CampaignInfoPatch = Partial<
  Pick<CampaignDetails, 'name' | 'marketingName' | 'startDate' | 'startTime' | 'endDate' | 'endTime' | 'topic' | 'tags' | 'keywords' | 'audienceType' | 'weight' | 'initialCtr' | 'places'>
>

export interface CampaignChange {
  info?: CampaignInfoPatch
  segments?: Segments
  // Сводка правки словами: несохранённый черновик правится через агента.
  summary: string[]
}

// PUT — полная замена, поэтому сначала читаем кампанию. В теле словарные поля идут как {value, label}.
async function updateCampaignInfo(id: number, patch: CampaignInfoPatch, dictionaries: Dictionaries) {
  const next = { ...(await getCampaign(id)), ...patch }
  await apiRequest(`/campaigns/${id}`, {
    method: 'PUT',
    body: {
      name: next.name,
      marketingName: next.marketingName,
      startDate: next.startDate,
      startTime: next.startTime,
      endDate: next.endDate,
      endTime: next.endTime,
      topic: { value: next.topic, label: dictionaries.topics.find((item) => item.value === next.topic)?.label },
      tags: next.tags.map((value) => ({ value, label: dictionaries.tags.find((item) => item.id === value)?.name })),
      keywords: next.keywords,
      audienceType: next.audienceType,
      weight: next.weight,
      initialCtr: next.initialCtr,
      places: next.places.map((value) => ({ value, label: dictionaries.places.find((item) => item.id === value)?.description })),
    },
  })
}

export async function saveCampaignChange(id: number, { info, segments }: CampaignChange, dictionaries: Dictionaries) {
  const putSegments = () => apiRequest(`/campaigns/${id}/segments`, { method: 'PUT', body: segments })
  // API не даёт поставить ALL_USERS, пока у кампании есть сегменты, и сегменты, пока стоит ALL_USERS.
  const clearsSegments = info?.audienceType === 'ALL_USERS'
  if (segments && clearsSegments) await putSegments()
  if (info) await updateCampaignInfo(id, info, dictionaries)
  if (segments && !clearsSegments) await putSegments()
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
