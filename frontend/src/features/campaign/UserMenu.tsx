import { Menu } from '@base-ui/react/menu'
import { Check, ChevronDown } from 'lucide-react'
import { USERS } from '@/api/currentUser'
import { Button } from '@/components/ui/button'

// ivanov.p → IP
function initials(login: string) {
  return login
    .split('.')
    .map((part) => part[0])
    .join('')
    .toUpperCase()
}

function Avatar({ login }: { login: string }) {
  return (
    <span aria-hidden="true" className="flex size-8 shrink-0 items-center justify-center rounded-full bg-accent text-xs leading-4 font-semibold text-accent-foreground">
      {initials(login)}
    </span>
  )
}

interface UserMenuProps {
  login: string
  disabled: boolean
  onSelect: (login: string) => void
}

export function UserMenu({ login, disabled, onSelect }: UserMenuProps) {
  const current = USERS.find((user) => user.login === login) ?? USERS[0]

  return (
    <Menu.Root>
      <Menu.Trigger
        disabled={disabled}
        render={
          <Button variant="outline" aria-label={`Пользователь: ${current.login}, ${current.title}`} className="h-auto min-h-11 gap-2 py-1 pr-3 pl-1.5 text-left">
            <Avatar login={current.login} />
            <span className="flex flex-col">
              <span className="text-[13px] leading-[18px] font-medium">{current.login}</span>
              <span className="text-xs leading-4 font-normal text-muted-foreground first-letter:uppercase">{current.title}</span>
            </span>
            <ChevronDown aria-hidden="true" />
          </Button>
        }
      />
      <Menu.Portal>
        <Menu.Positioner side="bottom" align="end" sideOffset={8} className="z-50">
          <Menu.Popup className="w-72 rounded-lg border bg-popover p-2 text-popover-foreground shadow-lg outline-none transition-[opacity,transform] duration-150 origin-[var(--transform-origin)] data-starting-style:scale-95 data-starting-style:opacity-0 data-ending-style:scale-95 data-ending-style:opacity-0">
            <Menu.RadioGroup
              value={login}
              onValueChange={(value: string) => {
                if (value !== login) onSelect(value)
              }}
            >
              {USERS.map((user) => (
                <Menu.RadioItem
                  key={user.login}
                  value={user.login}
                  closeOnClick
                  className="flex min-h-11 cursor-pointer items-center gap-3 rounded-md px-2 py-1.5 outline-none data-highlighted:bg-muted"
                >
                  <Avatar login={user.login} />
                  <span className="flex min-w-0 flex-1 flex-col">
                    <span className="text-sm leading-5 font-medium">{user.login}</span>
                    <span className="text-xs leading-4 text-muted-foreground">{user.description}</span>
                  </span>
                  <Menu.RadioItemIndicator>
                    <Check className="size-4" aria-hidden="true" />
                  </Menu.RadioItemIndicator>
                </Menu.RadioItem>
              ))}
            </Menu.RadioGroup>
          </Menu.Popup>
        </Menu.Positioner>
      </Menu.Portal>
    </Menu.Root>
  )
}
