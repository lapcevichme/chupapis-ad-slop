import { Pencil } from 'lucide-react'
import { useState } from 'react'
import type { ReactNode } from 'react'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'
import type { CampaignDraft, Dictionaries, EntityId } from '@/types/api'
import { Flash } from './Flash'
import { AudienceForm, MainForm, PlacesForm, RulesForm } from './PassportForms'
import type { PassportEdit } from './PassportForms'
import { formatCount, formatDateTime } from './format'

const NOT_SET = 'Не задано'

interface SectionProps {
  title: string
  edit?: PassportEdit
  form?: (onClose: () => void) => ReactNode
  children: ReactNode
}

function Section({ title, edit, form, children }: SectionProps) {
  const [editing, setEditing] = useState(false)
  const canEdit = edit && form

  return (
    <section className="flex flex-col gap-3 rounded-lg border bg-card p-4 text-card-foreground">
      <div className="flex items-center justify-between gap-3">
        <h2 className="m-0 text-sm leading-5 font-semibold">{title}</h2>
        {canEdit && !editing && (
          <Button
            variant="ghost"
            className="-my-2 -mr-2 text-[13px] font-medium"
            aria-label={`Изменить: ${title}`}
            title={edit.blockedReason}
            disabled={Boolean(edit.blockedReason)}
            onClick={() => setEditing(true)}
          >
            <Pencil aria-hidden="true" />
            Изменить
          </Button>
        )}
      </div>
      {canEdit && editing ? form(() => setEditing(false)) : children}
    </section>
  )
}

function Field({ label, value, code, flash, hint }: { label: string; value: ReactNode; code?: string; flash?: string; hint?: string }) {
  return (
    <div className="flex min-w-0 flex-col gap-0.5">
      <span className="text-xs leading-4 text-muted-foreground">{label}</span>
      <Flash value={flash ?? String(value)}>
        <span className="text-sm leading-5 font-medium wrap-anywhere">{value}</span>
      </Flash>
      {code && <span className="font-mono text-xs leading-4 text-muted-foreground">{code}</span>}
      {hint && <span className="text-xs leading-4 text-muted-foreground">{hint}</span>}
    </div>
  )
}

function Row({ name, code, aside, notice }: { name: string; code: string; aside?: string; notice?: string }) {
  return (
    <li className="flex animate-rise items-center justify-between gap-3 border-t py-2 first:border-t-0 first:pt-0 last:pb-0">
      <div className="flex min-w-0 flex-col gap-0.5">
        <span className="text-sm leading-5 font-medium wrap-anywhere">{name}</span>
        <span className="font-mono text-xs leading-4 wrap-anywhere text-muted-foreground">{code}</span>
      </div>
      {notice && <span className="shrink-0 rounded-sm bg-warning px-2 py-0.5 text-xs leading-4 text-warning-foreground">{notice}</span>}
      {aside && <span className="shrink-0 text-[13px] leading-[18px] text-muted-foreground tabular-nums">{aside}</span>}
    </li>
  )
}

function SegmentList({ title, codes, dictionaries }: { title: string; codes: string[]; dictionaries: Dictionaries }) {
  if (codes.length === 0) return null
  return (
    <div className="flex flex-col gap-2">
      <span className="text-xs leading-4 text-muted-foreground">{title}</span>
      <ul className="m-0 flex list-none flex-col p-0">
        {codes.map((code) => {
          const segment = dictionaries.segments.find((item) => item.code === code)
          return (
            <Row
              key={code}
              name={segment?.name ?? 'Нет в справочнике'}
              code={code}
              aside={segment && formatCount(segment.count)}
              notice={segment && segment.state !== 'ACTIVE' ? 'Не активен' : undefined}
            />
          )
        })}
      </ul>
    </div>
  )
}

interface CampaignPassportProps {
  campaign: CampaignDraft
  dictionaries: Dictionaries
  selectedBannerId?: EntityId
  onSelectBanner: (id: EntityId) => void
  edit?: PassportEdit
}

