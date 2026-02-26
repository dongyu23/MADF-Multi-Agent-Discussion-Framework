<template>
  <a-layout style="min-height: 100vh">
    <a-layout-sider
      v-model:collapsed="collapsed"
      collapsible
      theme="light"
      breakpoint="lg"
      :width="220"
      class="sider-layout"
    >
      <div class="logo">
        <span v-if="!collapsed" class="logo-text">MADF 论坛</span>
        <span v-else class="logo-text">M</span>
      </div>
      <a-menu v-model:selectedKeys="selectedKeys" theme="light" mode="inline">
        <a-menu-item key="dashboard">
          <router-link to="/dashboard">
            <dashboard-outlined />
            <span>概览</span>
          </router-link>
        </a-menu-item>
        
        <a-menu-item key="personas">
          <router-link to="/personas">
            <team-outlined />
            <span>智能体工坊</span>
          </router-link>
        </a-menu-item>
        
        <a-menu-item key="forums">
          <router-link to="/forums">
            <comment-outlined />
            <span>圆桌论坛</span>
          </router-link>
        </a-menu-item>

        <a-menu-item key="test">
          <router-link to="/test">
            <tool-outlined />
            <span>API测试</span>
          </router-link>
        </a-menu-item>
      </a-menu>
    </a-layout-sider>
    
    <a-layout class="site-layout">
      <a-layout-header style="background: #fff; padding: 0 24px; display: flex; align-items: center; justify-content: flex-end; box-shadow: 0 1px 4px rgba(0,21,41,.08); z-index: 1;">
        <a-space>
          <a-switch
            :checked="configStore.isDark"
            @change="configStore.toggleTheme"
            checked-children="🌙"
            un-checked-children="☀️"
          />
          <a-dropdown>
            <a class="ant-dropdown-link user-dropdown" @click.prevent>
              <a-avatar style="background-color: #1890ff" size="small">{{ authStore.user?.username?.[0]?.toUpperCase() }}</a-avatar>
              <span class="username">{{ authStore.user?.username }}</span>
            </a>
            <template #overlay>
              <a-menu>
                <a-menu-item>
                  <a href="javascript:;" @click="authStore.logout">退出登录</a>
                </a-menu-item>
              </a-menu>
            </template>
          </a-dropdown>
        </a-space>
      </a-layout-header>
      
      <a-layout-content style="margin: 24px 16px; padding: 0; min-height: 280px; overflow: initial;">
        <div :style="{ padding: '24px', background: '#fff', minHeight: '100%', borderRadius: '8px' }">
          <router-view />
        </div>
      </a-layout-content>
      
      <a-layout-footer style="text-align: center">
        MADF ©2026 Created by Trae AI
      </a-layout-footer>
    </a-layout>
  </a-layout>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useConfigStore } from '@/stores/config'
import {
  DashboardOutlined,
  TeamOutlined,
  CommentOutlined,
  ToolOutlined
} from '@ant-design/icons-vue'

const route = useRoute()
const authStore = useAuthStore()
const configStore = useConfigStore()
const collapsed = ref(false)

const selectedKeys = computed(() => {
  if (route.path === '/' || route.path.startsWith('/dashboard')) return ['dashboard']
  if (route.path.startsWith('/personas')) return ['personas']
  if (route.path.startsWith('/forums')) return ['forums']
  if (route.path.startsWith('/test')) return ['test']
  return []
})
</script>

<style scoped>
.logo {
  height: 32px;
  margin: 16px;
  background: rgba(24, 144, 255, 0.2);
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 4px;
  overflow: hidden;
  white-space: nowrap;
}

.logo-text {
  font-size: 18px;
  font-weight: bold;
  color: #1890ff;
}

.sider-layout {
  box-shadow: 2px 0 8px 0 rgba(29, 35, 41, 0.05);
  z-index: 10;
}

.user-dropdown {
  display: flex;
  align-items: center;
  cursor: pointer;
}

.username {
  margin-left: 8px;
  color: rgba(0, 0, 0, 0.85);
  font-weight: 500;
}

/* Ensure the layout takes full width */
.site-layout {
  min-height: 100vh;
}

@media (max-width: 768px) {
  .username {
    display: none;
  }
}
</style>
