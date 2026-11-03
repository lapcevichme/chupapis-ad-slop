import { useQueryClient } from '@tanstack/react-query'
import { useEffect, useState } from 'react'
import { flushSync } from 'react-dom'
import { logout, restoreSession, useCurrentUser, type SessionUser } from '@/api/auth'
import { Button } from '@/components/ui/button'
import { CampaignWorkspace } from '@/features/campaign/CampaignWorkspace'
import { forgetChatSession } from '@/features/chat/useChat'
import { EntryPage } from '@/features/entry/EntryPage'

// Плавная смена экрана там, где браузер это умеет; без поддержки и при reduced motion экран меняется сразу.
function changeScreen(update: () => void) {
  const animate = 'startViewTransition' in document && !matchMedia('(prefers-reduced-motion: reduce)').matches
  if (animate) document.startViewTransition(() => flushSync(update))
  else update()
}

type StaffUser = SessionUser & { role: 'campaignManager' | 'campaignModerator' }

const isStaff = (user: SessionUser): user is StaffUser => user.role !== 'admin'

// Администратор управляет пользователями через API, а кампании ведут менеджер и модератор.
function AdminNotice({ user, onSignOut }: { user: SessionUser; onSignOut: () => void }) {
  return (
    <main className="mx-auto flex min-h-dvh max-w-md flex-col justify-center gap-4 p-6">
      <h1 className="text-2xl font-semibold">Вы вошли как администратор ({user.username})</h1>
      <p className="text-muted-foreground">Управление пользователями и ролями доступно через API (раздел admin). Для работы с кампаниями войдите менеджером или модератором.</p>
      <Button onClick={onSignOut}>Выйти</Button>
    </main>
  )
}

function App() {
  const queryClient = useQueryClient()
  const user = useCurrentUser()
  const [restoring, setRestoring] = useState(true)
  const [brief, setBrief] = useState<string>()

  // Продолжаем прежнюю сессию по refresh-cookie, пока пользователь не увидел форму входа.
  useEffect(() => {
    void restoreSession().finally(() => setRestoring(false))
  }, [])

  if (restoring) return null

  if (!user) {
    return (
      <EntryPage
        onEnter={(nextBrief) => {
          // Вход начинает работу заново: бриф не должен попасть в чужой или старый диалог.
          forgetChatSession()
          queryClient.clear()
          changeScreen(() => setBrief(nextBrief))
        }}
      />
    )
  }

  const signOut = () => {
    void logout()
    forgetChatSession()
    changeScreen(() => {
      queryClient.clear()
      setBrief(undefined)
    })
  }

  if (!isStaff(user)) return <AdminNotice user={user} onSignOut={signOut} />
  return <CampaignWorkspace user={user} initialBrief={brief} onSignOut={signOut} />
}

export default App
