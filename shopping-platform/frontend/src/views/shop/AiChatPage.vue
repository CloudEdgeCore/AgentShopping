<template>
  <div class="ai-chat-page">
    <!-- 未登录提示 -->
    <div v-if="!authStore.isLoggedIn" class="login-gate">
      <div class="login-gate-card">
        <div class="login-gate-icon">🤖</div>
        <h2>AI 智能导购</h2>
        <p>登录后即可使用 AI 对话导购，帮你智能推荐商品、比价、加购物车。</p>
        <div class="login-gate-actions">
          <RouterLink to="/login" class="btn btn-primary">登录</RouterLink>
          <RouterLink to="/register" class="btn btn-outline">注册</RouterLink>
        </div>
      </div>
    </div>

    <!-- 已登录：聊天界面 -->
    <div v-else class="chat-container">
      <!-- 侧边栏：会话列表 -->
      <aside class="chat-sidebar" :class="{ open: sidebarOpen }">
        <div class="sidebar-header">
          <h3>AI 导购</h3>
          <button class="btn-new-chat" @click="createNewSession">
            <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.5"><line x1="10" y1="4" x2="10" y2="16"/><line x1="4" y1="10" x2="16" y2="10"/></svg>
            新对话
          </button>
        </div>
        <div class="session-list">
          <div
            v-for="s in sessions"
            :key="s.id"
            class="session-item"
            :class="{ active: s.id === currentSessionId }"
            @click="loadSession(s.id)"
          >
            <span class="session-title">{{ s.title || '新对话' }}</span>
            <button class="btn-delete" @click.stop="deleteSession(s.id)" title="删除">×</button>
          </div>
          <div v-if="sessions.length === 0" class="session-empty">暂无会话</div>
        </div>
      </aside>

      <!-- 主聊天区 -->
      <main class="chat-main">
        <!-- 顶栏 -->
        <div class="chat-topbar">
          <button class="btn-toggle-sidebar" @click="sidebarOpen = !sidebarOpen">
            <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.5"><line x1="3" y1="5" x2="17" y2="5"/><line x1="3" y1="10" x2="17" y2="10"/><line x1="3" y1="15" x2="17" y2="15"/></svg>
          </button>
          <span class="topbar-title">{{ currentSessionTitle }}</span>
          <span v-if="chat.streaming" class="streaming-badge">生成中...</span>
        </div>

        <!-- 消息列表 -->
        <div ref="messagesContainer" class="messages-container">
          <div v-if="chat.messages.length === 0" class="welcome-screen">
            <div class="welcome-icon">🤖</div>
            <h2>AI 智能导购</h2>
            <p>用自然语言描述你的购物需求，我来帮你找最合适的商品。</p>
            <div class="quick-prompts">
              <button v-for="prompt in quickPrompts" :key="prompt" @click="sendQuickPrompt(prompt)">
                {{ prompt }}
              </button>
            </div>
          </div>

          <div v-for="msg in chat.messages" :key="msg.id" class="message" :class="msg.role">
            <div class="message-avatar">
              {{ msg.role === 'user' ? avatarLetter : '🤖' }}
            </div>
            <div class="message-body">
              <div class="message-content" v-html="renderMarkdown(msg.content)"></div>
              <!-- 商品卡片 -->
              <div v-if="msg.cards?.length" class="product-cards">
                <div v-for="(card, idx) in msg.cards" :key="idx" class="product-card" @click="goToProduct(card)">
                  <img v-if="card.image_url" :src="fixImageUrl(card.image_url)" :alt="card.title" class="card-image" />
                  <div class="card-info">
                    <div class="card-title">{{ card.title }}</div>
                    <div class="card-price">¥{{ (card.price / 100).toFixed(2) }}</div>
                    <div v-if="card.reasons?.length" class="card-reason">{{ card.reasons[0] }}</div>
                  </div>
                </div>
              </div>
              <!-- 反馈按钮 -->
              <div v-if="msg.role === 'assistant' && msg.feedbackEnabled" class="feedback-bar">
                <button @click="submitFeedback(msg.id, 1)" title="有帮助">👍</button>
                <button @click="submitFeedback(msg.id, -1)" title="没帮助">👎</button>
              </div>
            </div>
          </div>

          <!-- 流式输出占位 -->
          <div v-if="chat.streaming && chat.streamText" class="message assistant">
            <div class="message-avatar">🤖</div>
            <div class="message-body">
              <div class="message-content" v-html="renderMarkdown(chat.streamText)"></div>
            </div>
          </div>
        </div>

        <!-- 输入区 -->
        <div class="input-area">
          <div class="input-row">
            <label class="btn-upload" title="上传图片搜索">
              📷
              <input type="file" accept="image/*" @change="handleImageUpload" hidden />
            </label>
            <textarea
              ref="inputRef"
              v-model="inputText"
              placeholder="描述你的购物需求，比如「推荐一款降噪耳机」..."
              rows="1"
              @keydown.enter.exact.prevent="sendMessage"
              @input="autoResize"
            ></textarea>
            <button class="btn-send" :disabled="!inputText.trim() || chat.streaming" @click="sendMessage">
              <svg viewBox="0 0 20 20" fill="currentColor"><path d="M2.94 5.22l14.3-2.76a.5.5 0 01.6.6L15.08 17.36a.5.5 0 01-.85.24L10.5 13.4l-2.3 3.1a.5.5 0 01-.9-.3V12.9L2.7 6.07a.5.5 0 01.24-.85z"/></svg>
            </button>
          </div>
          <div v-if="uploadedImage" class="uploaded-preview">
            <img :src="uploadedImage.preview" alt="uploaded" />
            <button @click="clearUpload">×</button>
          </div>
        </div>
      </main>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, nextTick, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useChatStore } from '@/stores/chat'
