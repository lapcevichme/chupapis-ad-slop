import type { StudioDocument, StudioLayer } from '@/api/studio'
import { ImageOff } from 'lucide-react'
import { useState } from 'react'
import { layerStyle } from './sceneStyle'
import './scene.css'
import { illustrationSource } from './illustrations'

function StudioImage({ layer }: { layer: StudioLayer }) {
  const [failed, setFailed] = useState(false)
  return failed ? <div role="img" aria-label={`Изображение недоступно: ${layer.name}`} className="studio-image-unavailable" title="Изображение недоступно. Замените файл в свойствах."><ImageOff size={16} /><span className="sr-only">Замените файл в свойствах</span></div> : <img src={layer.src} alt={layer.name} draggable={false} onError={() => setFailed(true)} style={{ width: '100%', height: '100%', objectFit: layer.fit, fontSize: 12 }} />
}

export function LayerContent({ layer }: { layer: StudioLayer }) {
  if (layer.kind === 'illustration') return <StudioImage key={layer.symbol} layer={{ ...layer, src: illustrationSource(layer.symbol), fit: 'contain' }} />
  if (layer.kind === 'image') return <StudioImage key={layer.src} layer={layer} />
  return layer.kind === 'text' ? layer.text : null
}

export function Scene({ document, scale = 1, onSelect }: { document: StudioDocument; scale?: number; onSelect?: (id: string) => void }) {
  return <div className="studio-scene-frame" style={{ width: document.width * scale, height: document.height * scale }}>
    <div className="studio-scene" style={{ width: document.width, height: document.height, background: document.background, transform: `scale(${scale})` }}>
      {document.layers.filter(x => !x.hidden).map(layer => { const style = { position: 'absolute' as const, left: layer.x, top: layer.y, width: layer.width, height: layer.height }; const body = <div style={layerStyle(layer)}><LayerContent layer={layer} /></div>; return onSelect ? <button type="button" className="preview-layer-target" key={layer.id} aria-label={`Редактировать слой: ${layer.name}`} style={style} onClick={() => onSelect(layer.id)}>{body}</button> : <div key={layer.id} style={style}>{body}</div> })}
    </div>
  </div>
}
