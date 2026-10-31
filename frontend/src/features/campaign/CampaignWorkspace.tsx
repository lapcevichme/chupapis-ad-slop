import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { getCampaign, getCampaignWarnings, getDictionaries, listCampaigns } from '@/api/campaigns'
import { CreativePreview } from '@/features/preview/CreativePreview'
import { CampaignPassport } from './CampaignPassport'
import { StatusBadge } from './StatusBadge'

const DEFAULT_CAMPAIGN_ID = 101

function Message({ children }: { children: string }) {
  return <p className="m-0 p-4 text-[13px] leading-[18px] text-muted-foreground">{children}</p>
}

export function CampaignWorkspace() {
  const [campaignId, setCampaignId] = useState(DEFAULT_CAMPAIGN_ID)
  const [requestedBannerId, setRequestedBannerId] = useState<number>()

  const campaigns = useQuery({ queryKey: ['campaigns'], queryFn: listCampaigns })
  const campaign = useQuery({ queryKey: ['campaign', campaignId], queryFn: () => getCampaign(campaignId) })
  const validation = useQuery({ queryKey: ['campaign', campaignId, 'warnings'], queryFn: () => getCampaignWarnings(campaignId) })
  const dictionaries = useQuery({ queryKey: ['dictionaries'], queryFn: getDictionaries })

  const details = campaign.data?.id === campaignId ? campaign.data : undefined
  const banner = details?.banners.find((item) => item.id === requestedBannerId) ?? details?.banners[0]
  const bannerType = dictionaries.data?.bannerTypes.find((type) => type.id === banner?.bannerTypeId)
  const contentId = details?.creatives.find((creative) => creative.bannerId === banner?.id && creative.contentId)?.contentId
  const content = details?.contents.find((item) => item.id === contentId)
  const failed = campaign.isError || validation.isError || dictionaries.isError

  return (
    <div className="flex min-h-screen flex-col">
      <header className="flex flex-wrap items-center justify-between gap-3 border-b bg-card px-6 py-3">
        <div className="flex min-w-0 flex-wrap items-center gap-4">
          <strong className="text-base font-bold text-accent-foreground">AdPilot AI</strong>
          {details && <span className="text-sm leading-5 wrap-anywhere">{details.name}</span>}
          {details && <StatusBadge state={details.state} />}
          {details?.published && (
            <span className="text-[13px] leading-[18px] text-muted-foreground">Показ идёт</span>
          )}
        </div>
        {/* Временный выбор кампании из моков, пока их не открывает ассистент */}
        <div className="flex items-center gap-2">
          <label htmlFor="campaign-select" className="text-[13px] leading-[18px] text-muted-foreground">
            Кампания
          </label>
          <select
            id="campaign-select"
            value={campaignId}
            onChange={(event) => {
              setCampaignId(Number(event.target.value))
              setRequestedBannerId(undefined)
            }}
            className="h-11 max-w-72 rounded-md border border-input bg-background px-3 text-sm outline-none focus-visible:ring-2 focus-visible:ring-ring"
          >
            {campaigns.data?.map((item) => (
              <option key={item.id} value={item.id}>
                {item.id}: {item.name}
              </option>
            ))}
          </select>
        </div>
      </header>

      <main className="flex flex-1 flex-wrap items-start gap-4 p-4">
        <section aria-label="Диалог с ассистентом" className="min-w-0 flex-[1_1_340px] rounded-lg border bg-card">
          <Message>Чат появится здесь после согласования его API.</Message>
        </section>

        <div className="min-w-0 flex-[1_1_400px]">
          {failed && <Message>Не удалось загрузить кампанию. Обновите страницу.</Message>}
          {details && validation.data && dictionaries.data && (
            <CampaignPassport
              campaign={details}
              validation={validation.data}
              dictionaries={dictionaries.data}
              selectedBannerId={banner?.id}
              onSelectBanner={(item) => setRequestedBannerId(item.id)}
            />
          )}
        </div>

        <section aria-label="Превью" className="flex min-w-0 flex-[0_1_368px] justify-center rounded-lg bg-muted p-6">
          {banner && bannerType ? (
            <CreativePreview key={banner.id} banner={banner} bannerType={bannerType} content={content} />
          ) : (
            <Message>У кампании пока нет креативов, показывать нечего.</Message>
          )}
        </section>
      </main>
    </div>
  )
}
