import { Check, ChevronDown, Copy, Plus, Trash2 } from 'lucide-react'
import { useLayoutEffect, useRef, useState } from 'react'
import type { StudioDocument } from '@/api/studio'
import type { StudioVariant } from './model'
import { Scene } from './Scene'

interface Props { variants: StudioVariant[]; activeId: string; compared: string[]; onSelect: (id: string) => void; onCompare: (id: string) => void; onAdd: () => void; onRemove: (id: string) => void; collapsed: boolean; onToggle: () => void }

export function StudioVariants({ variants, activeId, compared, onSelect, onCompare, onAdd, onRemove, collapsed, onToggle }: Props) {
  return <section className={`studio-variants ${collapsed ? 'collapsed' : ''}`} aria-label="Варианты креатива"><div className="studio-variants-heading"><button type="button" aria-label="Развернуть или свернуть варианты" aria-expanded={!collapsed} onClick={onToggle}>Варианты <span>{variants.length}</span><ChevronDown size={13} /></button><button type="button" onClick={onAdd}><Plus size={15} />Копия</button></div><div className="studio-variant-rail">
    {variants.map(variant => <div key={variant.id} className={`studio-variant-tile ${variant.id === activeId ? 'active' : ''}`}>
      <button type="button" className="studio-variant-pick" aria-label={`Открыть вариант: ${variant.label}`} aria-pressed={variant.id === activeId} onClick={() => onSelect(variant.id)}><Scene document={variant.document} scale={Math.min(64 / variant.document.height, 64 / variant.document.width)} /><span>{variant.label}</span></button>
      <label className="studio-compare-check"><input type="checkbox" checked={compared.includes(variant.id)} onChange={() => onCompare(variant.id)} aria-label={`Сравнивать: ${variant.label}`} /><Copy size={12} />Сравнить</label>
      {variants.length > 1 && <button type="button" className="studio-variant-delete" aria-label={`Удалить вариант: ${variant.label}`} onClick={() => onRemove(variant.id)}><Trash2 size={13} /></button>}
    </div>)}
  </div></section>
}

function ComparisonArt({ document }: { document: StudioDocument }) {
  const viewport = useRef<HTMLDivElement>(null)
  const [scale, setScale] = useState(.4)
  useLayoutEffect(() => {
    const element = viewport.current
    if (!element) return
    const observer = new ResizeObserver(([entry]) => setScale(Math.max(.1, Math.min((entry.contentRect.width - 24) / document.width, (entry.contentRect.height - 24) / document.height, 1.5))))
    observer.observe(element)
    return () => observer.disconnect()
  }, [document.width, document.height])
  return <div className="studio-compare-art" ref={viewport}><Scene document={document} scale={scale} /></div>
}

export function StudioComparison({ variants, activeId, onSelect }: { variants: StudioVariant[]; activeId: string; onSelect: (id: string) => void }) {
  return <section className="studio-comparison" aria-label="Сравнение креативов"><div className="studio-comparison-title"><p>Посмотрите рядом. Выберите своё.</p><span>До трёх вариантов рядом. Выбор откроет редактор; кампания пока не меняется.</span></div><div className="studio-comparison-grid">
    {variants.map((variant, index) => <article key={variant.id} className={`studio-compare-card ${activeId === variant.id ? 'active' : ''}`}><header><span>{String.fromCharCode(65 + index)}</span><h3>{variant.label}</h3></header><ComparisonArt document={variant.document} /><button type="button" onClick={() => onSelect(variant.id)}>{activeId === variant.id && <Check size={17} />}{activeId === variant.id ? 'Продолжить с этим' : 'Выбрать вариант'}</button></article>)}
  </div></section>
}
