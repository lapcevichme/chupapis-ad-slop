import { useEffect, useRef } from 'react'
import { createPearl } from './orbPearl'
import { createStars } from './orbStars'

export type OrbMode = 'idle' | 'listen' | 'think' | 'speak'
export type OrbRenderer = (time: number, level: number, think: number, compact: boolean) => void

const MAX_CANVAS_PX = 720
const RESTING_LEVEL: Record<OrbMode, number> = { idle: 0.06, listen: 0.08, think: 0.22, speak: 0.1 }

interface OrbProps {
  mode: OrbMode
  dark: boolean
  compact: boolean
  size: number
  getLevel: () => number
}

export function Orb({ mode, dark, compact, size, getLevel }: OrbProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const state = useRef({ mode, compact, getLevel })

  useEffect(() => {
    state.current = { mode, compact, getLevel }
  }, [mode, compact, getLevel])

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const pixels = Math.min(MAX_CANVAS_PX, Math.round(size * Math.min(devicePixelRatio || 1, 2)))
    canvas.width = pixels
    canvas.height = pixels
  }, [size])

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const render = dark ? createStars(canvas) : createPearl(canvas)
    if (!render) return
    const reduced = matchMedia('(prefers-reduced-motion: reduce)').matches
    const started = performance.now()
    let level = 0
    let think = 0
    let frame = 0
    const draw = (now: number) => {
      const current = state.current
      const target = Math.max(RESTING_LEVEL[current.mode], current.getLevel())
      level += (target - level) * (target > level ? 0.3 : 0.1)
      think += ((current.mode === 'think' ? 1 : 0) - think) * 0.05
      render((now - started) / 1000, level, think, current.compact)
      frame = requestAnimationFrame(draw)
    }
    if (reduced) {
      // Без движения сфера стоит на месте, а состояние передаёт подпись рядом.
      const redraw = () => render(4, 0.06, 0, state.current.compact)
      redraw()
      const timer = setInterval(redraw, 500)
      return () => clearInterval(timer)
    }
    frame = requestAnimationFrame(draw)
    return () => cancelAnimationFrame(frame)
  }, [dark])

  return <canvas ref={canvasRef} className="block size-full" aria-hidden="true" />
}
