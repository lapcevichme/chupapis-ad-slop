interface VoiceSummaryProps {
  // Сколько длился разговор; null, если человек в этом режиме ещё ничего не говорил.
  elapsedMs: number | null
  // Кампанию начали раньше, в чате: «собрано» было бы неправдой.
  startedFresh: boolean
  questions: number
  confirmations: number
}

function plural(count: number, one: string, few: string, many: string) {
  const tens = count % 100
  const units = count % 10
  if (tens >= 11 && tens <= 14) return many
  if (units === 1) return one
  return units >= 2 && units <= 4 ? few : many
}

function formatElapsed(ms: number) {
  const seconds = Math.round(ms / 1000)
  return `${Math.floor(seconds / 60)}:${String(seconds % 60).padStart(2, '0')}`
}

// Только замер этого разговора, а не обещание экономии. Отправка проходит лишь без ошибок проверки на сервере.
export function VoiceSummary({ elapsedMs, startedFresh, questions, confirmations }: VoiceSummaryProps) {
  return (
    <div className="flex flex-col items-center gap-3">
      {elapsedMs !== null && (
        <p className="m-0 text-2xl leading-8 font-semibold tabular-nums">
          {startedFresh ? 'Собрано за' : 'Завершено за'} {formatElapsed(elapsedMs)}
        </p>
      )}
      <dl className="m-0 flex justify-center gap-8">
        <div className="flex flex-col-reverse items-center">
          <dt className="text-[13px] leading-[18px] text-muted-foreground">{plural(questions, 'уточнение', 'уточнения', 'уточнений')}</dt>
          <dd className="m-0 text-xl leading-7 font-semibold tabular-nums">{questions}</dd>
        </div>
        <div className="flex flex-col-reverse items-center">
          <dt className="text-[13px] leading-[18px] text-muted-foreground">{plural(confirmations, 'подтверждение', 'подтверждения', 'подтверждений')}</dt>
          <dd className="m-0 text-xl leading-7 font-semibold tabular-nums">{confirmations}</dd>
        </div>
      </dl>
      <p className="m-0 text-[15px] leading-[22px] text-balance text-muted-foreground">Проверка прошла без ошибок. Решение примет модератор, клиенты пока ничего не видят.</p>
    </div>
  )
}
