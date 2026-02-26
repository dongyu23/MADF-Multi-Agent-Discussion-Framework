<template>
  <a-layout style="padding: 24px;">
    <a-typography-title :level="2">API Test Dashboard</a-typography-title>
    
    <a-tabs default-active-key="1">
      <a-tab-pane key="1" tab="User Management">
        <a-card title="Register User">
          <a-form layout="vertical" @finish="registerUser">
            <a-form-item label="Username" name="username">
              <a-input v-model:value="userForm.username" />
            </a-form-item>
            <a-form-item label="Password" name="password">
              <a-input-password v-model:value="userForm.password" />
            </a-form-item>
            <a-button type="primary" html-type="submit">Register</a-button>
          </a-form>
          <pre v-if="userResult">{{ userResult }}</pre>
        </a-card>
      </a-tab-pane>
      
      <a-tab-pane key="2" tab="Persona Management">
        <a-card title="Create Persona">
          <a-form layout="vertical" @finish="createPersona">
            <a-form-item label="Owner ID" name="ownerId">
              <a-input-number v-model:value="personaForm.ownerId" />
            </a-form-item>
            <a-form-item label="Name" name="name">
              <a-input v-model:value="personaForm.name" />
            </a-form-item>
            <a-button type="primary" html-type="submit">Create</a-button>
          </a-form>
          <pre v-if="personaResult">{{ personaResult }}</pre>
        </a-card>
      </a-tab-pane>
      
      <a-tab-pane key="3" tab="Forum Management">
        <a-card title="Create Forum">
          <a-form layout="vertical" @finish="createForum">
            <a-form-item label="Creator ID" name="creatorId">
              <a-input-number v-model:value="forumForm.creatorId" />
            </a-form-item>
            <a-form-item label="Topic" name="topic">
              <a-input v-model:value="forumForm.topic" />
            </a-form-item>
            <a-button type="primary" html-type="submit">Create</a-button>
          </a-form>
          <pre v-if="forumResult">{{ forumResult }}</pre>
        </a-card>
      </a-tab-pane>
    </a-tabs>
  </a-layout>
</template>

<script setup lang="ts">
import { reactive, ref } from 'vue'
import axios from 'axios'
import { message } from 'ant-design-vue'

const userForm = reactive({ username: 'testuser', password: 'password123' })
const userResult = ref('')

const personaForm = reactive({ ownerId: 1, name: 'Plato' })
const personaResult = ref('')

const forumForm = reactive({ creatorId: 1, topic: 'Philosophy and AI' })
const forumResult = ref('')

const registerUser = async () => {
  try {
    const res = await axios.post('/api/v1/users/', {
      username: userForm.username,
      password: userForm.password,
      role: 'user'
    })
    userResult.value = JSON.stringify(res.data, null, 2)
    message.success('User registered!')
  } catch (e: unknown) {
    if (e instanceof Error) {
        userResult.value = e.message
    } else {
        userResult.value = 'An error occurred'
    }
    message.error('Failed to register')
  }
}

const createPersona = async () => {
  try {
    const res = await axios.post(`/api/v1/personas/?owner_id=${personaForm.ownerId}`, {
      name: personaForm.name,
      bio: 'Test Bio',
      theories: ['T1', 'T2'],
      is_public: true
    })
    personaResult.value = JSON.stringify(res.data, null, 2)
    message.success('Persona created!')
  } catch (e: unknown) {
    if (e instanceof Error) {
        personaResult.value = e.message
    } else {
        personaResult.value = 'An error occurred'
    }
    message.error('Failed to create persona')
  }
}

const createForum = async () => {
  try {
    const res = await axios.post(`/api/v1/forums/?creator_id=${forumForm.creatorId}`, {
      topic: forumForm.topic,
      participant_ids: [1] // Simplified for test
    })
    forumResult.value = JSON.stringify(res.data, null, 2)
    message.success('Forum created!')
  } catch (e: unknown) {
    if (e instanceof Error) {
        forumResult.value = e.message
    } else {
        forumResult.value = 'An error occurred'
    }
    message.error('Failed to create forum')
  }
}
</script>
