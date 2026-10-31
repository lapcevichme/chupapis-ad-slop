import type { StudioDocument, StudioLayer } from '@/api/studio'
import { layerStyle } from './sceneStyle'

export function LayerContent({ layer }: { layer: StudioLayer }) {
  if (layer.kind === 'image') return <img src={layer.src} alt={layer.name} draggable={false} style={{ width: '100%', height: '100%', objectFit: layer.fit }} />
  return layer.kind === 'text' ? layer.text : null
}

export function Scene({ document, scale = 1 }: { document: StudioDocument; scale?: number }) {
  return <div className="studio-scene-frame" style={{ width: document.width * scale, height: document.height * scale }}>
    <div className="studio-scene" style={{ width: document.width, height: document.height, background: document.background, transform: `scale(${scale})` }}>
      {document.layers.filter(x => !x.hidden).map(layer => <div key={layer.id} style={{ position: 'absolute', left: layer.x, top: layer.y, width: layer.width, height: layer.height }}><div style={layerStyle(layer)}><LayerContent layer={layer} /></div></div>)}
    </div>
  </div>
}
