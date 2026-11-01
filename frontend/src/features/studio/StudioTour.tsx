import { ArrowRight, Check, HelpCircle, MousePointer2, Shapes, Sparkles, Columns2, X } from 'lucide-react'
import { useState } from 'react'

const KEY = 'adpilot.studio.tour.v1'
const STEPS = [
  { icon: MousePointer2, title: 'Возьмите любой объект', text: 'Нажмите на текст или предмет на холсте. Перетаскивайте его, тяните за уголки, меняйте текст и цвет справа.', target: 'Холст и свойства' },
  { icon: Shapes, title: 'Добавьте характер', text: 'В «Элементах» — объёмные предметы. Рядом можно добавить текст, фигуру или своё фото и SVG.', target: 'Панель инструментов' },
  { icon: Sparkles, title: 'Правьте вместе с AI', text: 'Выделите объект, опишите правку внизу и нажмите «Изменить». Или получите три композиции. Каждый ответ — отдельный вариант.', target: 'AI-дизайнер' },
  { icon: Columns2, title: 'Выберите и примените', text: 'Сравните варианты рядом. «Применить» покажет точное изображение: только после вашего подтверждения оно попадёт в кампанию.', target: 'Сравнение и применение' },
]

export function StudioTour({ step, onStep }: { step: number | null; onStep: (value: number | null) => void }) {
  const [offer, setOffer] = useState(() => !localStorage.getItem(KEY))
  function close() { localStorage.setItem(KEY, 'seen'); setOffer(false); onStep(null) }
  const current = step === null ? null : STEPS[step]
  const Icon = current?.icon ?? Sparkles
  return <>
    <button type="button" className="studio-tour-trigger" aria-label="Знакомство со студией" title="Знакомство со студией" onClick={() => { setOffer(false); onStep(0) }}><HelpCircle size={18} /></button>
    {(current || offer) && <aside className={`studio-tour ${current ? 'is-active' : ''}`} aria-label="Знакомство со студией" aria-live="polite"><button className="studio-tour-close" type="button" aria-label="Закрыть знакомство" onClick={close}><X size={16} /></button><span className="studio-tour-kicker"><Icon size={17} />{current ? `${(step ?? 0) + 1} / ${STEPS.length} · ${current.target}` : 'Ваша творческая студия'}</span><h3>{current?.title ?? 'От идеи — к своему макету.'}</h3><p>{current?.text ?? 'Четыре короткие подсказки: объекты, свои материалы, AI-правки и выбор вариантов.'}</p><div className="studio-tour-bottom">{current ? <><div className="studio-tour-dots">{STEPS.map((item, index) => <button key={item.title} aria-label={`Шаг ${index + 1}: ${item.title}`} aria-current={step === index ? 'step' : undefined} onClick={() => onStep(index)} />)}</div><button className="studio-tour-next" onClick={() => { if (step === STEPS.length - 1) close(); else onStep((step ?? 0) + 1) }}>{step === STEPS.length - 1 ? <>Готово<Check size={15} /></> : <>Дальше<ArrowRight size={15} /></>}</button></> : <><button onClick={close}>Позже</button><button className="studio-tour-next" onClick={() => { setOffer(false); onStep(0) }}>Показать<ArrowRight size={15} /></button></>}</div></aside>}
  </>
}
