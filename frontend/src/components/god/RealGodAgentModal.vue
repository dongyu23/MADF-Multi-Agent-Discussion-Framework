<template>
  <a-modal
    v-model:open="visible"
    title="上帝模式：创造真实智能体 (联网版)"
    :width="900"
    :footer="null"
    @cancel="handleCancel"
    class="god-agent-modal"
  >
    <div class="god-agent-container">
      <div class="chat-window" ref="chatWindowRef">
        <div v-for="(msg, index) in messages" :key="index" class="message-item" :class="msg.role">
          <div class="avatar">
            <a-avatar v-if="msg.role === 'assistant'" style="background-color: #faad14">R</a-avatar>
            <a-avatar v-else style="background-color: #1890ff">U</a-avatar>
          </div>
          <div class="content">
            <!-- Normal Text Content -->
            <div v-if="msg.content" class="bubble">
              {{ msg.content }}
            </div>

            <!-- ReAct Log (Thoughts, Actions) -->
            <div v-if="msg.logs && msg.logs.length > 0" class="react-logs">
              <div v-for="(log, li) in msg.logs" :key="li" class="log-entry" :class="log.type">
                <span class="log-icon" v-if="log.type === 'thought'">🤔</span>
                <span class="log-icon" v-else-if="log.type === 'action'">🎬</span>
                <span class="log-icon" v-else-if="log.type === 'observation'">👀</span>
                <span class="log-icon" v-else-if="log.type === 'error'">❌</span>
                <span class="log-text">{{ log.content }}</span>
              </div>
            </div>
            
            <!-- Generated Personas Preview -->
            <div v-if="msg.personas && msg.personas.length > 0" class="persona-preview">
              <a-card 
                v-for="p in msg.personas" 
                :key="p.id" 
                class="persona-card"
                size="small"
                :title="p.name"
              >
                <template #extra>
                  <a-tag color="orange">{{ p.title }}</a-tag>
                </template>
                <p class="persona-bio">{{ p.bio }}</p>
                <div class="persona-tags">
                  <a-tag v-for="t in p.theories.slice(0, 3)" :key="t">{{ t }}</a-tag>
                </div>
                <div class="actions">
                  <a-button type="primary" size="small" @click="handleViewPersona">查看详情</a-button>
                </div>
              </a-card>
            </div>
          </div>
        </div>
        
        <div v-if="loading" class="message-item assistant">
          <div class="avatar">
            <a-avatar style="background-color: #faad14">R</a-avatar>
          </div>
          <div class="content">
            <div class="bubble loading">
              <a-spin size="small" /> 正在联网搜索并构思...
            </div>
          </div>
        </div>
      </div>

      <div class="input-area">
        <a-textarea
          v-model:value="input"
          placeholder="描述您想要创建的真实人物或基于现实的角色（例如：寻找一位精通量子力学的现代物理学家...）"
          :auto-size="{ minRows: 2, maxRows: 4 }"
          @keydown.ctrl.enter.prevent="handleSend"
          :disabled="loading"
        />
        <a-button type="primary" class="send-btn" @click="handleSend" :loading="loading">
          发送
        </a-button>
      </div>
    </div>
  </a-modal>
</template>

<script setup lang="ts">
import { ref, nextTick, watch, computed } from 'vue'
import { useRouter } from 'vue-router'
import { message } from 'ant-design-vue'
import { usePersonaStore } from '@/stores/persona'

interface LogEntry {
  type: 'thought' | 'action' | 'observation' | 'error'
  content: string
}

interface ChatMessage {
  role: 'user' | 'assistant'
  content?: string
  logs?: LogEntry[]
  personas?: any[]
  timestamp: number
}

const props = defineProps<{
  open: boolean
}>()

const emit = defineEmits(['update:open'])

const router = useRouter()
const personaStore = usePersonaStore()
const input = ref('')
const chatWindowRef = ref<HTMLElement | null>(null)
const messages = ref<ChatMessage[]>([])
const loading = ref(false)

const visible = computed({
  get: () => props.open,
  set: (val) => emit('update:open', val)
})

const scrollToBottom = () => {
  nextTick(() => {
    if (chatWindowRef.value) {
      chatWindowRef.value.scrollTop = chatWindowRef.value.scrollHeight
    }
  })
}

watch(() => props.open, (val) => {
  if (val) {
    if (messages.value.length === 0) {
      messages.value.push({
        role: 'assistant',
        content: '我是联网版上帝智能体。我可以搜索互联网信息，为您创造基于真实背景的深度角色。',
        timestamp: Date.now()
      })
    }
    scrollToBottom()
  }
})

watch(() => messages.value.length, scrollToBottom)
watch(() => messages.value[messages.value.length - 1]?.logs?.length, scrollToBottom)

