import { Minus, Plus } from 'lucide-react'
import { useState } from 'react'
import type { FormEvent, ReactNode } from 'react'
import { ApiRequestError } from '@/api/http'
import type { CampaignChange, CampaignInfoPatch } from '@/api/campaigns'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'
import type { AudienceType, CampaignDraft, Dictionaries, Segment, Segments } from '@/types/api'
import { DateField, INPUT_CLASS, TimeField } from './DateTimeFields'
import { formatCount } from './format'

const CHECK_ROW_CLASS = 'flex min-h-11 cursor-pointer items-center gap-3 rounded-md px-2 py-1 hover:bg-muted'
const CHECKBOX_CLASS = 'size-4 shrink-0 accent-primary'

export interface PassportEdit {
  // Что произойдёт с кампанией после правки: например, снимется одобрение.
  notice?: string
  // Почему править сейчас нельзя. Кнопка «Изменить» при этом неактивна.
  blockedReason?: string
  onSubmit: (change: CampaignChange) => Promise<void>
}

interface FormProps {
  campaign: CampaignDraft
  dictionaries: Dictionaries
  edit: PassportEdit
  onClose: () => void
}

function errorMessages(error: unknown) {
  if (error instanceof ApiRequestError && error.errors.length > 0) return error.errors.map((item) => item.message)
  return ['Не удалось сохранить. Попробуйте ещё раз.']
}

interface EditFormProps {
  edit: PassportEdit
  onClose: () => void
  // null значит, что ничего не изменилось и сохранять нечего.
  getChange: () => CampaignChange | null
  children: ReactNode
}

function EditForm({ edit, onClose, getChange, children }: EditFormProps) {
  const [saving, setSaving] = useState(false)
  const [errors, setErrors] = useState<string[]>([])

  async function handleSubmit(event: FormEvent) {
    event.preventDefault()
    const change = getChange()
    if (!change) {
      onClose()
      return
    }
    setSaving(true)
    setErrors([])
    try {
      await edit.onSubmit(change)
      onClose()
    } catch (error) {
      setErrors(errorMessages(error))
      setSaving(false)
    }
  }

  return (
    <form
      className="flex animate-rise flex-col gap-3"
      onSubmit={(event) => void handleSubmit(event)}
      onKeyDown={(event) => {
        // Esc в открытом календаре закрывает только календарь: он в портале, но событие всплывает сюда через React.
        if (event.key === 'Escape' && !saving && event.currentTarget.contains(event.target as Node)) onClose()
      }}
    >
      {children}
      {edit.notice && <p className="m-0 rounded-md bg-warning px-3 py-2 text-[13px] leading-[18px] text-warning-foreground">{edit.notice}</p>}
      {errors.length > 0 && (
        <ul role="alert" className="m-0 flex list-none flex-col gap-1 rounded-md bg-error px-3 py-2 text-[13px] leading-[18px] text-error-foreground">
          {errors.map((message) => (
            <li key={message}>{message}</li>
          ))}
        </ul>
      )}
      {edit.blockedReason && <p className="m-0 text-[13px] leading-[18px] text-muted-foreground">{edit.blockedReason}</p>}
      <div className="flex flex-wrap gap-2">
        <Button type="submit" className="flex-1" disabled={saving || Boolean(edit.blockedReason)}>
          {saving ? 'Сохраняю…' : 'Сохранить'}
        </Button>
        <Button type="button" variant="outline" className="flex-1" disabled={saving} onClick={onClose}>
          Отмена
        </Button>
      </div>
    </form>
  )
}

function Labeled({ label, hint, className, children }: { label: string; hint?: string; className?: string; children: ReactNode }) {
  return (
    <label className={cn('flex min-w-0 flex-col gap-1', className)}>
      <span className="text-xs leading-4 text-muted-foreground">{label}</span>
      {children}
      {hint && <span className="text-xs leading-4 text-muted-foreground">{hint}</span>}
    </label>
  )
}

function toggled<T>(items: T[], item: T) {
  return items.includes(item) ? items.filter((value) => value !== item) : [...items, item]
}

function sameSet<T>(a: T[], b: T[]) {
  return a.length === b.length && a.every((item) => b.includes(item))
}

// Сводка для агента: несохранённый черновик правится через него.
function line(label: string, value: string) {
  return `${label}: ${value}`
}

