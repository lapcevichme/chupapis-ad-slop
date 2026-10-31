import type { CSSProperties } from 'react'
import type { StudioLayer } from '@/api/studio'

export function layerStyle(layer: StudioLayer): CSSProperties {
  return { width: '100%', height: '100%', opacity: layer.opacity, transform: `rotate(${layer.rotation}deg)`, transformOrigin: 'center', overflow: 'hidden', color: layer.fill, fontSize: layer.fontSize, fontWeight: layer.fontWeight, textAlign: layer.textAlign, lineHeight: 1.15, whiteSpace: 'pre-wrap', overflowWrap: 'anywhere', background: layer.kind === 'shape' ? layer.fill : undefined, borderRadius: layer.kind === 'shape' && layer.shape === 'ellipse' ? '50%' : layer.radius, fontFamily: '"Onest Variable", sans-serif' }
}

