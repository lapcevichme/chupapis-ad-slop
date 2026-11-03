import type { ApiError } from '@/types/api'
import { authFetch } from './auth'

export class ApiRequestError extends Error {
  status: number
  errors: ApiError[]

  constructor(status: number, errors: ApiError[]) {
    super(errors[0]?.message ?? `Ошибка API: ${status}`)
    this.status = status
    this.errors = errors
  }
}

interface RequestOptions {
  method?: 'GET' | 'POST' | 'PUT' | 'DELETE'
  body?: unknown
}

export async function apiRequest<T = unknown>(path: string, { method = 'GET', body }: RequestOptions = {}): Promise<T> {
  const response = await authFetch(`/api${path}`, {
    method,
    headers: body === undefined ? {} : { 'Content-Type': 'application/json' },
    body: body === undefined ? undefined : JSON.stringify(body),
  })
  if (!response.ok) {
    const payload = (await response.json().catch(() => null)) as { errors?: ApiError[] } | null
    throw new ApiRequestError(response.status, payload?.errors ?? [])
  }
  return (await response.json()) as T
}