export function MainForm({ campaign, dictionaries, edit, onClose }: FormProps) {
  const [name, setName] = useState(campaign.name ?? '')
  const [marketingName, setMarketingName] = useState(campaign.marketingName ?? '')
  const [startDate, setStartDate] = useState(campaign.startDate ?? '')
  const [startTime, setStartTime] = useState(campaign.startTime ?? '00:00')
  const [endDate, setEndDate] = useState(campaign.endDate ?? '')
  const [endTime, setEndTime] = useState(campaign.endTime ?? '23:59')
  const [topic, setTopic] = useState<string>(campaign.topic ?? '')
  const [tags, setTags] = useState(campaign.tags ?? [])
  const [keywords, setKeywords] = useState(campaign.keywords ?? '')

  function getChange(): CampaignChange | null {
    const info: CampaignInfoPatch = {}
    const summary: string[] = []
    const nextEndTime = endDate ? endTime : null
    if (name !== (campaign.name ?? '')) {
      info.name = name
      summary.push(line('название', name))
    }
    if (marketingName !== (campaign.marketingName ?? '')) {
      info.marketingName = marketingName || null
      summary.push(line('маркетинговое название', marketingName || 'убрать'))
    }
    if (startDate !== (campaign.startDate ?? '') || startTime !== (campaign.startTime ?? '00:00')) {
      info.startDate = startDate
      info.startTime = startTime
      summary.push(line('начало', `${startDate} ${startTime} UTC`))
    }
    if (endDate !== (campaign.endDate ?? '') || nextEndTime !== (campaign.endTime ?? null)) {
      info.endDate = endDate || null
      info.endTime = nextEndTime
      summary.push(line('конец', endDate ? `${endDate} ${endTime} UTC` : 'бессрочно'))
    }
    if (topic !== (campaign.topic ?? '')) {
      info.topic = topic as CampaignInfoPatch['topic']
      summary.push(line('тема', dictionaries.topics.find((item) => item.value === topic)?.label ?? topic))
    }
    if (!sameSet(tags, campaign.tags ?? [])) {
      info.tags = tags
      summary.push(line('теги', tags.map((id) => dictionaries.tags.find((tag) => tag.id === id)?.name ?? id).join(', ') || 'убрать'))
    }
    if (keywords !== (campaign.keywords ?? '')) {
      info.keywords = keywords || null
      summary.push(line('ключевые слова', keywords || 'убрать'))
    }
    return summary.length > 0 ? { info, summary } : null
  }

  return (
    <EditForm edit={edit} onClose={onClose} getChange={getChange}>
      <div className="grid grid-cols-2 gap-3">
        <Labeled label="Название" className="col-span-2">
          <input autoFocus required maxLength={100} value={name} onChange={(event) => setName(event.target.value)} className={INPUT_CLASS} />
        </Labeled>
        <Labeled label="Маркетинговое название" className="col-span-2">
          <input maxLength={100} value={marketingName} onChange={(event) => setMarketingName(event.target.value)} className={INPUT_CLASS} />
        </Labeled>
        <Labeled label="Дата начала">
          <DateField required value={startDate} onChange={setStartDate} placeholder="Выберите дату" />
        </Labeled>
        <Labeled label="Время начала, UTC">
          <TimeField required value={startTime} onChange={setStartTime} />
        </Labeled>
        <Labeled label="Дата конца" hint="Пусто значит бессрочно">
          <DateField value={endDate} onChange={setEndDate} placeholder="Бессрочно" min={startDate || undefined} clearLabel="Сделать бессрочной" />
        </Labeled>
        <Labeled label="Время конца, UTC">
          <TimeField required={Boolean(endDate)} disabled={!endDate} value={endTime} onChange={setEndTime} />
        </Labeled>
        <Labeled label="Тема" className="col-span-2">
          <select required value={topic} onChange={(event) => setTopic(event.target.value)} className={INPUT_CLASS}>
            {!topic && <option value="">Выберите тему</option>}
            {dictionaries.topics.map((item) => (
              <option key={item.value} value={item.value}>
                {item.label}
              </option>
            ))}
          </select>
        </Labeled>
        <Labeled label="Ключевые слова" hint="Через точку с запятой" className="col-span-2">
          <input maxLength={512} value={keywords} onChange={(event) => setKeywords(event.target.value)} className={INPUT_CLASS} />
        </Labeled>
      </div>
      <fieldset className="m-0 flex flex-col gap-1 border-0 p-0">
        <legend className="mb-1 p-0 text-xs leading-4 text-muted-foreground">Теги</legend>
        <div className="grid grid-cols-2 gap-x-3">
          {dictionaries.tags.map((tag) => (
            <label key={tag.id} className={CHECK_ROW_CLASS}>
              <input type="checkbox" checked={tags.includes(tag.id)} onChange={() => setTags(toggled(tags, tag.id))} className={CHECKBOX_CLASS} />
              <span className="min-w-0 text-sm leading-5 wrap-anywhere">{tag.name}</span>
            </label>
          ))}
        </div>
      </fieldset>
    </EditForm>
  )
}

