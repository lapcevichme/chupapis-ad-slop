import { LoaderCircle } from 'lucide-react'
import { useState } from 'react'
import type { ReactNode } from 'react'
import { Button } from '@/components/ui/button'
import { Flash } from '@/features/campaign/Flash'
import { cn } from '@/lib/utils'
import type { Banner, BannerType, Content } from '@/types/api'
import { BannerPreview } from './BannerPreview'
import { PromoPreview } from './PromoPreview'

type View = 'banner' | 'content'

interface CreativePreviewProps {
  banner: Banner
  bannerType: BannerType
  content?: Content
  // Что сейчас делает дизайнер, если он пересобирает этот креатив.
  status?: string
}

function PhoneFrame({ children }: { children: ReactNode }) {
  return (
    <div className="h-150 w-75 shrink-0 rounded-[2.5rem] bg-[#0B0D10] p-2.5">
      <div className="h-full overflow-y-auto rounded-[2rem] bg-white [color-scheme:light]">{children}</div>
    </div>
  )
}

export function DesignPlaceholder({ label }: { label: string }) {
  return (
    <PhoneFrame>
      <div role="status" className="flex h-full flex-col justify-end gap-3 p-4 text-sm leading-5 text-black/60">
        <div aria-hidden="true" className="flex animate-pulse flex-col gap-2">
          <div className="h-7 w-4/5 rounded-md bg-black/10" />
          <div className="h-4 w-full rounded-md bg-black/10" />
          <div className="h-4 w-2/3 rounded-md bg-black/10" />
          <div className="mt-2 h-11 rounded-xl bg-black/10" />
        </div>
        <p className="m-0 flex items-center gap-2">
          <LoaderCircle className="size-4 shrink-0 animate-spin" aria-hidden="true" />
          {label}
        </p>
      </div>
    </PhoneFrame>
  )
}

function LengthCounter({ label, value, max }: { label: string; value?: string | null; max: number }) {
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

export function CreativePreview({ banner, bannerType, content, status }: CreativePreviewProps) {
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

      {status && (
        <p role="status" className="m-0 flex items-center gap-2 text-[13px] leading-[18px] text-muted-foreground">
          <LoaderCircle className="size-4 shrink-0 animate-spin" aria-hidden="true" />
          {status}
        </p>
      )}

      <Flash value={JSON.stringify([banner.content, content?.content])} className="shrink-0 rounded-[2.5rem]" overlayClassName="inset-0 rounded-[inherit] animate-flash-ring">
        <PhoneFrame>
          {view === 'content' && content ? (
            <PromoPreview content={content.content} />
          ) : (
            <BannerPreview
              content={banner.content}
              type={bannerType.code}
              onOpen={content ? () => setRequestedView('content') : undefined}
            />
          )}
        </PhoneFrame>
      </Flash>

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
