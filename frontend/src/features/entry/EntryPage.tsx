import { useRef, useState } from 'react'
import type { FormEvent, KeyboardEvent } from 'react'
import { AuthError, login, register } from '@/api/auth'
import { Button } from '@/components/ui/button'
import { ThemeToggle } from '@/features/campaign/ThemeToggle'
import { EntrySphere } from './EntrySphere'

// Размер буфера, а не вёрстки: на телефоне сфера маленькая, а на большом экране точки не должны расплываться.
const ORB_SIZE = { phone: 260, desktop: 720 }
const TYPING_LEVEL = 0.5
const TYPING_DECAY_MS = 700

// Демо-стенд подсказывает учётки из кейса; в проде переменная не задана и подсказки нет.
const DEMO_PASSWORD = import.meta.env.VITE_DEMO_PASSWORD as string | undefined
const DEMO_ACCOUNTS = [
  { title: 'менеджер', email: 'ivanov.p@example.com' },
  { title: 'модератор', email: 'petrova.m@example.com' },
]

interface EntryPageProps {
  onEnter: (brief?: string) => void
}

export function EntryPage({ onEnter }: EntryPageProps) {
  const [mode, setMode] = useState<'login' | 'register'>('login')
  const [email, setEmail] = useState('')
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [brief, setBrief] = useState('')
  const [error, setError] = useState<string>()
  const [pending, setPending] = useState(false)
  const [dark, setDark] = useState(() => document.documentElement.classList.contains('dark'))
  const [orbSize] = useState(() => (matchMedia('(max-width: 900px)').matches ? ORB_SIZE.phone : ORB_SIZE.desktop))
  const lastInput = useRef(-Infinity)

  // Сфера откликается на ввод брифа так же, как в голосовом режиме на речь.
  function typingLevel() {
    return Math.max(0, TYPING_LEVEL * (1 - (performance.now() - lastInput.current) / TYPING_DECAY_MS))
  }

  async function submit(event?: FormEvent) {
    event?.preventDefault()
    setError(undefined)
    setPending(true)
    try {
      if (mode === 'login') await login(email.trim(), password)
      else await register(email.trim(), username.trim(), password)
      onEnter(brief.trim() || undefined)
    } catch (caught) {
      setError(caught instanceof AuthError ? caught.message : 'Не удалось связаться с сервером. Попробуйте ещё раз.')
      setPending(false)
    }
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
          <form onSubmit={submit}>
            <label className="sr-only" htmlFor="entry-email">Почта</label>
            <input id="entry-email" className="entry-input" type="email" autoComplete="email" required placeholder="Почта" value={email} onChange={(event) => setEmail(event.target.value)} />
            {mode === 'register' && (
              <>
                <label className="sr-only" htmlFor="entry-username">Имя пользователя</label>
                <input id="entry-username" className="entry-input" autoComplete="username" required minLength={3} maxLength={64} pattern="[A-Za-z0-9._\-]+" title="Латиница, цифры, точка, дефис и подчёркивание" placeholder="Имя пользователя" value={username} onChange={(event) => setUsername(event.target.value)} />
              </>
            )}
            <label className="sr-only" htmlFor="entry-password">Пароль</label>
            <input id="entry-password" className="entry-input" type="password" autoComplete={mode === 'login' ? 'current-password' : 'new-password'} required minLength={mode === 'register' ? 8 : undefined} placeholder={mode === 'register' ? 'Пароль, от 8 символов' : 'Пароль'} value={password} onChange={(event) => setPassword(event.target.value)} />
            <label className="sr-only" htmlFor="entry-brief">Бриф кампании</label>
            <textarea
              id="entry-brief"
              className="entry-brief"
              rows={2}
              placeholder="Бриф кампании, если хотите начать с него: продукт, аудитория, сроки"
              value={brief}
              onChange={(event) => {
                setBrief(event.target.value)
                lastInput.current = performance.now()
              }}
              onKeyDown={handleKeyDown}
            />
            {error && <p role="alert" className="entry-hint">{error}</p>}
            <Button type="submit" className="entry-action" disabled={pending}>
              {mode === 'login' ? (brief.trim() ? 'Войти и собрать кампанию' : 'Войти') : brief.trim() ? 'Создать аккаунт и собрать кампанию' : 'Создать аккаунт'}
            </Button>
          </form>
          <button type="button" className="entry-switch" onClick={() => { setMode(mode === 'login' ? 'register' : 'login'); setError(undefined) }}>
            {mode === 'login' ? 'Нет аккаунта? Создать' : 'Уже есть аккаунт? Войти'}
          </button>
          {DEMO_PASSWORD && mode === 'login' && (
            <p className="entry-note">
              Демо-стенд:{' '}
              {DEMO_ACCOUNTS.map((account, index) => (
                <span key={account.email}>
                  {index > 0 && ', '}
                  <button type="button" className="entry-switch" onClick={() => { setEmail(account.email); setPassword(DEMO_PASSWORD) }}>{account.title}</button>
                </span>
              ))}
              . Данные синтетические, реальных показов нет.
            </p>
          )}
        </div>
      </main>
      <EntrySphere dark={dark} size={orbSize} getLevel={typingLevel} />
    </div>
  )
}