export function RulesForm({ campaign, edit, onClose }: FormProps) {
  const [weight, setWeight] = useState(String(campaign.weight ?? 0))
  const [initialCtr, setInitialCtr] = useState(String(campaign.initialCtr ?? 15))

  function getChange(): CampaignChange | null {
    const info: CampaignInfoPatch = {}
    const summary: string[] = []
    if (Number(weight) !== (campaign.weight ?? 0)) {
      info.weight = Number(weight)
      summary.push(line('вес', weight))
    }
    if (Number(initialCtr) !== (campaign.initialCtr ?? 15)) {
      info.initialCtr = Number(initialCtr)
      summary.push(line('начальный CTR', `${initialCtr}%`))
    }
    return summary.length > 0 ? { info, summary } : null
  }

  return (
    <EditForm edit={edit} onClose={onClose} getChange={getChange}>
      <div className="grid grid-cols-2 gap-3">
        <Labeled label="Вес" hint="Приоритет среди кампаний в одном месте показа">
          <input autoFocus type="number" required min={0} step="any" value={weight} onChange={(event) => setWeight(event.target.value)} className={INPUT_CLASS} />
        </Labeled>
        <Labeled label="Начальный CTR, %" hint="Ожидаемая кликабельность, пока нет статистики">
          <input type="number" required min={0} max={100} step="any" value={initialCtr} onChange={(event) => setInitialCtr(event.target.value)} className={INPUT_CLASS} />
        </Labeled>
      </div>
    </EditForm>
  )
}

export function PlacesForm({ campaign, dictionaries, edit, onClose }: FormProps) {
  const [places, setPlaces] = useState(campaign.places ?? [])

  function getChange(): CampaignChange | null {
    if (sameSet(places, campaign.places ?? [])) return null
    const names = places.map((id) => dictionaries.places.find((place) => place.id === id)?.description ?? id)
    return { info: { places }, summary: [line('места показа', names.join(', '))] }
  }

  return (
    <EditForm edit={edit} onClose={onClose} getChange={getChange}>
      <fieldset className="m-0 flex max-h-72 flex-col overflow-y-auto border-0 p-0">
        <legend className="sr-only">Места показа</legend>
        {dictionaries.places.map((place) => {
          const inactive = place.state === 'INACTIVE'
          return (
            <label key={place.id} className={CHECK_ROW_CLASS}>
              <input
                type="checkbox"
                checked={places.includes(place.id)}
                // Деактивированное место можно убрать из кампании, но не добавить.
                disabled={inactive && !places.includes(place.id)}
                onChange={() => setPlaces(toggled(places, place.id))}
                className={CHECKBOX_CLASS}
              />
              <span className="flex min-w-0 flex-col">
                <span className="text-sm leading-5 wrap-anywhere">{place.description}</span>
                <span className="font-mono text-xs leading-4 wrap-anywhere text-muted-foreground">
                  {place.code}
                  {inactive && ', деактивировано'}
                </span>
              </span>
            </label>
          )
        })}
      </fieldset>
    </EditForm>
  )
}

function SegmentRow({ segment, segments, onChange }: { segment: Segment; segments: Segments; onChange: (next: Segments) => void }) {
  const included = segments.included?.includes(segment.code) ?? false
  const excluded = segments.excluded?.includes(segment.code) ?? false
  const without = {
    included: (segments.included ?? []).filter((code) => code !== segment.code),
    excluded: (segments.excluded ?? []).filter((code) => code !== segment.code),
  }

  return (
    <li className={cn('flex items-center gap-2 rounded-md px-2 py-1', included && 'bg-accent text-accent-foreground', excluded && 'bg-error text-error-foreground')}>
      <span className="flex min-w-0 flex-1 flex-col">
        <span className="text-sm leading-5 wrap-anywhere">{segment.name}</span>
        <span className="font-mono text-xs leading-4 wrap-anywhere opacity-80">
          {segment.code}, {formatCount(segment.count)}
          {included && ', включён'}
          {excluded && ', исключён'}
        </span>
      </span>
      <Button
        type="button"
        variant={included ? 'default' : 'outline'}
        size="icon"
        aria-pressed={included}
        aria-label={`Включить сегмент ${segment.name}`}
        title="Включить"
        onClick={() => onChange(included ? without : { ...without, included: [...without.included, segment.code] })}
      >
        <Plus aria-hidden="true" />
      </Button>
      <Button
        type="button"
        variant={excluded ? 'destructive' : 'outline'}
        size="icon"
        aria-pressed={excluded}
        aria-label={`Исключить сегмент ${segment.name}`}
        title="Исключить"
        onClick={() => onChange(excluded ? without : { ...without, excluded: [...without.excluded, segment.code] })}
      >
        <Minus aria-hidden="true" />
      </Button>
    </li>
  )
}

