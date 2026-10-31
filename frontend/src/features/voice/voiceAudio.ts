import { synthesizeSpeech } from '@/api/speech'

// Заготовки лежат в public/voice, их создаёт backend/app/generate_voice_cues.py: первый звук не должен ждать агента.
// У заполняющих фраз несколько вариантов, иначе на третьем ходе слышно, что это запись.
const CUES = {
  greet: ['greet'],
  wait: ['wait-1', 'wait-2', 'wait-3', 'wait-4', 'wait-5'],
  more: ['more-1', 'more-2', 'more-3'],
  form: ['form'],
  confirm: ['confirm'],
} as const
export type VoiceCue = keyof typeof CUES
const CUE_FILES: string[] = Object.values(CUES).flat()

function createAnalyser(context: AudioContext) {
  const analyser = context.createAnalyser()
  analyser.fftSize = 512
  analyser.smoothingTimeConstant = 0.5
  return analyser
}

class VoiceAudio {
  private context: AudioContext | null = null
  private output: AnalyserNode | null = null
  private microphone: AnalyserNode | null = null
  private microphoneSource: MediaStreamAudioSourceNode | null = null
  private playing: AudioBufferSourceNode | null = null
  private abort: AbortController | null = null
  private cues = new Map<string, Promise<AudioBuffer>>()
  private lastFile = new Map<VoiceCue, string>()
  private samples = new Uint8Array(512)
  muted = false

  // iOS разрешает запустить звук только внутри обработчика нажатия, поэтому вызываем его при входе в режим.
  unlock() {
    if (!this.context) {
      this.context = new AudioContext()
      this.output = createAnalyser(this.context)
      this.output.connect(this.context.destination)
      this.microphone = createAnalyser(this.context)
      for (const file of CUE_FILES) this.loadFile(file)
    }
    void this.context.resume()
  }

  private pickFile(cue: VoiceCue) {
    const files: readonly string[] = CUES[cue]
    const fresh = files.filter((file) => file !== this.lastFile.get(cue))
    const file = fresh[Math.floor(Math.random() * fresh.length)] ?? files[0]
    this.lastFile.set(cue, file)
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

  // Громкость 0..1 из того, что сейчас активно: микрофон или озвучка.
  level() {
    const analyser = this.microphoneSource ? this.microphone : this.playing ? this.output : null
    if (!analyser) return 0
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