import { agentApi } from '@/api/agent'

const router = useRouter()
const authStore = useAuthStore()
const chat = useChatStore()

// State
const sessions = ref([])
const inputText = ref('')
const sidebarOpen = ref(false)
const uploadedImage = ref(null)
const messagesContainer = ref(null)
const inputRef = ref(null)

const quickPrompts = [
  '推荐一款降噪耳机',
  '3000 元以内的手机推荐',
  '帮我找一款适合运动的蓝牙耳机',
  '比较一下 iPhone 16 和小米 16 Pro'
]

const avatarLetter = computed(() => {
  const name = authStore.userInfo?.nickname || authStore.userInfo?.username || '?'
  return name.charAt(0).toUpperCase()
})

// 将 Agent 的图片路径转为代理路径
function fixImageUrl(url) {
  if (!url) return ''
  if (url.startsWith('/static/')) return '/agent' + url
  return url
}

const currentSessionTitle = computed(() => {
  const s = sessions.value.find(s => s.id === chat.sessionId)
  return s?.title || 'AI 智能导购'
})

// Lifecycle
onMounted(async () => {
  await loadSessions()
  if (chat.sessionId && chat.messages.length === 0) {
    await loadSession(chat.sessionId)
  }
  if (inputRef.value) inputRef.value.focus()
})

// Methods
async function loadSessions() {
  try {
    sessions.value = await agentApi.getSessions()
  } catch (e) {
    console.warn('Failed to load sessions:', e)
  }
}

async function createNewSession() {
  try {
    const session = await agentApi.createSession()
    sessions.value.unshift(session)
    chat.sessionId = session.id
    chat.messages = []
    sidebarOpen.value = false
  } catch (e) {
    console.error('Failed to create session:', e)
  }
}

async function loadSession(sessionId) {
  chat.sessionId = sessionId
  sidebarOpen.value = false
  try {
    const msgs = await agentApi.getMessages(sessionId)
    chat.messages = msgs.map(m => ({
      id: m.id,
      role: m.role,
      content: m.content,
      productCards: m.product_cards || [],
      feedbackEnabled: m.role === 'assistant'
    }))
    await scrollToBottom()
  } catch (e) {
    console.error('Failed to load messages:', e)
  }
}

async function deleteSession(sessionId) {
  try {
    await agentApi.deleteSession(sessionId)
    sessions.value = sessions.value.filter(s => s.id !== sessionId)
    if (chat.sessionId === sessionId) {
      chat.sessionId = null
      chat.messages = []
    }
  } catch (e) {
    console.error('Failed to delete session:', e)
  }
}

async function sendMessage() {
  const text = inputText.value.trim()
  if (!text || chat.streaming) return

  // 如果没有当前会话，先创建
  if (!chat.sessionId) {
    await createNewSession()
  }

  inputText.value = ''
  await chat.sendMessage(text, { uploadId: uploadedImage.value?.upload_id })
  if (uploadedImage.value) clearUpload()
  await scrollToBottom()
  loadSessions()
}

function sendQuickPrompt(prompt) {
  inputText.value = prompt
  sendMessage()
}

async function handleImageUpload(e) {
  const file = e.target.files?.[0]
  if (!file) return
  try {
    const result = await agentApi.uploadImage(file)
    uploadedImage.value = {
      upload_id: result.upload_id,
      preview: result.preview_url,
      file
    }
  } catch (err) {
    console.error('Upload failed:', err)
  }
  e.target.value = ''
}

function clearUpload() {
  uploadedImage.value = null
}

function goToProduct(card) {
  const productId = card.product_id || card.id
  if (productId) {
    // Agent 商品使用字符串 ID，跳转到 Agent 专属详情页
    router.push({ name: 'AgentProduct', params: { productId } })
  }
}

