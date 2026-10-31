import { useEffect, useRef } from 'react'

// Первая реплика раньше остальных: после кнопки на карточке или в анкете модель сама ещё ничего не сказала.
const FIRST_AFTER_MS = 5000
const QUIET_LIMIT_MS = 10_000
const STEP_GAP_MS = 6000
const TICK_MS = 1000
const REQUEST_CHARS = 140

const STYLE = 'Одной короткой живой фразой, своими словами и не так, как раньше. Без «работа ещё идёт», без результата, без вопросов, без упоминания агентов и номеров попыток.'

// Голосу незачем знать про внутреннего дизайнера и повторы: модель читала это вслух, несмотря на просьбу не делать так.
function spokenStep(label: string) {
  return label
    .replace(/,?\s*попытка\s*\d+/i, '')
    .replace('Дизайнер собирает', 'Собираю')
    .replace('Дизайнер правит', 'Правлю')
}

interface LiveNarrationOptions {
  active: boolean
  busy: boolean
  step?: string
  warnings: { message: string }[]
  request: string
  report: (content: string, final?: boolean) => void
}

// Пока агент работает, модель рассказывает о настоящем этапе: приходят только факты из потока агента, иначе она бы гадала.
export function useLiveNarration({ active, busy, step, warnings, request, report }: LiveNarrationOptions) {
  const spokenWarnings = useRef(warnings.length)
  const lastSpoke = useRef(0)
  const lastStep = useRef<string | undefined>(undefined)
  const latest = useRef({ step, request })
  useEffect(() => {
    latest.current = { step, request }
  })

  useEffect(() => {
    if (!busy) return
    spokenWarnings.current = 0
    lastStep.current = undefined
    lastSpoke.current = Date.now() - (QUIET_LIMIT_MS - FIRST_AFTER_MS)
  }, [busy])

  // Предупреждение важнее пауз: его говорим сразу, как только агент его выдал.
  useEffect(() => {
    if (!active) return
    for (const warning of warnings.slice(spokenWarnings.current)) {
      report(`Обязательно скажи человеку сейчас, своими словами, но без потери смысла: ${warning.message}`, false)
      lastSpoke.current = Date.now()
    }
    spokenWarnings.current = warnings.length
  }, [active, warnings, report])

  useEffect(() => {
    if (!active || !busy) return
    function narrate(content: string) {
      report(`${content} ${STYLE}`, false)
      lastSpoke.current = Date.now()
    }
    const timer = setInterval(() => {
      const quiet = Date.now() - lastSpoke.current
      const { step, request } = latest.current
      if (step && spokenStep(step) !== lastStep.current && quiet >= STEP_GAP_MS) {
        lastStep.current = spokenStep(step)
        narrate(`Сейчас идёт этап «${spokenStep(step)}». Скажи об этом.`)
      } else if (quiet >= QUIET_LIMIT_MS) {
        narrate(`Ответа ещё нет, идёт работа над запросом «${request.slice(0, REQUEST_CHARS)}». Скажи, чем сейчас занимаешься именно по этому запросу.`)
      }
    }, TICK_MS)
    return () => clearInterval(timer)
  }, [active, busy, report])
}
