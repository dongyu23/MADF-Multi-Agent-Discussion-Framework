import { defineStore } from 'pinia'
import request from '@/utils/request'

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
}

export const useForumStore = defineStore('forum', {
  state: () => ({
    forums: [] as Forum[],
    currentForum: null as Forum | null,
    messages: [] as Message[],
    ws: null as WebSocket | null,
    loading: false
  }),
  actions: {
    async fetchForums() {
      this.loading = true
      try {
        const res = await request.get('/forums/')
        this.forums = res.data
      } finally {
        this.loading = false
      }
    },
    async fetchForum(id: number) {
        this.loading = true
        try {
            const res = await request.get(`/forums/${id}`)
            this.currentForum = res.data
            await this.fetchMessages(id)
        } finally {
            this.loading = false
        }
    },
    async fetchMessages(forumId: number) {
      const res = await request.get(`/forums/${forumId}/messages`)
      this.messages = res.data
    },
    async createForum(topic: string, participantIds: number[]) {
      await request.post('/forums/', {
        topic,
        participant_ids: participantIds
      })
      await this.fetchForums()
    },
    connectWebSocket(forumId: number) {
      if (this.ws) {
        this.ws.close()
      }
      
      // Handle WS protocol based on current location
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
      const host = window.location.host
      
      // Vite proxy forwards /api to backend, including WS upgrade
      const wsUrl = `${protocol}//${host}/api/v1/forums/${forumId}/ws`
      
      console.log('Connecting to WS:', wsUrl)
      
      this.ws = new WebSocket(wsUrl)
      
      this.ws.onmessage = (event) => {
        const data = JSON.parse(event.data)
        // Check if data is wrapper or direct message
        // Backend broadcasts: { type: "new_message", data: { ... } }
        if (data.type === 'new_message') {
          // Check if message already exists (optimistic update or double send)
          const exists = this.messages.find(m => m.id === data.data.id)
          if (!exists) {
            this.messages.push(data.data)
          }
        }
      }
      
      this.ws.onopen = () => {
        console.log('Connected to Forum WS')
      }
      
      this.ws.onerror = (e) => {
        console.error('WS Error', e)
        // message.error('Connection error') // Don't spam error
      }
      
      this.ws.onclose = () => {
        console.log('WS Closed')
      }
    },
    async sendMessage(forumId: number, content: string, personaId?: number | null, speakerName?: string) {
      await request.post(`/forums/${forumId}/messages`, {
        forum_id: forumId,
        content,
        persona_id: personaId, 
        speaker_name: speakerName || 'User',
        turn_count: this.messages.length + 1
      })
    },
    leaveForum() {
      if (this.ws) {
        this.ws.close()
        this.ws = null
      }
      this.messages = []
      this.currentForum = null
    }
  }
})