async function submitFeedback(messageId, rating) {
  try {
    await agentApi.submitFeedback(messageId, rating)
  } catch (e) {
    console.warn('Feedback failed:', e)
  }
}

function autoResize(e) {
  const el = e.target
  el.style.height = 'auto'
  el.style.height = Math.min(el.scrollHeight, 120) + 'px'
}

async function scrollToBottom() {
  await nextTick()
  if (messagesContainer.value) {
    messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
  }
}

function renderMarkdown(text) {
  if (!text) return ''
  // 简单的 Markdown 渲染：加粗、换行
  return text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    .replace(/\n/g, '<br>')
}
</script>

<style scoped>
.ai-chat-page {
  height: calc(100vh - 64px);
  display: flex;
  flex-direction: column;
}

/* 登录提示 */
.login-gate {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 40px 20px;
}

.login-gate-card {
  text-align: center;
  max-width: 400px;
  padding: 48px 40px;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 16px;
  box-shadow: var(--shadow-lg);
}

.login-gate-icon {
  font-size: 56px;
  margin-bottom: 16px;
}

.login-gate-card h2 {
  font-size: 22px;
  font-weight: 700;
  color: var(--ink);
  margin-bottom: 12px;
}

.login-gate-card p {
  font-size: 15px;
  color: var(--ink-muted);
  line-height: 1.6;
  margin-bottom: 28px;
}

.login-gate-actions {
  display: flex;
  gap: 12px;
  justify-content: center;
}

.btn {
  padding: 10px 28px;
  border-radius: 10px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all var(--transition);
  text-decoration: none;
}

.btn-primary {
  background: var(--ink);
  color: var(--gold);
  border: none;
}

.btn-primary:hover { transform: scale(1.02); }

.btn-outline {
  background: var(--surface);
  color: var(--ink-soft);
  border: 1.5px solid var(--border);
}

.btn-outline:hover { border-color: var(--ink); color: var(--ink); }

.chat-container {
  flex: 1;
  display: flex;
  overflow: hidden;
}

/* Sidebar */
.chat-sidebar {
  width: 260px;
  border-right: 1px solid var(--border);
  background: var(--surface-dim);
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
}

.sidebar-header {
  padding: 16px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  border-bottom: 1px solid var(--border);
}

.sidebar-header h3 {
  font-size: 16px;
  font-weight: 600;
  color: var(--ink);
}

.btn-new-chat {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 6px 12px;
  border-radius: 8px;
  font-size: 13px;
  color: var(--ink);
  background: var(--surface);
  border: 1px solid var(--border);
  cursor: pointer;
  transition: all var(--transition);
}

.btn-new-chat:hover { background: var(--ink); color: var(--gold); }
.btn-new-chat svg { width: 14px; height: 14px; }

.session-list {
  flex: 1;
  overflow-y: auto;
  padding: 8px;
}

.session-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 12px;
  border-radius: 8px;
  cursor: pointer;
  transition: all var(--transition);
}

.session-item:hover { background: var(--surface); }
.session-item.active { background: var(--surface); font-weight: 600; }

