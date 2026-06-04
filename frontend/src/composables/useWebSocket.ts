import { ref, onUnmounted } from 'vue'
import { WS_URL } from '../api/client'

type MessageHandler = (data: unknown) => void

export function useWebSocket(onMessage: MessageHandler) {
  const connected = ref(false)
  let ws: WebSocket | null = null
  let pingTimer: ReturnType<typeof setInterval> | null = null
  let reconnectTimer: ReturnType<typeof setTimeout> | null = null

  function connect() {
    ws = new WebSocket(WS_URL)

    ws.onopen = () => {
      connected.value = true
      pingTimer = setInterval(() => ws?.send('ping'), 20_000)
    }

    ws.onmessage = (event) => {
      try {
        const payload = JSON.parse(event.data)
        if (payload.type !== 'pong') onMessage(payload)
      } catch {
        // ignore malformed frames
      }
    }

    ws.onclose = () => {
      connected.value = false
      if (pingTimer) clearInterval(pingTimer)
      // Auto-reconnect after 3s
      reconnectTimer = setTimeout(connect, 3_000)
    }

    ws.onerror = () => {
      ws?.close()
    }
  }

  connect()

  onUnmounted(() => {
    if (pingTimer) clearInterval(pingTimer)
    if (reconnectTimer) clearTimeout(reconnectTimer)
    ws?.close()
  })

  return { connected }
}
