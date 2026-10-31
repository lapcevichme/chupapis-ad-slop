import Markdown, { type Components } from 'react-markdown'

// Сырой HTML react-markdown не исполняет, а опасные ссылки вырезает. Картинки не показываем: текст приходит от LLM,
// и внешняя картинка стала бы запросом на чужой сервер.
const DISALLOWED = ['img']

const HEADING = 'm-0 text-sm leading-5 font-semibold'

const COMPONENTS: Components = {
  p: ({ children }) => <p className="m-0">{children}</p>,
  h1: ({ children }) => <h3 className={HEADING}>{children}</h3>,
  h2: ({ children }) => <h3 className={HEADING}>{children}</h3>,
  h3: ({ children }) => <h3 className={HEADING}>{children}</h3>,
  h4: ({ children }) => <h3 className={HEADING}>{children}</h3>,
  ul: ({ children }) => <ul className="m-0 flex list-disc flex-col gap-1 pl-5">{children}</ul>,
  ol: ({ children }) => <ol className="m-0 flex list-decimal flex-col gap-1 pl-5">{children}</ol>,
  a: ({ children, href }) => (
    <a href={href} target="_blank" rel="noreferrer" className="text-primary underline underline-offset-2">
      {children}
    </a>
  ),
  code: ({ children }) => <code className="rounded-sm bg-muted px-1 font-mono text-[13px]">{children}</code>,
  pre: ({ children }) => <pre className="m-0 overflow-x-auto rounded-md bg-muted p-2 font-mono text-[13px] [&_code]:bg-transparent [&_code]:p-0">{children}</pre>,
  blockquote: ({ children }) => <blockquote className="m-0 flex flex-col gap-2 border-l-2 border-input pl-3 text-muted-foreground">{children}</blockquote>,
  hr: () => <hr className="m-0 w-full border-border" />,
}

export function ChatMarkdown({ text }: { text: string }) {
  return (
    <div className="flex flex-col gap-2 text-sm leading-5 wrap-anywhere">
      <Markdown components={COMPONENTS} disallowedElements={DISALLOWED} unwrapDisallowed>
        {text}
      </Markdown>
    </div>
  )
}
