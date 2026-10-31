import type { BannerContent, PromoContent } from '@/types/api'
import { getCampaign } from './campaigns'
import { apiRequest } from './http'
import { saveStudioDocument } from './studio'
import type { StudioDocument } from './studio'
import type { PromoButton, StudioSource } from '@/features/studio/model'

function canonical(value: unknown): string {
  function sort(item: unknown): unknown {
    if (Array.isArray(item)) return item.map(sort)
    if (item && typeof item === 'object') return Object.fromEntries(Object.entries(item).sort(([a], [b]) => a.localeCompare(b)).map(([key, val]) => [key, sort(val)]))
    return item
  }
  return JSON.stringify(sort(value))
}

export async function applyStudioToCampaign(campaignId: number, source: StudioSource, document: StudioDocument, png: Blob, buttons: PromoButton[]) {
  const fresh = await getCampaign(campaignId)
  const current = source.kind === 'banner' ? fresh.banners.find(x => x.id === source.item.id) : fresh.contents.find(x => x.id === source.item.id)
  if (!current || canonical(current.content) !== canonical(source.item.content) || current.name !== source.item.name) throw new Error('Креатив изменился, пока вы работали. Закройте студию и откройте свежую версию; локальные варианты сохранены.')
  if (source.kind === 'content' && buttons.length > 5) throw new Error('В промо-экране может быть не больше пяти банковских кнопок вместе с композицией.')
  const asset = await saveStudioDocument(document, png)
  if (source.kind === 'banner') {
    const original = source.item.content
    const content: BannerContent = { actionType: original.actionType, link: original.link, background: { color: document.background.length === 7 ? document.background + 'FF' : document.background }, image: { url: asset.url }, voiceOver: document.layers.filter(x => x.kind === 'text' && !x.hidden).map(x => x.text).join('. ').slice(0, 200) }
    await apiRequest(`/campaigns/${campaignId}/banners/${source.item.id}`, { method: 'PUT', body: { name: source.item.name, bannerTypeId: source.type.id, content } })
  } else {
    const content: PromoContent = { role: 'promo', component: { role: 'linearContainer', axis: 'v', style: { backgroundColor: document.background }, components: [{ role: 'image', url: asset.url, aspectRatio: document.width / document.height }, ...buttons] } }
    await apiRequest(`/campaigns/${campaignId}/contents/${source.item.id}`, { method: 'PUT', body: { name: source.item.name, contentType: 'PROMO', content } })
  }
}
