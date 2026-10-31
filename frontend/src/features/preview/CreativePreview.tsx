import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'
import type { Banner, BannerType, Content } from '@/types/creative'
import { BannerPreview } from './BannerPreview'
import { PromoPreview } from './PromoPreview'

type View = 'banner' | 'content'

interface CreativePreviewProps {
  banner: Banner
  bannerType: BannerType
  content?: Content
}

function LengthCounter({ label, value, max }: { label: string; value?: string; max: number }) {
  const length = value?.length ?? 0
  const exceeded = length > max

  return (
    <div className="flex justify-between gap-4">
      <dt className="text-muted-foreground">{label}</dt>
      <dd className={cn('m-0 tabular-nums', exceeded && 'font-medium text-destructive')}>
        {length} из {max}
        {exceeded && ', больше лимита'}
      </dd>
    </div>
  )
}

export function CreativePreview({ banner, bannerType, content }: CreativePreviewProps) {
  const [requestedView, setRequestedView] = useState<View>('banner')
  const view = content ? requestedView : 'banner'
  const { title, text, actionType, link } = banner.content
  const linkText = link?.iOS ?? link?.android ?? link?.web

  return (
    <div className="flex w-full max-w-80 flex-col items-center gap-4">
      <div className="flex w-full gap-2" role="group" aria-label="Что показать в телефоне">
        <Button
          variant={view === 'banner' ? 'default' : 'outline'}
          aria-pressed={view === 'banner'}
          className="flex-1"
          onClick={() => setRequestedView('banner')}
        >
          Баннер
        </Button>
        <Button
          variant={view === 'content' ? 'default' : 'outline'}
          aria-pressed={view === 'content'}
          disabled={!content}
          className="flex-1"
          onClick={() => setRequestedView('content')}
        >
          Промо-экран
        </Button>
      </div>

      <div className="h-150 w-75 shrink-0 rounded-[2.5rem] bg-[#0B0D10] p-2.5">
        <div className="h-full overflow-y-auto rounded-[2rem] bg-white">
          {view === 'content' && content ? (
            <PromoPreview content={content.content} />
          ) : (
            <BannerPreview
              content={banner.content}
              type={bannerType.code}
              onOpen={content ? () => setRequestedView('content') : undefined}
            />
          )}
        </div>
      </div>

      <dl className="m-0 flex w-full flex-col gap-1 text-[13px] leading-[18px]">
        <div className="flex justify-between gap-4">
          <dt className="text-muted-foreground">Формат</dt>
          <dd className="m-0">{bannerType.description}</dd>
        </div>
        <LengthCounter label="Заголовок" value={title} max={bannerType.titleMaxLength} />
        <LengthCounter label="Текст" value={text} max={bannerType.textMaxLength} />
        <div className="flex justify-between gap-4">
          <dt className="text-muted-foreground">Действие</dt>
          <dd className="m-0 font-mono text-xs">{actionType}</dd>
        </div>
        {linkText && (
          <div className="flex justify-between gap-4">
            <dt className="text-muted-foreground">Ссылка</dt>
            <dd className="m-0 min-w-0 text-right font-mono text-xs wrap-anywhere">{linkText}</dd>
          </div>
        )}
      </dl>
    </div>
  )
}
