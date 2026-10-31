import { synthesizeSpeech } from '@/api/speech'

// Заготовки лежат в public/voice, их создаёт backend/app/generate_voice_cues.py: первый звук не должен ждать агента.
// Вариантов много: фраза не повторится, пока не прозвучат все остальные в этой группе.
function numbered(name: string, count: number) {
  return Array.from({ length: count }, (_, index) => `${name}-${index + 1}`)
}

const CUES = {
  greet: ['greet', ...numbered('greet', 4).slice(1)],
  wait: numbered('wait', 16),
  more: numbered('more', 10),
  form: ['form', ...numbered('form', 5).slice(1)],
  confirm: ['confirm', ...numbered('confirm', 4).slice(1)],
} as const
export type VoiceCue = keyof typeof CUES
const CUE_NAMES = Object.keys(CUES) as VoiceCue[]

function shuffled(files: readonly string[]) {
  const result = [...files]
  for (let index = result.length - 1; index > 0; index--) {
    const other = Math.floor(Math.random() * (index + 1))
    ;[result[index], result[other]] = [result[other], result[index]]
  }
  return result
}

const VOLUME_KEY = 'adpilot.voiceVolume'

function storedVolume() {
  const value = Number(localStorage.getItem(VOLUME_KEY) ?? 1)
  return Number.isFinite(value) ? Math.min(1, Math.max(0, value)) : 1
}

function createAnalyser(context: AudioContext) {
  const analyser = context.createAnalyser()
  analyser.fftSize = 512
  analyser.smoothingTimeConstant = 0.5
  return analyser
}

class VoiceAudio {
  private context: AudioContext | null = null
  private output: AnalyserNode | null = null
  private gain: GainNode | null = null
  private currentVolume = storedVolume()
  private microphone: AnalyserNode | null = null
  private microphoneSource: MediaStreamAudioSourceNode | null = null
  private liveOutput: AnalyserNode | null = null
  private liveOutputSource: MediaStreamAudioSourceNode | null = null
  private playing: AudioBufferSourceNode | null = null
  private abort: AbortController | null = null
  private cues = new Map<string, Promise<AudioBuffer>>()
  private queues = new Map<VoiceCue, string[]>()
  private samples = new Uint8Array(512)
  muted = false

  // iOS разрешает запустить звук только внутри обработчика нажатия, поэтому вызываем его при входе в режим.
  unlock() {
    if (!this.context) {
      this.context = new AudioContext()
      this.output = createAnalyser(this.context)
      // Анализатор стоит до громкости: сфера реагирует на речь, даже когда звук тихий.
      this.gain = this.context.createGain()
      this.gain.gain.value = this.currentVolume
      this.output.connect(this.gain)
      this.gain.connect(this.context.destination)
      this.microphone = createAnalyser(this.context)
      // Заранее грузим только следующую фразу каждой группы: все сразу — лишний мегабайт на телефоне.
      for (const cue of CUE_NAMES) void this.loadFile(this.nextFile(cue)).catch(() => undefined)
    }
    void this.context.resume()
  }

  private nextFile(cue: VoiceCue) {
    const queue = this.queues.get(cue)
    if (queue?.length) return queue[0]
    const fresh = shuffled(CUES[cue])
    this.queues.set(cue, fresh)
    return fresh[0]
  }

  private pickFile(cue: VoiceCue) {
    const file = this.nextFile(cue)
    this.queues.get(cue)?.shift()
    // Новый круг не начинаем с только что сказанной фразы.
    if (this.queues.get(cue)?.length === 0) {
      const fresh = shuffled(CUES[cue])
      if (fresh[0] === file) fresh.push(fresh.shift() as string)
      this.queues.set(cue, fresh)
    }
    void this.loadFile(this.nextFile(cue)).catch(() => undefined)
    return file
  }

