import { Menu } from '@base-ui/react/menu'
import { ChevronDown, LogOut } from 'lucide-react'
import { ROLE_TITLES, type SessionUser } from '@/api/auth'
import { Button } from '@/components/ui/button'

// ivanov.p → IP
function initials(login: string) {
  return login
    .split(/[.\-_]/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0])
    .join('')
    .toUpperCase()
}

export function Avatar({ login }: { login: string }) {
  return (
    <span aria-hidden="true" className="flex size-8 shrink-0 items-center justify-center rounded-full bg-accent text-xs leading-4 font-semibold text-accent-foreground">
      {initials(login)}
    </span>
  )
}

interface UserMenuProps {
  user: SessionUser
  onSignOut: () => void
}

export function UserMenu({ user, onSignOut }: UserMenuProps) {
  const title = ROLE_TITLES[user.role]

  return (
    <Menu.Root>
      <Menu.Trigger
        render={
          <Button variant="outline" aria-label={`Пользователь: ${user.username}, ${title}`} className="h-auto min-h-11 gap-2 py-1 pr-3 pl-1.5 text-left">
            <Avatar login={user.username} />
            <span className="flex flex-col">
              <span className="text-[13px] leading-[18px] font-medium">{user.username}</span>
              <span className="text-xs leading-4 font-normal text-muted-foreground first-letter:uppercase">{title}</span>
            </span>
            <ChevronDown aria-hidden="true" />
          </Button>
        }
      />
      <Menu.Portal>
        <Menu.Positioner side="bottom" align="end" sideOffset={8} className="z-50">
          <Menu.Popup className="w-64 rounded-lg border bg-popover p-2 text-popover-foreground shadow-lg outline-none transition-[opacity,transform] duration-150 origin-[var(--transform-origin)] data-starting-style:scale-95 data-starting-style:opacity-0 data-ending-style:scale-95 data-ending-style:opacity-0">
            <p className="px-2 py-1.5 text-xs leading-4 text-muted-foreground">{user.email}</p>
            <Menu.Separator className="my-1 h-px bg-border" />
            <Menu.Item onClick={onSignOut} className="flex min-h-11 cursor-pointer items-center gap-3 rounded-md px-2 py-1.5 text-sm leading-5 outline-none data-highlighted:bg-muted">
              <span aria-hidden="true" className="flex size-8 shrink-0 items-center justify-center text-muted-foreground"><LogOut className="size-4" /></span>
              Выйти
            </Menu.Item>
          </Menu.Popup>
        </Menu.Positioner>
      </Menu.Portal>
    </Menu.Root>
  )
}
