import type { Suggestion } from '@/types/api'

export interface QuestionPage {
  group: string
  options: Suggestion[]
}

export interface Answer {
  value: string
  custom: boolean
}

export type Answers = Record<string, Answer>

export function buildPages(items: Suggestion[], questions: string[] = []): QuestionPage[] {
  return addQuestions(mergeItems([], items, ''), questions)
}

// Вопрос без вариантов становится страницей только со свободным ответом.
export function addQuestions(pages: QuestionPage[], questions: string[]): QuestionPage[] {
  const missing = questions.filter((question) => !pages.some((page) => page.group === question))
  return [...pages, ...missing.map((group) => ({ group, options: [] }))]
}

// Варианты без темы относятся к тому пункту, который сейчас обсуждают.
export function mergeItems(pages: QuestionPage[], items: Suggestion[], fallbackGroup: string): QuestionPage[] {
  const result = pages.map((page) => ({ ...page, options: [...page.options] }))
  for (const item of items) {
    const group = item.group ?? fallbackGroup
    let page = result.find((candidate) => candidate.group === group)
    if (!page) {
      page = { group, options: [] }
      result.push(page)
    }
    if (!page.options.some((option) => option.value === item.value)) page.options.push(item)
  }
  return result
}

// Ответы уходят одним сообщением. Тему пишем рядом: свой текст без неё агенту не понять.
export function formatAnswers(pages: QuestionPage[], answers: Answers): string {
  return pages
    .flatMap((page) => {
      const answer = answers[page.group]
      if (!answer?.value.trim()) return []
      const value = answer.value.trim()
      // Готовый вариант агента часто уже содержит название темы.
      const named = !page.group || value.toLowerCase().startsWith(page.group.toLowerCase())
      return [named ? value : `${page.group}: ${value}`]
    })
    .join('\n')
}

// Этот префикс разбирает правило в prompts/voice.md: агент отвечает коротко и предлагает варианты для этого пункта.
export function discussionMessage(group: string, text: string): string {
  return group ? `По пункту анкеты «${group}»: ${text}` : text
}
