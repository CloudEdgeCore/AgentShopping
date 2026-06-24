import axios from 'axios'
import NProgress from 'nprogress'
import { useAuthStore } from '@/stores/auth'
import router from '@/router'

const http = axios.create({
  baseURL: '/api',
  timeout: 15000,
  headers: { 'Content-Type': 'application/json' }
})

// Request interceptor
http.interceptors.request.use(config => {
  NProgress.start()
  const token = localStorage.getItem('access_token')
  if (token) {
    config.headers['Authorization'] = `Bearer ${token}`
  }
  return config
}, err => {
  NProgress.done()
  return Promise.reject(err)
})

// Response interceptor
http.interceptors.response.use(res => {
  NProgress.done()
  const data = res.data
  if (data.success === false) {
    // Business error
    const error = new Error(data.message || '操作失败')
    error.code = data.code
    error.isBusinessError = true
    return Promise.reject(error)
  }
  return data
}, err => {
  NProgress.done()
  const status = err.response?.status
  if (status === 401) {
    const authStore = useAuthStore()
    authStore.logout({ remote: false })
    router.push('/login')
  } else if (status === 403) {
    router.push('/403')
  }
  const msg = err.response?.data?.message || err.message || '网络错误'
  const error = new Error(msg)
  error.status = status
  return Promise.reject(error)
})

export default http
