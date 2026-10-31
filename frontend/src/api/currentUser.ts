import type { User } from '@/types/api'

const STORAGE_KEY = 'adpilot.user'

export const USERS: (User & { title: string; description: string })[] = [
  { login: 'ivanov.p', role: 'campaignManager', title: 'менеджер', description: 'Менеджер: собирает кампании' },
  { login: 'petrova.m', role: 'campaignModerator', title: 'модератор', description: 'Модератор: одобряет кампании' },
]

export function getCurrentUser(): User {
  const login = localStorage.getItem(STORAGE_KEY)
  return USERS.find((user) => user.login === login) ?? USERS[0]
}

export function setCurrentUser(login: string) {
  localStorage.setItem(STORAGE_KEY, login)
}

export function userHeaders() {
  const { login, role } = getCurrentUser()
  return { 'X-User': login, 'X-Role': role }
}
