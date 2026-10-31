import type { BannerContent, BannerType } from '@/types/api'
import { CreativeImage } from './CreativeImage'
import { textStyleToCss } from './creativeStyle'

const DEFAULT_BACKGROUND = '#FFFFFF'
const DEFAULT_TEXT = '#000000'

interface BannerPreviewProps {
  content: BannerContent
  type: BannerType['code']
  onOpen?: () => void
}

interface BannerBodyProps {
  content: BannerContent
}

function BannerCta({ content }: BannerBodyProps) {
  if (!content.buttonName) return null
  // В схеме баннера нет стиля кнопки, поэтому берём цвета самого баннера.
  return (
    <span
      className="flex min-h-11 animate-rise items-center justify-center rounded-xl px-4 text-center text-sm font-semibold [animation-delay:240ms]"
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
    <strong className="font-bold wrap-anywhere" style={textStyleToCss(content.titleStyle)}>
      {content.title}
    </strong>
  )
  const text = content.text && (
    <span className="wrap-anywhere" style={textStyleToCss(content.textStyle)}>
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

function SmartBannerBody({ content }: BannerBodyProps) {
  return (
    <div className="flex flex-col gap-3 p-3 text-left">
      <div className="flex items-start gap-3">
        <div className="flex min-w-0 flex-1 animate-stagger flex-col gap-1">
          {content.title && (
            <strong className="font-semibold wrap-anywhere" style={textStyleToCss(content.titleStyle)}>
              {content.title}
            </strong>
          )}
          {content.text && (
            <span className="wrap-anywhere" style={textStyleToCss(content.textStyle)}>
              {content.text}
            </span>
          )}
        </div>
        {content.image && <CreativeImage url={content.image.url} className="size-16 shrink-0 rounded-lg" />}
      </div>
      <BannerCta content={content} />
    </div>
  )
}

export function BannerPreview({ content, type, onOpen }: BannerPreviewProps) {
  const isStory = type === 'STORY'
  const Body = isStory ? StoryBody : SmartBannerBody
  const style = { background: content.background?.color ?? DEFAULT_BACKGROUND, color: DEFAULT_TEXT }
  const className = isStory ? 'flex min-h-full w-full flex-col' : 'block w-full shrink-0 overflow-hidden rounded-2xl shadow-sm'

  const banner = onOpen ? (
    <button type="button" onClick={onOpen} aria-label={content.voiceOver ?? undefined} className={`${className} cursor-pointer`} style={style}>
      <Body content={content} />
    </button>
  ) : (
    <div aria-label={content.voiceOver ?? undefined} className={className} style={style}>
      <Body content={content} />
    </div>
  )

  if (isStory) return banner

  // Смарт-баннер живёт на экране приложения: вокруг него условная главная.
  return (
    <div className="flex min-h-full flex-col gap-3 bg-[#F2F3F5] p-3">
      <div aria-hidden="true" className="h-16 shrink-0 rounded-2xl bg-white" />
      {banner}
      <div aria-hidden="true" className="min-h-10 flex-1 rounded-2xl bg-white" />
    </div>
  )
}
