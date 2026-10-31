import { Popover } from '@base-ui/react/popover'
import { ChevronDown, Search } from 'lucide-react'
import { useRef, useState } from 'react'
import type { KeyboardEvent } from 'react'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'
import type { CampaignListItem, CampaignState, UserRole } from '@/types/api'
import { StatusBadge } from './StatusBadge'

// От этих статусов кампания ждёт действия именно этой роли.
const ATTENTION: Record<UserRole, CampaignState[]> = {
  campaignManager: ['NEEDS_WORK', 'APPROVED'],
  campaignModerator: ['ON_MODERATION'],
}

interface CampaignPickerProps {
  campaigns: CampaignListItem[]
  currentId: number | null
  // Название и статус текущей кампании: у несохранённого черновика статуса ещё нет.
  name?: string | null
  state?: CampaignState
  role?: UserRole
  disabled: boolean
  onSelect: (id: number) => void
}

export function CampaignPicker({ campaigns, currentId, name, state, role, disabled, onSelect }: CampaignPickerProps) {
  const [open, setOpen] = useState(false)
  const [query, setQuery] = useState('')
  const [activeIndex, setActiveIndex] = useState(0)
  const input = useRef<HTMLInputElement>(null)
  const list = useRef<HTMLDivElement>(null)

  const needle = query.trim().toLowerCase()
  const found = campaigns.filter((item) => item.name.toLowerCase().includes(needle) || String(item.id).includes(needle))
  const attentionStates = role ? ATTENTION[role] : []
  const groups = [
    { title: 'Требуют внимания', items: found.filter((item) => attentionStates.includes(item.state)) },
    { title: attentionStates.length > 0 && found.some((item) => attentionStates.includes(item.state)) ? 'Остальные' : 'Все кампании', items: found.filter((item) => !attentionStates.includes(item.state)) },
  ].filter((group) => group.items.length > 0)
  // Порядок клавиатуры совпадает с порядком на экране.
  const options = groups.flatMap((group) => group.items)
  const active = options[Math.min(activeIndex, options.length - 1)]

  function move(step: number) {
    if (options.length === 0) return
    const next = (options.indexOf(active) + step + options.length) % options.length
    setActiveIndex(next)
    list.current?.querySelector(`[data-campaign="${options[next].id}"]`)?.scrollIntoView({ block: 'nearest' })
  }

  function choose(id: number) {
    setOpen(false)
    if (id !== currentId) onSelect(id)
  }

  function handleKeyDown(event: KeyboardEvent<HTMLInputElement>) {
    if (event.key === 'ArrowDown' || event.key === 'ArrowUp') {
      event.preventDefault()
      move(event.key === 'ArrowDown' ? 1 : -1)
    } else if (event.key === 'Enter' && active) {
      event.preventDefault()
      choose(active.id)
    }
  }

  return (
    <Popover.Root
      open={open}
      onOpenChange={(next) => {
        setOpen(next)
        if (next) {
          setQuery('')
          setActiveIndex(0)
        }
      }}
    >
      <Popover.Trigger
        disabled={disabled}
        render={
          <Button variant="outline" className="h-auto min-h-11 max-w-md min-w-0 justify-start gap-2 py-1 pr-3 pl-3 text-left whitespace-normal">
            <span className="min-w-0 truncate text-sm leading-5 font-medium">{name ?? (role === 'campaignModerator' ? 'Выберите кампанию' : 'Новая кампания')}</span>
            {state && <StatusBadge state={state} />}
            {name && !state && <span className="shrink-0 text-[13px] leading-[18px] font-normal text-muted-foreground">Не сохранена</span>}
            <ChevronDown className="ml-auto" aria-hidden="true" />
          </Button>
        }
      />
      <Popover.Portal>
        <Popover.Positioner side="bottom" align="start" sideOffset={8} className="z-50">
          <Popover.Popup initialFocus={input} className="flex max-h-[min(70dvh,480px)] w-[min(460px,calc(100vw-2rem))] flex-col rounded-lg border bg-popover text-popover-foreground shadow-lg outline-none">
            <div className="flex items-center gap-2 border-b px-3">
              <Search className="size-4 shrink-0 text-muted-foreground" aria-hidden="true" />
              <input
                ref={input}
                role="combobox"
                aria-expanded="true"
                aria-controls="campaign-options"
                aria-activedescendant={active ? `campaign-option-${active.id}` : undefined}
                aria-label="Найти кампанию"
                placeholder="Название или номер"
                value={query}
                onChange={(event) => {
                  setQuery(event.target.value)
                  setActiveIndex(0)
                }}
                onKeyDown={handleKeyDown}
                className="h-11 min-w-0 flex-1 bg-transparent text-sm leading-5 outline-none placeholder:text-muted-foreground"
              />
            </div>
            <div ref={list} id="campaign-options" role="listbox" aria-label="Кампании" className="min-h-0 flex-1 overflow-y-auto p-2">
              {options.length === 0 && <p className="m-0 p-3 text-[13px] leading-[18px] text-muted-foreground">Ничего не найдено</p>}
              {groups.map((group) => (
                <div key={group.title} role="group" aria-label={group.title} className="flex flex-col">
                  <span className="px-2 pt-2 pb-1 text-xs leading-4 font-medium text-muted-foreground">{group.title}</span>
                  {group.items.map((item) => (
                    <div
                      key={item.id}
                      id={`campaign-option-${item.id}`}
                      data-campaign={item.id}
                      role="option"
                      aria-selected={item.id === currentId}
                      onClick={() => choose(item.id)}
                      onMouseMove={() => setActiveIndex(options.indexOf(item))}
                      className={cn('flex min-h-11 cursor-pointer items-center justify-between gap-3 rounded-md px-2 py-1.5', item === active && 'bg-muted')}
                    >
                      <span className="flex min-w-0 flex-col">
                        <span className={cn('truncate text-sm leading-5', item.id === currentId && 'font-semibold')}>{item.name}</span>
                        <span className="text-xs leading-4 text-muted-foreground tabular-nums">№ {item.id}</span>
                      </span>
                      <StatusBadge state={item.state} />
                    </div>
                  ))}
                </div>
              ))}
            </div>
          </Popover.Popup>
        </Popover.Positioner>
      </Popover.Portal>
    </Popover.Root>
  )
}
