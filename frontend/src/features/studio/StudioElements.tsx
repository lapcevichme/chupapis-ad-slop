import { Shapes } from 'lucide-react'
import { useEffect, useRef } from 'react'
import type { StudioLayer } from '@/api/studio'
import { ILLUSTRATIONS } from './illustrations'

export function StudioElements({ disabled, onAdd }: { disabled: boolean; onAdd: (symbol: StudioLayer['symbol']) => void }) {
  const root = useRef<HTMLDetailsElement>(null)
  useEffect(() => {
    const close = (event: PointerEvent) => { if (root.current && !root.current.contains(event.target as Node)) root.current.open = false }
    document.addEventListener('pointerdown', close)
    return () => document.removeEventListener('pointerdown', close)
  }, [])
  return <details className="studio-elements" ref={root} onKeyDown={event => { if (event.key === 'Escape' && root.current) root.current.open = false }}>
    <summary aria-disabled={disabled} onClick={event => { if (disabled) event.preventDefault() }}><Shapes size={17} />Элементы</summary>
    <div className="studio-elements-grid" aria-label="Предметные иллюстрации">{ILLUSTRATIONS.map(item => <button type="button" key={item.symbol} aria-label={`Добавить: ${item.label}`} disabled={disabled} onClick={() => { onAdd(item.symbol); if (root.current) root.current.open = false }}><img src={item.src} alt="" /><span>{item.label}</span></button>)}</div>
  </details>
}
