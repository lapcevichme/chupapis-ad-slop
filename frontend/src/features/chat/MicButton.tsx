import { LoaderCircle, Mic, Square } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { dictationSupported, type DictationStatus } from './useDictation'

const LABELS: Record<DictationStatus, string> = {
  idle: 'Надиктовать сообщение',
  starting: 'Включаем микрофон',
  recording: 'Остановить запись',
  transcribing: 'Распознаём запись',
}

interface MicButtonProps {
  status: DictationStatus
  onToggle: () => void
}

export function MicButton({ status, onToggle }: MicButtonProps) {
  if (!dictationSupported()) return null
  const recording = status === 'recording'
  const pending = status === 'starting' || status === 'transcribing'
  return (
    // На телефонах диктовка уже есть в клавиатуре, поэтому кнопка только для устройств с точным указателем.
    <Button
      type="button"
      size="icon"
      variant={recording ? 'destructive' : 'secondary'}
      aria-label={LABELS[status]}
      aria-pressed={recording}
      title={LABELS[status]}
      disabled={pending}
      onClick={onToggle}
      className="pointer-coarse:hidden"
    >
      {pending ? <LoaderCircle className="animate-spin" aria-hidden="true" /> : recording ? <Square className="animate-pulse fill-current" aria-hidden="true" /> : <Mic aria-hidden="true" />}
    </Button>
  )
}