export function AudienceForm({ campaign, dictionaries, edit, onClose }: FormProps) {
  const [audienceType, setAudienceType] = useState<AudienceType>(campaign.audienceType ?? 'SEGMENTED')
  const [segments, setSegments] = useState<Segments>({ included: campaign.segments?.included ?? [], excluded: campaign.segments?.excluded ?? [] })
  const [query, setQuery] = useState('')
  const needle = query.trim().toLowerCase()
  // Порядок по исходному выбору, а не по текущему: иначе строка уедет из-под курсора при клике.
  const chosen = (segment: Segment) => campaign.segments?.included?.includes(segment.code) || campaign.segments?.excluded?.includes(segment.code)
  const visible = dictionaries.segments
    .filter((segment) => segment.name.toLowerCase().includes(needle) || segment.code.toLowerCase().includes(needle))
    // Выбранные наверху: в справочнике сорок сегментов.
    .toSorted((a, b) => Number(chosen(b)) - Number(chosen(a)))

  function getChange(): CampaignChange | null {
    const nextSegments: Segments = audienceType === 'ALL_USERS' ? { included: [], excluded: [] } : segments
    const typeChanged = audienceType !== (campaign.audienceType ?? 'SEGMENTED')
    const segmentsChanged =
      !sameSet(nextSegments.included ?? [], campaign.segments?.included ?? []) || !sameSet(nextSegments.excluded ?? [], campaign.segments?.excluded ?? [])
    if (!typeChanged && !segmentsChanged) return null
    const nameOf = (code: string) => dictionaries.segments.find((segment) => segment.code === code)?.name ?? code
    const summary =
      audienceType === 'ALL_USERS'
        ? [line('аудитория', 'все пользователи')]
        : [
            line('аудитория, включить сегменты', (nextSegments.included ?? []).map(nameOf).join(', ') || 'нет'),
            line('исключить сегменты', (nextSegments.excluded ?? []).map(nameOf).join(', ') || 'нет'),
          ]
    return { info: typeChanged ? { audienceType } : undefined, segments: segmentsChanged ? nextSegments : undefined, summary }
  }

  return (
    <EditForm edit={edit} onClose={onClose} getChange={getChange}>
      <fieldset className="m-0 flex flex-wrap gap-x-4 border-0 p-0">
        <legend className="sr-only">Кому показываем</legend>
        <label className={CHECK_ROW_CLASS}>
          <input type="radio" name="audience" checked={audienceType === 'SEGMENTED'} onChange={() => setAudienceType('SEGMENTED')} className={CHECKBOX_CLASS} />
          <span className="text-sm leading-5">По сегментам</span>
        </label>
        <label className={CHECK_ROW_CLASS}>
          <input type="radio" name="audience" checked={audienceType === 'ALL_USERS'} onChange={() => setAudienceType('ALL_USERS')} className={CHECKBOX_CLASS} />
          <span className="text-sm leading-5">Все пользователи</span>
        </label>
      </fieldset>
      {audienceType === 'SEGMENTED' && (
        <>
          <p className="m-0 text-[13px] leading-[18px] text-muted-foreground">Включённые сегменты объединяются по ИЛИ: клиент попадает в аудиторию, если он есть хотя бы в одном.</p>
          <Labeled label="Найти сегмент">
            <input value={query} onChange={(event) => setQuery(event.target.value)} className={INPUT_CLASS} />
          </Labeled>
          <ul className="m-0 flex max-h-72 list-none flex-col gap-1 overflow-y-auto p-0">
            {visible.map((segment) => (
              <SegmentRow key={segment.code} segment={segment} segments={segments} onChange={setSegments} />
            ))}
            {visible.length === 0 && <li className="p-2 text-[13px] leading-[18px] text-muted-foreground">Ничего не найдено</li>}
          </ul>
        </>
      )}
    </EditForm>
  )
}
