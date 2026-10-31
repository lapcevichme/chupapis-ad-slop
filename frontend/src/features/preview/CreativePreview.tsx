import { Dialog } from '@base-ui/react/dialog'
import { ChevronDown, Maximize2, PencilLine, Smartphone, X } from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'
import type { ReactNode } from 'react'
import { Button } from '@/components/ui/button'
import { Flash } from '@/features/campaign/Flash'
import { cn } from '@/lib/utils'
import type { Banner, BannerType, Content } from '@/types/api'
import { BannerPreview } from './BannerPreview'
import { FitPhone } from './FitPhone'
import { PromoPreview } from './PromoPreview'
import { loadStudioDocument } from '@/api/studio'
import type { StudioDocument } from '@/api/studio'
import { importSource } from '@/features/studio/model'
import { Scene } from '@/features/studio/Scene'
import { GenerationScene } from './GenerationScene'
import { SMART_BANNER_SIZES, type SmartBannerSize } from './smartBannerSizes'

type View = 'banner' | 'content'

interface CreativePreviewProps {
  banner: Banner
  bannerType: BannerType
  content?: Content
  // Что сейчас делает дизайнер, если он пересобирает этот креатив.
  status?: string
  // Действие над макетом, например своё фото.
  action?: ReactNode
  onEdit?: (kind: View, document: StudioDocument, layerId?: string) => void
}

function PhoneFrame({ children }: { children: ReactNode }) {
  return (
    <div className="creative-device h-150 w-75 shrink-0 rounded-[1.5rem] bg-card p-1.5">
      <div className="h-full overflow-y-auto rounded-[1.2rem] bg-white [color-scheme:light]">{children}</div>
    </div>
  )
}

// idle: креатива пока нет и никто его не собирает, поэтому заглушка стоит на месте.
export function DesignPlaceholder({ label, idle = false }: { label: string; idle?: boolean }) {
  return <GenerationScene label={label} idle={idle} />
}