  private loadFile(file: string) {
    let buffer = this.cues.get(file)
    if (!buffer) {
      buffer = fetch(`/voice/${file}.mp3`)
        .then((response) => response.arrayBuffer())
        .then((data) => (this.context as AudioContext).decodeAudioData(data))
      // Без заготовки режим работает, просто тише; при следующем запросе попробуем загрузить снова.
      buffer.catch(() => this.cues.delete(file))
      this.cues.set(file, buffer)
    }
    return buffer
  }

  get volume() {
    return this.currentVolume
  }

  set volume(value: number) {
    this.currentVolume = value
    localStorage.setItem(VOLUME_KEY, String(value))
    if (this.gain && this.context) this.gain.gain.setTargetAtTime(value, this.context.currentTime, 0.02)
  }

  get isPlaying() {
    return this.playing !== null
  }

  stop() {
    this.abort?.abort()
    this.abort = null
    const current = this.playing
    this.playing = null
    if (current) {
      current.onended = null
      current.stop()
    }
  }

  private play(buffer: AudioBuffer) {
    return new Promise<void>((resolve) => {
      const source = (this.context as AudioContext).createBufferSource()
      source.buffer = buffer
      source.connect(this.output as AnalyserNode)
      source.onended = () => {
        if (this.playing === source) this.playing = null
        resolve()
      }
      this.playing = source
      source.start()
    })
  }

  async cue(cue: VoiceCue) {
    if (this.muted || !this.context) return
    this.stop()
    const controller = new AbortController()
    this.abort = controller
    try {
      const buffer = await this.loadFile(this.pickFile(cue))
      if (!controller.signal.aborted) await this.play(buffer)
    } catch {
      // Заготовка только заполняет паузу: её отсутствие не должно мешать разговору.
    }
  }

  // Ошибка синтеза уходит вызывающему: он показывает, что ответ только текстом.
  async speak(text: string) {
    if (this.muted || !this.context) return
    this.stop()
    const controller = new AbortController()
    this.abort = controller
    let data: ArrayBuffer
    try {
      data = await synthesizeSpeech(text, controller.signal)
    } catch (error) {
      if (controller.signal.aborted) return
      throw error
    }
    const buffer = await this.context.decodeAudioData(data)
    if (!controller.signal.aborted) await this.play(buffer)
  }

  attachMicrophone(stream: MediaStream) {
    if (!this.context || !this.microphone) return
    this.detachMicrophone()
    this.microphoneSource = this.context.createMediaStreamSource(stream)
    // В выход не подключаем: иначе человек услышит сам себя.
    this.microphoneSource.connect(this.microphone)
  }

  detachMicrophone() {
    this.microphoneSource?.disconnect()
    this.microphoneSource = null
  }

  // Голос GPT-Live только измеряем: играет его элемент audio, см. liveSession.ts.
  attachLiveOutput(stream: MediaStream) {
    if (!this.context) return
    this.liveOutputSource?.disconnect()
    this.liveOutput ??= createAnalyser(this.context)
    this.liveOutputSource = this.context.createMediaStreamSource(stream)
    this.liveOutputSource.connect(this.liveOutput)
  }

  detachLive() {
    this.liveOutputSource?.disconnect()
    this.liveOutputSource = null
    this.detachMicrophone()
  }

  // Громкость 0..1 из того, что сейчас активно: микрофон, озвучка или оба сразу в разговоре с GPT-Live.
  level() {
    if (this.liveOutputSource && this.liveOutput) {
      return Math.max(this.measure(this.liveOutput), this.microphoneSource && this.microphone ? this.measure(this.microphone) : 0)
    }
    const analyser = this.microphoneSource ? this.microphone : this.playing ? this.output : null
    return analyser ? this.measure(analyser) : 0
  }

  private measure(analyser: AnalyserNode) {
    analyser.getByteTimeDomainData(this.samples.subarray(0, analyser.fftSize))
    let sum = 0
    for (let index = 0; index < analyser.fftSize; index++) {
      const value = (this.samples[index] - 128) / 128
      sum += value * value
    }
    return Math.min(1, Math.sqrt(sum / analyser.fftSize) * 4)
  }
}

export const voiceAudio = new VoiceAudio()
