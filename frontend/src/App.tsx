import { useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { flushSync } from 'react-dom'
import { clearCurrentUser, hasCurrentUser, setCurrentUser } from '@/api/currentUser'
import { CampaignWorkspace } from '@/features/campaign/CampaignWorkspace'
import { forgetChatSession } from '@/features/chat/useChat'
import { EntryPage } from '@/features/entry/EntryPage'

// Плавная смена экрана там, где браузер это умеет; без поддержки и при reduced motion экран меняется сразу.
function changeScreen(update: () => void) {
  const animate = 'startViewTransition' in document && !matchMedia('(prefers-reduced-motion: reduce)').matches
  if (animate) document.startViewTransition(() => flushSync(update))
  else update()
}

function App() {
  const queryClient = useQueryClient()
  const [entered, setEntered] = useState(hasCurrentUser)
  const [brief, setBrief] = useState<string>()

  if (!entered) {
    return (
      <EntryPage
        onEnter={(login, nextBrief) => {
          setCurrentUser(login)
          // Вход начинает работу заново: бриф не должен попасть в чужой или старый диалог.
          forgetChatSession()
          changeScreen(() => {
            setBrief(nextBrief)
            setEntered(true)
          })
        }}
      />
    )
  }

  return (
    <CampaignWorkspace
      initialBrief={brief}
      onSignOut={() => {
        clearCurrentUser()
        forgetChatSession()
        changeScreen(() => {
          queryClient.clear()
          setBrief(undefined)
          setEntered(false)
        })
      }}
    />
  )
}

export default App
