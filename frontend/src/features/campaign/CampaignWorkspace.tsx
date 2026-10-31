import { useQuery, useQueryClient } from '@tanstack/react-query'
import { ArrowUpRight, LayoutGrid, Menu, MessageSquare, Plus, X } from 'lucide-react'
import { useState } from 'react'
import { getCampaign, getCampaignAudit, getCampaignWarnings, getDictionaries, listCampaigns, saveCampaignChange } from '@/api/campaigns'
import type { CampaignChange } from '@/api/campaigns'
import { getCurrentUser, setCurrentUser, USERS } from '@/api/currentUser'
import { Button } from '@/components/ui/button'
import { ChatPanel } from '@/features/chat/ChatPanel'
import { useChat } from '@/features/chat/useChat'
import { dictationSupported } from '@/features/chat/useDictation'
import { CreativePreview, DesignPlaceholder } from '@/features/preview/CreativePreview'
import { voiceAudio } from '@/features/voice/voiceAudio'
import { VoiceMode } from '@/features/voice/VoiceMode'
import type { CampaignState, EntityId } from '@/types/api'
import { CampaignLifecycle } from './CampaignLifecycle'
import { CampaignPassport } from './CampaignPassport'
import { managerNextStep } from './nextStep'
import type { PassportEdit } from './PassportForms'
import { StatusBadge } from './StatusBadge'
import { ValidationSummary } from './ValidationSummary'
import { ThemeToggle } from './ThemeToggle'
import { UserMenu } from './UserMenu'

const NEW_CAMPAIGN = ''
const VOICE_ENABLED = import.meta.env.VITE_VOICE_MODE !== 'false'
// В контракте чата у шага нет типа, поэтому работу дизайнера узнаём по подписи. Если она изменится, пропадёт только индикатор в превью.
const DESIGN_STEP = /^(Дизайнер|Генерирую)/
const EDITABLE_STATES: CampaignState[] = ['DRAFT', 'NEEDS_WORK', 'APPROVED', 'ACTIVE', 'ACTIVE_EDITING']
const EDIT_NOTICES: Partial<Record<CampaignState, string>> = {
  APPROVED: 'Правка снимет одобрение: кампания вернётся в черновик, и её снова проверит модератор.',
  ACTIVE: 'Показ продолжится по одобренной версии, а правки вступят в силу после новой модерации.',
}