.session-title {
  flex: 1;
  font-size: 13px;
  color: var(--ink-soft);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.btn-delete {
  opacity: 0;
  width: 24px;
  height: 24px;
  border-radius: 4px;
  font-size: 16px;
  color: var(--ink-muted);
  background: none;
  border: none;
  cursor: pointer;
  transition: all var(--transition);
}

.session-item:hover .btn-delete { opacity: 1; }
.btn-delete:hover { background: #fef2f2; color: var(--danger); }

.session-empty {
  padding: 24px;
  text-align: center;
  font-size: 13px;
  color: var(--ink-muted);
}

/* Main Chat */
.chat-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.chat-topbar {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 20px;
  border-bottom: 1px solid var(--border);
  background: var(--surface);
}

.btn-toggle-sidebar {
  display: none;
  width: 36px;
  height: 36px;
  border-radius: 8px;
  background: none;
  border: none;
  cursor: pointer;
  color: var(--ink-soft);
}

.btn-toggle-sidebar svg { width: 18px; height: 18px; }

.topbar-title {
  font-size: 15px;
  font-weight: 600;
  color: var(--ink);
}

.streaming-badge {
  margin-left: auto;
  padding: 4px 10px;
  border-radius: 100px;
  font-size: 12px;
  background: var(--gold);
  color: var(--ink);
  font-weight: 500;
}

/* Messages */
.messages-container {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.welcome-screen {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
  gap: 16px;
  color: var(--ink-muted);
}

.welcome-icon { font-size: 48px; }
.welcome-screen h2 { font-size: 24px; font-weight: 600; color: var(--ink); }
.welcome-screen p { font-size: 15px; max-width: 400px; }

.quick-prompts {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  justify-content: center;
  margin-top: 8px;
}

.quick-prompts button {
  padding: 8px 16px;
  border-radius: 100px;
  font-size: 13px;
  color: var(--ink-soft);
  background: var(--surface);
  border: 1px solid var(--border);
  cursor: pointer;
  transition: all var(--transition);
}

.quick-prompts button:hover {
  background: var(--ink);
  color: var(--gold);
  border-color: var(--ink);
}

/* Message */
.message {
  display: flex;
  gap: 12px;
  max-width: 800px;
}

.message.user { margin-left: auto; flex-direction: row-reverse; }

.message-avatar {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  font-weight: 600;
  flex-shrink: 0;
}

.message.user .message-avatar {
  background: var(--ink);
  color: var(--gold);
}

.message.assistant .message-avatar {
  background: var(--surface-dim);
  font-size: 20px;
}

.message-body {
  flex: 1;
  min-width: 0;
}

.message-content {
  padding: 12px 16px;
  border-radius: 16px;
  font-size: 14px;
  line-height: 1.6;
  color: var(--ink);
  word-break: break-word;
}

.message.user .message-content {
  background: var(--ink);
  color: var(--gold);
  border-bottom-right-radius: 4px;
}

.message.assistant .message-content {
  background: var(--surface-dim);
  border-bottom-left-radius: 4px;
}

/* Product Cards */
.product-cards {
  display: flex;
  gap: 12px;
  margin-top: 12px;
  overflow-x: auto;
  padding-bottom: 4px;
}

.product-card {
  flex-shrink: 0;
  width: 200px;
  border: 1px solid var(--border);
  border-radius: 12px;
  overflow: hidden;
  cursor: pointer;
  transition: all var(--transition);
  background: var(--surface);
}

.product-card:hover {
  box-shadow: var(--shadow-md);
  transform: translateY(-2px);
}

.card-image {
  width: 100%;
  height: 140px;
  object-fit: cover;
}

.card-info {
  padding: 10px 12px;
}

.card-title {
  font-size: 13px;
  font-weight: 500;
  color: var(--ink);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.card-price {
  font-size: 15px;
  font-weight: 700;
  color: var(--danger);
  margin-top: 4px;
}

.card-reason {
  font-size: 11px;
  color: var(--ink-muted);
  margin-top: 4px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* Feedback */
.feedback-bar {
  display: flex;
  gap: 4px;
  margin-top: 8px;
}

.feedback-bar button {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  font-size: 14px;
  background: var(--surface);
  border: 1px solid var(--border);
  cursor: pointer;
  transition: all var(--transition);
}

.feedback-bar button:hover {
  background: var(--surface-dim);
  transform: scale(1.1);
}

/* Input Area */
.input-area {
  border-top: 1px solid var(--border);
  padding: 16px 20px;
  background: var(--surface);
}

.input-row {
  display: flex;
  align-items: flex-end;
  gap: 8px;
  background: var(--surface-dim);
  border: 1.5px solid var(--border);
  border-radius: 16px;
  padding: 8px 12px;
  transition: all var(--transition);
}

.input-row:focus-within {
  border-color: var(--ink);
  box-shadow: 0 0 0 3px rgba(15,15,20,0.06);
}

.btn-upload {
  width: 36px;
  height: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 18px;
  cursor: pointer;
  border-radius: 8px;
  transition: all var(--transition);
}

.btn-upload:hover { background: var(--surface); }

.input-row textarea {
  flex: 1;
  border: none;
  background: none;
  outline: none;
  font-size: 14px;
  color: var(--ink);
  resize: none;
  min-height: 24px;
  max-height: 120px;
  font-family: inherit;
}

.input-row textarea::placeholder { color: var(--ink-faint); }

.btn-send {
  width: 36px;
  height: 36px;
  border-radius: 10px;
  background: var(--ink);
  color: var(--gold);
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all var(--transition);
  flex-shrink: 0;
}

.btn-send:disabled { opacity: 0.4; cursor: not-allowed; }
.btn-send:hover:not(:disabled) { transform: scale(1.05); }
.btn-send svg { width: 16px; height: 16px; }

.uploaded-preview {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 8px;
  padding: 8px;
  background: var(--surface-dim);
  border-radius: 8px;
}

.uploaded-preview img {
  width: 48px;
  height: 48px;
  object-fit: cover;
  border-radius: 6px;
}

.uploaded-preview button {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  font-size: 14px;
  background: var(--surface);
  border: 1px solid var(--border);
  cursor: pointer;
}

/* Responsive */
@media (max-width: 768px) {
  .chat-sidebar {
    position: fixed;
    left: 0;
    top: 64px;
    bottom: 0;
    z-index: 150;
    transform: translateX(-100%);
    transition: transform 300ms ease;
  }

  .chat-sidebar.open { transform: translateX(0); }
  .btn-toggle-sidebar { display: flex; }
}
</style>
