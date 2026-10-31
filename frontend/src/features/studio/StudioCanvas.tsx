import { useLayoutEffect, useRef, useState } from 'react'
import { Rnd } from 'react-rnd'
import type { StudioDocument, StudioLayer } from '@/api/studio'
import { LayerContent } from './Scene'
import { layerStyle } from './sceneStyle'

interface Props {
  document: StudioDocument
  selected: string | null
  onSelect: (id: string | null) => void
  onChange: (document: StudioDocument) => void
  editable: boolean
}

export function StudioCanvas({ document, selected, onSelect, onChange, editable }: Props) {
  const viewport = useRef<HTMLDivElement>(null)
  const [scale, setScale] = useState(1)
  useLayoutEffect(() => {
    const element = viewport.current
    if (!element) return
    const observer = new ResizeObserver(([entry]) => {
      const { width, height } = entry.contentRect
      if (width && height) setScale(Math.max(.15, Math.min(1.5, (width - 80) / document.width, (height - 64) / document.height)))
    })
    observer.observe(element)
    return () => observer.disconnect()
  }, [document.width, document.height])

  function patch(id: string, values: Partial<StudioLayer>) {
    onChange({ ...document, layers: document.layers.map(layer => layer.id === id ? { ...layer, ...values } : layer) })
  }

  return <div ref={viewport} className="studio-canvas-viewport" aria-label="Холст редактора">
    <span className="studio-canvas-caption">{document.format} <span>{document.width} × {document.height}</span></span>
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
    <span className="studio-canvas-scale">{Math.round(scale * 100)}% · По размеру окна</span>
  </div>
}
