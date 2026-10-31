import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Plus } from 'lucide-react'
import { useState } from 'react'
import { getCampaign, getCampaignAudit, getCampaignWarnings, getDictionaries, listCampaigns } from '@/api/campaigns'
import { getCurrentUser, setCurrentUser, USERS } from '@/api/currentUser'
import { Button } from '@/components/ui/button'
import { ChatPanel } from '@/features/chat/ChatPanel'
import { useChat } from '@/features/chat/useChat'
import { CreativePreview, DesignPlaceholder } from '@/features/preview/CreativePreview'
import type { EntityId } from '@/types/api'
import { CampaignLifecycle } from './CampaignLifecycle'
import { CampaignPassport } from './CampaignPassport'
import { CampaignPicker } from './CampaignPicker'
import { managerNextStep } from './nextStep'
import { ThemeToggle } from './ThemeToggle'

const NEW_CAMPAIGN = ''
// В контракте чата у шага нет типа, поэтому работу дизайнера узнаём по подписи. Если она изменится, пропадёт только индикатор в превью.
const DESIGN_STEP = /^(Дизайнер|Генерирую)/
const SELECT_CLASS =
  'h-11 max-w-72 rounded-md border border-input bg-background px-3 text-sm outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:opacity-50'

function Message({ children }: { children: string }) {
  return <p className="m-0 p-4 text-[13px] leading-[18px] text-muted-foreground">{children}</p>
}

export function CampaignWorkspace() {
  const chat = useChat()
  const queryClient = useQueryClient()
  const [login, setLogin] = useState(() => getCurrentUser().login)
  const [requestedBannerId, setRequestedBannerId] = useState<EntityId>()
  const campaignId = chat.campaignId

  const campaigns = useQuery({ queryKey: ['campaigns'], queryFn: listCampaigns })
  const campaign = useQuery({
    queryKey: ['campaign', campaignId],
    queryFn: () => getCampaign(campaignId as number),
    enabled: campaignId !== null,
  })
  const warnings = useQuery({
    queryKey: ['campaign', campaignId, 'warnings'],
    queryFn: () => getCampaignWarnings(campaignId as number),
    enabled: campaignId !== null,
  })
  const audit = useQuery({
    queryKey: ['campaign', campaignId, 'audit'],
    queryFn: () => getCampaignAudit(campaignId as number),
    enabled: campaignId !== null,
  })
  const dictionaries = useQuery({ queryKey: ['dictionaries'], queryFn: getDictionaries })

  const saved = campaign.data?.id === campaignId ? campaign.data : undefined
  // Черновик содержит неподтверждённые правки, поэтому важнее сохранённой версии. Статус есть только у сохранённой.
  const details = chat.draft ?? saved
  const validation = chat.validation ?? (saved ? warnings.data : undefined)
  const banners = details?.banners ?? []
  const banner = banners.find((item) => item.id === requestedBannerId) ?? banners[0]
  const bannerType = dictionaries.data?.bannerTypes.find((type) => type.id === banner?.bannerTypeId)
  const contentId = details?.creatives?.find((creative) => creative.bannerId === banner?.id && creative.contentId)?.contentId
  const content = details?.contents?.find((item) => item.id === contentId)
  const failed = campaign.isError || warnings.isError || dictionaries.isError
  const role = USERS.find((user) => user.login === login)?.role
  const nextStep = role === 'campaignManager' && saved && warnings.data ? managerNextStep(saved.state, warnings.data.errors.length > 0) : null
  const designStep = chat.messages.at(-1)?.steps.find((step) => step.status === 'running' && DESIGN_STEP.test(step.label))

  function openCampaign(id: number | null) {
    setRequestedBannerId(undefined)
    void chat.open(id)
  }

  return (
    <div className="flex min-h-screen flex-col xl:h-dvh">
      <header className="flex flex-wrap items-center justify-between gap-3 border-b bg-card px-6 py-3">
        <div className="flex min-w-0 flex-wrap items-center gap-4">
          <strong className="text-base font-bold text-accent-foreground">AdPilot AI</strong>
          <CampaignPicker
            campaigns={campaigns.data ?? []}
            currentId={campaignId}
            name={details?.name}
            state={saved?.state}
            role={role}
            disabled={chat.busy}
            onSelect={openCampaign}
          />
          <Button variant="outline" disabled={chat.busy || (campaignId === null && !chat.draft && chat.messages.length === 0)} onClick={() => openCampaign(null)}>
            <Plus aria-hidden="true" />
            Новая
          </Button>
          {saved?.published && <span className="text-[13px] leading-[18px] text-muted-foreground">Показ идёт</span>}
        </div>
        <div className="flex flex-wrap items-center gap-4">
          <div className="flex items-center gap-2">
            <label htmlFor="user-select" className="text-[13px] leading-[18px] text-muted-foreground">
              Пользователь
            </label>
            <select
              id="user-select"
              value={login}
              disabled={chat.busy}
              onChange={(event) => {
                setCurrentUser(event.target.value)
                setLogin(event.target.value)
                void queryClient.invalidateQueries()
              }}
              className={SELECT_CLASS}
            >
              {USERS.map((user) => (
                <option key={user.login} value={user.login}>
                  {user.login}, {user.title}
                </option>
              ))}
            </select>
          </div>
          <ThemeToggle />
        </div>
      </header>

      <main className="flex flex-1 flex-wrap items-start gap-4 p-4 xl:min-h-0 xl:flex-nowrap xl:items-stretch">
        <section
          aria-label="Диалог с ассистентом"
          className="h-[70dvh] min-h-96 min-w-0 flex-[1_1_340px] overflow-hidden rounded-lg border bg-card xl:h-auto xl:min-h-0"
        >
          <ChatPanel
            chat={chat}
            dictionaries={dictionaries.data}
            awaitsModeration={saved?.state === 'ON_MODERATION' && role === 'campaignModerator'}
            nextStep={nextStep}
          />
        </section>

        <div className="flex min-w-0 flex-[1_1_400px] flex-col gap-3 xl:overflow-y-auto">
          {failed && <Message>Не удалось загрузить данные с сервера. Обновите страницу.</Message>}
          {saved && <CampaignLifecycle state={saved.state} audit={audit.data} />}
          {details && validation && dictionaries.data ? (
            <CampaignPassport
              key={campaignId ?? NEW_CAMPAIGN}
              campaign={details}
              validation={validation}
              dictionaries={dictionaries.data}
              selectedBannerId={banner?.id}
              onSelectBanner={setRequestedBannerId}
            />
          ) : (
            !failed && !chat.busy && <Message>Паспорт кампании появится здесь, когда ассистент начнёт её собирать.</Message>
          )}
        </div>

        <section aria-label="Превью" className="flex min-w-0 flex-[0_1_368px] items-start justify-center rounded-lg bg-muted p-6 xl:overflow-y-auto">
          {banner && bannerType ? (
            <CreativePreview key={banner.id} banner={banner} bannerType={bannerType} content={content} status={designStep?.label} />
          ) : designStep ? (
            <DesignPlaceholder label={designStep.label} />
          ) : (
            <Message>Креативов пока нет, показывать нечего.</Message>
          )}
        </section>
      </main>
    </div>
  )
}
