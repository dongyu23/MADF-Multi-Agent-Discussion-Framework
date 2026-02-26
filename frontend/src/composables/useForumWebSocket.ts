import { ref, onUnmounted } from 'vue'
import { useForumStore, type Message } from '@/stores/forum'

export function useForumWebSocket(forumId: number) {
  const store = useForumStore()
  let ws: WebSocket | null = null
  const isConnected = ref(false)

  const connect = () => {
    if (ws) ws.close()
    
    // Determine protocol
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    // In dev, vite proxy might handle /api, but WS often needs direct port or proxy config.
    // Assuming backend is at same host/port as API request base or relative.
    // If using proxy, window.location.host is frontend host (localhost:5173).
    // Vite proxy forwards /api. So ws://localhost:5173/api/v1... should work if configured.
    // Safest is to use the same logic as before or env var.
    const host = window.location.host
    const wsUrl = `${protocol}//${host}/api/v1/forums/${forumId}/ws`
    
    console.log('Connecting to WS:', wsUrl)
    
    try {
      ws = new WebSocket(wsUrl)
      
      ws.onopen = () => {
        console.log('WS Connected')
        isConnected.value = true
      }
      
      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data)
          if (data.type === 'new_message' && data.data) {
             store.addMessage(data.data)
          } else if (data.type === 'message_chunk' && data.data) {
             store.updateStreamingMessage(data.data)
          }
        } catch (e) {
          console.error('WS Parse Error', e)
        }
      }
      
      ws.onclose = () => {
        console.log('WS Closed')
        isConnected.value = false
      }
      
      ws.onerror = (e) => {
        console.error('WS Error', e)
      }
    } catch (e) {
      console.error('WS Connection Failed', e)
    }
  }

  const disconnect = () => {
    if (ws) {
      ws.close()
      ws = null
      isConnected.value = false
    }
  }

  onUnmounted(() => {
    disconnect()
  })

  return {
    connect,
    disconnect,
    isConnected
  }
}
