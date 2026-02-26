import { defineStore } from 'pinia'
import request from '@/utils/request'

export interface Persona {
  id: number
  owner_id: number
  name: string
  title: string
  bio: string
  theories: string[]
  stance: string
  system_prompt: string
  is_public: boolean
}

interface CreatePersonaData {
    name: string;
    title?: string;
    bio?: string;
    theories?: string[];
    stance?: string;
    system_prompt?: string;
    is_public?: boolean;
}

export const usePersonaStore = defineStore('persona', {
  state: () => ({
    personas: [] as Persona[],
    loading: false
  }),
  actions: {
    async fetchPersonas(ownerId?: number) {
      this.loading = true
      try {
        const params = ownerId ? { owner_id: ownerId } : {}
        const res = await request.get('/personas/', { params })
        this.personas = res.data
      } finally {
        this.loading = false
      }
    },
    async createPersona(data: CreatePersonaData) {
      await request.post('/personas/', data)
      await this.fetchPersonas()
    },
    async createPresetPersonas() {
        await request.post('/personas/batch/preset')
        await this.fetchPersonas()
    },
    async updatePersona(id: number, data: Partial<CreatePersonaData>) {
      await request.put(`/personas/${id}`, data)
      await this.fetchPersonas()
    },
    async deletePersona(id: number) {
      await request.delete(`/personas/${id}`)
      await this.fetchPersonas()
    }
  }
})
