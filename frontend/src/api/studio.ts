import type { components } from '@/types/openapi'
import { userHeaders } from './currentUser'
import { apiRequest, ApiRequestError } from './http'

type Schemas = components['schemas']
export type StudioLayer = Required<Schemas['StudioLayer']>
export type StudioDocument = Omit<Required<Schemas['StudioDocument']>, 'layers'> & { layers: StudioLayer[] }
export type StoredStudioDocument = Omit<Schemas['StoredStudioDocument'], 'document'> & { document: StudioDocument }

export function studioKey(url?: string | null): string | null {
  return url?.match(/\/upload-studio-([0-9a-f]{32})\.png$/)?.[1] ?? null
}

export async function loadStudioDocument(url?: string | null): Promise<StudioDocument | null> {
  const key = studioKey(url)
  return key ? apiRequest<StudioDocument>(`/studio/documents/${key}`) : null
}

export async function saveStudioDocument(document: StudioDocument, png: Blob): Promise<StoredStudioDocument> {
  const body = new FormData()
  body.append('document', JSON.stringify(document))
  body.append('file', png, 'creative.png')
  const response = await fetch('/api/studio/documents', { method: 'POST', headers: userHeaders(), body, signal: AbortSignal.timeout(60_000) })
  if (!response.ok) {
    const payload = await response.json().catch(() => null)
    throw new ApiRequestError(response.status, payload?.errors ?? [])
  }
  return response.json()
}

export async function generateStudioVariants(document: StudioDocument, prompt: string): Promise<StudioDocument[]> {
  const result = await apiRequest<{ variants: StudioDocument[] }>('/studio/generate', { method: 'POST', body: { document, prompt, count: 3 } })
  return result.variants
}
