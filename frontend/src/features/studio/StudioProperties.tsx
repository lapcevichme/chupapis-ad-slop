import { AlignCenter, AlignLeft, AlignRight, ArrowDown, ArrowUp, Copy, ImagePlus, Trash2 } from 'lucide-react'
import type { StudioDocument, StudioLayer } from '@/api/studio'
import type { PromoButton } from './model'
import { StudioPromoButtons } from './StudioPromoButtons'

interface Props {
  document: StudioDocument
  layer?: StudioLayer
  editable: boolean
  patch: (values: Partial<StudioLayer>) => void
  onDocument: (document: StudioDocument) => void
  onDuplicate: () => void
  onDelete: () => void
  onOrder: (direction: number) => void
  onReplace: () => void
  buttons: PromoButton[]
  isPromo: boolean
  onButtons: (buttons: PromoButton[]) => void
}

function Numeric({ label, value, onChange, min = -2400, max = 2400 }: { label: string; value: number; onChange: (value: number) => void; min?: number; max?: number }) {
  return <label className="studio-number"><span>{label}</span><input type="number" value={Math.round(value * 10) / 10} min={min} max={max} onChange={event => { if (event.target.value !== '') onChange(Math.max(min, Math.min(max, Number(event.target.value)))) }} /></label>
}

export function StudioProperties({ document, layer, editable, patch, onDocument, onDuplicate, onDelete, onOrder, onReplace, buttons, onButtons, isPromo }: Props) {
  return <aside className="studio-properties" aria-label="Свойства объекта">
    <div className="studio-panel-title"><strong>{layer ? 'Объект' : 'Макет'}</strong><span>{layer?.kind === 'text' ? 'Текст' : layer?.kind === 'image' ? 'Изображение' : layer ? 'Фигура' : document.format}</span></div>
    <fieldset disabled={!editable} className="studio-property-fields">
      {layer ? <>
        <label className="studio-field">Название<input value={layer.name} maxLength={100} onChange={e => patch({ name: e.target.value })} /></label>
        <div className="studio-property-grid">
          <Numeric label="X" value={layer.x} onChange={x => patch({ x })} /><Numeric label="Y" value={layer.y} onChange={y => patch({ y })} />
          <Numeric label="Ширина" min={8} value={layer.width} onChange={width => patch({ width })} /><Numeric label="Высота" min={8} value={layer.height} onChange={height => patch({ height })} />
        </div>
        <Numeric label="Поворот, °" min={-180} max={180} value={layer.rotation} onChange={rotation => patch({ rotation })} />
        {layer.kind === 'text' && <>
          <label className="studio-field">Текст<textarea data-studio-text rows={4} value={layer.text} onChange={e => patch({ text: e.target.value })} /></label>
          <div className="studio-property-grid"><Numeric label="Размер" min={8} max={120} value={layer.fontSize} onChange={fontSize => patch({ fontSize })} />
            <label className="studio-field">Начертание<select value={layer.fontWeight} onChange={e => patch({ fontWeight: Number(e.target.value) as StudioLayer['fontWeight'] })}><option value={400}>Обычный</option><option value={500}>Средний</option><option value={600}>Плотный</option><option value={700}>Жирный</option><option value={800}>Акцентный</option></select></label></div>
          <div className="studio-align" aria-label="Выравнивание текста">{([['left', AlignLeft, 'По левому краю'], ['center', AlignCenter, 'По центру'], ['right', AlignRight, 'По правому краю']] as const).map(([align, Icon, label]) => <button type="button" key={align} aria-label={label} aria-pressed={layer.textAlign === align} onClick={() => patch({ textAlign: align })}><Icon size={18} /></button>)}</div>
        </>}
        {layer.kind !== 'image' && <label className="studio-color">Цвет<input type="color" value={layer.fill.slice(0, 7)} onChange={e => patch({ fill: e.target.value })} /><input className="studio-color-code" aria-label="Цвет HEX" maxLength={9} value={layer.fill} onChange={e => patch({ fill: e.target.value })} /></label>}
        {layer.kind === 'shape' && <>
          <label className="studio-field">Форма<select value={layer.shape} onChange={e => patch({ shape: e.target.value as StudioLayer['shape'] })}><option value="rect">Прямоугольник</option><option value="ellipse">Эллипс</option></select></label>
          {layer.shape === 'rect' && <Numeric label="Скругление" min={0} max={600} value={layer.radius} onChange={radius => patch({ radius })} />}
        </>}
        {layer.kind === 'image' && <><button type="button" className="studio-soft-button" onClick={onReplace}><ImagePlus size={16} />Заменить изображение</button><label className="studio-field">В кадре<select value={layer.fit} onChange={e => patch({ fit: e.target.value as StudioLayer['fit'] })}><option value="cover">Заполнить</option><option value="contain">Вписать целиком</option></select></label></>}
        <label className="studio-field">Прозрачность · {Math.round(layer.opacity * 100)}%<input type="range" min={0} max={100} value={layer.opacity * 100} onChange={e => patch({ opacity: Number(e.target.value) / 100 })} /></label>
        <div className="studio-object-actions"><button type="button" onClick={() => onOrder(1)} title="На слой выше" aria-label="На слой выше"><ArrowUp size={17} /></button><button type="button" onClick={() => onOrder(-1)} title="На слой ниже" aria-label="На слой ниже"><ArrowDown size={17} /></button><button type="button" onClick={onDuplicate} title="Дублировать слой" aria-label="Дублировать слой"><Copy size={17} /></button><button type="button" onClick={onDelete} title="Удалить слой" aria-label="Удалить слой"><Trash2 size={17} /></button></div>
      </> : <>
        <label className="studio-field">Название макета<input value={document.name} maxLength={100} onChange={e => onDocument({ ...document, name: e.target.value || 'Без названия' })} /></label>
        <label className="studio-color">Фон<input type="color" value={document.background.slice(0, 7)} onChange={e => onDocument({ ...document, background: e.target.value })} /><input className="studio-color-code" aria-label="Фон HEX" maxLength={9} value={document.background} onChange={e => onDocument({ ...document, background: e.target.value })} /></label>
        <p className="studio-help">Выберите текст, фигуру или изображение на холсте — здесь появятся его свойства.</p>
        {isPromo && <StudioPromoButtons buttons={buttons} onChange={onButtons} />}
      </>}
    </fieldset>
  </aside>
}
