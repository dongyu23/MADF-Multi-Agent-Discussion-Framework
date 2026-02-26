<template>
  <div class="forum-detail-container">
    <div class="forum-header">
      <div class="header-left">
        <a-button @click="$router.push('/forums')" type="text">
          <arrow-left-outlined />
        </a-button>
        <span class="forum-topic">{{ forumStore.currentForum?.topic }}</span>
        <a-tag color="processing" v-if="forumStore.currentForum?.status === 'active'">进行中</a-tag>
      </div>
      <div class="header-right">
        <a-tooltip title="查看参与者">
          <team-outlined style="font-size: 18px; cursor: pointer" />
        </a-tooltip>
      </div>
    </div>

    <!-- Moderator Controls -->
    <div class="moderator-controls" v-if="true"> <!-- Everyone for dev -->
      <span class="control-label">主持人控制：</span>
      <a-space>
        <a-button size="small" type="primary" ghost @click="handleModerator('auto')" :loading="forumStore.thinking">自动控场</a-button>
        <a-button size="small" @click="handleModerator('start')" :loading="forumStore.thinking">开场</a-button>
        <a-button size="small" @click="handleModerator('summary')" :loading="forumStore.thinking">阶段总结</a-button>
        <a-button size="small" danger @click="handleModerator('end')" :loading="forumStore.thinking">结束讨论</a-button>
      </a-space>
    </div>
    
    <div class="chat-area" ref="chatAreaRef">
      <div v-if="forumStore.loading" class="loading-state">
        <a-spin tip="加载消息记录..." />
      </div>
      
      <div v-else class="message-list">
        <div 
          v-for="msg in forumStore.messages" 
          :key="msg.id" 
          class="message-item"
          :class="{ 'message-self': isSelf(msg) }"
        >
          <div class="message-avatar">
            <a-avatar :style="{ backgroundColor: getAvatarColor(msg.speaker_name) }" size="large">
              {{ msg.speaker_name[0] }}
            </a-avatar>
          </div>
          
          <div class="message-content-wrapper">
            <div class="message-info">
              <span class="speaker-name">{{ msg.speaker_name }}</span>
              <span class="time">{{ new Date(msg.timestamp).toLocaleTimeString() }}</span>
            </div>
            
            <div class="message-bubble">
              {{ msg.content }}
            </div>
          </div>
        </div>
      </div>
      <div ref="bottomRef"></div>
    </div>
    
    <div class="input-area">
      <div class="role-selector">
        <span>当前身份：</span>
        <a-select 
          v-model:value="selectedPersonaId" 
          style="width: 160px" 
          placeholder="选择发言身份" 
          allowClear
          :options="roleOptions"
        >
        </a-select>
        
        <a-button 
          v-if="selectedPersonaId"
          type="primary"
          ghost
          size="small"
          @click="triggerAgent"
          :loading="forumStore.thinking"
          style="margin-left: 12px"
        >
          <robot-outlined /> 让 TA 思考并发言
        </a-button>
      </div>
      
      <div class="input-box">
        <a-textarea
          v-model:value="input"
          :placeholder="forumStore.thinking ? '正在思考中...' : '输入您的观点... (Ctrl + Enter 发送)'"
          :auto-size="{ minRows: 2, maxRows: 6 }"
          @keydown.ctrl.enter.prevent="handleSend"
          :disabled="forumStore.thinking"
        />
        <div class="send-btn-wrapper">
          <a-button type="primary" @click="handleSend" :disabled="!input.trim()">
            发送 <send-outlined />
          </a-button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, onUnmounted, ref, computed, nextTick, watch } from 'vue'
import { useRoute } from 'vue-router'
import { useForumStore, type Message } from '@/stores/forum'
import { usePersonaStore } from '@/stores/persona'
import { useAuthStore } from '@/stores/auth'
import { 
  ArrowLeftOutlined, 
  TeamOutlined, 
  SendOutlined,
  RobotOutlined
} from '@ant-design/icons-vue'

const route = useRoute()
const forumStore = useForumStore()
const personaStore = usePersonaStore()
const authStore = useAuthStore()

const input = ref('')
const bottomRef = ref<HTMLElement | null>(null)
const selectedPersonaId = ref<number | undefined>(undefined)
const chatAreaRef = ref<HTMLElement | null>(null)

const forumId = Number(route.params.id)

onMounted(async () => {
  await forumStore.fetchForum(forumId)
  await personaStore.fetchPersonas(authStore.user?.id) // Fetch my personas
  forumStore.connectWebSocket(forumId)
  scrollToBottom()
})

onUnmounted(() => {
  forumStore.leaveForum()
})

watch(() => forumStore.messages.length, () => {
  nextTick(() => scrollToBottom())
})

