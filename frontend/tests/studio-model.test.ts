import assert from 'node:assert/strict'
import test from 'node:test'
import { contrastingText, importSource, makeLayoutVariants, newLayer, validateDocument } from '../src/features/studio/model.ts'

test('layout alternatives preserve every offer string and do not mutate the source', () => {
  const document = { version: 1 as const, name: 'Вклад', format: 'STORY' as const, width: 300, height: 600, background: '#3155ff', layers: [newLayer('text', { role: 'title', text: 'Вклад 16%' }), newLayer('text', { text: 'С 5 ноября до конца года' })] }
  const before = JSON.stringify(document)
  const variants = makeLayoutVariants(document)
  assert.equal(variants.length, 3)
  for (const variant of variants) {
    assert.deepEqual(variant.layers.filter(x => x.kind === 'text').map(x => [x.id, x.text]), document.layers.map(x => [x.id, x.text]))
    assert.equal(new Set(variant.layers.map(x => x.id)).size, variant.layers.length)
  }
  assert.equal(JSON.stringify(document), before)
  assert.equal(new Set(variants.map(v => v.background)).size, 3)
  assert.equal(new Set(variants.map(v => JSON.stringify(v.layers.filter(x => x.kind === 'text').map(x => [x.x, x.y, x.textAlign])))).size, 3)
  assert.ok(variants.every(v => validateDocument(v).length === 0))
})

test('compact alternatives keep CTA inside the artwork with a contrasting surface', () => {
  const document = { version: 1 as const, name: 'Карта', format: 'SMART_BANNER' as const, width: 300, height: 160, background: '#ffffff', layers: [newLayer('text', { role: 'title', text: 'Карта с кэшбэком' }), newLayer('text', { text: 'До конца ноября' }), newLayer('text', { role: 'button', text: 'Подробнее' })] }
  for (const variant of makeLayoutVariants(document)) {
    const button = variant.layers.find(x => x.role === 'button')!
    const background = variant.layers.find(x => x.name === 'Кнопка — фон')!
    assert.ok(button.y + button.height <= 160)
    assert.notEqual(button.fill, background.fill)
    assert.ok(variant.layers.filter(x => x.kind === 'text' && x.role !== 'button').every(x => x.y + x.height < background.y))
  }
  assert.equal(contrastingText('#ffffff'), '#17223d')
  assert.equal(contrastingText('#17223d'), '#ffffff')
})

test('hidden text cannot silently bypass the banking copy limit', () => {
  const document = { version: 1 as const, name: 'Вклад', format: 'STORY' as const, width: 300, height: 600, background: '#3155ff', layers: [newLayer('text', { role: 'title', text: 'А'.repeat(101), hidden: true })] }
  assert.match(validateDocument(document).join(' '), /101.*100/)
})

test('PROMO import retains text while bank buttons stay separate', () => {
  const document = importSource({ kind: 'content', item: { id: 1, name: 'Тест', contentType: 'PROMO', content: { role: 'promo', component: { role: 'linearContainer', axis: 'v', components: [{ role: 'text', format: 'html', text: '<b>Вклад</b> 16%' }, { role: 'text', format: 'none', text: 'До конца ноября' }, { role: 'button', text: 'Подробнее', actionType: 'default' }] } } } })
  assert.deepEqual(document.layers.filter(x => x.kind === 'text').map(x => [x.text, x.role]), [['Вклад 16%', 'title'], ['До конца ноября', 'body']])
  assert.equal(document.format, 'PROMO')
})
