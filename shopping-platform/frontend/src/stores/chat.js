import { defineStore } from 'pinia'
import { ref, computed, watch } from 'vue'
import { useAuthStore } from './auth'
import { agentApi } from '@/api/agent'

export const useChatStore = defineStore('chat', () => {
  const authStore = useAuthStore()

  const messages = ref([])
  const sessionId = ref(null)
  const streaming = ref(false)
  const streamText = ref('')

  const storageKey = computed(() => `ai_chat_${authStore.userInfo?.userId || 'guest'}`)

  // ─── 持久化 ───

  function save() {
    try {
      localStorage.setItem(storageKey.value, JSON.stringify({
        sessionId: sessionId.value,
        messages: messages.value,
      }))
    } catch {}
  }

  function load() {
    try {
      const raw = localStorage.getItem(storageKey.value)
      if (raw) {
        const data = JSON.parse(raw)
        sessionId.value = data.sessionId || null
        messages.value = data.messages || []
      }
    } catch {}
  }

  // 自动保存
  watch(messages, save, { deep: true })
  watch(sessionId, save)

  // 初始化
  load()

  // ─── 操作 ───

  async function sendMessage(text, options = {}) {
    if (!text.trim() || streaming.value) return

    messages.value.push({ id: `u-${Date.now()}`, role: 'user', content: text })
    streamText.value = ''
    streaming.value = true

    try {
      await agentApi.streamChat(
        {
          message: text,
          session_id: sessionId.value,
          upload_id: options.uploadId || null,
          memory: { user_id: String(authStore.userInfo?.userId || '') },
        },
        {
          onStatus: (data) => {
            if (data.session_id && !sessionId.value) {
              sessionId.value = data.session_id
            }
          },
          onMessageDelta: (data) => {
            if (data.content) streamText.value += data.content
          },
          onMessage: (data) => {
            sessionId.value = data.session_id || sessionId.value
            messages.value.push({
              id: data.id || `a-${Date.now()}`,
              role: 'assistant',
              content: data.content || streamText.value,
              cards: data.product_cards || [],
            })
            streamText.value = ''
          },
          onError: (msg) => {
            messages.value.push({ id: `e-${Date.now()}`, role: 'assistant', content: `出错了：${msg}` })
            streamText.value = ''
          },
          onDone: () => {
            streaming.value = false
            streamText.value = ''
          },
        }
      )
    } catch (e) {
      streaming.value = false
      streamText.value = ''
      messages.value.push({ id: `e-${Date.now()}`, role: 'assistant', content: `连接失败：${e.message}` })
    }
  }

  async function syncFromServer() {
    if (!sessionId.value) return
    try {
      const msgs = await agentApi.getMessages(sessionId.value)
      if (msgs.length > messages.value.length) {
        messages.value = msgs.map(m => ({
          id: m.id,
          role: m.role,
          content: m.content,
          cards: m.product_cards || [],
        }))
      }
    } catch {}
  }

  function clear() {
    messages.value = []
    sessionId.value = null
    streamText.value = ''
    save()
  }

  return {
    messages, sessionId, streaming, streamText,
    sendMessage, syncFromServer, clear, load,
  }
})
