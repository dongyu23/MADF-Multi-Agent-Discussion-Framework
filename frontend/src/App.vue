<template>
  <a-config-provider :locale="zhCN" :theme="{ algorithm: configStore.isDark ? theme.darkAlgorithm : theme.defaultAlgorithm }">
    <div class="app-container">
      <router-view />
    </div>
  </a-config-provider>
</template>

<script setup lang="ts">
import { theme } from 'ant-design-vue'
import zhCN from 'ant-design-vue/es/locale/zh_CN'
import { useConfigStore } from '@/stores/config'

const configStore = useConfigStore()
</script>

<style>
html, body, #app, .app-container {
  height: 100%;
  margin: 0;
  padding: 0;
  overflow: hidden; /* Prevent global scrollbar */
}
</style>
