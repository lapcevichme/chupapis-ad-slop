import { useEffect, useRef, useState, useSyncExternalStore } from 'react'
import { ChatMarkdown } from './ChatMarkdown'

const MOTION_QUERY = '(prefers-reduced-motion: reduce)'
function reducedMotion() { return matchMedia(MOTION_QUERY).matches }
function subscribeMotion(notify: () => void) {
  const media = matchMedia(MOTION_QUERY)
  media.addEventListener('change', notify)
  return () => media.removeEventListener('change', notify)
}

// Сглаживаем входящие SSE-порции; готовый ответ и восстановленная история доступны сразу.
export function AnimatedAnswer({ text, active }: { text: string; active: boolean }) {
  const reduced = useSyncExternalStore(subscribeMotion, reducedMotion)
  const [visible, setVisible] = useState(active ? '' : text)
  const shown = useRef(active ? '' : text)

  useEffect(() => {
    if (!active || reduced || !text.startsWith(shown.current)) {
      shown.current = text
      setVisible(text)
      return
    }
    const start = performance.now()
    const from = shown.current.length
    const length = text.length - from
    let frame = 0
    function reveal(now: number) {
      let end = from + Math.ceil(length * Math.min(1, (now - start) / 120))
      // Не показываем половину emoji на промежуточном кадре.
      if (end < text.length && /[\uDC00-\uDFFF]/.test(text[end])) end++
      shown.current = text.slice(0, end)
      setVisible(shown.current)
      if (end < text.length) frame = requestAnimationFrame(reveal)
    }
    frame = requestAnimationFrame(reveal)
    return () => cancelAnimationFrame(frame)
  }, [text, active, reduced])

  return (
    <div className="assistant-answer" data-streaming={active && !reduced} aria-busy={active}>
      <ChatMarkdown text={active && !reduced && text.startsWith(visible) ? visible : text} />
    </div>
  )
}
