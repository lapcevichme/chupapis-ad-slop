import { Eye, EyeOff, Image, Layers2, LockKeyhole, Square, Type, UnlockKeyhole } from 'lucide-react'
import type { StudioDocument, StudioLayer } from '@/api/studio'

export function StudioLayers({ document, selected, onSelect, onPatch, editable }: { document: StudioDocument; selected: string | null; onSelect: (id: string | null) => void; onPatch: (id: string, values: Partial<StudioLayer>) => void; editable: boolean }) {
  return <aside className="studio-layers" aria-label="Слои макета">
    <div className="studio-panel-title"><strong><Layers2 size={16} />Слои</strong><span>{document.layers.length}</span></div>
    <div className="studio-layer-list">{[...document.layers].reverse().map(layer => {
      const Icon = layer.kind === 'text' ? Type : layer.kind === 'image' ? Image : Square
      return <div className={`studio-layer-row ${selected === layer.id ? 'selected' : ''}`} key={layer.id}>
        <button type="button" className="studio-layer-select" aria-label={`Выбрать слой: ${layer.name}`} aria-pressed={selected === layer.id} onClick={() => onSelect(layer.id)}><Icon size={16} /><span>{layer.name}</span></button>
        <button type="button" className="studio-layer-toggle" disabled={!editable} aria-label={`${layer.hidden ? 'Показать' : 'Скрыть'} слой: ${layer.name}`} title={layer.hidden ? 'Показать' : 'Скрыть'} onClick={() => onPatch(layer.id, { hidden: !layer.hidden })}>{layer.hidden ? <EyeOff size={14} /> : <Eye size={14} />}</button>
        <button type="button" className="studio-layer-toggle" disabled={!editable} aria-label={`${layer.locked ? 'Разблокировать' : 'Заблокировать'} слой: ${layer.name}`} title={layer.locked ? 'Разблокировать' : 'Заблокировать'} onClick={() => onPatch(layer.id, { locked: !layer.locked })}>{layer.locked ? <LockKeyhole size={14} /> : <UnlockKeyhole size={14} />}</button>
      </div>
    })}</div>
    <button type="button" className={`studio-background-row ${selected === null ? 'selected' : ''}`} onClick={() => onSelect(null)}><i style={{ background: document.background }} />Фон макета</button>
    <p className="studio-help">Выберите объект здесь или прямо на холсте. Порядок слоёв меняется в свойствах.</p>
  </aside>
}
