import { Button } from '@/components/ui/button'
import type { NextStep } from '@/features/campaign/nextStep'

export function NextStepBar({ step, onSend }: { step: NextStep; onSend: (text: string) => void }) {
  return (
    <section aria-label="Следующий шаг" className="flex flex-col gap-3 rounded-lg border bg-info p-4 text-info-foreground">
      <h3 className="m-0 text-sm leading-5 font-semibold">{step.title}</h3>
      <div className="flex flex-wrap gap-2">
        {step.actions.map((action, index) => (
          <Button key={action.label} variant={index === 0 ? 'default' : 'outline'} className="flex-1" onClick={() => onSend(action.message)}>
            {action.label}
          </Button>
        ))}
      </div>
    </section>
  )
}
