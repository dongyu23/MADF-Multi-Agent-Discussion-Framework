<template>
  <div class="persona-page">
    <div class="page-header">
      <div class="header-title">
        <span class="title">智能体工坊</span>
        <span class="subtitle">管理您的智能体角色，定义个性与认知体系</span>
      </div>
      <a-space>
        <a-button type="default" size="large" @click="handleCreatePreset" :loading="presetLoading">
          <thunderbolt-outlined /> 一键生成预设智能体
        </a-button>
        <a-button type="primary" size="large" @click="showModal()">
          <plus-outlined /> 创建智能体
        </a-button>
      </a-space>
    </div>

    <a-tabs v-model:activeKey="activeTab" class="persona-tabs">
      <a-tab-pane key="grid" tab="卡片视图">
        <a-spin :spinning="personaStore.loading">
          <div class="persona-grid">
            <a-card
              v-for="persona in personaStore.personas"
              :key="persona.id"
              hoverable
              class="persona-card"
            >
              <template #actions>
                <edit-outlined key="edit" @click="showModal(persona)" />
                <a-popconfirm
                  title="确定要删除这个智能体吗？"
                  @confirm="handleDelete(persona.id)"
                >
                  <delete-outlined key="delete" style="color: #ff4d4f" />
                </a-popconfirm>
              </template>
              <a-card-meta :title="persona.name" :description="persona.title || '暂无头衔'">
                <template #avatar>
                  <a-avatar
                    :style="{ backgroundColor: getAvatarColor(persona.name) }"
                    size="large"
                  >
                    {{ persona.name[0] }}
                  </a-avatar>
                </template>
              </a-card-meta>
              <div class="persona-content">
                <p class="bio">{{ persona.bio || '暂无简介' }}</p>
                <div class="tags">
                  <a-tag v-if="persona.is_public" color="green">公开</a-tag>
                  <a-tag v-else color="blue">私有</a-tag>
                  <a-tag v-for="tag in persona.theories.slice(0, 2)" :key="tag">{{ tag }}</a-tag>
                  <a-tag v-if="persona.theories.length > 2">...</a-tag>
                </div>
              </div>
            </a-card>
            
            <!-- Empty State -->
            <div v-if="personaStore.personas.length === 0" class="empty-state">
              <a-empty description="暂无智能体，快去创建一个吧" />
            </div>
          </div>
        </a-spin>
      </a-tab-pane>
      
      <a-tab-pane key="list" tab="列表视图">
        <a-table
          :columns="columns"
          :data-source="personaStore.personas"
          :loading="personaStore.loading"
          row-key="id"
        >
          <template #bodyCell="{ column, record }">
            <template v-if="column.key === 'theories'">
              <a-tag v-for="tag in record.theories" :key="tag">{{ tag }}</a-tag>
            </template>
            <template v-if="column.key === 'is_public'">
              <a-tag :color="record.is_public ? 'green' : 'blue'">
                {{ record.is_public ? '公开' : '私有' }}
              </a-tag>
            </template>
            <template v-if="column.key === 'action'">
              <a-space>
                <a-button type="link" size="small" @click="showModal(record)">编辑</a-button>
                <a-popconfirm title="确定要删除吗？" @confirm="handleDelete(record.id)">
                  <a-button type="link" size="small" danger>删除</a-button>
                </a-popconfirm>
              </a-space>
            </template>
          </template>
        </a-table>
      </a-tab-pane>
    </a-tabs>

    <a-modal
      v-model:open="visible"
      :title="editingId ? '编辑智能体' : '创建智能体'"
      width="640px"
      @ok="handleOk"
      :confirmLoading="submitting"
    >
      <a-form
        layout="vertical"
        ref="formRef"
        :model="formState"
        class="persona-form"
      >
        <a-divider orientation="left">基本信息</a-divider>
        <a-row :gutter="16">
          <a-col :span="12">
            <a-form-item label="名称" name="name" :rules="[{ required: true, message: '请输入名称' }]">
              <a-input v-model:value="formState.name" placeholder="例如：苏格拉底" />
            </a-form-item>
          </a-col>
          <a-col :span="12">
            <a-form-item label="头衔" name="title">
              <a-input v-model:value="formState.title" placeholder="例如：古希腊哲学家" />
            </a-form-item>
          </a-col>
        </a-row>
        
        <a-form-item label="简介" name="bio">
          <a-textarea v-model:value="formState.bio" :rows="3" placeholder="简要描述智能体的背景和生平" />
        </a-form-item>

        <a-divider orientation="left">认知体系</a-divider>
        
        <a-form-item label="理论标签 (用逗号分隔)" name="theories_str">
          <a-input v-model:value="formState.theories_str" placeholder="例如：精神助产术, 辩证法, 讽刺" />
        </a-form-item>
        
        <a-form-item label="核心立场" name="stance">
          <a-input v-model:value="formState.stance" placeholder="例如：追求真理，质疑一切" />
        </a-form-item>

        <a-divider orientation="left">高级设置</a-divider>
        
        <a-form-item label="系统提示词 (System Prompt)" name="system_prompt">
          <a-textarea
            v-model:value="formState.system_prompt"
            :rows="4"
            placeholder="定义智能体在对话中的行为准则和指令"
          />
        </a-form-item>
        
        <a-form-item name="is_public">
          <a-checkbox v-model:checked="formState.is_public">
            设为公开智能体 (其他用户可见)
          </a-checkbox>
        </a-form-item>
      </a-form>
    </a-modal>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { usePersonaStore, type Persona } from '@/stores/persona'
