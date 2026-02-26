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
    loading: false,
    thinking: false
  }),
  actions: {
    updateStreamingMessage(chunk: { speaker_name: string, content: string, persona_id: number | null, timestamp: number }) {
        const lastMsg = this.messages[this.messages.length - 1]
        
        // Use a composite key or just check speaker + streaming status
        if (lastMsg && lastMsg.speaker_name === chunk.speaker_name && (lastMsg as any).isStreaming) {
            lastMsg.content += chunk.content
        } else {
            const newMsg: Message = {
                id: Date.now(), // Temp ID
                forum_id: this.currentForum?.id || 0,
                persona_id: chunk.persona_id || 0,
                speaker_name: chunk.speaker_name,
                content: chunk.content,
                timestamp: new Date(chunk.timestamp * 1000).toISOString(),
            }
            ;(newMsg as any).isStreaming = true
            this.messages.push(newMsg)
        }
    },
    addMessage(msg: Message) {
        // When the full message arrives (type: 'new_message'), replace the streaming one
        // Match by speaker name AND ensure we are replacing a streaming message
        const streamingMsgIndex = this.messages.findIndex(m => m.speaker_name === msg.speaker_name && (m as any).isStreaming)
        
        if (streamingMsgIndex !== -1) {
            // Replace streaming message with the final one
            // Use the backend timestamp from msg, which is now correctly generated
            this.messages.splice(streamingMsgIndex, 1, msg)
        } else {
             const exists = this.messages.find(m => m.id === msg.id)
             if (!exists) {
                 this.messages.push(msg)
             }
        }
    },
    async fetchForums() {
      this.loading = true
      try {
        const res = await request.get('/forums/')
        this.forums = res.data
      } catch (error) {
        console.error('Failed to fetch forums:', error)
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
    async createForum(topic: string, participantIds: number[], duration: number) {
      this.loading = true
      try {
        const res = await request.post('/forums/', {
          topic,
          participant_ids: participantIds,
          duration_minutes: duration
        })
        message.success('论坛创建成功')
        await this.fetchForums()
        return res.data
      } catch (error) {
        console.error('Failed to create forum:', error)
        throw error
      } finally {
        this.loading = false
      }
    },
    async startForum(id: number) {
      try {
        await request.post(`/forums/${id}/start`)
        message.success('论坛已开始')
        if (this.currentForum && this.currentForum.id === id) {
            this.currentForum.status = 'running'
        }
      } catch (error) {
        console.error('Failed to start forum:', error)
        message.error('启动失败')
      }
    },
    async deleteForum(id: number) {
      try {
        await request.delete(`/forums/${id}`)
        message.success('论坛已删除')
        if (this.currentForum && this.currentForum.id === id) {
            this.currentForum = null
        }
        this.forums = this.forums.filter(f => f.id !== id)
      } catch (error) {
        console.error('Failed to delete forum:', error)
        message.error('删除失败')
      }
    },
    leaveForum() {
      this.messages = []
      this.currentForum = null
      this.thinking = false
      this.loading = false
    }
  }
})
