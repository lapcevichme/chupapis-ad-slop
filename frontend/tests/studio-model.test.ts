import assert from 'node:assert/strict'
import test from 'node:test'
import { importSource, makeLayoutVariants, newLayer, validateDocument } from '../src/features/studio/model.ts'

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
})

test('hidden text cannot silently bypass the banking copy limit', () => {
  const document = { version: 1 as const, name: 'Вклад', format: 'STORY' as const, width: 300, height: 600, background: '#3155ff', layers: [newLayer('text', { role: 'title', text: 'А'.repeat(101), hidden: true })] }
  assert.match(validateDocument(document).join(' '), /101.*100/)
})

test('PROMO import retains text while bank buttons stay separate', () => {
  const document = importSource({ kind: 'content', item: { id: 1, name: 'Тест', contentType: 'PROMO', content: { role: 'promo', component: { role: 'linearContainer', axis: 'v', components: [{ role: 'text', format: 'html', text: '<b>Вклад</b> 16%' }, { role: 'button', text: 'Подробнее', actionType: 'default' }] } } } })
  assert.deepEqual(document.layers.filter(x => x.kind === 'text').map(x => x.text), ['Вклад 16%'])
  assert.equal(document.format, 'PROMO')
})