function ViewTab({ selected, disabled, onClick, children }: { selected: boolean; disabled?: boolean; onClick: () => void; children: ReactNode }) {
  return (
    <Button
      variant="ghost"
      aria-pressed={selected}
      disabled={disabled}
      className={cn('flex-1', selected ? 'border-input bg-card font-semibold text-card-foreground hover:bg-card' : 'text-muted-foreground')}
      onClick={onClick}
    >
      {children}
    </Button>
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

export function CreativePreview({ banner, bannerType, content, status, action, onEdit }: CreativePreviewProps) {
  const [requestedView, setRequestedView] = useState<View>('banner')
  const [size, setSize] = useState<SmartBannerSize>('card')
  const view = content ? requestedView : 'banner'
  const [inApp, setInApp] = useState(false)
  const source = useMemo(() => view === 'content' && content ? { kind: 'content' as const, item: content } : { kind: 'banner' as const, item: banner, type: bannerType }, [view, content, banner, bannerType])
  const fallback = useMemo(() => importSource(source), [source])
  const imageUrl = source.kind === 'banner' ? source.item.content.image?.url : source.item.content.component.components.find(item => item.role === 'image')?.url
  const sourceKey = JSON.stringify([source.kind, source.item.content])
  const [loaded, setLoaded] = useState<{ key: string; document: StudioDocument | null; error?: string }>()
  useEffect(() => {
    let active = true
    loadStudioDocument(imageUrl).then(document => { if (active) setLoaded({ key: sourceKey, document }) }).catch(() => { if (active) setLoaded({ key: sourceKey, document: null, error: 'Не удалось загрузить слои. Обновите страницу перед редактированием.' }) })
    return () => { active = false }
  }, [imageUrl, sourceKey])
  const document = loaded?.key === sourceKey && loaded.document ? loaded.document : fallback
  const loadError = loaded?.key === sourceKey ? loaded.error : undefined
  const art = <Scene document={document} onSelect={onEdit && !loadError ? id => onEdit(view, document, id) : undefined} />
  const { title, text, actionType, link } = banner.content
  const linkText = link?.iOS ?? link?.android ?? link?.web
  const phone = (
    <Flash value={JSON.stringify([banner.content, content?.content])} className="shrink-0 rounded-[2.5rem]" overlayClassName="inset-0 rounded-[inherit] animate-flash-ring">
      <PhoneFrame>
        {view === 'content' && content ? (
          <PromoPreview content={content.content} />
        ) : (
          <BannerPreview content={banner.content} type={bannerType.code} size={size} onOpen={content ? () => setRequestedView('content') : undefined} />
        )}
      </PhoneFrame>
    </Flash>
  )

  return (
    <Dialog.Root>
    <div className="creative-preview">
      <div className="preview-creative-actions">{onEdit && <Button className="preview-edit-button" disabled={Boolean(status) || Boolean(loadError)} onClick={() => onEdit(view, document)}><PencilLine size={17} />Редактировать</Button>}{action}</div>
      <div className="preview-toolbar">
      <div className="flex min-w-0 flex-1 gap-1" role="group" aria-label="Что показать в креативе">
        <ViewTab selected={view === 'banner'} onClick={() => setRequestedView('banner')}>
          Баннер
        </ViewTab>
        <ViewTab selected={view === 'content'} disabled={!content} onClick={() => setRequestedView('content')}>
          Промо-экран
        </ViewTab>
      </div>
      <Button size="icon" variant="ghost" aria-label={inApp ? 'Показать крупный макет' : 'Посмотреть в приложении'} title={inApp ? 'Крупный макет' : 'В приложении'} aria-pressed={inApp} onClick={() => setInApp(!inApp)}><Smartphone size={17} /></Button>
      <Dialog.Trigger render={<Button size="icon" variant="ghost" />} aria-label="Увеличить превью" title="Увеличить превью">
        <Maximize2 aria-hidden="true" />
      </Dialog.Trigger>
      </div>

      {inApp && bannerType.code === 'SMART_BANNER' && view === 'banner' && (
        <div className="flex w-full gap-1" role="group" aria-label="Экран приложения">
          {SMART_BANNER_SIZES.map((option) => (
            <Button
              key={option.value}
              size="sm"
              variant={size === option.value ? 'secondary' : 'ghost'}
              aria-pressed={size === option.value}
              className="flex-1"
              onClick={() => setSize(option.value)}
            >
              {option.label}
            </Button>
          ))}
        </div>
      )}

      {loadError && <p role="alert" className="preview-load-error">{loadError}</p>}
      {status ? <GenerationScene label={status} /> : inApp ? <FitPhone>{phone}</FitPhone> : <FitPhone width={document.width} height={document.height} maxScale={2} minScale={.72}><div className="preview-artwork">{art}</div></FitPhone>}
      {onEdit && !inApp && !status && <p className="preview-edit-hint">Нажмите на текст или предмет, чтобы изменить его вручную или с AI</p>}

      <details className="preview-inspector">
      <summary>О креативе<span>{bannerType.description}</span><ChevronDown size={14} aria-hidden="true" /></summary>
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
      </details>
    </div>
    <Dialog.Portal>
      <Dialog.Backdrop className="preview-dialog-backdrop" />
      <Dialog.Popup className="preview-dialog">
        <div className="preview-dialog-heading">
          <Dialog.Title className="text-sm font-medium">{view === 'content' ? 'Промо-экран' : 'Баннер'} · 100%</Dialog.Title>
          <Dialog.Close render={<Button size="icon" variant="ghost" />} aria-label="Закрыть увеличенное превью"><X aria-hidden="true" /></Dialog.Close>
        </div>
        <div className="preview-full-size">{inApp ? phone : art}</div>
      </Dialog.Popup>
    </Dialog.Portal>
    </Dialog.Root>
  )
}
