import { useLayoutEffect, useRef, useState } from 'react'
import type { ReactNode } from 'react'

// Меняем масштаб целого макета, сохраняя исходные 300×600 и размеры текста в JSON.
export function FitPhone({ children, width: artWidth = 300, height: artHeight = 600, maxScale = 1, minScale = 0 }: { children: ReactNode; width?: number; height?: number; maxScale?: number; minScale?: number }) {
  const viewport = useRef<HTMLDivElement>(null)
  const [scale, setScale] = useState(1)

  useLayoutEffect(() => {
    const element = viewport.current
    if (!element) return
    const observer = new ResizeObserver(([entry]) => {
      const { width, height } = entry.contentRect
      if (width > 0 && height > 0) setScale(Math.max(Math.min(minScale, width / artWidth), Math.min(maxScale, width / artWidth, height / artHeight)))
    })
    observer.observe(element)
    return () => observer.disconnect()
  }, [artWidth, artHeight, maxScale, minScale])

  return (
    <div ref={viewport} className="preview-phone-area">
      <div style={{ width: artWidth * scale, height: artHeight * scale, margin: 'auto', flexShrink: 0 }}>
        <div className="preview-phone-native" style={{ width: artWidth, height: artHeight, transform: `scale(${scale})` }}>{children}</div>
      </div>
    </div>
  )
}