import { message } from 'ant-design-vue'
import {
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  ThunderboltOutlined
} from '@ant-design/icons-vue'

const personaStore = usePersonaStore()
const visible = ref(false)
const submitting = ref(false)
const editingId = ref<number | null>(null)
const activeTab = ref('grid')
const presetLoading = ref(false)

const columns = [
  { title: '名称', dataIndex: 'name', key: 'name' },
  { title: '头衔', dataIndex: 'title', key: 'title' },
  { title: '理论标签', dataIndex: 'theories', key: 'theories' },
  { title: '可见性', dataIndex: 'is_public', key: 'is_public' },
  { title: '操作', key: 'action', width: 150 }
]

const formState = reactive({
  name: '',
  title: '',
  bio: '',
  theories_str: '',
  stance: '',
  system_prompt: '',
  is_public: false
})

onMounted(() => {
  personaStore.fetchPersonas()
})

const getAvatarColor = (name: string) => {
  const colors = ['#f56a00', '#7265e6', '#ffbf00', '#00a2ae', '#1890ff', '#52c41a', '#eb2f96']
  let hash = 0
  for (let i = 0; i < name.length; i++) {
    hash = name.charCodeAt(i) + ((hash << 5) - hash)
  }
  const index = Math.abs(hash) % colors.length
  return colors[index]
}

const showModal = (record?: Persona) => {
  visible.value = true
  if (record) {
    editingId.value = record.id
    Object.assign(formState, {
      ...record,
      theories_str: record.theories.join(', ')
    })
  } else {
    editingId.value = null
    Object.assign(formState, {
      name: '', title: '', bio: '', theories_str: '', stance: '', system_prompt: '', is_public: false
    })
  }
}

const handleOk = async () => {
  if (!formState.name) {
    message.warning('请输入智能体名称')
    return
  }

  submitting.value = true
  const data = {
    ...formState,
    theories: formState.theories_str.split(/[,，]/).map(s => s.trim()).filter(s => s)
  }
  
  try {
    if (editingId.value) {
      await personaStore.updatePersona(editingId.value, data)
      message.success('更新成功')
    } else {
      await personaStore.createPersona(data)
      message.success('创建成功')
    }
    visible.value = false
  } catch (e: unknown) {
    if (e instanceof Error) {
        message.error(e.message || '操作失败')
    }
  } finally {
    submitting.value = false
  }
}

const handleDelete = async (id: number) => {
  try {
    await personaStore.deletePersona(id)
    message.success('删除成功')
  } catch (e) {
    message.error('删除失败')
  }
}

const handleCreatePreset = async () => {
    presetLoading.value = true
    try {
        await personaStore.createPresetPersonas()
        message.success('预设智能体已生成')
    } catch (e) {
        message.error('生成失败')
    } finally {
        presetLoading.value = false
    }
}
</script>

<style scoped>
.persona-page {
  max-width: 1200px;
  margin: 0 auto;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
}

.header-title {
  display: flex;
  flex-direction: column;
}

.title {
  font-size: 24px;
  font-weight: 500;
  color: rgba(0,0,0,0.85);
}

.subtitle {
  font-size: 14px;
  color: rgba(0,0,0,0.45);
  margin-top: 4px;
}

.persona-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 24px;
  padding-bottom: 24px;
}

.persona-card {
  transition: all 0.3s;
}

.persona-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 4px 12px rgba(0,0,0,0.1);
}

.persona-content {
  margin-top: 16px;
  height: 100px;
  display: flex;
  flex-direction: column;
}

.bio {
  color: rgba(0,0,0,0.45);
  font-size: 13px;
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  margin-bottom: 8px;
}

.tags {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}

.empty-state {
  grid-column: 1 / -1;
  padding: 48px 0;
  text-align: center;
}
</style>
