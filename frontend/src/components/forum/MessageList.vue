<template>
  <div class="chat-area" ref="chatAreaRef">
    <div v-if="loading" class="loading-state">
      <a-spin tip="加载消息记录..." />
    </div>
    
    <div v-else class="message-list">
      <ChatBubble
        v-for="msg in messages"
        :key="msg.id"
        :speaker-name="msg.speaker_name"
        :content="msg.content"
        :timestamp="msg.timestamp"
        :is-self="isSelf(msg)"
      />
    </div>
    <div ref="bottomRef"></div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, nextTick } from 'vue'
import ChatBubble from './ChatBubble.vue'
import type { Message } from '@/stores/forum'
import { useAuthStore } from '@/stores/auth'
import { usePersonaStore } from '@/stores/persona'

const props = defineProps<{
  messages: Message[]
  loading: boolean
}>()

const authStore = useAuthStore()
const personaStore = usePersonaStore()
const bottomRef = ref<HTMLElement | null>(null)

const scrollToBottom = () => {
  bottomRef.value?.scrollIntoView({ behavior: 'smooth' })
}

watch(() => props.messages.length, () => {
  nextTick(scrollToBottom)
})

const isSelf = (msg: Message) => {
  if (msg.speaker_name === authStore.user?.username) return true
  if (msg.persona_id && personaStore.personas.find(p => p.id === msg.persona_id)) return true
  return false
}

defineExpose({ scrollToBottom })
</script>

<style scoped>
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
</style>