export function CampaignWorkspace() {
  const chat = useChat()
  const queryClient = useQueryClient()
  const [login, setLogin] = useState(() => getCurrentUser().login)
  const [requestedBannerId, setRequestedBannerId] = useState<EntityId>()
  const [voiceOpen, setVoiceOpen] = useState(false)
  const [pane, setPane] = useState<'creative' | 'details' | 'history'>('creative')
  const [mobilePane, setMobilePane] = useState<'dialog' | 'work'>('dialog')
  const [navOpen, setNavOpen] = useState(false)
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
  const nextStep = role === 'campaignManager' && saved && warnings.data ? managerNextStep(saved.state, warnings.data.errors.length, (saved.creatives?.length ?? 0) > 0) : null
  const designStep = chat.messages.at(-1)?.steps.find((step) => step.status === 'running' && DESIGN_STEP.test(step.label))
  const moderator = role === 'campaignModerator'

  async function applyChange(change: CampaignChange) {
    if (!saved) {
      // Несохранённый черновик живёт в сессии агента, поэтому правка идёт через него и потом через карточку подтверждения.
      void chat.send(`Поправь в черновике: ${change.summary.join('; ')}`)
      return
    }
    if (!dictionaries.data) return
    try {
      await saveCampaignChange(saved.id, change, dictionaries.data)
    } finally {
      // Правка из двух запросов могла пройти наполовину, поэтому экран обновляем и при ошибке.
      await queryClient.invalidateQueries({ queryKey: ['campaigns'] })
      await queryClient.invalidateQueries({ queryKey: ['campaign'] })
      chat.clearDraft()
    }
  }

  function blockedReason() {
    if (chat.busy) return 'Подождите, пока ассистент закончит'
    if (saved && chat.confirmation) return 'Сначала ответьте на карточку подтверждения в чате'
    return undefined
  }

  // Правит только менеджер и только там, где это разрешает жизненный цикл. Модератору формы не показываем.
  const edit: PassportEdit | undefined =
    role === 'campaignManager' && (!saved || EDITABLE_STATES.includes(saved.state))
      ? { notice: saved && EDIT_NOTICES[saved.state], blockedReason: blockedReason(), onSubmit: applyChange }
      : undefined

  function openCampaign(id: number | null) {
    setRequestedBannerId(undefined)
    setNavOpen(false)
    setPane('creative')
    if (id !== null) setMobilePane('work')
    else setMobilePane('dialog')
    void chat.open(id)
  }

  const hasResult = Boolean(details)
  const creativeSelector = banners.length > 1 && <div className="creative-selector" aria-label="Выбор креатива">{banners.map((item,index) => <button key={item.id} aria-pressed={banner?.id === item.id} onClick={() => setRequestedBannerId(item.id)}><span>{String(index+1).padStart(2,'0')}</span>{item.name}</button>)}</div>
  const chatProps = {
    chat, dictionaries: dictionaries.data,
    awaitsModeration: saved?.state === 'ON_MODERATION' && moderator,
    nextStep, role,
    moderationQueue: campaigns.data?.filter((item) => item.state === 'ON_MODERATION') ?? [],
    onOpenCampaign: openCampaign,
    onOpenVoiceMode: VOICE_ENABLED && role === 'campaignManager' && dictationSupported()
      ? () => { voiceAudio.unlock(); setVoiceOpen(true) }
      : undefined,
  }

  return (
    <div className={`pilot-shell ${hasResult ? 'has-result' : 'is-start'} ${navOpen ? 'nav-open' : ''}`} data-mobile-pane={mobilePane}>
      <aside className="pilot-nav" aria-label="Кампании">
        <div className="pilot-brand">adpilot<span>.</span><button className="mobile-close" aria-label="Закрыть меню" onClick={() => setNavOpen(false)}><X size={20} /></button></div>
        {!moderator && <Button variant="outline" className="new-campaign" disabled={chat.busy} onClick={() => openCampaign(null)}><Plus />Новая кампания</Button>}
        <div className="nav-section-title">Рабочее пространство</div>
        <div className="campaign-list">
          {campaigns.isPending && <p className="nav-message">Загружаем кампании…</p>}
          {campaigns.isError && <button className="nav-retry" onClick={() => void campaigns.refetch()}>Не удалось загрузить. Повторить</button>}
          {campaigns.data?.map((item) => <button key={item.id} disabled={chat.busy} className={`campaign-link ${item.id === campaignId ? 'selected' : ''}`} onClick={() => openCampaign(item.id)}><span>{item.name}</span><small>{item.state === 'ON_MODERATION' ? 'На модерации' : item.published ? 'Показ идёт' : item.state === 'NEEDS_WORK' ? 'Нужны правки' : ''}</small></button>)}
          {campaigns.data?.length === 0 && <p className="nav-message">Здесь будут ваши кампании.</p>}
        </div>
        <div className="nav-bottom"><UserMenu login={login} disabled={chat.busy} onSelect={(next) => {setCurrentUser(next); setLogin(next); void queryClient.invalidateQueries(); openCampaign(campaignId)}} /><ThemeToggle /></div>
      </aside>
      {navOpen && <button className="nav-scrim" aria-label="Закрыть меню кампаний" onClick={() => setNavOpen(false)} />}
      <div className="pilot-workspace">
        <header className="pilot-topbar">
          <button className="mobile-menu" aria-label="Открыть меню кампаний" onClick={() => setNavOpen(true)}><Menu size={21} /></button>
          <div className="workspace-location"><span>Кампании</span><span className="location-divider">/</span><strong>{details?.name ?? (moderator ? 'На проверке' : 'Новая кампания')}</strong></div>
          <div className="topbar-actions">{saved && <StatusBadge state={saved.state} />}{chat.confirmation && <span className="unsaved-label">Предложенные изменения</span>}
          </div>
        </header>
        <div className="pilot-stage">
          {hasResult && <main className="campaign-canvas" data-pane={pane} aria-label="Рабочая область кампании">
            <div className="canvas-heading"><div><p className="canvas-state">{saved ? 'Кампания' : 'Ваш новый черновик'}{saved?.published ? ' · Показ идёт' : ''}</p><h1>{details?.name ?? 'Собираем кампанию'}</h1>{(pane !== 'creative' || chat.confirmation) && <p className="canvas-description">{chat.confirmation ? 'Проверьте результат и состав изменений перед подтверждением.' : 'Ваш оффер, аудитория и креативы — в одном месте.'}</p>}</div><ArrowUpRight className="canvas-heading-mark" aria-hidden="true" /></div>
            <nav className="canvas-tabs" aria-label="Разделы кампании">{([['creative','Креативы'],['details','Параметры'],['history','Проверка и история']] as const).map(([id,label]) => <button key={id} aria-pressed={pane === id} onClick={() => setPane(id)}>{label}{id === 'creative' && banners.length > 0 && <span>{banners.length}</span>}</button>)}</nav>
            <div className="canvas-content">
              {failed && <div role="alert" className="workspace-error"><p>Не удалось загрузить часть данных.</p><Button variant="outline" onClick={() => {void campaign.refetch(); void warnings.refetch(); void dictionaries.refetch()}}>Повторить загрузку</Button></div>}
              {pane === 'creative' && <><div className="creative-gallery">
                {creativeSelector}
                <section className="creative-stage" aria-label="Превью">{banner && bannerType ? <CreativePreview key={banner.id} banner={banner} bannerType={bannerType} content={content} status={designStep?.label} /> : <DesignPlaceholder idle={!designStep} label={designStep?.label ?? 'Креатив появится здесь. Попросите ассистента собрать баннер.'} />}</section>
              </div>{validation && <div className="canvas-validation"><ValidationSummary validation={validation} /></div>}</>}
              {pane === 'details' && details && dictionaries.data && <div className="passport-sheet"><CampaignPassport key={campaignId ?? NEW_CAMPAIGN} campaign={details} dictionaries={dictionaries.data} selectedBannerId={banner?.id} onSelectBanner={(id) => {setRequestedBannerId(id); setPane('creative')}} edit={edit} /></div>}
              {pane === 'history' && details && <CampaignLifecycle key={`lifecycle-${saved?.id ?? NEW_CAMPAIGN}`} state={saved?.state ?? 'DRAFT'} audit={saved && audit.data} validation={validation} />}
            </div>
          </main>}
          <section className="pilot-assistant" aria-label="Диалог с ассистентом">
            {hasResult && <div className="assistant-heading"><span className="assistant-monogram">a</span><strong>Ассистент</strong><span>{chat.busy ? 'Собираю кампанию' : 'Давайте создадим точнее'}</span></div>}
            <ChatPanel {...chatProps} />
          </section>
        </div>
        {hasResult && <nav className="mobile-work-tabs" aria-label="Рабочие области"><button aria-pressed={mobilePane === 'dialog'} onClick={() => setMobilePane('dialog')}><MessageSquare size={18} />Диалог{chat.confirmation && <span className="attention-dot" />}</button><button aria-pressed={mobilePane === 'work' && pane !== 'creative'} onClick={() => {setMobilePane('work');setPane('details')}}><LayoutGrid size={18} />Кампания</button><button aria-pressed={mobilePane === 'work' && pane === 'creative'} onClick={() => {setMobilePane('work');setPane('creative')}}><ArrowUpRight size={18} />Превью</button></nav>}
      </div>
      {voiceOpen && (
        <VoiceMode
          chat={chat}
          dictionaries={dictionaries.data}
          nextStep={nextStep}
          campaignState={saved?.state}
          preview={banner && bannerType ? <div className="voice-creatives">{creativeSelector}<CreativePreview key={banner.id} banner={banner} bannerType={bannerType} content={content} status={designStep?.label} /></div> : undefined}
          onClose={() => setVoiceOpen(false)}
        />
      )}
    </div>
  )
}
