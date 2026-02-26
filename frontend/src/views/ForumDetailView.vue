<template>
  <div class="forum-detail-container">
    <div class="forum-header">
      <div class="header-left">
        <a-button @click="$router.push('/forums')" type="text">
          <arrow-left-outlined />
        </a-button>
        <span class="forum-topic">{{ forumStore.currentForum?.topic }}</span>
        <a-tag color="warning" v-if="forumStore.currentForum?.status === 'pending'">未开始</a-tag>
        <a-tag color="processing" v-if="forumStore.currentForum?.status === 'running'">进行中</a-tag>
        <a-tag color="default" v-if="forumStore.currentForum?.status === 'closed' || forumStore.currentForum?.status === 'finished'">已结束</a-tag>
      </div>
      <div class="header-right">
        <a-space>
             <a-button 
                v-if="forumStore.currentForum?.status === 'pending'" 
                type="primary" 
                @click="handleStart"
                :loading="starting"
            >
                <play-circle-outlined /> 开始论坛
            </a-button>
            <a-popconfirm title="确定删除该论坛吗？" @confirm="handleDelete">
                <a-button danger>
                    <delete-outlined /> 删除
                </a-button>
            </a-popconfirm>
            <a-tooltip title="查看参与者">
              <team-outlined style="font-size: 18px; cursor: pointer" />
            </a-tooltip>
        </a-space>
      </div>
    </div>
    
    <MessageList 
      :messages="forumStore.messages" 
      :loading="forumStore.loading" 
    />
    
    <ForumTimer 
      v-if="forumStore.currentForum"
      :start-time="forumStore.currentForum.start_time"
      :duration-minutes="forumStore.currentForum.duration_minutes || 30" 
      :status="forumStore.currentForum.status"
    />
  </div>
</template>

<script setup lang="ts">
import { onMounted, onUnmounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useForumStore } from '@/stores/forum'
import { usePersonaStore } from '@/stores/persona'
import { useAuthStore } from '@/stores/auth'
import { useForumWebSocket } from '@/composables/useForumWebSocket'
import MessageList from '@/components/forum/MessageList.vue'
import { 
  ArrowLeftOutlined, 
  TeamOutlined, 
  DeleteOutlined,
  PlayCircleOutlined
} from '@ant-design/icons-vue'

const route = useRoute()
const forumStore = useForumStore()
const personaStore = usePersonaStore()
const authStore = useAuthStore()
const router = useRouter()

const starting = ref(false)
const forumId = Number(route.params.id)
const { connect, disconnect } = useForumWebSocket(forumId)

onMounted(async () => {
  await forumStore.fetchForum(forumId)
  // Fetch my personas not strictly needed for display but good for context
  await personaStore.fetchPersonas(authStore.user?.id) 
  connect()
})

onUnmounted(() => {
  disconnect()
  forumStore.leaveForum()
})

const handleDelete = async () => {
    await forumStore.deleteForum(forumId)
    router.push('/forums')
}

const handleStart = async () => {
    starting.value = true
    try {
        await forumStore.startForum(forumId)
    } finally {
        starting.value = false
    }
}
</script>

<style scoped>
.forum-detail-container {
  display: flex;
  flex-direction: column;
  height: 100vh; /* Occupy full viewport height */
  background: #fff;
  overflow: hidden;
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
</style>