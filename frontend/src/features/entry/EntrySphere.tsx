import { useRef, useState } from 'react'
import { Orb } from '@/features/voice/Orb'
import { SPHERE_RADIUS, spherePosition } from '@/features/voice/orbStars'
import { SPHERE_EXAMPLES } from './sphereExamples'

// Сфера вращается медленнее, чем в голосовом режиме, чтобы карточки можно было прочитать на ходу.
const SPEED = 0.5
const RADIUS_CQ = SPHERE_RADIUS * 100
const DEGREES = Math.PI / 180
// Карточка гаснет, уходя за край сферы: сзади её не видно.
const FADE_FROM_Z = -0.02
const FADE_TO_Z = 0.28
// Лёгкий наклон по кривизне сферы; сильнее текст начинает выглядеть курсивом.
const TILT = 0.2

const ANCHORS = SPHERE_EXAMPLES.map(({ longitude, latitude }) => {
  const ring = Math.cos(latitude * DEGREES)
  return [ring * Math.cos(longitude * DEGREES), Math.sin(latitude * DEGREES), ring * Math.sin(longitude * DEGREES)] as const
})

interface EntrySphereProps {
  dark: boolean
  size: number
  getLevel: () => number
}

export function EntrySphere({ dark, size, getLevel }: EntrySphereProps) {
  const cards = useRef<(HTMLLIElement | null)[]>([])
  // Без движения полупрозрачная карточка так и осталась бы нечитаемой, поэтому показываем только целые.
  const [still] = useState(() => matchMedia('(prefers-reduced-motion: reduce)').matches)

  // Положение меняем прямо в DOM: перерисовывать React на каждом кадре незачем.
  function place(time: number) {
    ANCHORS.forEach(([anchorX, anchorY, anchorZ], index) => {
      const card = cards.current[index]
      if (!card) return
      const { x, y, z } = spherePosition(anchorX, anchorY, anchorZ, time)
      const front = Math.max(z, 0)
      const fade = Math.min(1, Math.max(0, (z - FADE_FROM_Z) / (FADE_TO_Z - FADE_FROM_Z)))
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
      <ul className="entry-examples" aria-label="Примеры акций">
        {SPHERE_EXAMPLES.map((example, index) => (
          <li
            key={example.source}
            ref={(node) => {
              cards.current[index] = node
            }}
            className="entry-example"
            style={{ background: example.background }}
          >
            <strong style={{ color: example.titleColor }}>{example.title}</strong>
            <span className="entry-example-text" style={{ color: example.textColor }}>{example.text}</span>
            {example.buttonName && <span className="entry-example-button" style={{ background: example.titleColor, color: example.background }}>{example.buttonName}</span>}
          </li>
        ))}
      </ul>
    </div>
  )
}
