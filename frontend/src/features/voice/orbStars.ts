import type { OrbRenderer } from './Orb'

const POINTS = 1500
const GOLDEN_ANGLE = Math.PI * (3 - Math.sqrt(5))
const TILT_COS = Math.cos(0.32)
const TILT_SIN = Math.sin(0.32)

export const DOTS_ON_DARK = '236,239,232'
// Цвет текста панели (--foreground светлой темы).
export const DOTS_ON_LIGHT = '40,39,37'

export function createStars(canvas: HTMLCanvasElement, color = DOTS_ON_DARK): OrbRenderer | null {
  const context = canvas.getContext('2d')
  if (!context) return null
  const points = Array.from({ length: POINTS }, (_, index) => {
    const y = 1 - (2 * (index + 0.5)) / POINTS
    const radius = Math.sqrt(1 - y * y)
    const angle = GOLDEN_ANGLE * index
    return [Math.cos(angle) * radius, y, Math.sin(angle) * radius]
  })
  let band = 0

  return (t, level, think, compact) => {
    const { width, height } = canvas
    const radius = Math.min(width, height) * 0.4
    context.clearRect(0, 0, width, height)
    band += ((think > 0.5 ? 1 : 0) - band) * 0.05
    const rotation = t * (0.16 + 0.35 * think)
    const cos = Math.cos(rotation)
    const sin = Math.sin(rotation)
    // В плашке холст сжат в десять раз: мелкие точки исчезли бы, поэтому там они крупнее и реже.
    const step = compact ? 6 : 1
    for (let index = 0; index < POINTS; index += step) {
      const [baseX, baseY, baseZ] = points[index]
      const snapped = Math.round(baseY * 3.5) / 3.5
      const y = baseY + (snapped - baseY) * band
      const stretch = Math.sqrt(Math.max(0.01, 1 - y * y) / Math.max(0.01, 1 - baseY * baseY))
      const wave = Math.sin(y * 5 - t * 4) * 0.5 + 0.5
      const scale = 1 + level * (0.05 + 0.11 * wave)
      const x1 = baseX * stretch * scale
      const y1 = y * scale
      const z1 = baseZ * stretch * scale
      const x2 = x1 * cos + z1 * sin
      const z2 = -x1 * sin + z1 * cos
      const y2 = y1 * TILT_COS - z2 * TILT_SIN
      const z3 = y1 * TILT_SIN + z2 * TILT_COS
      const depth = (z3 + 1.4) / 2.4
      const size = compact ? width / 45 : Math.max(1, (width / 560) * (1 + 2.4 * depth * depth))
      context.fillStyle = `rgba(${color},${(compact ? 0.35 + 0.65 * depth : 0.1 + 0.9 * depth * depth).toFixed(3)})`
      context.fillRect(width / 2 + x2 * radius - size / 2, height / 2 - y2 * radius - size / 2, size, size)
    }
  }
}