const handleSend = async () => {
  if (!input.value.trim() || loading.value) return
  
  const prompt = input.value
  input.value = ''
  
  // Add user message
  messages.value.push({
    role: 'user',
    content: prompt,
    timestamp: Date.now()
  })
  
  loading.value = true
  
  // Prepare assistant message container
  const assistantMsg = ref<ChatMessage>({
    role: 'assistant',
    content: '', // Start empty, maybe fill with "Thinking..."
    logs: [],
    timestamp: Date.now()
  })
  messages.value.push(assistantMsg.value)
  
  try {
    // Fetch SSE
    const response = await fetch('/api/v1/god/generate_real', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        // Add auth token if needed. Assuming cookie auth or header injection by proxy?
        // The project uses `request.ts` (axios) which likely adds headers.
        // For fetch, we need to add token manually if it's in localStorage or similar.
        // Let's check `auth` store or `request.ts`.
        // Usually `Authorization: Bearer ...`
        'Authorization': `Bearer ${localStorage.getItem('token') || ''}`
      },
      body: JSON.stringify({ prompt, n: 1 })
    })

    if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
    }

    const reader = response.body?.getReader()
    const decoder = new TextDecoder()
    
    if (!reader) throw new Error('No reader')

    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      
      const chunk = decoder.decode(value, { stream: true })
      // SSE format: data: {...}\n\n
      const lines = chunk.split('\n\n')
      
      for (const line of lines) {
        if (line.startsWith('data: ')) {
          try {
            const jsonStr = line.slice(6)
            if (!jsonStr.trim()) continue
            
            const event = JSON.parse(jsonStr)
            
            if (event.type === 'thought') {
                assistantMsg.value.logs?.push({ type: 'thought', content: event.content })
            } else if (event.type === 'action') {
                assistantMsg.value.logs?.push({ type: 'action', content: event.content })
            } else if (event.type === 'observation') {
                assistantMsg.value.logs?.push({ type: 'observation', content: event.content })
            } else if (event.type === 'result') {
                if (!assistantMsg.value.personas) assistantMsg.value.personas = []
                // Handle both single object and list results
                if (Array.isArray(event.content)) {
                    assistantMsg.value.personas.push(...event.content)
                } else {
                    assistantMsg.value.personas.push(event.content)
                }
                assistantMsg.value.content = `已为您生成 ${assistantMsg.value.personas.length} 位真实背景角色。`
            } else if (event.type === 'error') {
                assistantMsg.value.logs?.push({ type: 'error', content: event.content })
                message.error('生成过程中发生错误')
            }
            
            scrollToBottom()
          } catch (e) {
            console.error('JSON parse error', e)
          }
        }
      }
    }

  } catch (error: any) {
    assistantMsg.value.logs?.push({ type: 'error', content: error.message || '网络请求失败' })
  } finally {
    loading.value = false
  }
}

const handleCancel = () => {
  visible.value = false
}

const handleViewPersona = () => {
  visible.value = false
  personaStore.fetchPersonas()
  router.push('/personas')
}
</script>

<style scoped>
.god-agent-container {
  display: flex;
  flex-direction: column;
  height: 600px;
}

.chat-window {
  flex: 1;
  padding: 16px;
  overflow-y: auto;
  background: #f0f2f5;
  display: flex;
  flex-direction: column;
  gap: 16px;
  border-radius: 4px;
}

.message-item {
  display: flex;
  gap: 12px;
  max-width: 95%;
}

.message-item.user {
  align-self: flex-end;
  flex-direction: row-reverse;
}

.message-item.assistant {
  align-self: flex-start;
}

.content {
  display: flex;
  flex-direction: column;
  gap: 8px;
  width: 100%;
}

.bubble {
  padding: 10px 14px;
  border-radius: 8px;
  background: #fff;
  box-shadow: 0 1px 2px rgba(0,0,0,0.05);
  font-size: 14px;
  line-height: 1.6;
  white-space: pre-wrap;
}

.message-item.user .bubble {
  background: #1890ff;
  color: #fff;
  border-radius: 8px 0 8px 8px;
}

.message-item.assistant .bubble {
  border-radius: 0 8px 8px 8px;
}

.react-logs {
  background: #2d2d2d;
  color: #ccc;
  padding: 12px;
  border-radius: 8px;
  font-family: monospace;
  font-size: 12px;
  display: flex;
  flex-direction: column;
  gap: 6px;
  max-height: 300px;
  overflow-y: auto;
}

.log-entry {
  display: flex;
  gap: 6px;
  word-break: break-all;
}

.log-icon {
  flex-shrink: 0;
}

.log-entry.thought { color: #87d068; }
.log-entry.action { color: #1890ff; font-weight: bold; }
.log-entry.observation { color: #faad14; font-style: italic; }
.log-entry.error { color: #ff4d4f; }

.loading {
  font-style: italic;
  color: #8c8c8c;
}

.persona-preview {
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin-top: 8px;
}

.persona-card {
  width: 100%;
}

.persona-bio {
  font-size: 12px;
  color: #666;
  margin: 8px 0;
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.persona-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  margin-bottom: 8px;
}

.input-area {
  padding: 16px 0 0 0;
  background: #fff;
  display: flex;
  gap: 12px;
  align-items: flex-end;
}

.send-btn {
  height: auto;
  padding: 8px 24px;
}
</style>
