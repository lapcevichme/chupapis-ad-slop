import { Dialog } from '@base-ui/react/dialog'
import { ArrowLeft, Check, ChevronLeft, Columns2, Download, ImagePlus, Layers2, LoaderCircle, Plus, Redo2, Settings2, Sparkles, Square, Type, Undo2, X } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import { editStudioDocument, generateStudioVariants, loadStudioDocument } from '@/api/studio'
import type { StudioDocument, StudioLayer } from '@/api/studio'
import { getCurrentUser } from '@/api/currentUser'
import { Button } from '@/components/ui/button'
import { buttonActionLabel, contrastingText, importSource, makeLayoutVariants, newLayer, validateDocument } from './model'
import type { PromoButton, StudioSource } from './model'
import { downloadBlob, renderDocument } from './render'
import { StudioElements } from './StudioElements'
import { ILLUSTRATIONS } from './illustrations'
import { StudioCanvas } from './StudioCanvas'
import { StudioLayers } from './StudioLayers'
import { StudioProperties } from './StudioProperties'
import { StudioComparison, StudioVariants } from './StudioVariants'
import { uploadStudioImage } from './upload'
import { useStudioProject } from './useStudioProject'
import './studio.css'

interface Props {
  source: StudioSource
  initialDocument?: StudioDocument
  initialSelection?: string
  campaignId: number | null
  editable: boolean
  applyReason?: string
  notice?: string
  hasContent: boolean
  onSource: (kind: 'banner' | 'content') => void
  onClose: () => void
  onApply: (source: StudioSource, document: StudioDocument, png: Blob, buttons: PromoButton[]) => Promise<void>
}

export function CreativeStudio(props: Props) {
  const [source] = useState(() => structuredClone(props.source))
  const [initial, setInitial] = useState<StudioDocument | null>(props.initialDocument ?? null)
  const [error, setError] = useState('')
  const [applying, setApplying] = useState(false)
  const image = source.kind === 'banner' ? source.item.content.image?.url : source.item.content.component.components.find(x => x.role === 'image')?.url
  useEffect(() => {
    if (props.initialDocument) return
    let active = true
    loadStudioDocument(image).then(saved => { if (active) setInitial(saved ?? importSource(source)) }).catch(reason => { if (active) setError(reason instanceof Error ? reason.message : 'Не удалось открыть документ слоёв.') })
    return () => { active = false }
  }, [image, source, props.initialDocument])
  return <Dialog.Root open onOpenChange={open => { if (!open && !applying) props.onClose() }}><Dialog.Portal><Dialog.Backdrop className="studio-backdrop" /><Dialog.Popup className="creative-studio">
    <Dialog.Title className="sr-only">Студия креативов</Dialog.Title>
    {initial ? <StudioEditor {...props} source={source} initial={initial} onApplying={setApplying} /> : <div className="studio-loading">{error ? <><p role="alert">{error}</p><Button onClick={props.onClose}>Закрыть студию</Button></> : <><LoaderCircle className="animate-spin" />Открываю слои…</>}</div>}
  </Dialog.Popup></Dialog.Portal></Dialog.Root>
}

