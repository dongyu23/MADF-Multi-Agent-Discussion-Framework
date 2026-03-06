import axios from 'axios'
import { message } from 'ant-design-vue'

const request = axios.create({
  // Use relative path for Vercel deployment compatibility
  // In dev (Vite), /api/v1 is proxied to localhost:8000/api/v1
  // In prod (Vercel), /api/v1 is routed to /api/index.py via vercel.json rewrites
  baseURL: '/api/v1',
  timeout: 10000 // Increased timeout for serverless cold starts
})

request.interceptors.request.use(
  (config) => {
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
        localStorage.removeItem('token')
        localStorage.removeItem('user')
        if (!window.location.pathname.includes('/auth/login')) {
             message.error('会话已过期，请重新登录')
             window.location.href = '/auth/login'
        }
      } else if (error.response.status >= 500) {
        // Log detailed error for debugging
        // Use JSON.stringify to safely print object content
        console.error('Server Error:', JSON.stringify(error.response.data, null, 2))
        message.error('服务器内部错误，请稍后重试')
      } else {
        const detail = error.response.data?.detail
        const msg = typeof detail === 'string' ? detail : (detail?.message || '请求失败')
        message.error(msg)
      }
    } else if (error.request) {
        message.error('网络连接失败，请检查网络设置')
    } else {
        message.error('请求配置错误')
    }
    return Promise.reject(error)
  }
)

export default request
