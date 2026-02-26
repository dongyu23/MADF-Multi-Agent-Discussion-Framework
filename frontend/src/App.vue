<template>
  <a-config-provider :locale="zhCN" :theme="{ algorithm: configStore.isDark ? theme.darkAlgorithm : theme.defaultAlgorithm }">
    <router-view />
  </a-config-provider>
</template>

<script setup lang="ts">
import { theme } from 'ant-design-vue'
import zhCN from 'ant-design-vue/es/locale/zh_CN'
import { useConfigStore } from '@/stores/config'

const configStore = useConfigStore()
</script>
