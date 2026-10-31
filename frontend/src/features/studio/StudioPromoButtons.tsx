import { ArrowDown, ArrowUp, Plus, Trash2 } from 'lucide-react'
import type { PromoButton } from './model'

export function StudioPromoButtons({ buttons, onChange }: { buttons: PromoButton[]; onChange: (buttons: PromoButton[]) => void }) {
  function patch(index: number, value: Partial<PromoButton>) { onChange(buttons.map((button, i) => i === index ? { ...button, ...value } : button)) }
  function move(index: number, direction: number) {
    const next = [...buttons], target = index + direction
    if (target < 0 || target >= next.length) return
    ;[next[index], next[target]] = [next[target], next[index]]
    onChange(next)
  }
  return <section className="studio-native-buttons"><strong>Кнопки промо-экрана</strong>
    <p className="studio-help">Настоящие банковские кнопки идут под композицией. Их порядок и оформление можно менять; действия существующих кнопок сохраняются.</p>
    {buttons.map((button, index) => <div className="studio-native-button-editor" key={index}>
      <label className="studio-field">Текст кнопки {index + 1}<input value={button.text} onChange={e => patch(index, { text: e.target.value })} /></label>
      <div className="studio-property-grid">
        <label className="studio-field">Фон кнопки<input type="color" value={button.style?.backgroundColor?.slice(0, 7) ?? '#3155ff'} onChange={e => patch(index, { style: { ...button.style, backgroundColor: e.target.value } })} /></label>
        <label className="studio-field">Цвет текста<input type="color" value={button.textStyle?.textColor?.slice(0, 7) ?? '#ffffff'} onChange={e => patch(index, { textStyle: { ...button.textStyle, textColor: e.target.value } })} /></label>
      </div>
      <label className="studio-field">Размер текста<input type="number" min={10} max={40} value={button.textStyle?.fontSize ?? 16} onChange={e => { if (e.target.value) patch(index, { textStyle: { ...button.textStyle, fontSize: Math.max(10, Math.min(40, Number(e.target.value))) } }) }} /></label>
      <p className="studio-help">Действие: {button.actionType}</p>
      <div className="studio-object-actions"><button type="button" disabled={index === 0} aria-label={`Кнопку ${index + 1} выше`} onClick={() => move(index, -1)}><ArrowUp size={16} /></button><button type="button" disabled={index === buttons.length - 1} aria-label={`Кнопку ${index + 1} ниже`} onClick={() => move(index, 1)}><ArrowDown size={16} /></button><button type="button" aria-label={`Удалить кнопку ${index + 1}`} onClick={() => onChange(buttons.filter((_, i) => i !== index))}><Trash2 size={16} /></button></div>
    </div>)}
    <button type="button" className="studio-soft-button" disabled={buttons.length >= 5} onClick={() => onChange([...buttons, { role: 'button', text: 'Подробнее', actionType: 'default', style: { backgroundColor: '#3155ff' }, textStyle: { textColor: '#ffffff', fontSize: 16 } }])}><Plus size={15} />Добавить кнопку</button>
  </section>
}
