import { useEffect, useState } from 'react'

export function WelcomeTitle({ text }: { text: string }) {
  const [length, setLength] = useState(text.length)

  useEffect(() => {
    const media = matchMedia('(prefers-reduced-motion: reduce)')
    let frame = 0
    function start() {
      cancelAnimationFrame(frame)
      if (media.matches) {
        setLength(text.length)
        return
      }
      const startTime = performance.now()
      setLength(0)
      function type(now: number) {
        const next = Math.min(text.length, Math.floor((now - startTime) / 35))
        setLength(next)
        if (next < text.length) frame = requestAnimationFrame(type)
      }
      frame = requestAnimationFrame(type)
    }
    start()
    media.addEventListener('change', start)
    return () => {
      cancelAnimationFrame(frame)
      media.removeEventListener('change', start)
    }
  }, [text])

  return (
    <h1 className="welcome-title m-0" aria-label={text}>
      <span className="welcome-title-space" aria-hidden="true">{text}</span>
      <span className="welcome-title-text" aria-hidden="true" data-typing={length < text.length}>{text.slice(0, length)}</span>
    </h1>
  )
}
