import type { ReactNode } from 'react'
import type { BannerContent, BannerType } from '@/types/api'
import { CreativeImage } from './CreativeImage'
import { textStyleToCss } from './creativeStyle'
import type { SmartBannerSize } from './smartBannerSizes'

const DEFAULT_BACKGROUND = '#FFFFFF'
const DEFAULT_TEXT = '#000000'

interface BannerPreviewProps {
  content: BannerContent
  type: BannerType['code']
  size?: SmartBannerSize
  onOpen?: () => void
}

interface BannerBodyProps {
  content: BannerContent
}

function BannerCta({ content, compact = false }: BannerBodyProps & { compact?: boolean }) {
  if (!content.buttonName) return null
  // В схеме баннера нет стиля кнопки, поэтому берём цвета самого баннера.
  return (
    <span
      className={`flex animate-rise items-center justify-center text-center font-semibold [animation-delay:240ms] ${
        compact ? 'min-h-8 shrink-0 rounded-lg px-3 text-xs' : 'min-h-11 rounded-xl px-4 text-sm'
      }`}
      style={{
        background: content.titleStyle?.textColor ?? DEFAULT_TEXT,
        color: content.background?.color ?? DEFAULT_BACKGROUND,
      }}
    >
      {content.buttonName}
    </span>
  )
}

function StoryBody({ content }: BannerBodyProps) {
  const title = content.title && (
    <strong className="leading-[1.15] font-bold wrap-anywhere" style={textStyleToCss(content.titleStyle)}>
      {content.title}
    </strong>
  )
  const text = content.text && (
    <span className="leading-[1.3] wrap-anywhere" style={textStyleToCss(content.textStyle)}>
      {content.text}
    </span>
  )

  if (!content.image) {
    return (
      <div className="flex flex-1 flex-col gap-3 p-4 text-left">
        <div className="mt-auto flex animate-stagger flex-col gap-2">
          {title}
          {text}
          <BannerCta content={content} />
        </div>
      </div>
    )
  }

  // Картинка генерируется под этот макет: верх и нижняя полоса пустые, поэтому текст читается без подложки.
  return (
    <div className="relative flex flex-1 flex-col text-left">
      <CreativeImage url={content.image.url} className="absolute inset-0 size-full" />
      <div className="relative flex flex-1 flex-col justify-between gap-3 p-4">
        <div className="flex animate-stagger flex-col gap-2">
          {title}
          {text}
        </div>
        <BannerCta content={content} />
      </div>
    </div>
  )
}

// Длинный текст в маленьком формате обрезается, как в приложении.
const CLAMP: Record<SmartBannerSize, { title: string; text: string }> = {
  card: { title: '', text: '' },
  tile: { title: 'line-clamp-2', text: 'line-clamp-2' },
  strip: { title: 'line-clamp-1', text: 'line-clamp-1' },
}

function SmartBannerBody({ content, size }: BannerBodyProps & { size: SmartBannerSize }) {
  const texts = (
    <div className={`flex min-w-0 animate-stagger flex-col ${size === 'strip' ? 'gap-0.5' : 'gap-1'}`}>
      {content.title && (
        <strong className={`font-semibold wrap-anywhere ${CLAMP[size].title}`} style={textStyleToCss(content.titleStyle)}>
          {content.title}
        </strong>
      )}
      {content.text && (
        <span className={`wrap-anywhere ${CLAMP[size].text}`} style={textStyleToCss(content.textStyle)}>
          {content.text}
        </span>
      )}
    </div>
  )
  // Картинка — фон всей карточки: паттерн тон в тон с фоном, поэтому текст идёт поверх на всю ширину.
  const background = content.image && <CreativeImage url={content.image.url} className="absolute inset-0 size-full" />

  if (size === 'strip') {
    return (
      <div className="relative flex min-h-16 items-center text-left">
        {background}
        <div className="relative flex flex-1 items-center gap-3 p-3">
          <div className="min-w-0 flex-1">{texts}</div>
          <BannerCta content={content} compact />
        </div>
      </div>
    )
  }

  if (size === 'tile') {
    return (
      <div className="relative flex aspect-[4/5] flex-col text-left">
        {background}
        <div className="relative flex min-h-0 flex-1 flex-col justify-between gap-2 overflow-hidden p-3">
          {texts}
          <div className="self-start">
            <BannerCta content={content} compact />
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className={`relative flex flex-col text-left ${background ? 'min-h-36' : ''}`}>
      {background}
      <div className="relative flex flex-1 flex-col justify-between gap-3 p-3">
        {texts}
        <div className={background ? 'self-start' : ''}>
          <BannerCta content={content} />
        </div>
      </div>
    </div>
  )
}

const BLOCK = 'rounded-2xl bg-white'

// Условный экран приложения вокруг смарт-баннера.
function AppScreen({ size, children }: { size: SmartBannerSize; children: ReactNode }) {
  if (size === 'tile') {
    return (
      <div className="flex min-h-full flex-col gap-3 bg-[#F2F3F5] p-3">
        <div aria-hidden="true" className={`h-10 shrink-0 ${BLOCK}`} />
        <div className="grid grid-cols-2 gap-3">
          {children}
          <div aria-hidden="true" className={BLOCK} />
          <div aria-hidden="true" className={`aspect-[4/5] ${BLOCK}`} />
          <div aria-hidden="true" className={`aspect-[4/5] ${BLOCK}`} />
        </div>
      </div>
    )
  }
  if (size === 'strip') {
    return (
      <div className="flex min-h-full flex-col gap-3 bg-[#F2F3F5] p-3">
        <div aria-hidden="true" className={`h-28 shrink-0 ${BLOCK}`} />
        {children}
        {[0, 1, 2, 3, 4].map((row) => (
          <div key={row} aria-hidden="true" className="h-12 shrink-0 rounded-xl bg-white" />
        ))}
      </div>
    )
  }
  return (
    <div className="flex min-h-full flex-col gap-3 bg-[#F2F3F5] p-3">
      <div aria-hidden="true" className={`h-16 shrink-0 ${BLOCK}`} />
      {children}
      <div aria-hidden="true" className={`min-h-10 flex-1 ${BLOCK}`} />
    </div>
  )
}

export function BannerPreview({ content, type, size = 'card', onOpen }: BannerPreviewProps) {
  const isStory = type === 'STORY'
  const body = isStory ? <StoryBody content={content} /> : <SmartBannerBody content={content} size={size} />
  const style = { background: content.background?.color ?? DEFAULT_BACKGROUND, color: DEFAULT_TEXT }
  const className = isStory
    ? 'flex min-h-full w-full flex-col'
    : `block w-full shrink-0 overflow-hidden shadow-sm ${size === 'strip' ? 'rounded-xl' : 'rounded-2xl'}`

  const banner = onOpen ? (
    <button type="button" onClick={onOpen} aria-label={content.voiceOver ?? undefined} className={`${className} cursor-pointer`} style={style}>
      {body}
    </button>
  ) : (
    <div aria-label={content.voiceOver ?? undefined} className={className} style={style}>
      {body}
    </div>
  )

  if (isStory) return banner
  return <AppScreen size={size}>{banner}</AppScreen>
}