const scrollToBottom = () => {
  bottomRef.value?.scrollIntoView({ behavior: 'smooth' })
}

const myPersonas = computed(() => personaStore.personas)

const roleOptions = computed(() => {
  const options = [
    { label: `${authStore.user?.username} (本人)`, value: undefined }
  ]
  myPersonas.value.forEach(p => {
    options.push({ label: `${p.name} (智能体)`, value: p.id })
  })
  return options
})

const isSelf = (msg: Message) => {
  // Check if speaker matches auth user name
  if (msg.speaker_name === authStore.user?.username) return true
  // Check if persona belongs to me
  if (msg.persona_id && myPersonas.value.find(p => p.id === msg.persona_id)) return true
  return false
}

const getAvatarColor = (name: string) => {
  const colors = ['#f56a00', '#7265e6', '#ffbf00', '#00a2ae', '#1890ff', '#52c41a', '#eb2f96']
  let hash = 0
  for (let i = 0; i < name.length; i++) {
    hash = name.charCodeAt(i) + ((hash << 5) - hash)
  }
  const index = Math.abs(hash) % colors.length
  return colors[index]
}

const handleSend = async () => {
  if (!input.value.trim()) return
  
  let speaker = authStore.user?.username || 'User'
  if (selectedPersonaId.value) {
    const p = myPersonas.value.find(x => x.id === selectedPersonaId.value)
    if (p) speaker = p.name
  }
  
  try {
    await forumStore.sendMessage(forumId, input.value, selectedPersonaId.value || null, speaker)
    input.value = ''
    scrollToBottom()
  } catch (e) {
    // Error handled globally or show toast
  }
}

const handleModerator = async (action: string) => {
  try {
    await forumStore.triggerModerator(forumId, action)
    scrollToBottom()
  } catch (e) {
    console.error(e)
  }
}

const triggerAgent = async () => {
  if (!selectedPersonaId.value) return
  try {
    await forumStore.triggerAgent(forumId, selectedPersonaId.value)
    scrollToBottom()
  } catch (e) {
    console.error(e)
  }
}
</script>

<style scoped>
.moderator-controls {
  padding: 8px 24px;
  background: #fafafa;
  border-bottom: 1px solid #f0f0f0;
  display: flex;
  align-items: center;
  gap: 12px;
}

.control-label {
  font-size: 13px;
  font-weight: 500;
  color: #595959;
}

.forum-detail-container {
  display: flex;
  flex-direction: column;
  height: calc(100vh - 120px); /* Adjust based on layout header/footer */
  background: #fff;
  border-radius: 8px;
  overflow: hidden;
  box-shadow: 0 1px 2px rgba(0,0,0,0.05);
}

.forum-header {
  height: 60px;
  padding: 0 24px;
  border-bottom: 1px solid #f0f0f0;
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: #fff;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.forum-topic {
  font-size: 16px;
  font-weight: 500;
  color: #262626;
}

.chat-area {
  flex: 1;
  background: #f5f5f5;
  padding: 24px;
  overflow-y: auto;
}

.loading-state {
  height: 100%;
  display: flex;
  justify-content: center;
  align-items: center;
}

.message-item {
  display: flex;
  margin-bottom: 24px;
  gap: 12px;
}

.message-self {
  flex-direction: row-reverse;
}

.message-content-wrapper {
  max-width: 70%;
  display: flex;
  flex-direction: column;
}

.message-self .message-content-wrapper {
  align-items: flex-end;
}

.message-info {
  margin-bottom: 4px;
  font-size: 12px;
  color: #8c8c8c;
}

.message-self .message-info {
  text-align: right;
}

.message-info .time {
  margin-left: 8px;
  font-size: 10px;
}

.message-self .message-info .time {
  margin-left: 0;
  margin-right: 8px;
}

.message-bubble {
  padding: 12px 16px;
  border-radius: 8px;
  background: #fff;
  box-shadow: 0 1px 2px rgba(0,0,0,0.05);
  font-size: 14px;
  line-height: 1.6;
  white-space: pre-wrap;
  word-break: break-word;
}

.message-self .message-bubble {
  background: #1890ff;
  color: #fff;
  border-radius: 8px 0 8px 8px;
}

.message-item:not(.message-self) .message-bubble {
  border-radius: 0 8px 8px 8px;
}

.input-area {
  border-top: 1px solid #f0f0f0;
  padding: 16px 24px;
  background: #fff;
}

.role-selector {
  margin-bottom: 12px;
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  color: #595959;
}

.input-box {
  position: relative;
}

.send-btn-wrapper {
  position: absolute;
  bottom: 8px;
  right: 8px;
}
</style>
