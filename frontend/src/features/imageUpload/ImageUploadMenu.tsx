import { ImagePlus, LoaderCircle, X } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import type { DragEvent } from 'react'
import { uploadImage } from '@/api/media'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'
import { imageMessage } from './imageMessage'
import { IMAGE_ACCEPT, IMAGE_LIMITS_HINT, ImageRejected, prepareImage } from './prepareImage'
import type { PreparedImage } from './prepareImage'

interface ImageUploadMenuProps {
  banner?: { id: unknown; name: string }
  disabled?: boolean
  onSend: (message: string) => void
}

export function ImageUploadMenu({ banner, disabled = false, onSend }: ImageUploadMenuProps) {
  const dialog = useRef<HTMLDialogElement>(null)
  const input = useRef<HTMLInputElement>(null)
  const [image, setImage] = useState<PreparedImage | null>(null)
  const [dragging, setDragging] = useState(false)
  const [reading, setReading] = useState(false)
  const [uploading, setUploading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const previewUrl = image?.previewUrl
  useEffect(() => () => {
    if (previewUrl) URL.revokeObjectURL(previewUrl)
  }, [previewUrl])

  function close() {
    if (uploading) return
    dialog.current?.close()
    setImage(null)
    setError(null)
    setDragging(false)
  }

  async function choose(file: File | undefined) {
    if (!file) return
    setError(null)
    setReading(true)
    try {
      setImage(await prepareImage(file))
    } catch (failure) {
      setImage(null)
      setError(failure instanceof ImageRejected ? failure.message : 'Не получилось обработать фото.')
    } finally {
      setReading(false)
      if (input.current) input.current.value = ''
    }
  }

  async function submit() {
    if (!image) return
    setError(null)
    setUploading(true)
    try {
      const url = await uploadImage(image.blob)
      dialog.current?.close()
      setImage(null)
      onSend(imageMessage(url, image.colors, image.tone, banner))
    } catch (failure) {
      setError(failure instanceof Error && failure.name !== 'TimeoutError' && failure.name !== 'TypeError' ? failure.message : 'Не удалось загрузить фото, проверьте связь и повторите.')
    } finally {
      setUploading(false)
    }
  }

  function handleDrop(event: DragEvent) {
    event.preventDefault()
    setDragging(false)
    void choose(event.dataTransfer.files[0])
  }

  return (
    <>
      <Button variant="secondary" className="w-full" disabled={disabled} onClick={() => dialog.current?.showModal()}>
        <ImagePlus aria-hidden="true" />
        Своё фото
      </Button>
      <dialog
        ref={dialog}
        aria-labelledby="image-upload-title"
        // Esc закрывает только меню, а не голосовой режим под ним.
        onKeyDown={(event) => {
          if (event.key === 'Escape') event.stopPropagation()
        }}
        onCancel={(event) => {
          event.preventDefault()
          close()
        }}
        onClick={(event) => {
          if (event.target === dialog.current) close()
        }}
        className="image-upload-menu m-auto w-[calc(100%-24px)] max-w-110 rounded-2xl border bg-card p-0 text-card-foreground shadow-xl backdrop:bg-foreground/40 max-sm:mb-3"
      >
        <div className="flex max-h-[calc(100dvh-48px)] flex-col gap-4 overflow-y-auto p-5">
          <div className="flex items-start justify-between gap-3">
            <div className="flex min-w-0 flex-col gap-1">
              <h2 id="image-upload-title" className="m-0 text-lg leading-6 font-semibold">
                Своё фото для креатива
              </h2>
              <p className="m-0 text-sm leading-5 text-muted-foreground">Поставим его в креатив и подберём цвета фона, текста и кнопки. Ничего не сохранится, пока вы не подтвердите карточку.</p>
            </div>
            <Button variant="ghost" size="icon" className="shrink-0" aria-label="Закрыть" disabled={uploading} onClick={close}>
              <X aria-hidden="true" />
            </Button>
          </div>

          {image ? (
            <div className="flex flex-col gap-3">
              <img src={image.previewUrl} alt="Выбранное фото" className="max-h-64 w-full rounded-xl bg-muted object-contain" />
              <div className="flex flex-col gap-2">
                <p className="m-0 text-[13px] leading-[18px] text-muted-foreground">Цвета, которые мы нашли на фото</p>
                <ul aria-label="Цвета фото" className="m-0 flex list-none flex-wrap gap-3 p-0">
                  {image.colors.map((color) => (
                    <li key={color} className="flex items-center gap-1.5 font-mono text-xs tabular-nums">
                      <span className="size-5 rounded-full border" style={{ backgroundColor: color }} aria-hidden="true" />
                      {color}
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          ) : (
            <label
              onDragOver={(event) => {
                event.preventDefault()
                setDragging(true)
              }}
              onDragLeave={() => setDragging(false)}
              onDrop={handleDrop}
              className={cn(
                'flex min-h-44 cursor-pointer flex-col items-center justify-center gap-2 rounded-xl border border-dashed p-5 text-center transition-colors focus-within:ring-2 focus-within:ring-ring',
                dragging ? 'border-primary bg-accent' : 'border-input hover:bg-muted',
              )}
            >
              {reading ? <LoaderCircle className="size-6 animate-spin text-muted-foreground" aria-hidden="true" /> : <ImagePlus className="size-6 text-muted-foreground" aria-hidden="true" />}
              <span className="text-sm leading-5 font-medium">{reading ? 'Смотрим фото…' : 'Выберите фото или перетащите его сюда'}</span>
              <span className="text-[13px] leading-[18px] text-muted-foreground">{IMAGE_LIMITS_HINT}</span>
              <input ref={input} type="file" aria-label="Файл с фото" accept={IMAGE_ACCEPT} className="sr-only" disabled={reading} onChange={(event) => void choose(event.target.files?.[0])} />
            </label>
          )}

          {error && (
            <p role="alert" className="m-0 text-sm leading-5 text-destructive">
              {error}
            </p>
          )}

          <p className="m-0 text-[13px] leading-[18px] text-muted-foreground">Не загружайте фото клиентов и чужие логотипы.</p>

          {image && (
            <div className="flex items-center gap-2">
              <Button variant="ghost" disabled={uploading} onClick={() => setImage(null)}>
                Другое фото
              </Button>
              <Button className="flex-1" disabled={uploading} onClick={() => void submit()}>
                {uploading && <LoaderCircle className="animate-spin" aria-hidden="true" />}
                {uploading ? 'Загружаем…' : 'Подстроить креатив'}
              </Button>
            </div>
          )}
        </div>
      </dialog>
    </>
  )
}
