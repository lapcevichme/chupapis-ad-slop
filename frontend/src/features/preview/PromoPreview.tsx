import type { PromoComponent, PromoContent } from '@/types/creative'
import { CreativeImage } from './CreativeImage'
import { parseRichText, textStyleToCss } from './creativeStyle'

function PromoItem({ item }: { item: PromoComponent }) {
  switch (item.role) {
    case 'text':
      return (
        <p className="m-0 whitespace-pre-line wrap-anywhere" style={textStyleToCss(item.textStyle)}>
          {item.format === 'html'
            ? parseRichText(item.text).map((part, index) =>
                part.bold ? <b key={index}>{part.text}</b> : <span key={index}>{part.text}</span>,
              )
            : item.text}
        </p>
      )
    case 'image':
      return <CreativeImage url={item.url} className="w-full rounded-xl" style={{ aspectRatio: item.aspectRatio ?? 2 }} />
    case 'button':
      // В превью кнопка ничего не открывает: ссылки показываем текстом рядом с телефоном.
      return (
        <span
          className="flex min-h-11 items-center justify-center rounded-xl px-4 text-center"
          style={{ ...textStyleToCss(item.textStyle), background: item.style?.backgroundColor }}
        >
          {item.text}
        </span>
      )
  }
}

export function PromoPreview({ content }: { content: PromoContent }) {
  const container = content.component

  return (
    <div
      className="flex min-h-full flex-col gap-3 p-4"
      style={{ background: container?.style?.backgroundColor ?? '#FFFFFF', color: '#000000' }}
    >
      {container?.components?.map((item, index) => <PromoItem key={index} item={item} />)}
    </div>
  )
}
