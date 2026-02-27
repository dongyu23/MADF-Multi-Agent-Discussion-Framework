import { ref, onUnmounted } from 'vue'
import { useForumStore, type Message } from '@/stores/forum'

export function useForumWebSocket(forumId: number) {
  const store = useForumStore()
  let ws: WebSocket | null = null
  const isConnected = ref(false)

  const connect = () => {
    if (ws) ws.close()
    
    // Use correct WS URL based on environment
    // In dev, Vite proxies /api to backend. 
    // WS needs to connect to the same host/port as the page, but with ws protocol.
    // If backend is on 8000 and frontend on 5173, and we rely on proxy:
    // ws://localhost:5173/api/v1/forums/1/ws -> Vite Proxy -> ws://127.0.0.1:8000/api/v1/forums/1/ws
    
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
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
          } else if (data.type === 'system_log' && data.data) {
             store.addSystemLog(data.data)
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
