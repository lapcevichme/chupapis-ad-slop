import { useState } from 'react'
import { Button } from '@/components/ui/button'

// Кнопки только формулируют решение человека для агента: запись всё равно идёт через карточку подтверждения.
export function ModerationBar({ onSend }: { onSend: (text: string) => void }) {
  const [declining, setDeclining] = useState(false)
  const [comment, setComment] = useState('')

  return (
    <section aria-label="Решение модератора" className="flex flex-col gap-3 rounded-lg border bg-info p-4 text-info-foreground">
      <h3 className="m-0 text-sm leading-5 font-semibold">Кампания ждёт вашего решения</h3>
      {declining ? (
        <form
          className="flex flex-col gap-2"
          onSubmit={(event) => {
            event.preventDefault()
            onSend(`Возвращаю кампанию на правки. Комментарий модератора: ${comment.trim()}`)
          }}
        >
          <label htmlFor="decline-comment" className="text-[13px] leading-[18px]">
            Что нужно исправить? Менеджер увидит этот комментарий.
          </label>
          <textarea
            id="decline-comment"
            autoFocus
            rows={2}
            value={comment}
            onChange={(event) => setComment(event.target.value)}
            className="min-h-11 resize-none rounded-md border border-input bg-background px-3 py-2 text-sm leading-5 text-foreground outline-none focus-visible:ring-2 focus-visible:ring-ring"
          />
          <div className="flex flex-wrap gap-2">
            <Button type="submit" variant="destructive" className="flex-1 bg-background" disabled={!comment.trim()}>
              Вернуть на правки
            </Button>
            <Button type="button" variant="outline" className="flex-1" onClick={() => setDeclining(false)}>
              Назад
            </Button>
          </div>
        </form>
      ) : (
        <div className="flex flex-wrap gap-2">
          <Button className="flex-1" onClick={() => onSend('Одобряю кампанию')}>
            Одобрить
          </Button>
          <Button variant="destructive" className="flex-1 bg-background" onClick={() => setDeclining(true)}>
            Вернуть на правки
          </Button>
        </div>
      )}
    </section>
  )
}
