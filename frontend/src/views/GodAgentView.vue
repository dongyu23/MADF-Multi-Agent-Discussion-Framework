<template>
  <div class="god-agent-container">
    <div class="chat-window" ref="chatWindowRef">
      <div v-for="(msg, index) in godStore.messages" :key="index" class="message-item" :class="msg.role">
        <div class="avatar">
          <a-avatar v-if="msg.role === 'assistant'" style="background-color: #7265e6">G</a-avatar>
          <a-avatar v-else style="background-color: #1890ff">U</a-avatar>
        </div>
        <div class="content">
          <div class="bubble">
            {{ msg.content }}
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
                <a-tag color="blue">{{ p.title }}</a-tag>
              </template>
              <p class="persona-bio">{{ p.bio }}</p>
              <div class="persona-tags">
                <a-tag v-for="t in p.theories.slice(0, 3)" :key="t">{{ t }}</a-tag>
              </div>
              <div class="actions">
                <a-button type="primary" size="small" @click="$router.push('/personas')">查看详情</a-button>
              </div>
            </a-card>
          </div>
        </div>
      </div>
      
      <div v-if="godStore.loading" class="message-item assistant">
        <div class="avatar">
          <a-avatar style="background-color: #7265e6">G</a-avatar>
        </div>
        <div class="content">
          <div class="bubble loading">
            <a-spin size="small" /> 正在构思智能体...
          </div>
        </div>
      </div>
    </div>

    <div class="input-area">
      <a-textarea
        v-model:value="input"
        placeholder="描述您想要创建的智能体（例如：一个性格暴躁但心地善良的资深程序员，信奉极简主义代码哲学...）"
        :auto-size="{ minRows: 2, maxRows: 4 }"
        @keydown.ctrl.enter.prevent="handleSend"
        :disabled="godStore.loading"
      />
      <a-button type="primary" class="send-btn" @click="handleSend" :loading="godStore.loading">
        发送
      </a-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, nextTick, watch, onMounted } from 'vue'
import { useGodStore } from '@/stores/god'

const godStore = useGodStore()
const input = ref('')
const chatWindowRef = ref<HTMLElement | null>(null)

const scrollToBottom = () => {
  nextTick(() => {
    if (chatWindowRef.value) {
      chatWindowRef.value.scrollTop = chatWindowRef.value.scrollHeight
    }
  })
}

onMounted(() => {
    if (godStore.messages.length === 0) {
        godStore.messages.push({
            role: 'assistant',
            content: '我是上帝智能体代理。请告诉我您想创建什么样的角色，我会为您生成详细的设定。',
            timestamp: Date.now()
        })
    }
    scrollToBottom()
})

watch(() => godStore.messages.length, scrollToBottom)

const handleSend = async () => {
  if (!input.value.trim() || godStore.loading) return
  
  const prompt = input.value
  input.value = ''
  
  await godStore.sendMessage(prompt)
}
</script>

<style scoped>
.god-agent-container {
  display: flex;
  flex-direction: column;
  height: calc(100vh - 120px);
  background: #fff;
  border-radius: 8px;
  overflow: hidden;
  box-shadow: 0 1px 2px rgba(0,0,0,0.05);
}

.chat-window {
  flex: 1;
  padding: 24px;
  overflow-y: auto;
  background: #f0f2f5;
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.message-item {
  display: flex;
  gap: 12px;
  max-width: 80%;
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
}

.bubble {
  padding: 12px 16px;
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
  width: 300px;
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
  padding: 16px 24px;
  background: #fff;
  border-top: 1px solid #e8e8e8;
  display: flex;
  gap: 12px;
  align-items: flex-end;
}

.send-btn {
  height: auto;
  padding: 8px 24px;
}
</style>
