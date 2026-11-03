import { useSyncExternalStore } from 'react'
import type { ApiError } from '@/types/api'
import type { components } from '@/types/openapi'

export type SessionUser = components['schemas']['UserOut']
export type Role = SessionUser['role']

export const ROLE_TITLES: Record<Role, string> = { campaignManager: 'менеджер', campaignModerator: 'модератор', admin: 'администратор' }

interface Session {
  accessToken: string
  user: SessionUser
}

let session: Session | null = null
const listeners = new Set<() => void>()

function setSession(next: Session | null) {
  session = next
  listeners.forEach((listener) => listener())
}

export function currentUser(): SessionUser | null {
  return session?.user ?? null
}

export function useCurrentUser(): SessionUser | null {
  return useSyncExternalStore(
    (listener) => {
      listeners.add(listener)
      return () => listeners.delete(listener)
    },
    currentUser,
  )
}

export class AuthError extends Error {
  status: number
  errors: ApiError[]

  constructor(status: number, errors: ApiError[]) {
    super(errors[0]?.message ?? `Ошибка входа: ${status}`)
    this.status = status
    this.errors = errors
  }
}

function csrfToken() {
  return document.cookie.match(/(?:^|;\s*)csrf_token=([^;]+)/)?.[1] ?? ''
}

async function authRequest(path: string, init: RequestInit = {}): Promise<Response> {
  return fetch(`/api/auth${path}`, { ...init, credentials: 'same-origin' })
}

async function readFailure(response: Response): Promise<AuthError> {
  const payload = (await response.json().catch(() => null)) as { errors?: ApiError[] } | null
  return new AuthError(response.status, payload?.errors ?? [])
}

async function openSession(response: Response): Promise<SessionUser> {
  if (!response.ok) throw await readFailure(response)
  const { access_token: accessToken } = (await response.json()) as { access_token: string }
  const me = await fetch('/api/users/me', { headers: { Authorization: `Bearer ${accessToken}` } })
  if (!me.ok) throw await readFailure(me)
  const user = (await me.json()) as SessionUser
  setSession({ accessToken, user })
  return user
}

const jsonPost = (body: unknown): RequestInit => ({
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify(body),
})

export const login = (email: string, password: string) => authRequest('/login', jsonPost({ email, password })).then(openSession)

export const register = (email: string, username: string, password: string) =>
  authRequest('/register', jsonPost({ email, username, password })).then(openSession)

// Refresh-токен лежит в httpOnly-cookie, JS его не видит: браузер сам шлёт cookie, а мы повторяем CSRF-токен в заголовке.
let refreshing: Promise<boolean> | null = null

function refreshSession(): Promise<boolean> {
  refreshing ??= authRequest('/refresh', { method: 'POST', headers: { 'X-CSRF-Token': csrfToken() } })
    .then(async (response) => {
      if (!response.ok) return false
      await openSession(response)
      return true
    })
    .catch(() => false)
    .finally(() => {
      refreshing = null
    })
  return refreshing
}

// Пытаемся продолжить прежнюю сессию при загрузке страницы.
export const restoreSession = refreshSession

export async function logout() {
  await authRequest('/logout', { method: 'POST' }).catch(() => undefined)
  setSession(null)
}

// fetch с токеном; один раз обновляет просроченный токен и повторяет запрос. Тела-потоки не повторяем: у FormData и строк это безопасно.
export async function authFetch(input: string, init: RequestInit = {}): Promise<Response> {
  const send = () => {
    const headers = new Headers(init.headers)
    if (session) headers.set('Authorization', `Bearer ${session.accessToken}`)
    return fetch(input, { ...init, headers })
  }
  const response = await send()
  if (response.status !== 401 || !session) return response
  if (await refreshSession()) return send()
  setSession(null)
  return response
}
