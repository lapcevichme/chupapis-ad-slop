import { useState } from 'react'
import type { StudioDocument } from '@/api/studio'
import type { StudioVariant } from './model'

export function useStudioProject(key: string, initial: StudioDocument) {
  const [project, setProject] = useState<{ variants: StudioVariant[]; activeId: string }>(() => {
    try {
      const value = JSON.parse(localStorage.getItem(key) ?? 'null')
      if (value?.variants?.length && value.variants.every((v: StudioVariant) => v.document?.version === 1 && Array.isArray(v.document.layers))) return value
    } catch { /* Повреждённый локальный черновик не должен ломать открытие исходного креатива. */ }
    const id = crypto.randomUUID()
    return { variants: [{ id, label: 'Исходный', document: initial }], activeId: id }
  })
  const [past, setPast] = useState<StudioDocument[]>([])
  const [future, setFuture] = useState<StudioDocument[]>([])
  const [storageError, setStorageError] = useState(false)
  const active = project.variants.find(v => v.id === project.activeId) ?? project.variants[0]

  function store(next: typeof project) {
    setProject(next)
    try { localStorage.setItem(key, JSON.stringify(next)); setStorageError(false) }
    catch { setStorageError(true) }
  }

  function change(document: StudioDocument, remember = true) {
    if (remember) { setPast(old => [...old.slice(-59), active.document]); setFuture([]) }
    store({ ...project, variants: project.variants.map(v => v.id === active.id ? { ...v, document } : v) })
  }
  function select(id: string) { store({ ...project, activeId: id }); setPast([]); setFuture([]) }
  function add(documents: StudioDocument[], label?: string) {
    const incoming = documents.map(document => ({ id: crypto.randomUUID(), label: label ?? document.name, document: structuredClone(document) }))
    store({ variants: [...project.variants.slice(-11), ...incoming], activeId: incoming[0].id })
    setPast([]); setFuture([])
  }
  function undo() {
    if (!past.length) return
    setFuture(old => [active.document, ...old]); change(past[past.length - 1], false); setPast(old => old.slice(0, -1))
  }
  function redo() {
    if (!future.length) return
    setPast(old => [...old, active.document]); change(future[0], false); setFuture(old => old.slice(1))
  }
  return { variants: project.variants, active, change, select, add, undo, redo, canUndo: past.length > 0, canRedo: future.length > 0, storageError }
}
