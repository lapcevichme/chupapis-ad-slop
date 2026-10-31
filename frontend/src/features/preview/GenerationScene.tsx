import { Layers3, Sparkles } from 'lucide-react'

export function GenerationScene({ label, idle = false }: { label: string; idle?: boolean }) {
  return <div className={`generation-stage ${idle ? 'is-idle' : ''}`} role={idle ? undefined : 'status'}>
    <div className="generation-art" aria-hidden="true"><div className="generation-sheet sheet-back" /><div className="generation-sheet sheet-middle" /><div className="generation-sheet sheet-front"><div className="generation-type"><i /><i /></div><div className="generation-object"><span /><span /></div><div className="generation-copy"><i /><i /><i /></div><div className="generation-cta" /><div className="generation-scan" /></div><span className="generation-corner"><Layers3 size={19} /></span></div>
    <div className="generation-caption"><Sparkles size={19} /><strong>{label}</strong><p>{idle ? 'Опишите продукт и предложение — здесь появится ваш макет.' : 'Собираем композицию, типографику и детали в один макет.'}</p></div>
  </div>
}
