import { Dialog } from '@base-ui/react/dialog'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { ArchiveRestore, ArrowLeft, LoaderCircle, Trash2 } from 'lucide-react'
import { useState } from 'react'
import { archiveChatSession, listChatSessions, restoreChatSession } from '@/api/chat'
import type { ChatSummary } from '@/api/chat'

const OLD_BEFORE = Date.parse('2026-10-31T21:00:00Z')
const timestamp = (value: string) => Date.parse(value.endsWith('Z') || /[+-]\d\d:\d\d$/.test(value) ? value : value + 'Z')

export function ChatHistory({ login, currentId, disabled, onOpen, onDeleted }: { login: string; currentId: string | null; disabled: boolean; onOpen: (id: string) => void; onDeleted: (id: string) => void }) {
  const [trash, setTrash] = useState(false)
  const [pending, setPending] = useState<ChatSummary[]>([])
  const [working, setWorking] = useState(false)
  const [error, setError] = useState('')
  const cache = useQueryClient()
  const history = useQuery({ queryKey: ['chats', login, trash], queryFn: () => listChatSessions(trash) })
  const old = history.data?.filter(row => timestamp(row.createdAt) < OLD_BEFORE) ?? []
  async function act(task: () => Promise<void>) {
    setWorking(true); setError('')
    try { await task(); setPending([]) }
    catch (reason) { setError(reason instanceof Error ? reason.message : 'Не удалось изменить историю.') }
    finally { setWorking(false); void cache.invalidateQueries({ queryKey: ['chats'] }) }
  }
  return <div className="chat-history">
    <div className="chat-history-tools"><button disabled={working} onClick={() => { setTrash(!trash); setError('') }}>{trash ? <ArrowLeft size={14} /> : <Trash2 size={14} />}{trash ? 'К диалогам' : 'Корзина'}</button>{!trash && old.length > 0 && <button disabled={disabled || working} onClick={() => setPending(old)}>Очистить старые</button>}</div>
    {error && <p role="alert" className="chat-history-error">{error}</p>}
    <div className="campaign-list">
      {history.isPending && <p className="nav-message"><LoaderCircle size={15} className="animate-spin" />Загружаем диалоги…</p>}
      {history.isError && <button className="nav-retry" onClick={() => void history.refetch()}>Не удалось загрузить. Повторить</button>}
      {history.data?.map(row => <div className="chat-history-row" key={row.sessionId}><button className={`campaign-link ${!trash && currentId === row.sessionId ? 'selected' : ''}`} disabled={disabled || working || trash} onClick={() => onOpen(row.sessionId)}><span>{row.name}</span><small>{new Date(timestamp(row.createdAt)).toLocaleDateString('ru-RU', { day: 'numeric', month: 'short' })}{row.campaignId ? ` · Кампания ${row.campaignId}` : ' · Новый бриф'}</small></button><button className="chat-history-action" disabled={disabled || working} aria-label={trash ? `Восстановить диалог: ${row.name}` : `Удалить диалог: ${row.name}`} title={trash ? 'Восстановить' : 'Удалить'} onClick={() => { if (trash) void act(async () => { await restoreChatSession(row.sessionId); setTrash(false); onOpen(row.sessionId) }); else setPending([row]) }}>{trash ? <ArchiveRestore size={16} /> : <Trash2 size={16} />}</button></div>)}
      {history.data?.length === 0 && <p className="nav-message">{trash ? 'Корзина пуста. Удалённые диалоги можно восстановить здесь.' : 'Здесь появятся ваши разговоры с ассистентом.'}</p>}
    </div>
    <Dialog.Root open={pending.length > 0} onOpenChange={open => { if (!open && !working) setPending([]) }}><Dialog.Portal><Dialog.Backdrop className="history-dialog-backdrop" /><Dialog.Popup className="history-dialog"><Dialog.Title>{pending.length === 1 ? 'Удалить диалог?' : `Убрать старые диалоги: ${pending.length}?`}</Dialog.Title><Dialog.Description>{pending.length === 1 ? `«${pending[0]?.name}» переместится в корзину.` : 'Диалоги, созданные до 1 ноября, переместятся в корзину.'} Кампании и креативы сохранятся. Диалог можно восстановить.</Dialog.Description>{error && <p role="alert">{error}</p>}<div><button disabled={working} onClick={() => setPending([])}>Отмена</button><button className="history-confirm" disabled={working || disabled} onClick={() => void act(async () => { for (const row of pending) { await archiveChatSession(row.sessionId); onDeleted(row.sessionId) } })}>{working ? 'Удаляем…' : 'В корзину'}</button></div></Dialog.Popup></Dialog.Portal></Dialog.Root>
  </div>
}
