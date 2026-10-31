import { formatDateTime } from '@/features/campaign/format'
import type { CampaignListItem } from '@/types/api'

interface ModerationQueueProps {
  campaigns: CampaignListItem[]
  onOpen: (id: number) => void
}

export function ModerationQueue({ campaigns, onOpen }: ModerationQueueProps) {
  if (campaigns.length === 0) {
    return <p className="m-0 text-sm leading-5">Кампаний на модерации нет. Когда менеджер отправит кампанию, она появится здесь.</p>
  }

  return (
    <section aria-label="Очередь модерации" className="flex animate-rise flex-col gap-3">
      <p className="m-0 text-sm leading-5">Эти кампании ждут вашего решения. Откройте кампанию, чтобы проверить её.</p>
      <ul className="m-0 flex animate-stagger list-none flex-col gap-2 p-0">
        {campaigns.map((campaign) => (
          <li key={campaign.id}>
            <button
              type="button"
              onClick={() => onOpen(campaign.id)}
              className="flex min-h-11 w-full cursor-pointer flex-col justify-center gap-0.5 rounded-md border px-3 py-2 text-left outline-none hover:bg-muted focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background"
            >
              <span className="text-sm leading-5 font-medium wrap-anywhere">{campaign.name}</span>
              <span className="text-xs leading-4 text-muted-foreground">
                № {campaign.id}, старт {formatDateTime(campaign.startDate, campaign.startTime)}
              </span>
            </button>
          </li>
        ))}
      </ul>
    </section>
  )
}
