import { Moon, Sun } from 'lucide-react'
import { useState } from 'react'
import { Button } from '@/components/ui/button'

// Этот же ключ читает скрипт в index.html: тема должна примениться до первой отрисовки.
const THEME_KEY = 'adpilot.theme'

export function ThemeToggle({ onChange }: { onChange?: (dark: boolean) => void }) {
  const [dark, setDark] = useState(() => document.documentElement.classList.contains('dark'))
  const label = dark ? 'Включить светлую тему' : 'Включить тёмную тему'

  return (
    <Button
      type="button"
      variant="outline"
      size="icon"
      aria-label={label}
      title={label}
      onClick={() => {
        document.documentElement.classList.toggle('dark', !dark)
        localStorage.setItem(THEME_KEY, dark ? 'light' : 'dark')
        setDark(!dark)
        onChange?.(!dark)
      }}
    >
      {dark ? <Sun aria-hidden="true" /> : <Moon aria-hidden="true" />}
    </Button>
  )
}
