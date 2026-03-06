<template>
  <div class="participant-list-container">
    <a-list item-layout="horizontal" :data-source="participants">
      <template #renderItem="{ item }">
        <a-list-item>
          <a-list-item-meta
            :description="item.persona.bio || '暂无简介'"
          >
            <template #title>
              <span class="participant-name">{{ item.persona.name }}</span>
              <a-tag v-if="item.persona.title" color="blue">{{ item.persona.title }}</a-tag>
              <a-tag v-if="item.persona.stance" :color="getStanceColor(item.persona.stance)">
                {{ item.persona.stance }}
              </a-tag>
            </template>
            <template #avatar>
              <a-avatar :style="{ backgroundColor: getAvatarColor(item.persona.name) }" size="large">
                {{ item.persona.name[0] }}
              </a-avatar>
            </template>
          </a-list-item-meta>
        </a-list-item>
      </template>
    </a-list>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useForumStore } from '@/stores/forum'

const store = useForumStore()
const participants = computed(() => store.currentForum?.participants ?? [])

const getAvatarColor = (name: string) => {
  const colors = ['#f56a00', '#7265e6', '#ffbf00', '#00a2ae', '#1890ff', '#52c41a', '#eb2f96']
  let hash = 0
  for (let i = 0; i < name.length; i++) {
    hash = name.charCodeAt(i) + ((hash << 5) - hash)
  }
  const index = Math.abs(hash) % colors.length
  return colors[index]
}

const getStanceColor = (stance: string) => {
  if (stance.includes('支持') || stance.includes('正方')) return 'green'
  if (stance.includes('反对') || stance.includes('反方')) return 'red'
  return 'default'
}
</script>

<style scoped>
.participant-list-container {
  max-height: 400px;
  overflow-y: auto;
  padding-right: 8px;
}
.participant-name {
  font-weight: bold;
  margin-right: 8px;
}
</style>