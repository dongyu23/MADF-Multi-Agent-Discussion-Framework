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
        localStorage.removeItem('token')
        localStorage.removeItem('user')
        if (!window.location.pathname.includes('/auth/login')) {
             message.error('会话已过期，请重新登录')
             window.location.href = '/auth/login'
        }
      } else if (error.response.status >= 500) {
        message.error('服务器内部错误，请稍后重试')
      } else {
        const detail = error.response.data?.detail
        const msg = typeof detail === 'string' ? detail : (detail?.message || '请求失败')
        message.error(msg)
      }
    } else if (error.request) {
        // The request was made but no response was received
        message.error('网络连接失败，请检查网络设置')
    } else {
        // Something happened in setting up the request that triggered an Error
        message.error('请求配置错误')
    }
    return Promise.reject(error)
  }
)

export default request
