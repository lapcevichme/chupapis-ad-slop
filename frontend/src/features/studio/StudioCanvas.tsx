import { useLayoutEffect, useRef, useState } from 'react'
import { Rnd } from 'react-rnd'
import { Maximize2, Minus, Plus } from 'lucide-react'
import type { StudioDocument, StudioLayer } from '@/api/studio'
import { LayerContent } from './Scene'
import { layerStyle } from './sceneStyle'

interface Props {
  document: StudioDocument
  selected: string | null
  onSelect: (id: string | null) => void
  onChange: (document: StudioDocument) => void
  editable: boolean
  onFile: (file: File) => void
}

export function StudioCanvas({ document, selected, onSelect, onChange, editable, onFile }: Props) {
  const viewport = useRef<HTMLDivElement>(null)
  const [fitScale, setFitScale] = useState(1)
  const [zoom, setZoom] = useState<number | null>(null)
  const scale = zoom ?? fitScale
  useLayoutEffect(() => {
    const element = viewport.current
    if (!element) return
    const observer = new ResizeObserver(([entry]) => {
      const { width, height } = entry.contentRect
      if (width && height) setFitScale(Math.max(.15, Math.min(1.5, (width - 80) / document.width, (height - 64) / document.height)))
    })
    observer.observe(element)
    return () => observer.disconnect()
  }, [document.width, document.height])

  function patch(id: string, values: Partial<StudioLayer>) {
    onChange({ ...document, layers: document.layers.map(layer => layer.id === id ? { ...layer, ...values } : layer) })
  }

  return <div ref={viewport} className="studio-canvas-container" aria-label="Холст редактора" onDragOver={event => { if (editable && event.dataTransfer.types.includes('Files')) event.preventDefault() }} onDrop={event => { if (editable && event.dataTransfer.files[0]) { event.preventDefault(); onFile(event.dataTransfer.files[0]) } }}>
    <span className="studio-canvas-caption">{document.format} <span>{document.width} × {document.height}</span></span>
    <div className="studio-canvas-viewport">
    <div className="studio-board-frame" style={{ width: document.width * scale, height: document.height * scale }}>
      <div className="studio-board" style={{ width: document.width, height: document.height, background: document.background, transform: `scale(${scale})` }} onPointerDown={event => { if (event.target === event.currentTarget) onSelect(null) }}>
        {document.layers.filter(layer => !layer.hidden).map(layer => <Rnd
          key={layer.id}
          scale={scale}
          position={{ x: layer.x, y: layer.y }}
          size={{ width: layer.width, height: layer.height }}
          minWidth={8} minHeight={8} maxWidth={2400} maxHeight={2400}
          disableDragging={!editable || layer.locked}
          enableResizing={editable && !layer.locked && selected === layer.id}
          onMouseDown={event => { event.stopPropagation(); onSelect(layer.id) }}
          onTouchStart={() => onSelect(layer.id)}
          onDoubleClick={() => { if (editable && layer.kind === 'text') { onSelect(layer.id); requestAnimationFrame(() => window.document.querySelector<HTMLTextAreaElement>('[data-studio-text]')?.focus()) } }}
          onDragStart={() => { onSelect(layer.id) }}
          onDragStop={(_event, position) => patch(layer.id, { x: Math.max(-2400, Math.min(2400, position.x)), y: Math.max(-2400, Math.min(2400, position.y)) })}
          onResizeStop={(_event, _direction, ref, _delta, position) => patch(layer.id, { width: parseFloat(ref.style.width), height: parseFloat(ref.style.height), x: position.x, y: position.y })}
          className={`studio-object ${selected === layer.id ? 'is-selected' : ''} ${layer.locked ? 'is-locked' : ''}`}
          aria-label={`Объект: ${layer.name}`}
          resizeHandleComponent={{ bottomRight: <span className="studio-resize-dot" /> }}
        >
          <div style={layerStyle(layer)}><LayerContent layer={layer} /></div>
        </Rnd>)}
      </div>
    </div>
    </div><div className="studio-zoom-controls"><button type="button" aria-label="Уменьшить холст" onClick={() => setZoom(Math.max(.2, scale - .2))}><Minus size={15} /></button><button type="button" aria-label="Масштаб 100 процентов" onClick={() => setZoom(1)}>{Math.round(scale * 100)}%</button><button type="button" aria-label="Увеличить холст" onClick={() => setZoom(Math.min(2, scale + .2))}><Plus size={15} /></button><button type="button" title="Вписать в окно" aria-label="Вписать холст в окно" onClick={() => setZoom(null)}><Maximize2 size={14} /></button></div></div>
}
