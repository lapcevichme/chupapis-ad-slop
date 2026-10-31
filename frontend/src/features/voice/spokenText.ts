const MAX_SPOKEN_CHARS = 300
const MIN_FIRST_CHARS = 16
// Точка после этих слов не заканчивает предложение.
const ABBREVIATION = /(?:^|[\s(«])(?:г|гг|руб|коп|тыс|млн|млрд|т\.д|т\.п|др|пр|см|стр|ул|им)\.$/i
const SENTENCE_END = /[.!?…]+[»")]?(?=\s+[«"(]?[А-ЯЁA-Z0-9]|\s*$)/g

export function plainText(markdown: string): string {
  return markdown
    .replace(/```[\s\S]*?```/g, ' ')
    .replace(/!?\[([^\]]*)\]\([^)]*\)/g, '$1')
    .replace(/^\s{0,3}(?:#{1,6}\s+|[-*+]\s+|\d+[.)]\s+|>\s*)/gm, '')
    .replace(/[*_`~|]/g, '')
    .trim()
}

export function splitSentences(text: string): string[] {
  const result: string[] = []
  for (const line of text.split(/\n+/)) {
    let start = 0
    for (const match of line.matchAll(SENTENCE_END)) {
      const end = match.index + match[0].length
      if (ABBREVIATION.test(line.slice(start, end))) continue
      result.push(line.slice(start, end).trim())
      start = end
    }
    const rest = line.slice(start).trim()
    if (rest) result.push(rest)
  }
  return result.filter((sentence) => /[\p{L}\p{N}]/u.test(sentence))
}

// Вслух только суть: начало ответа и его конец, где обычно стоит вопрос. Остальное человек видит на экране.
export function spokenText(markdown: string): string {
  const sentences = splitSentences(plainText(markdown))
  if (sentences.length === 0) return ''
  // Приветствие вроде «Здравствуйте!» само по себе ничего не сообщает.
  const first = sentences[0].length < MIN_FIRST_CHARS && sentences.length > 1 ? sentences[1] : sentences[0]
  const last = sentences.at(-1) ?? first
  const both = first === last ? first : `${first} ${last}`
  if (both.length <= MAX_SPOKEN_CHARS) return both
  if (last.endsWith('?') && last.length <= MAX_SPOKEN_CHARS) return last
  if (first.length <= MAX_SPOKEN_CHARS) return first
  const cut = first.slice(0, MAX_SPOKEN_CHARS)
  return `${cut.slice(0, cut.lastIndexOf(' '))}…`
}
