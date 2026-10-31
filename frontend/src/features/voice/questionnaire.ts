import type { SuggestionQuestion } from '@/types/api'

export type QuestionOption = SuggestionQuestion['options'][number]

export interface QuestionPage {
  group: string
  question?: string
  options: QuestionOption[]
}

export interface Answer {
  value: string
  custom: boolean
}

export type Answers = Record<string, Answer>

// Страница анкеты — вопрос агента. Вопрос без вариантов остаётся страницей только со своим ответом.
export function buildPages(questions: SuggestionQuestion[]): QuestionPage[] {
  return questions.reduce<QuestionPage[]>(
    (pages, question) => mergeOptions(pages, question.options, question.header, question.question),
    [],
  )
}

// Варианты добавляются к странице с той же темой: так ход обсуждения дополняет свой пункт.
export function mergeOptions(pages: QuestionPage[], options: QuestionOption[], group: string, question?: string): QuestionPage[] {
  const result = pages.map((page) => ({ ...page, options: [...page.options] }))
  let page = result.find((candidate) => candidate.group === group)
  if (!page) {
    page = { group, question, options: [] }
    result.push(page)
  }
  for (const option of options) {
    if (!page.options.some((known) => known.value === option.value)) page.options.push(option)
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
