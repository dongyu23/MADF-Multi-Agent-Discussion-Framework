<template>
  <div class="message-item" :class="{ 'message-self': isSelf, 'message-moderator': isModerator }">
    <div class="message-avatar">
      <a-avatar :style="{ backgroundColor: avatarColor }" size="large">
        <template #icon v-if="isModerator">
          <user-outlined />
        </template>
        <span v-if="!isModerator">
          {{ speakerName[0] }}
        </span>
      </a-avatar>
    </div>
    
    <div class="message-content-wrapper">
      <div class="message-info">
        <span class="speaker-name">
          {{ speakerName }}
          <a-tag v-if="isModerator" color="gold" style="margin-left: 4px; font-size: 10px; line-height: 14px; height: 16px; padding: 0 4px;">主持人</a-tag>
        </span>
        <span class="time">{{ formatTime(timestamp) }}</span>
      </div>
      
      <div class="message-bubble">
        <div v-if="isStreaming" class="streaming-indicator">
          <loading-outlined />
        </div>
        {{ content }}
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { LoadingOutlined, UserOutlined } from '@ant-design/icons-vue'

const props = defineProps<{
  speakerName: string
  content: string
  timestamp: string
  isSelf: boolean
  isStreaming?: boolean
  moderatorId?: number | null
}>()

const isModerator = computed(() => {
  return !!props.moderatorId || props.speakerName.includes('主持人')
})

const isStreaming = computed(() => {
    return props.isStreaming || false
})

const formatTime = (isoString: string) => {
    if (!isoString) return ''
    const date = new Date(isoString)
    return date.toLocaleTimeString()
}

const avatarColor = computed(() => {
  if (isModerator.value) return '#faad14' // Gold for moderator
  const colors = ['#f56a00', '#7265e6', '#ffbf00', '#00a2ae', '#1890ff', '#52c41a', '#eb2f96']
  let hash = 0
  for (let i = 0; i < props.speakerName.length; i++) {
    hash = props.speakerName.charCodeAt(i) + ((hash << 5) - hash)
  }
  const index = Math.abs(hash) % colors.length
  return colors[index]
})
</script>

<style scoped>
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
  display: flex;
  align-items: center;
}

.message-self .message-info {
  text-align: right;
  flex-direction: row-reverse;
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

/* Moderator specific styles */
.message-moderator .message-bubble {
  background: #fffbe6; /* Light gold background */
  border: 1px solid #ffe58f;
}
</style>