import type { StudioDocument, StudioLayer } from '@/api/studio'
import { newLayer } from './model.ts'

function lines(text: string, width: number, size: number) {
  const capacity = Math.max(1, Math.floor(width / (size * .58)))
  return text.split('\n').reduce((total, line) => total + Math.max(1, Math.ceil(line.length / capacity)), 0)
}

function stack(layers: StudioLayer[], x: number, y: number, width: number, available: number, ink: string, tall: boolean, editorial: boolean) {
  const gap = tall ? 14 : 6
  let shrink = 1
  const size = (layer: StudioLayer) => Math.max(8, (layer.role === 'title' ? (tall ? 36 : 21) : (tall ? 18 : 12)) * shrink)
  const height = (layer: StudioLayer) => Math.ceil(lines(layer.text, width, size(layer)) * size(layer) * 1.15) + 3
  while (shrink > .3 && layers.reduce((h, layer) => h + height(layer) + gap, -gap) > available) shrink -= .025
  return layers.map(layer => {
    const next = { ...layer, x, y, width, height: height(layer), fontSize: size(layer), fill: ink, rotation: 0, opacity: 1, fontWeight: (layer.role === 'title' ? 800 : 500) as 800 | 500, textAlign: (editorial ? 'right' : 'left') as 'left' | 'right' }
    y += next.height + gap
    return next
  })
}

export function makeLayoutVariants(base: StudioDocument): StudioDocument[] {
  const { width: w, height: h } = base
  const tall = h > 300, pad = tall ? 24 : 16
  const images = base.layers.filter(x => x.kind === 'image' || x.kind === 'illustration')
  const text = base.layers.filter(x => x.kind === 'text' && x.role !== 'button')
  const buttons = base.layers.filter(x => x.kind === 'text' && x.role === 'button')
  return ['Плакат', 'Редакционный', 'Контраст'].map((name, index) => {
    const [background, ink, accent] = [['#3155ff', '#ffffff', '#d6f45b'], ['#f4eadb', '#23283c', '#ff714e'], ['#d6f45b', '#222b59', '#3155ff']][index]
    const graphics: StudioLayer[] = []
    const shape = (values: Partial<StudioLayer>) => graphics.push(newLayer('shape', values))
    if (index === 0) {
      shape({ name: 'Диагональная плоскость', x: w * .55, y: tall ? h * .58 : 12, width: w * .7, height: tall ? h * .27 : h * .8, rotation: -18, fill: accent, radius: 10 })
      shape({ name: 'Типографическая линия', x: pad, y: tall ? h * .5 : h - 45, width: w * .35, height: tall ? 7 : 3, fill: accent })
    } else if (index === 1) {
      shape({ name: 'Редакционная обложка', x: 0, y: 0, width: w, height: tall ? h * .39 : 12, fill: accent })
      shape({ name: 'Вертикальный акцент', x: w - pad - 4, y: tall ? h * .43 : 22, width: 4, height: tall ? h * .36 : h - 66, fill: accent })
    } else {
      shape({ name: 'Контрастный блок', x: tall ? 0 : w * .65, y: tall ? h * .55 : 0, width: tall ? w : w * .35, height: tall ? h * .45 : h, fill: accent })
      shape({ name: 'Графический знак', shape: 'ellipse', x: tall ? w * .64 : w * .77, y: tall ? h * .44 : 18, width: w * .3, height: w * .3, fill: ink })
    }
    const pictureLayers = images.map((image, i) => ({ ...image, x: tall ? pad + i * 8 : w * .69, y: tall ? (index === 1 ? 20 : index === 2 ? h * .27 : h * .56) + i * 8 : 24 + i * 5, width: tall ? w - pad * 2 : w * .26, height: tall ? h * .27 : h - 76, rotation: index === 1 ? -4 : 0, opacity: 1, radius: index === 1 ? 0 : 16 }))
    const textWidth = (tall ? w - pad * 2 : (images.length || index === 2 ? w * .59 : w - pad * 2)) - (index === 1 ? 12 : 0)
    const textY = tall && index === 1 ? h * .44 : (tall ? 30 : 18)
    const available = tall ? (index === 1 ? h * .42 : h * .46) : h - 70
    const copy = tall && index === 2 ? [...stack(text.filter(x => x.role === 'title'), pad, 30, textWidth, h * .23, ink, true, false), ...stack(text.filter(x => x.role !== 'title'), pad, h * .6, textWidth, h * .23, '#ffffff', true, false)] : stack(text, pad, textY, textWidth, available, ink, tall, index === 1)
    const buttonHeight = tall ? 42 : 26
    const buttonY = h - pad - buttonHeight
    if (buttons.length) shape({ name: 'Кнопка — фон', x: pad, y: buttonY, width: w - pad * 2, height: buttonHeight, fill: index === 2 ? '#ffffff' : ink, radius: 12 })
    const cta = buttons.map((button, i) => ({ ...button, x: pad + 10, y: buttonY + (tall ? 12 : 6) + i * buttonHeight, width: w - pad * 2 - 20, height: tall ? 24 : 16, fontSize: tall ? 15 : 11, fill: index === 2 ? '#222b59' : background, rotation: 0, opacity: 1, textAlign: 'center' as const }))
    // Preserve text order/IDs so each alternative remains an exact, editable copy of the offer.
    const byId = new Map([...copy, ...cta].map(layer => [layer.id, layer]))
    const copyInOrder = base.layers.filter(x => x.kind === 'text').map(layer => byId.get(layer.id)!)
    return { ...structuredClone(base), name, background, layers: [...graphics.slice(0, Math.max(0, 40 - pictureLayers.length - copyInOrder.length)), ...pictureLayers, ...copyInOrder] }
  })
}
