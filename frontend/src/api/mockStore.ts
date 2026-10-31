import type { Campaign, CampaignDetails } from '@/types/api'

// Кампании, «сохранённые» имитацией чата. Файл уходит вместе с chatMock.ts, когда появится бэкенд.

const STORAGE_KEY = 'adpilot.mock.campaigns'

function readAll(): CampaignDetails[] {
  return JSON.parse(localStorage.getItem(STORAGE_KEY) ?? '[]') as CampaignDetails[]
}

export function listMockCampaigns(): Campaign[] {
  return readAll()
}

export function getMockCampaign(id: number) {
  return readAll().find((item) => item.id === id)
}

export function saveMockCampaign(campaign: CampaignDetails) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify([...readAll().filter((item) => item.id !== campaign.id), campaign]))
}
