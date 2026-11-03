import type { ApiError } from '@/types/api'
import { authFetch } from './auth'
import { ApiRequestError } from './http'

const UPLOAD_TIMEOUT_MS = 60_000

export async function uploadImage(image: Blob): Promise<string> {
  const body = new FormData()
  body.append('file', image, 'photo.jpg')
  const response = await authFetch('/api/media/images', {
    method: 'POST',
        body,
    signal: AbortSignal.timeout(UPLOAD_TIMEOUT_MS),
  })
  if (!response.ok) {
    const payload = (await response.json().catch(() => null)) as { errors?: ApiError[] } | null
    throw new ApiRequestError(response.status, payload?.errors ?? [])
  }
  const { url } = (await response.json()) as { url: string }
  return url
}
