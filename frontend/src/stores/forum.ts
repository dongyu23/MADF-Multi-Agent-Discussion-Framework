import { defineStore } from 'pinia'
import request from '@/utils/request'
import { message } from 'ant-design-vue'

export interface Message {
  id: number
  forum_id: number
  persona_id: number
  speaker_name: string
  content: string
  timestamp: string
}

export interface Forum {
  id: number
  topic: string
  creator_id: number
  status: string
  start_time: string
  summary_history: string[]
}

export const useForumStore = defineStore('forum', {
  state: () => ({
    forums: [] as Forum[],
    currentForum: null as Forum | null,
    messages: [] as Message[],
    ws: null as WebSocket | null,
    loading: false,
    thinking: false
  }),
  actions: {
    async fetchForums() {
      this.loading = true
      try {
        const res = await request.get('/forums/')
        this.forums = res.data
      } catch (error) {
        console.error('Failed to fetch forums:', error)
        // Global interceptor handles the error message, but we ensure state is clean
        this.forums = []
      } finally {
        this.loading = false
      }
    },
    async fetchForum(id: number) {
        this.loading = true
        this.currentForum = null
        try {
            const res = await request.get(`/forums/${id}`)
            this.currentForum = res.data
            await this.fetchMessages(id)
        } catch (error) {
            console.error(`Failed to fetch forum ${id}:`, error)
        } finally {
            this.loading = false
        }
    },
    async fetchMessages(forumId: number) {
      try {
        const res = await request.get(`/forums/${forumId}/messages`)
        this.messages = res.data
      } catch (error) {
        console.error(`Failed to fetch messages for forum ${forumId}:`, error)
        this.messages = []
      }
    },
    async createForum(topic: string, participantIds: number[]) {
      this.loading = true
      try {
        await request.post('/forums/', {
          topic,
          participant_ids: participantIds
        })
        message.success('论坛创建成功')
        await this.fetchForums()
      } catch (error) {
        console.error('Failed to create forum:', error)
      } finally {
        this.loading = false
      }
    },
    connectWebSocket(forumId: number) {
      if (this.ws) {
        this.ws.close()
      }
      
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
      const host = window.location.host
      const wsUrl = `${protocol}//${host}/api/v1/forums/${forumId}/ws`
      
      console.log('Connecting to WS:', wsUrl)
      
      try {
        this.ws = new WebSocket(wsUrl)
        
        this.ws.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data)
            if (data.type === 'new_message' && data.data) {
              const exists = this.messages.find(m => m.id === data.data.id)
              if (!exists) {
                this.messages.push(data.data)
              }
            }
          } catch (e) {
            console.error('WS Message Parse Error', e)
          }
        }
        
        this.ws.onopen = () => {
          console.log('Connected to Forum WS')
        }
        
        this.ws.onerror = (e) => {
          console.error('WS Error', e)
        }
        
        this.ws.onclose = () => {
          console.log('WS Closed')
        }
      } catch (e) {
        console.error('WS Connection Failed', e)
      }
    },
    async sendMessage(forumId: number, content: string, personaId?: number | null, speakerName?: string) {
      try {
        await request.post(`/forums/${forumId}/messages`, {
          forum_id: forumId,
          content,
          persona_id: personaId, 
          speaker_name: speakerName || 'User',
          turn_count: this.messages.length + 1
        })
      } catch (error) {
        console.error('Failed to send message:', error)
        throw error // Re-throw to let UI handle if needed
      }
    },
    async triggerAgent(forumId: number, personaId?: number) {
      if (this.thinking) return
      this.thinking = true
      try {
        const res = await request.post(`/forums/${forumId}/trigger_agent`, {
          persona_id: personaId
        })
        // Optimistically push if returned, though WS should handle it
        if (res.data) {
            const exists = this.messages.find(m => m.id === res.data.id)
            if (!exists) this.messages.push(res.data)
        }
      } catch (error) {
        console.error('Trigger Agent Failed:', error)
      } finally {
        this.thinking = false
      }
    },
    async triggerModerator(forumId: number, action: string = 'auto') {
      if (this.thinking) return
      this.thinking = true
      try {
        const res = await request.post(`/forums/${forumId}/trigger_moderator`, {
          action
        })
        if (res.data) {
             const exists = this.messages.find(m => m.id === res.data.id)
             if (!exists) this.messages.push(res.data)
        }
      } catch (error) {
        console.error('Trigger Moderator Failed:', error)
      } finally {
        this.thinking = false
      }
    },
    leaveForum() {
      if (this.ws) {
        this.ws.close()
        this.ws = null
      }
      this.messages = []
      this.currentForum = null
      this.thinking = false
      this.loading = false
    }
  }
})
