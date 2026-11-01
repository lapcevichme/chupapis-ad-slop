import { useRef, useState } from 'react'
import type { FormEvent, KeyboardEvent } from 'react'
import { USERS } from '@/api/currentUser'
import { Button } from '@/components/ui/button'
import { ThemeToggle } from '@/features/campaign/ThemeToggle'
import { Avatar } from '@/features/campaign/UserMenu'
import { EntrySphere } from './EntrySphere'

// Размер буфера, а не вёрстки: на телефоне сфера маленькая, а на большом экране точки не должны расплываться.
const ORB_SIZE = { phone: 260, desktop: 720 }
const TYPING_LEVEL = 0.5
const TYPING_DECAY_MS = 700

interface EntryPageProps {
  onEnter: (login: string, brief?: string) => void
}

// Настоящей аутентификации в проекте нет: вход выбирает, с какой ролью идут запросы.
export function EntryPage({ onEnter }: EntryPageProps) {
  const [brief, setBrief] = useState('')
  const [missing, setMissing] = useState(false)
  const [dark, setDark] = useState(() => document.documentElement.classList.contains('dark'))
  const [orbSize] = useState(() => (matchMedia('(max-width: 900px)').matches ? ORB_SIZE.phone : ORB_SIZE.desktop))
  const field = useRef<HTMLTextAreaElement>(null)
  const lastInput = useRef(-Infinity)
  const manager = USERS.find((user) => user.role === 'campaignManager') ?? USERS[0]

  // Сфера откликается на ввод брифа так же, как в голосовом режиме на речь.
  function typingLevel() {
    return Math.max(0, TYPING_LEVEL * (1 - (performance.now() - lastInput.current) / TYPING_DECAY_MS))
  }

  function submit(event?: FormEvent) {
    event?.preventDefault()
    const text = brief.trim()
    if (text) {
      onEnter(manager.login, text)
      return
    }
    setMissing(true)
    field.current?.focus()
  }

  function handleKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === 'Enter' && !event.shiftKey && !event.nativeEvent.isComposing) {
      event.preventDefault()
      submit()
    }
  }

  return (
    <div className="entry-page">
      <header className="entry-header">
        <div className="pilot-brand entry-brand">adpilot<span>.</span></div>
        <ThemeToggle onChange={setDark} />
      </header>
      <main className="entry-main animate-stagger">
        <h1>От брифа<br />до модерации</h1>
        <p className="entry-lead">Ассистент соберёт кампанию и ничего не запишет без вашего подтверждения</p>
        <div className="entry-card">
          {USERS.map((user) => (
            <Button key={user.login} variant="secondary" className="entry-action" onClick={() => onEnter(user.login)}>
              <Avatar login={user.login} />
              Войти как {user.title}
            </Button>
          ))}
          <p className="entry-or">или</p>
          <form onSubmit={submit}>
            <label className="sr-only" htmlFor="entry-brief">Бриф кампании</label>
            <textarea
              ref={field}
              id="entry-brief"
              className="entry-brief"
              rows={2}
              placeholder="Продукт, аудитория, сроки"
              value={brief}
              aria-invalid={missing}
              aria-describedby={missing ? 'entry-brief-hint' : undefined}
              onChange={(event) => {
                setBrief(event.target.value)
                setMissing(false)
                lastInput.current = performance.now()
              }}
              onKeyDown={handleKeyDown}
            />
            {missing && <p id="entry-brief-hint" role="alert" className="entry-hint">Опишите кампанию или войдите по роли</p>}
            <Button type="submit" className="entry-action">Собрать кампанию</Button>
          </form>
          <p className="entry-note">Демо-стенд: данные синтетические, реальных показов нет.</p>
        </div>
      </main>
      <EntrySphere dark={dark} size={orbSize} getLevel={typingLevel} />
    </div>
  )
}