function StudioEditor({ source, initial, campaignId, editable, applyReason, notice, hasContent, onSource, onClose, onApply, onApplying, initialDocument, initialSelection }: Props & { initial: StudioDocument; onApplying: (value: boolean) => void }) {
  const key = `adpilot.studio.v1.${getCurrentUser().login}.${campaignId ?? 'draft'}.${source.kind}.${source.item.id}`
  const project = useStudioProject(key, initial, JSON.stringify(source.item.content), Boolean(initialDocument))
  const document = project.active.document
  const [selected, setSelected] = useState<string | null>(initialSelection ?? null)
  const layer = document.layers.find(x => x.id === selected)
  const [compare, setCompare] = useState(false)
  const [variantsCollapsed, setVariantsCollapsed] = useState(true)
  const [compared, setCompared] = useState<string[]>([project.active.id])
  const [panel, setPanel] = useState<'layers' | 'properties' | null>(initialSelection ? 'properties' : null)
  const [prompt, setPrompt] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState('')
  const [review, setReview] = useState<{ blob: Blob; url: string } | null>(null)
  const [buttons, setButtons] = useState<PromoButton[]>(() => {
    const original = source.kind === 'content' ? source.item.content.component.components.filter((x): x is PromoButton => x.role === 'button') : []
    try { const saved = JSON.parse(localStorage.getItem(key + '.buttons') ?? 'null'); return saved?.origin === JSON.stringify(source.item.content) && Array.isArray(saved.buttons) ? saved.buttons : original } catch { return original }
  })
  const upload = useRef<HTMLInputElement>(null)
  const replacement = useRef<string | null>(null)
  const mounted = useRef(true)
  useEffect(() => { mounted.current = true; return () => { mounted.current = false } }, [])
  const mutable = editable && !busy
  const errors = [...validateDocument(document), ...(buttons.some(button => !button.text.trim()) ? ['Укажите текст банковской кнопки.'] : [])]
  useEffect(() => () => { if (review) URL.revokeObjectURL(review.url) }, [review])

  function patch(id: string, values: Partial<StudioLayer>) { project.change({ ...document, layers: document.layers.map(x => x.id === id ? { ...x, ...values } : x) }) }
  function removeLayer() { if (layer && !layer.locked) { project.change({ ...document, layers: document.layers.filter(x => x.id !== layer.id) }); setSelected(null) } }
  function duplicate() { if (layer) { const copy = { ...layer, id: crypto.randomUUID(), name: layer.name.slice(0, 90) + ' · копия', x: layer.x + 10, y: layer.y + 10 }; project.change({ ...document, layers: [...document.layers, copy] }); setSelected(copy.id) } }
  function order(direction: number) {
    if (!layer) return
    const layers = [...document.layers], index = layers.findIndex(x => x.id === layer.id)
    const target = Math.max(0, Math.min(layers.length - 1, index + direction))
    layers.splice(index, 1); layers.splice(target, 0, layer); project.change({ ...document, layers })
  }
  function select(id: string | null) { setSelected(id); if (id) setPanel('properties') }
  function addLayer(kind: 'text' | 'shape') {
    if (document.layers.length >= 40) { setError('В макете уже 40 слоёв. Удалите ненужные.'); return }
    const added = newLayer(kind, { x: 24, y: Math.min(80, document.height / 3), width: document.width - 48, height: kind === 'text' ? 64 : 120, fill: kind === 'text' ? contrastingText(document.background) : '#d6f45b' })
    project.change({ ...document, layers: [...document.layers, added] }); select(added.id)
  }
  function addIllustration(symbol: StudioLayer['symbol']) {
    if (document.layers.length >= 40) { setError('В макете уже 40 слоёв. Удалите ненужные.'); return }
    const size = Math.min(document.width * .65, document.height * .45)
    const added = newLayer('illustration', { symbol, name: ILLUSTRATIONS.find(item => item.symbol === symbol)?.label ?? 'Предмет', x: (document.width - size) / 2, y: Math.max(12, document.height * .48 - size / 2), width: size, height: size, fit: 'contain' })
    project.change({ ...document, layers: [...document.layers, added] }); select(added.id)
  }
  function addVariants(documents: StudioDocument[], label?: string) { if (!mounted.current) return; const ids = project.add(documents, label); if (!ids) setError('Сохранено 12 вариантов. Удалите ненужный вариант перед добавлением новых.'); else { setCompared(ids); setVariantsCollapsed(false) } }
  function toggleCompare(id: string) { setCompared(old => old.includes(id) ? old.filter(x => x !== id) : old.length < 3 ? [...old, id] : old) }
  async function run(label: string, task: () => Promise<void>) { setBusy(label); setError(''); onApplying(label === 'Применяю макет'); try { await task() } catch (reason) { if (mounted.current) setError(reason instanceof Error ? reason.message : 'Не удалось выполнить действие.') } finally { if (mounted.current) { setBusy(''); onApplying(false) } } }
  async function handleUpload(file: File) {
    await run('Загружаю изображение', async () => {
      const image = await uploadStudioImage(file)
      if (!mounted.current) return
      if (replacement.current) patch(replacement.current, { kind: 'image', src: image.url, name: file.name.slice(0, 100) })
      else {
        const added = newLayer('image', { name: file.name.slice(0, 100), src: image.url, width: 220, height: Math.min(300, 220 / image.aspect), x: 40, y: Math.min(180, document.height / 3) })
        project.change({ ...document, layers: [...document.layers, added] }); select(added.id)
      }
    })
    replacement.current = null
  }
  useEffect(() => {
    function keyboard(event: KeyboardEvent) {
      if (!mutable || compare || (event.target instanceof HTMLElement && (event.target.closest('input,textarea,select') || event.target.isContentEditable))) return
      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'z') { event.preventDefault(); if (event.shiftKey) project.redo(); else project.undo(); return }
      if (event.key === 'Delete' || event.key === 'Backspace') { event.preventDefault(); removeLayer() }
      if (layer && !layer.locked && ['ArrowLeft', 'ArrowRight', 'ArrowUp', 'ArrowDown'].includes(event.key)) {
        event.preventDefault(); const step = event.shiftKey ? 10 : 1
        patch(layer.id, { x: layer.x + (event.key === 'ArrowRight' ? step : event.key === 'ArrowLeft' ? -step : 0), y: layer.y + (event.key === 'ArrowDown' ? step : event.key === 'ArrowUp' ? -step : 0) })
      }
    }
    window.addEventListener('keydown', keyboard)
    return () => window.removeEventListener('keydown', keyboard)
  })

  return <div className={`studio-shell ${compare ? 'is-comparing' : ''}`} data-panel={panel ?? ''} data-working={busy.startsWith('AI')}>
    <header className="studio-topbar"><button type="button" className="studio-back" disabled={busy === 'Применяю макет'} onClick={onClose} aria-label="Закрыть студию"><ArrowLeft size={19} /></button><div className="studio-wordmark">adpilot<span>studio</span></div><div className="studio-project-name"><strong>{source.item.name}</strong><span>{project.storageError ? 'Черновик не сохранён — скачайте PNG' : 'Варианты на этом устройстве'}</span></div>
      <div className="studio-history"><button type="button" title="Отменить" aria-label="Отменить правку" disabled={!mutable || !project.canUndo} onClick={project.undo}><Undo2 size={18} /></button><button type="button" title="Повторить" aria-label="Повторить правку" disabled={!mutable || !project.canRedo} onClick={project.redo}><Redo2 size={18} /></button></div>
      <button type="button" className={`studio-outline-button ${compare ? 'selected' : ''}`} aria-label={compare ? 'К редактору' : 'Сравнить'} disabled={Boolean(busy)} onClick={() => { if (!compare) setVariantsCollapsed(true); if (!compare && compared.length < 2) setCompared(project.variants.slice(-3).map(v => v.id)); setCompare(!compare) }}><Columns2 size={17} /><span>{compare ? 'К редактору' : 'Сравнить'}</span></button>
      <button type="button" className="studio-outline-button" aria-label="Скачать PNG" disabled={Boolean(busy)} onClick={() => void run('Собираю PNG', async () => downloadBlob(await renderDocument(document), `${document.name}.png`))}><Download size={17} /><span>PNG</span></button>
      <button type="button" className="studio-primary-button" disabled={Boolean(busy) || Boolean(applyReason) || !editable || errors.length > 0} title={applyReason || errors[0]} onClick={() => void run('Готовлю просмотр', async () => { const blob = await renderDocument(document); if (mounted.current) setReview({ blob, url: URL.createObjectURL(blob) }) })}><Check size={17} /><span>Применить</span></button>
    </header>
    <div className="studio-command-bar"><div className="studio-source-switch"><button type="button" aria-pressed={source.kind === 'banner'} disabled={Boolean(busy)} onClick={() => onSource('banner')}>Баннер</button><button type="button" aria-pressed={source.kind === 'content'} disabled={!hasContent || Boolean(busy)} onClick={() => onSource('content')}>Промо-экран</button></div><span className="studio-document-name">{project.active.label}</span><div className="studio-tools"><StudioElements disabled={!mutable || compare} onAdd={addIllustration} /><button type="button" disabled={!mutable || compare} onClick={() => addLayer('text')}><Type size={17} />Текст</button><button type="button" disabled={!mutable || compare} onClick={() => addLayer('shape')}><Square size={17} />Фигура</button><button type="button" disabled={!mutable || compare} onClick={() => { replacement.current = null; upload.current?.click() }}><ImagePlus size={17} />Загрузить</button></div><div className="studio-mobile-panels"><button type="button" aria-label="Показать слои" onClick={() => setPanel(panel === 'layers' ? null : 'layers')}><Layers2 size={18} /></button><button type="button" aria-label="Показать свойства" onClick={() => setPanel(panel === 'properties' ? null : 'properties')}><Settings2 size={18} /></button></div></div>
    <input ref={upload} type="file" disabled={!mutable || compare} accept="image/*,.svg" className="sr-only" aria-label="Загрузить материал в креатив" onChange={event => { const file = event.target.files?.[0]; if (file) void handleUpload(file); event.target.value = '' }} />
    {error && <div className="studio-error" role="alert">{error}<button type="button" aria-label="Закрыть сообщение" onClick={() => setError('')}><X size={16} /></button></div>}
    {busy && <div className="studio-progress" role="status"><LoaderCircle size={16} className="animate-spin" />{busy}…</div>}
    <div className="studio-workspace">
      {compare ? <StudioComparison variants={project.variants.filter(v => (compared.length ? compared : [project.active.id]).includes(v.id))} activeId={project.active.id} onSelect={id => { project.select(id); setCompare(false); setSelected(null) }} /> : <>
        <StudioLayers document={document} selected={selected} onSelect={select} onPatch={patch} editable={mutable} />
        <div className="studio-middle"><StudioCanvas document={document} selected={selected} onSelect={select} onChange={project.change} editable={mutable} onFile={file => { replacement.current = null; void handleUpload(file) }} />{source.kind === 'content' && buttons.length > 0 && <div className="studio-native-preview">{buttons.map((button, i) => <span key={i} style={{ background: button.style?.backgroundColor ?? '#3155ff', color: button.textStyle?.textColor ?? '#ffffff', fontSize: Math.min(16, button.textStyle?.fontSize ?? 16) }}>{button.text}</span>)}<small>Банковские кнопки · под композицией</small></div>}
          <div className="studio-ai-bar"><Sparkles size={18} /><textarea rows={1} aria-label="Задача AI-дизайнеру" placeholder={layer ? `Что изменить: ${layer.name.toLowerCase()}?` : "Добавьте кофе, измените цвета или попробуйте новую композицию…"} value={prompt} onChange={e => setPrompt(e.target.value)} disabled={!mutable} /><button type="button" disabled={!mutable || errors.length > 0} onClick={() => void run('AI собирает варианты', async () => addVariants(await generateStudioVariants(document, prompt.trim() || 'Три выразительные композиции с предметной иллюстрацией по смыслу оффера.')))}>3 варианта <Sparkles size={15} /></button><button type="button" className="studio-ai-edit" disabled={!mutable || !prompt.trim() || Boolean(layer?.locked) || errors.length > 0} onClick={() => void run(layer ? 'AI меняет выделенный объект' : 'AI меняет композицию', async () => addVariants([await editStudioDocument(document, prompt, selected ? [selected] : [])], 'AI · правка'))}>Изменить</button></div>
        </div>
        <StudioProperties document={document} layer={layer} editable={mutable && !layer?.locked} patch={values => { if (layer) patch(layer.id, values) }} onDocument={project.change} onDuplicate={duplicate} onDelete={removeLayer} onOrder={order} onReplace={() => { replacement.current = layer?.id ?? null; upload.current?.click() }} buttons={buttons} isPromo={source.kind === 'content'} onButtons={next => { setButtons(next); try { localStorage.setItem(key + '.buttons', JSON.stringify({ origin: JSON.stringify(source.item.content), buttons: next })) } catch { setError('Не удалось сохранить кнопки локально.') } }} />
        {panel && <button type="button" className="studio-panel-close" aria-label="Скрыть панель" onClick={() => setPanel(null)}><ChevronLeft size={18} /></button>}
      </>}
    </div>
    <fieldset disabled={Boolean(busy)} className="studio-variants-wrap"><StudioVariants variants={project.variants} activeId={project.active.id} compared={compared} collapsed={variantsCollapsed} onToggle={() => setVariantsCollapsed(!variantsCollapsed)} onSelect={id => { project.select(id); setSelected(null) }} onCompare={toggleCompare} onAdd={() => addVariants([document], 'Копия')} onRemove={id => { if (window.confirm('Удалить этот локальный вариант? Остальные варианты и кампания останутся.')) project.remove(id) }} /></fieldset>
    <footer className="studio-footer" data-important={Boolean(errors.length || applyReason || project.storageError)}><span>{errors[0] || applyReason || 'Перетаскивайте объекты. Стрелки — 1 px, Shift — 10 px. Ctrl / ⌘ Z — отмена.'}</span><button type="button" disabled={!mutable} onClick={() => addVariants(makeLayoutVariants(document))}><Plus size={13} />3 локальных макета</button></footer>
    <Dialog.Root open={review !== null} onOpenChange={open => { if (!open && busy !== 'Применяю макет') setReview(null) }}><Dialog.Portal><Dialog.Backdrop className="studio-review-backdrop" /><Dialog.Popup className="studio-review"><Dialog.Title>Применить этот макет?</Dialog.Title><Dialog.Description>{source.kind === 'banner' ? 'Баннер' : 'Промо-экран'} «{source.item.name}» изменится после подтверждения. Модерация остаётся отдельным действием.</Dialog.Description>{notice && <p className="studio-review-notice">{notice}</p>}{review && <img src={review.url} alt="Точный PNG, который будет сохранён в кампании" />}{source.kind === 'content' && buttons.length > 0 && <div className="studio-review-buttons">{buttons.map((button, index) => <span key={index} style={{ background: button.style?.backgroundColor ?? '#3155ff', color: button.textStyle?.textColor ?? '#ffffff', fontSize: button.textStyle?.fontSize ?? 16 }}>{button.text}<small>{buttonActionLabel(button.actionType)}</small></span>)}</div>}{error && <p role="alert" className="studio-review-error">{error}</p>}<div><button type="button" className="studio-outline-button" disabled={Boolean(busy)} onClick={() => setReview(null)}>Вернуться</button><button type="button" className="studio-primary-button" disabled={Boolean(busy)} onClick={() => { if (review) void run('Применяю макет', async () => { await onApply(source, document, review.blob, buttons); setReview(null); onClose() }) }}>{busy ? 'Сохраняю…' : 'Применить к кампании'}</button></div></Dialog.Popup></Dialog.Portal></Dialog.Root>
  </div>
}