export function CampaignPassport({ campaign, dictionaries, selectedBannerId, onSelectBanner, edit }: CampaignPassportProps) {
  const formProps = edit && { campaign, dictionaries, edit }
  const topic = dictionaries.topics.find((item) => item.value === campaign.topic)
  const places = campaign.places ?? []
  const banners = campaign.banners ?? []
  const creatives = campaign.creatives ?? []
  const tagNames = (campaign.tags ?? []).map((id) => dictionaries.tags.find((tag) => tag.id === id)?.name ?? `Тег ${id}`)

  return (
    <div className="flex animate-stagger flex-col gap-3">
      <Section title="Основное" edit={edit} form={formProps && ((onClose) => <MainForm {...formProps} onClose={onClose} />)}>
        <div className="grid grid-cols-[repeat(auto-fit,minmax(160px,1fr))] gap-3.5">
          <Field label="Название" value={campaign.name ?? NOT_SET} />
          {campaign.marketingName && <Field label="Маркетинговое название" value={campaign.marketingName} />}
          <Field label="Начало" value={campaign.startDate ? formatDateTime(campaign.startDate, campaign.startTime) : NOT_SET} />
          <Field label="Конец" value={campaign.endDate ? formatDateTime(campaign.endDate, campaign.endTime) : 'Бессрочно'} />
          <Field label="Тема" value={topic?.label ?? campaign.topic ?? NOT_SET} code={campaign.topic ?? undefined} />
          <Field label="Теги" value={tagNames.length > 0 ? tagNames.join(', ') : 'Не заданы'} />
          {campaign.keywords && <Field label="Ключевые слова" value={campaign.keywords.split(';').join(', ')} />}
        </div>
      </Section>

      <Section title="Аудитория" edit={edit} form={formProps && ((onClose) => <AudienceForm {...formProps} onClose={onClose} />)}>
        <Flash value={JSON.stringify([campaign.audienceType, campaign.segments])} className="flex flex-col gap-3">
          {campaign.audienceType === 'ALL_USERS' && <Field label="Кому показываем" value="Все пользователи" code="ALL_USERS" />}
          {campaign.audienceType === 'SEGMENTED' && (
            <>
              <SegmentList title="Включить, любой из сегментов" codes={campaign.segments?.included ?? []} dictionaries={dictionaries} />
              <SegmentList title="Исключить" codes={campaign.segments?.excluded ?? []} dictionaries={dictionaries} />
            </>
          )}
          {!campaign.audienceType && <p className="m-0 text-[13px] leading-[18px] text-muted-foreground">Аудитория не выбрана</p>}
        </Flash>
      </Section>

      <Section title="Места показа" edit={edit} form={formProps && ((onClose) => <PlacesForm {...formProps} onClose={onClose} />)}>
        <Flash value={places.join()}>
          {places.length > 0 ? (
            <ul className="m-0 flex list-none flex-col p-0">
              {places.map((id) => {
                const place = dictionaries.places.find((item) => item.id === id)
                return (
                  <Row
                    key={id}
                    name={place?.description ?? 'Нет в справочнике'}
                    code={place?.code ?? String(id)}
                    notice={place?.state === 'INACTIVE' ? 'Деактивировано' : undefined}
                  />
                )
              })}
            </ul>
          ) : (
            <p className="m-0 text-[13px] leading-[18px] text-muted-foreground">Места показа не выбраны</p>
          )}
        </Flash>
      </Section>

      <Section title="Правила показа" edit={edit} form={formProps && ((onClose) => <RulesForm {...formProps} onClose={onClose} />)}>
        <div className="grid grid-cols-2 gap-3.5">
          <Field
            label="Вес"
            hint="Приоритет среди кампаний в одном месте показа"
            value={<span className="tabular-nums">{campaign.weight ?? NOT_SET}</span>}
            flash={String(campaign.weight)}
          />
          <Field
            label="Начальный CTR"
            hint="Ожидаемая кликабельность, пока нет статистики"
            value={<span className="tabular-nums">{campaign.initialCtr == null ? NOT_SET : `${campaign.initialCtr}%`}</span>}
            flash={String(campaign.initialCtr)}
          />
        </div>
      </Section>

      <Section title="Креативы">
        <Flash value={JSON.stringify([banners.map((banner) => banner.name), creatives.map((creative) => creative.channelCode)])}>
          {banners.length > 0 ? (
            <ul className="m-0 flex list-none flex-col gap-1 p-0">
              {banners.map((banner) => {
                const channels = creatives.filter((creative) => creative.bannerId === banner.id).map((creative) => creative.channelCode)
                const selected = banner.id === selectedBannerId
                return (
                  <li key={banner.id} className="animate-rise">
                    <button
                      type="button"
                      aria-current={selected}
                      onClick={() => onSelectBanner(banner.id)}
                      className={cn(
                        'flex min-h-11 w-full cursor-pointer flex-col justify-center rounded-md px-3 py-2 text-left outline-none hover:bg-muted focus-visible:ring-2 focus-visible:ring-ring',
                        selected && 'bg-accent text-accent-foreground hover:bg-accent',
                      )}
                    >
                      <span className="text-sm leading-5 font-medium">{banner.name}</span>
                      <span className="text-xs leading-4 opacity-80">{channels.length > 0 ? channels.join(', ') : 'Канал не назначен'}</span>
                    </button>
                  </li>
                )
              })}
            </ul>
          ) : (
            <p className="m-0 text-[13px] leading-[18px] text-muted-foreground">Креативов пока нет</p>
          )}
        </Flash>
      </Section>
    </div>
  )
}
