import axios from 'axios'
import { message } from 'ant-design-vue'

const request = axios.create({
  baseURL: '/api/v1',
  timeout: 5000
})

request.interceptors.request.use(
  (config) => {
    // Access localStorage directly to avoid circular dependency with auth store
    const token = localStorage.getItem('token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

request.interceptors.response.use(
  (response) => {
    return response
  },
  (error) => {
    if (error.response) {
      if (error.response.status === 401) {
        // Clear storage and redirect to login
        // We use window.location to force a full refresh and state reset, 
        // avoiding dependency on router or store here
        localStorage.removeItem('token')
        localStorage.removeItem('user')
        if (!window.location.pathname.includes('/auth/login')) {
             message.error('会话已过期，请重新登录')
             window.location.href = '/auth/login'
        }
      } else {
        message.error(error.response.data.detail || '请求失败')
      }
    }
    return Promise.reject(error)
  }
)

export default request
