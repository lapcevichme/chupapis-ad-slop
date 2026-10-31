import { useEffect, useRef, useState } from 'react'
import { BannerCreative } from '@/features/preview/BannerPreview'
import { PromoPreview } from '@/features/preview/PromoPreview'
import { Orb } from '@/features/voice/Orb'
import { SPHERE_RADIUS, spherePosition } from '@/features/voice/orbStars'
import { SPHERE_EXAMPLES } from './sphereExamples'
import type { SphereExample } from './sphereExamples'

// Сфера вращается медленнее, чем в голосовом режиме, чтобы карточки можно было прочитать на ходу.
const SPEED = 0.5
const RADIUS_CQ = SPHERE_RADIUS * 100
const DEGREES = Math.PI / 180
// Карточка гаснет, уходя за край сферы: сзади её не видно.
const FADE = { from: -0.02, to: 0.28 }
// На маленькой сфере названия длиннее её радиуса, поэтому видны только те, что ближе к зрителю: так они не наезжают друг на друга.
const COMPACT_FADE = { from: 0.3, to: 0.5 }
const COMPACT_CANVAS = 300
// Лёгкий наклон по кривизне сферы; сильнее текст начинает выглядеть курсивом.
const TILT = 0.2
// Масштаб креативов: сторона холста, при которой они показаны в свой размер, и нижний предел.
const FULL_SIZE_CANVAS = 800
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

  useEffect(() => {
    const element = list.current
    if (!element) return
    const observer = new ResizeObserver(([entry]) => {
      const scale = Math.min(1, Math.max(MIN_SCALE, entry.contentRect.width / FULL_SIZE_CANVAS))
      element.style.setProperty('--entry-scale', scale.toFixed(3))
      fadeRange.current = entry.contentRect.width < COMPACT_CANVAS ? COMPACT_FADE : FADE
    })
    observer.observe(element)
    return () => observer.disconnect()
  }, [])

  // Положение меняем прямо в DOM: перерисовывать React на каждом кадре незачем.
  function place(time: number) {
    ANCHORS.forEach(([anchorX, anchorY, anchorZ], index) => {
      const card = cards.current[index]
      if (!card) return
      const { x, y, z } = spherePosition(anchorX, anchorY, anchorZ, time)
      const front = Math.max(z, 0)
      const { from, to } = fadeRange.current
      const fade = Math.min(1, Math.max(0, (z - from) / (to - from)))
      const turnY = Math.atan2(x, Math.max(z, 0.05)) * TILT
      const turnX = Math.atan2(y, Math.max(z, 0.05)) * TILT
      card.style.transform = `translate(-50%, -50%) translate(${(x * RADIUS_CQ).toFixed(2)}cqmin, ${(-y * RADIUS_CQ).toFixed(2)}cqmin) perspective(900px) rotateY(${turnY.toFixed(3)}rad) rotateX(${turnX.toFixed(3)}rad) scale(${(0.8 + 0.2 * front).toFixed(3)})`
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
