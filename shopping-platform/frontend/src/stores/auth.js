import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { authApi } from '@/api'
import { agentApi } from '@/api/agent'

export const useAuthStore = defineStore('auth', () => {
  const token = ref(localStorage.getItem('access_token') || '')
  const userInfo = ref(JSON.parse(localStorage.getItem('user_info') || 'null'))

  const isLoggedIn = computed(() => !!token.value)
  const isAdmin = computed(() => userInfo.value?.userType === 2)

  async function login(data) {
    let res
    try {
      // 优先用 Agent 登录（统一用户系统）
      res = await agentApi.login(data.username, data.password)
    } catch {
      // Agent 不可用时降级到 Java
      res = await authApi.login(data)
    }
    token.value = res.data.accessToken
    userInfo.value = res.data.userInfo
    localStorage.setItem('access_token', res.data.accessToken)
    localStorage.setItem('user_info', JSON.stringify(res.data.userInfo))
    return res.data
  }

  async function register(data) {
    let res
    try {
      res = await agentApi.register(data.username, data.password, data.nickname || '')
    } catch {
      res = await authApi.register(data)
    }
    return res.data
  }

  async function fetchMe() {
    const res = await authApi.me()
    userInfo.value = res.data
    localStorage.setItem('user_info', JSON.stringify(res.data))
    return res.data
  }

  function clearAuthState() {
    token.value = ''
    userInfo.value = null
    localStorage.removeItem('access_token')
    localStorage.removeItem('user_info')
  }

  async function logout(options = {}) {
    const remote = options.remote !== false
    try {
      if (remote && token.value) {
        await authApi.logout()
      }
    } catch (error) {
      // Keep logout idempotent on the client. We still clear local auth state.
    } finally {
      clearAuthState()
    }
  }

  function updateUserInfo(info) {
    userInfo.value = { ...userInfo.value, ...info }
    localStorage.setItem('user_info', JSON.stringify(userInfo.value))
  }

  return { token, userInfo, isLoggedIn, isAdmin, login, register, fetchMe, logout, updateUserInfo }
})
