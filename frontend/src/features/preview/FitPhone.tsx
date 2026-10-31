import { useLayoutEffect, useRef, useState } from 'react'
import type { ReactNode } from 'react'

// Меняем масштаб целого макета, сохраняя исходные 300×600 и размеры текста в JSON.
export function FitPhone({ children }: { children: ReactNode }) {
  const viewport = useRef<HTMLDivElement>(null)
  const [scale, setScale] = useState(1)

  useLayoutEffect(() => {
    const element = viewport.current
    if (!element) return
    const observer = new ResizeObserver(([entry]) => {
      const { width, height } = entry.contentRect
      if (width > 0 && height > 0) setScale(Math.min(1, width / 300, height / 600))
    })
    observer.observe(element)
    return () => observer.disconnect()
  }, [])

  return (
    <div ref={viewport} className="preview-phone-area">
      <div style={{ width: 300 * scale, height: 600 * scale }}>
        <div className="preview-phone-native" style={{ transform: `scale(${scale})` }}>{children}</div>
      </div>
    </div>
  )
}
