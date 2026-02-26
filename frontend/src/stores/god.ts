import { defineStore } from 'pinia'
import request from '@/utils/request'
import { message } from 'ant-design-vue'

interface Persona {
    id: number
    name: string
    title: string
    bio: string
    theories: string[]
    stance: string
    system_prompt: string
    is_public: boolean
}

interface ChatMessage {
    role: 'user' | 'assistant'
    content: string
    timestamp: number
    personas?: Persona[] // If assistant generated personas
}

export const useGodStore = defineStore('god', {
    state: () => ({
        messages: [] as ChatMessage[],
        loading: false
    }),
    actions: {
        async sendMessage(prompt: string) {
            // Add user message
            this.messages.push({
                role: 'user',
                content: prompt,
                timestamp: Date.now()
            })

            this.loading = true
            try {
                // Call backend
                // The API expects { prompt: string, n: int }
                const res = await request.post('/god/generate', {
                    prompt,
                    n: 1 
                })

                // The backend returns List[PersonaResponse]
                const personas = res.data

                // Add assistant response
                this.messages.push({
                    role: 'assistant',
                    content: `已为您生成 ${personas.length} 位智能体角色。`,
                    timestamp: Date.now(),
                    personas: personas
                })
                
                message.success('生成成功')
            } catch (error) {
                console.error('God generation failed:', error)
                this.messages.push({
                    role: 'assistant',
                    content: '抱歉，生成失败，请稍后重试。',
                    timestamp: Date.now()
                })
            } finally {
                this.loading = false
            }
        },
        clearHistory() {
            this.messages = []
        }
    }
})
