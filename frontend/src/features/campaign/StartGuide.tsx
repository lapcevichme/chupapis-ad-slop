import { Eye, Search, ShieldCheck, Sparkles } from 'lucide-react'

const STEPS = [
  { icon: Sparkles, title: 'Соберёт черновик', text: 'Разберёт бриф, а неясные даты и условия уточнит вопросом.' },
  { icon: Search, title: 'Подберёт аудиторию и места', text: 'Только из справочников банка, с размером каждого сегмента.' },
  { icon: Eye, title: 'Подготовит креатив', text: 'Баннер и промо-экран с превью на телефоне и проверкой по правилам.' },
  { icon: ShieldCheck, title: 'Спросит перед записью', text: 'Сохранит кампанию и отправит на модерацию только после вашего подтверждения.' },
]

export function StartGuide() {
  return (
    <section className="flex animate-rise flex-col gap-4 rounded-lg border bg-card p-4 text-card-foreground">
      <h2 className="m-0 text-sm leading-5 font-semibold">Что сделает ассистент</h2>
      <ol className="m-0 flex list-none flex-col gap-4 p-0">
        {STEPS.map(({ icon: Icon, title, text }) => (
          <li key={title} className="flex items-start gap-3">
            <span className="flex size-8 shrink-0 items-center justify-center rounded-md bg-accent text-accent-foreground">
              <Icon className="size-4" aria-hidden="true" />
            </span>
            <span className="flex min-w-0 flex-col gap-0.5">
              <span className="text-sm leading-5 font-medium">{title}</span>
              <span className="text-[13px] leading-[18px] text-muted-foreground">{text}</span>
            </span>
          </li>
        ))}
      </ol>
    </section>
  )
}
