import { createLiveVoiceSession } from '@/api/speech'

const ICE_GATHERING_TIMEOUT_MS = 3000
const CLOSE_TIMEOUT_MS = 1000

export type LiveEvent = { type: string; [key: string]: unknown }

interface LiveSessionHandlers {
  onEvent: (event: LiveEvent) => void
  // Соединение потеряно или сессия закрыта не нами.
  onLost: () => void
  onOutputStream: (stream: MediaStream) => void
  onInputStream: (stream: MediaStream) => void
}

function iceGathered(connection: RTCPeerConnection) {
  return new Promise<void>((resolve) => {
    if (connection.iceGatheringState === 'complete') return resolve()
    const timer = setTimeout(resolve, ICE_GATHERING_TIMEOUT_MS)
    connection.addEventListener('icegatheringstatechange', () => {
      if (connection.iceGatheringState !== 'complete') return
      clearTimeout(timer)
      resolve()
    })
  })
}

// Соединение WebRTC с GPT-Live: звук идёт дорожками, события — каналом данных.
export class LiveSession {
  private connection: RTCPeerConnection | null = null
  private channel: RTCDataChannel | null = null
  private microphone: MediaStream | null = null
  private player: HTMLAudioElement | null = null
  private closing = false
  private eventNumber = 0
  private handlers: LiveSessionHandlers
  private wantMicrophone = true
  private wantVolume = 1

  constructor(handlers: LiveSessionHandlers) {
    this.handlers = handlers
  }

  async start() {
    this.microphone = await navigator.mediaDevices.getUserMedia({ audio: { echoCancellation: true, noiseSuppression: true } })
    if (this.closing) return this.releaseMicrophone()
    this.microphoneEnabled = this.wantMicrophone
    this.handlers.onInputStream(this.microphone)

    const connection = new RTCPeerConnection()
    this.connection = connection
    for (const track of this.microphone.getAudioTracks()) connection.addTrack(track, this.microphone)
    connection.ontrack = ({ streams: [stream] }) => {
      // Звук играет обычный элемент, а не Web Audio: иначе браузер не вычтет его из микрофона и модель услышит себя.
      const player = new Audio()
      player.srcObject = stream
      player.volume = this.wantVolume
      this.player = player
      void player.play().catch(() => undefined)
      this.handlers.onOutputStream(stream)
    }
    connection.onconnectionstatechange = () => {
      if (!this.closing && ['failed', 'closed'].includes(connection.connectionState)) this.handlers.onLost()
    }

    const channel = connection.createDataChannel('oai-events')
    this.channel = channel
    channel.onmessage = ({ data }) => this.receive(data)
    channel.onclose = () => {
      if (!this.closing) this.handlers.onLost()
    }

    await connection.setLocalDescription(await connection.createOffer())
    await iceGathered(connection)
    // Созданная сессия оплачивается: если экран уже закрыт, не создаём её.
    if (this.closing) return
    const answer = await createLiveVoiceSession(connection.localDescription?.sdp ?? '')
    if (this.closing) return
    await connection.setRemoteDescription({ type: 'answer', sdp: answer })
  }

  private receive(data: unknown) {
    if (typeof data !== 'string') return
    let event: LiveEvent
    try {
      event = JSON.parse(data) as LiveEvent
    } catch {
      return
    }
    this.handlers.onEvent(event)
  }

  send(event: LiveEvent) {
    if (this.channel?.readyState !== 'open') return
    this.channel.send(JSON.stringify({ event_id: `client-${++this.eventNumber}`, ...event }))
  }

  // Выключенная дорожка гарантирует на стороне клиента, что речь не уйдёт модели, пока открыта карточка.
  set microphoneEnabled(enabled: boolean) {
    this.wantMicrophone = enabled
    for (const track of this.microphone?.getAudioTracks() ?? []) track.enabled = enabled
  }

  set volume(value: number) {
    this.wantVolume = value
    if (this.player) this.player.volume = value
  }

  private releaseMicrophone() {
    for (const track of this.microphone?.getTracks() ?? []) track.stop()
    this.microphone = null
  }

  // Секунды оплачиваются, поэтому сессию закрываем явно. Микрофон выключаем сразу, не дожидаясь ответа.
  close() {
    if (this.closing) return
    this.closing = true
    this.releaseMicrophone()
    if (this.player) {
      this.player.pause()
      this.player.srcObject = null
    }
    const connection = this.connection
    if (!connection) return
    const channel = this.channel
    if (channel?.readyState !== 'open') {
      connection.close()
      return
    }
    const finish = () => connection.close()
    channel.addEventListener('message', ({ data }) => {
      if (typeof data === 'string' && data.includes('"session.closed"')) finish()
    })
    setTimeout(finish, CLOSE_TIMEOUT_MS)
    this.send({ type: 'session.close' })
  }
}
