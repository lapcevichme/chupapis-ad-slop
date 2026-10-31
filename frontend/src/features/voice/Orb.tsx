import { useEffect, useRef } from 'react'
import { createStars, DOTS_ON_DARK, DOTS_ON_LIGHT } from './orbStars'

export type OrbMode = 'idle' | 'listen' | 'think' | 'speak'
export type OrbRenderer = (time: number, level: number, think: number, compact: boolean) => void

const MAX_CANVAS_PX = 720
const RESTING_LEVEL: Record<OrbMode, number> = { idle: 0.06, listen: 0.08, think: 0.22, speak: 0.1 }
const REDUCED_MOTION_TIME = 4

interface OrbProps {
  mode: OrbMode
  dark: boolean
  compact: boolean
  size: number
  getLevel: () => number
  // Множитель времени: всё движение сферы замедляется или ускоряется целиком.
  speed?: number
  // Вызывается на каждом кадре с тем же временем, что получила сфера.
  onFrame?: (time: number) => void
}

export function Orb({ mode, dark, compact, size, getLevel, speed = 1, onFrame }: OrbProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const state = useRef({ mode, compact, getLevel, onFrame })

  useEffect(() => {
    state.current = { mode, compact, getLevel, onFrame }
  }, [mode, compact, getLevel, onFrame])

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
    // Плашка тёмная в обеих темах, поэтому в ней точки всегда светлые.
    const render = createStars(canvas, dark ? DOTS_ON_DARK : DOTS_ON_LIGHT, DOTS_ON_DARK)
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
      const time = ((now - started) / 1000) * speed
      render(time, level, think, current.compact)
      current.onFrame?.(time)
      frame = requestAnimationFrame(draw)
    }
    if (reduced) {
      // Без движения сфера стоит на месте, а состояние передаёт подпись рядом.
      const redraw = () => {
        render(REDUCED_MOTION_TIME, 0.06, 0, state.current.compact)
        state.current.onFrame?.(REDUCED_MOTION_TIME)
      }
      redraw()
      const timer = setInterval(redraw, 500)
      return () => clearInterval(timer)
    }
    frame = requestAnimationFrame(draw)
    return () => cancelAnimationFrame(frame)
  }, [dark, speed])

  return <canvas ref={canvasRef} className="block size-full" aria-hidden="true" />
}
