import { useEffect, useRef, useState } from 'react'
import { BannerCreative } from '@/features/preview/BannerPreview'
import { PromoPreview } from '@/features/preview/PromoPreview'
import { Orb } from '@/features/voice/Orb'
import { SPHERE_RADIUS, spherePosition } from '@/features/voice/orbStars'
import { SPHERE_EXAMPLES } from './sphereExamples'
import type { SphereExample } from './sphereExamples'

// Сфера вращается медленнее, чем в голосовом режиме, чтобы карточки можно было прочитать на ходу.
const SPEED = 0.5
const DEGREES = Math.PI / 180
// Карточка гаснет, уходя за край сферы: сзади её не видно.
const FADE = { from: -0.02, to: 0.28 }
// На маленькой сфере названия длиннее её радиуса. Соседи на одной широте сменяют друг друга при z≈0,55: ниже этого порога они наехали бы друг на друга.
const COMPACT_FADE = { from: 0.55, to: 0.68 }
const COMPACT_CANVAS = 300
// Поворот по кривизне сферы: карточка лежит на поверхности и сжимается к краю. По вертикали слабее, иначе текст выглядит курсивом.
const TURN = { y: 0.4, x: 0.22 }
const COMPACT_TURN = { y: 0.2, x: 0.2 }
// Какая доля карточки может выйти за контур сферы: углы скруглены, и совсем без выхода она прижималась бы к центру.
const EDGE_REACH = 0.85
// Масштаб креативов: сторона холста, при которой они показаны в свой размер, и нижний предел.
const FULL_SIZE_CANVAS = 880
const MIN_SCALE = 0.6

const ANCHORS = SPHERE_EXAMPLES.map(({ longitude, latitude }) => {
  const ring = Math.cos(latitude * DEGREES)
  return [ring * Math.cos(longitude * DEGREES), Math.sin(latitude * DEGREES), ring * Math.sin(longitude * DEGREES)] as const
})

function Creative({ example }: { example: SphereExample }) {
  if (example.kind === 'promo') return <PromoPreview content={example.promo} />
  if (example.kind === 'story') return <BannerCreative content={example.banner} type="STORY" />
  return <BannerCreative content={example.banner} type="SMART_BANNER" size={example.kind} />
}

interface EntrySphereProps {
  dark: boolean
  size: number
  getLevel: () => number
}

export function EntrySphere({ dark, size, getLevel }: EntrySphereProps) {
  const cards = useRef<(HTMLLIElement | null)[]>([])
  // Без движения полупрозрачная карточка так и осталась бы нечитаемой, поэтому показываем только целые.
  const [still] = useState(() => matchMedia('(prefers-reduced-motion: reduce)').matches)

  const list = useRef<HTMLUListElement>(null)
  const fadeRange = useRef(FADE)
  const canvasSide = useRef(0)
  const cardSizes = useRef<{ width: number; height: number }[]>([])

  useEffect(() => {
    const element = list.current
    if (!element) return
    const observer = new ResizeObserver(([entry]) => {
      const scale = Math.min(1, Math.max(MIN_SCALE, entry.contentRect.width / FULL_SIZE_CANVAS))
      element.style.setProperty('--entry-scale', scale.toFixed(3))
      fadeRange.current = entry.contentRect.width < COMPACT_CANVAS ? COMPACT_FADE : FADE
      canvasSide.current = entry.contentRect.width
      cardSizes.current = []
    })
    observer.observe(element)
    return () => observer.disconnect()
  }, [])

  // Положение меняем прямо в DOM: перерисовывать React на каждом кадре незачем.
  function place(time: number) {
    const side = canvasSide.current
    if (!side) return
    const radius = side * SPHERE_RADIUS
    const compact = side < COMPACT_CANVAS
    const turn = compact ? COMPACT_TURN : TURN
    ANCHORS.forEach(([anchorX, anchorY, anchorZ], index) => {
      const card = cards.current[index]
      if (!card) return
      const { x, y, z } = spherePosition(anchorX, anchorY, anchorZ, time)
      const scale = 0.8 + 0.2 * Math.max(z, 0)
      const { from, to } = fadeRange.current
      const fade = Math.min(1, Math.max(0, (z - from) / (to - from)))
      const turnY = Math.atan2(x, Math.max(z, 0.05)) * turn.y
      const turnX = Math.atan2(y, Math.max(z, 0.05)) * turn.x
      let left = x * radius
      let top = -y * radius
      // Названия на маленькой сфере шире её радиуса: притянув их внутрь контура, мы собрали бы их в центре.
      if (!compact) {
        cardSizes.current[index] ??= { width: card.offsetWidth, height: card.offsetHeight }
        const { width, height } = cardSizes.current[index]
        const distance = Math.hypot(left, top) || 1
        // Сколько занимает карточка в сторону края сферы с учётом сжатия при повороте.
        const reach = (Math.abs(left / distance) * (width / 2) * Math.cos(turnY) + Math.abs(top / distance) * (height / 2) * Math.cos(turnX)) * scale * EDGE_REACH
        const pull = Math.min(1, Math.max(0, radius - reach) / distance)
        left *= pull
        top *= pull
      }
      card.style.transform = `translate(-50%, -50%) translate(${left.toFixed(1)}px, ${top.toFixed(1)}px) perspective(900px) rotateY(${turnY.toFixed(3)}rad) rotateX(${turnX.toFixed(3)}rad) scale(${scale.toFixed(3)})`
      card.style.opacity = still ? String(Math.floor(fade)) : fade.toFixed(3)
      card.style.zIndex = String(Math.round(z * 100) + 100)
    })
  }

  return (
    <div className="entry-orb">
      <Orb key={String(dark)} mode="idle" dark={dark} compact={false} size={size} getLevel={getLevel} speed={SPEED} onFrame={place} />
      <ul ref={list} className="entry-examples" aria-label="Примеры акций">
        {SPHERE_EXAMPLES.map((example, index) => (
          <li
            key={example.source}
            ref={(node) => {
              cards.current[index] = node
            }}
            className="entry-example"
            data-kind={example.kind}
          >
            <span className="entry-example-label">{example.label}</span>
            <div className="entry-creative" style={{ background: example.background }}>
              <Creative example={example} />
            </div>
            <span className="entry-chip" style={{ background: example.background }}>
              <img src={example.image} alt="" width={24} height={24} />
              <strong style={{ color: example.titleColor }}>{example.title}</strong>
            </span>
          </li>
        ))}
      </ul>
    </div>
  )
}
