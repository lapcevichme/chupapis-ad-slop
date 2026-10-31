import { useState } from 'react'
import type { ReactNode } from 'react'
import { cn } from '@/lib/utils'

interface FlashProps {
  // Подсветка срабатывает, когда значение изменилось. При первом показе её нет.
  value: string
  className?: string
  overlayClassName?: string
  children: ReactNode
}

export function Flash({ value, className, overlayClassName = '-inset-x-1 -inset-y-0.5 rounded-md animate-flash', children }: FlashProps) {
  const [seen, setSeen] = useState(value)
  const [changes, setChanges] = useState(0)
  if (value !== seen) {
    setSeen(value)
    setChanges(changes + 1)
  }

  return (
    <div className={cn('relative', className)}>
      {children}
      {/* Новый key перезапускает анимацию, а содержимое при этом не пересоздаётся. */}
      {changes > 0 && <span key={changes} aria-hidden="true" className={cn('pointer-events-none absolute', overlayClassName)} />}
    </div>
  )
}
