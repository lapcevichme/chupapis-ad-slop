import type { StudioDocument, StudioLayer } from '@/api/studio'
import { ImageOff } from 'lucide-react'
import { useState } from 'react'
import { layerStyle } from './sceneStyle'

function StudioImage({ layer }: { layer: StudioLayer }) {
  const [failed, setFailed] = useState(false)
  return failed ? <div role="img" aria-label={`Изображение недоступно: ${layer.name}`} className="studio-image-unavailable" title="Изображение недоступно. Замените файл в свойствах."><ImageOff size={16} /><span className="sr-only">Замените файл в свойствах</span></div> : <img src={layer.src} alt={layer.name} draggable={false} onError={() => setFailed(true)} style={{ width: '100%', height: '100%', objectFit: layer.fit, fontSize: 12 }} />
}

export function LayerContent({ layer }: { layer: StudioLayer }) {
  if (layer.kind === 'image') return <StudioImage key={layer.src} layer={layer} />
  return layer.kind === 'text' ? layer.text : null
}

export function Scene({ document, scale = 1 }: { document: StudioDocument; scale?: number }) {
  return <div className="studio-scene-frame" style={{ width: document.width * scale, height: document.height * scale }}>
    <div className="studio-scene" style={{ width: document.width, height: document.height, background: document.background, transform: `scale(${scale})` }}>
      {document.layers.filter(x => !x.hidden).map(layer => <div key={layer.id} style={{ position: 'absolute', left: layer.x, top: layer.y, width: layer.width, height: layer.height }}><div style={layerStyle(layer)}><LayerContent layer={layer} /></div></div>)}
    </div>
  </div>
}
