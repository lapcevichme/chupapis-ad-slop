import { useState } from 'react'
import { CreativePreview } from '@/features/preview/CreativePreview'
import bannerTypesJson from '@/fixtures/banner_types.json'
import bannersJson from '@/fixtures/campaign_banners.json'
import contentsJson from '@/fixtures/campaign_contents.json'
import creativesJson from '@/fixtures/campaign_creatives.json'
import { cn } from '@/lib/utils'
import type { Banner, BannerType, Content, Creative } from '@/types/creative'

// Временный стенд для проверки превью на моках. Заменить экраном чата и паспорта.
const banners = bannersJson as Banner[]
const bannerTypes = bannerTypesJson as BannerType[]
const contents = contentsJson as Content[]
const creatives = creativesJson as Creative[]

function findContent(bannerId: number) {
  const contentId = creatives.find((creative) => creative.bannerId === bannerId && creative.contentId)?.contentId
  return contents.find((content) => content.id === contentId)
}

function App() {
  const [selectedId, setSelectedId] = useState(banners[0].id)
  const banner = banners.find((item) => item.id === selectedId) ?? banners[0]
  const bannerType = bannerTypes.find((type) => type.id === banner.bannerTypeId) ?? bannerTypes[0]

  return (
    <div className="flex min-h-screen flex-col">
      <header className="flex items-center gap-4 border-b bg-card px-6 py-3">
        <strong className="text-base font-bold text-accent-foreground">AdPilot AI</strong>
        <span className="text-[13px] text-muted-foreground">Стенд превью креативов</span>
      </header>
      <main className="flex flex-1 flex-wrap items-start gap-4 p-4">
        <nav aria-label="Баннеры из моков" className="flex min-w-0 flex-[1_1_320px] flex-col gap-1 rounded-lg border bg-card p-2">
          {banners.map((item) => (
            <button
              key={item.id}
              type="button"
              aria-current={item.id === selectedId}
              onClick={() => setSelectedId(item.id)}
              className={cn(
                'flex min-h-11 cursor-pointer flex-col rounded-md px-3 py-2 text-left text-sm outline-none hover:bg-muted focus-visible:ring-2 focus-visible:ring-ring',
                item.id === selectedId && 'bg-accent text-accent-foreground hover:bg-accent',
              )}
            >
              <span className="font-medium">{item.name}</span>
              <span className="text-xs opacity-80">
                Баннер {item.id}, кампания {item.campaignId}
              </span>
            </button>
          ))}
        </nav>
        <section aria-label="Превью" className="flex flex-[1_1_360px] justify-center rounded-lg border bg-muted p-6">
          <CreativePreview key={banner.id} banner={banner} bannerType={bannerType} content={findContent(banner.id)} />
        </section>
      </main>
    </div>
  )
}

export default App
