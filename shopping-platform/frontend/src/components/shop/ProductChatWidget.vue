<template>
  <Teleport to="body">
    <!-- 触发按钮（可选显示） -->
    <button class="pcw-trigger" @click="open" v-if="showTrigger && !isOpen" title="问问 AI">
      🤖
    </button>

    <!-- 聊天面板 -->
    <Transition name="pcw">
      <div
        v-if="isOpen"
        ref="panelEl"
        class="pcw-panel"
        :style="panelStyle"
      >
        <!-- 可拖动头部 -->
        <div
          class="pcw-header"
          @mousedown="onDragStart"
          @touchstart.prevent="onTouchStart"
        >
          <span class="pcw-title">🤖 {{ productTitle?.slice(0, 12) || 'AI 导购' }}</span>
          <div class="pcw-header-actions">
            <button class="pcw-btn-min" @click.stop="isOpen = false" title="最小化">—</button>
            <button class="pcw-btn-close" @click.stop="close" title="关闭">×</button>
          </div>
        </div>

        <!-- 消息列表 -->
        <div ref="messagesEl" class="pcw-messages">
          <div v-if="messages.length === 0" class="pcw-welcome">
            <p>你好！我可以帮你了解这款商品，有什么想问的？</p>
            <div class="pcw-quick-tags">
              <button v-for="q in quickPrompts" :key="q" @click="sendQuick(q)">{{ q }}</button>
            </div>
          </div>

          <div v-for="msg in messages" :key="msg.id" class="pcw-msg" :class="msg.role">
            <div class="pcw-msg-content" v-html="renderMd(msg.content)"></div>
          </div>

          <div v-if="streaming && streamText" class="pcw-msg assistant">
            <div class="pcw-msg-content" v-html="renderMd(streamText)"></div>
          </div>
        </div>

        <!-- 输入区 -->
        <div class="pcw-input">
          <input
            ref="inputEl"
            v-model="inputText"
            placeholder="问问这款商品..."
            @keydown.enter.exact.prevent="send"
            :disabled="streaming"
          />
          <button class="pcw-btn-send" :disabled="!inputText.trim() || streaming" @click="send">➤</button>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup>
import { ref, computed, nextTick, watch, onBeforeUnmount } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { agentApi } from '@/api/agent'

const props = defineProps({
  productId: { type: String, required: true },
  productTitle: { type: String, default: '' },
  productCategory: { type: String, default: '' },
  productBrand: { type: String, default: '' },
  showTrigger: { type: Boolean, default: true },
})

const authStore = useAuthStore()

const isOpen = ref(false)
const messages = ref([])
const inputText = ref('')
const streaming = ref(false)
const streamText = ref('')
const sessionId = ref(null)
const messagesEl = ref(null)
const inputEl = ref(null)
const panelEl = ref(null)

// ─── 拖动状态 ───
const dragState = ref({ dragging: false, startX: 0, startY: 0, offsetX: 0, offsetY: 0 })
const panelPos = ref({ x: 0, y: 0 })
const panelSize = ref({ w: 360, h: 480 })

const panelStyle = computed(() => ({
  left: `${panelPos.value.x}px`,
  top: `${panelPos.value.y}px`,
  width: `${panelSize.value.w}px`,
  height: `${panelSize.value.h}px`,
}))

const quickPrompts = computed(() => [
  `这款怎么样？`,
  '有什么优缺点？',
  '适合什么人？',
  '和同类比呢？',
])

function open() {
  isOpen.value = true
  // 首次打开定位到右下角
  if (panelPos.value.x === 0 && panelPos.value.y === 0) {
    panelPos.value = {
      x: window.innerWidth - panelSize.value.w - 20,
      y: window.innerHeight - panelSize.value.h - 20,
    }
  }
  nextTick(() => inputEl.value?.focus())
}

function close() {
  isOpen.value = false
  messages.value = []
  sessionId.value = null
  streamText.value = ''
}

// ─── 拖动逻辑 ───
function onDragStart(e) {
  if (e.target.closest('button')) return
  dragState.value = {
    dragging: true,
    startX: e.clientX,
    startY: e.clientY,
    offsetX: panelPos.value.x,
    offsetY: panelPos.value.y,
  }
  document.addEventListener('mousemove', onDragMove)
  document.addEventListener('mouseup', onDragEnd)
}

function onDragMove(e) {
  if (!dragState.value.dragging) return
  const dx = e.clientX - dragState.value.startX
  const dy = e.clientY - dragState.value.startY
  panelPos.value = {
    x: Math.max(0, Math.min(window.innerWidth - 100, dragState.value.offsetX + dx)),
    y: Math.max(0, Math.min(window.innerHeight - 60, dragState.value.offsetY + dy)),
  }
}

function onDragEnd() {
  dragState.value.dragging = false
  document.removeEventListener('mousemove', onDragMove)
  document.removeEventListener('mouseup', onDragEnd)
}

// 移动端触摸拖动
function onTouchStart(e) {
  if (e.target.closest('button')) return
  const touch = e.touches[0]
  dragState.value = {
    dragging: true,
    startX: touch.clientX,
    startY: touch.clientY,
    offsetX: panelPos.value.x,
    offsetY: panelPos.value.y,
  }
  document.addEventListener('touchmove', onTouchMove, { passive: false })
  document.addEventListener('touchend', onTouchEnd)
}

function onTouchMove(e) {
  if (!dragState.value.dragging) return
  e.preventDefault()
  const touch = e.touches[0]
  const dx = touch.clientX - dragState.value.startX
  const dy = touch.clientY - dragState.value.startY
  panelPos.value = {
    x: Math.max(0, Math.min(window.innerWidth - 100, dragState.value.offsetX + dx)),
    y: Math.max(0, Math.min(window.innerHeight - 60, dragState.value.offsetY + dy)),
  }
}

function onTouchEnd() {
  dragState.value.dragging = false
  document.removeEventListener('touchmove', onTouchMove)
  document.removeEventListener('touchend', onTouchEnd)
}

onBeforeUnmount(() => {
  document.removeEventListener('mousemove', onDragMove)
  document.removeEventListener('mouseup', onDragEnd)
  document.removeEventListener('touchmove', onTouchMove)
  document.removeEventListener('touchend', onTouchEnd)
})

// ─── 聊天逻辑 ───
async function send() {
  const text = inputText.value.trim()
  if (!text || streaming.value) return
  inputText.value = ''
  streamText.value = ''
  streaming.value = true
  messages.value.push({ id: `u-${Date.now()}`, role: 'user', content: text })
  scrollToBottom()

  try {
    await agentApi.streamChat(
      {
        message: text,
        session_id: sessionId.value,
        memory: {
          user_id: String(authStore.userInfo?.userId || ''),
          product_id: props.productId,
          product_title: props.productTitle,
          product_category: props.productCategory,
          product_brand: props.productBrand,
          answer_policy: `用户正在浏览商品"${props.productTitle}"（ID: ${props.productId}），请围绕这款商品回答问题。如果用户问的不是这款商品，也要先关联到这款商品再回答。`,
        },
      },
      {
        onStatus: (data) => {
          if (data.session_id && !sessionId.value) sessionId.value = data.session_id
        },
        onMessageDelta: (data) => {
          if (data.content) { streamText.value += data.content; scrollToBottom() }
        },
        onMessage: (data) => {
          sessionId.value = data.session_id || sessionId.value
          messages.value.push({
            id: data.id || `a-${Date.now()}`,
            role: 'assistant',
            content: data.content || streamText.value,
          })
          streamText.value = ''
          scrollToBottom()
        },
        onError: (msg) => {
          messages.value.push({ id: `e-${Date.now()}`, role: 'assistant', content: `出错了：${msg}` })
          streamText.value = ''
        },
        onDone: () => { streaming.value = false; streamText.value = '' },
      }
    )
  } catch {
    streaming.value = false
    streamText.value = ''
  }
}

function sendQuick(q) { inputText.value = q; send() }

function scrollToBottom() {
  nextTick(() => { if (messagesEl.value) messagesEl.value.scrollTop = messagesEl.value.scrollHeight })
}

watch(() => messages.value.length, () => nextTick(scrollToBottom))
watch(streamText, () => nextTick(scrollToBottom))

function renderMd(text) {
  if (!text) return ''
  return text.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>').replace(/\n/g, '<br>')
}

defineExpose({ open, close, isOpen })
</script>

<style>
/* 非 scoped，因为 Teleport 到 body */
.pcw-trigger {
  position: fixed;
  bottom: 24px;
  right: 24px;
  width: 48px;
  height: 48px;
  border-radius: 50%;
  background: var(--ink, #0f0f14);
  color: var(--gold, #c9a84c);
  border: none;
  cursor: pointer;
  font-size: 22px;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 4px 16px rgba(0,0,0,0.2);
  transition: all 200ms ease;
  z-index: 9999;
}
.pcw-trigger:hover { transform: scale(1.08); box-shadow: 0 6px 24px rgba(0,0,0,0.28); }

.pcw-panel {
  position: fixed;
  z-index: 10000;
  background: var(--surface, #fff);
  border: 1px solid var(--border, #e5e5e5);
  border-radius: 14px;
  box-shadow: 0 8px 40px rgba(0,0,0,0.16);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  min-width: 300px;
  min-height: 360px;
}

.pcw-enter-active, .pcw-leave-active { transition: all 200ms ease; }
.pcw-enter-from, .pcw-leave-to { opacity: 0; transform: scale(0.95); }

/* 头部（可拖动） */
.pcw-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 14px;
  border-bottom: 1px solid var(--border, #e5e5e5);
  background: var(--surface-dim, #f8f8f8);
  cursor: move;
  user-select: none;
  flex-shrink: 0;
}
.pcw-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--ink, #0f0f14);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  pointer-events: none;
}
.pcw-header-actions { display: flex; gap: 4px; }
.pcw-btn-min, .pcw-btn-close {
  width: 26px; height: 26px; border-radius: 6px; font-size: 16px;
  color: var(--ink-muted, #999); background: none; border: none; cursor: pointer;
  display: flex; align-items: center; justify-content: center;
  transition: all 150ms ease;
}
.pcw-btn-min:hover, .pcw-btn-close:hover { background: var(--surface, #f0f0f0); color: var(--ink, #333); }

/* 消息区 */
.pcw-messages {
  flex: 1;
  overflow-y: auto;
  padding: 12px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.pcw-welcome { text-align: center; padding: 16px 8px; color: var(--ink-muted, #999); font-size: 12px; }
.pcw-quick-tags { display: flex; flex-wrap: wrap; gap: 5px; justify-content: center; margin-top: 10px; }
.pcw-quick-tags button {
  padding: 4px 10px; border-radius: 100px; font-size: 11px;
  background: var(--surface-dim, #f5f5f5); border: 1px solid var(--border, #e5e5e5);
  color: var(--ink-soft, #666); cursor: pointer; transition: all 150ms ease;
}
.pcw-quick-tags button:hover { background: var(--ink, #0f0f14); color: var(--gold, #c9a84c); border-color: var(--ink, #0f0f14); }

.pcw-msg { max-width: 92%; }
.pcw-msg.user { align-self: flex-end; }
.pcw-msg.assistant { align-self: flex-start; }
.pcw-msg-content {
  padding: 8px 12px; border-radius: 12px; font-size: 12px; line-height: 1.6; word-break: break-word;
}
.pcw-msg.user .pcw-msg-content { background: var(--ink, #0f0f14); color: var(--gold, #c9a84c); border-bottom-right-radius: 4px; }
.pcw-msg.assistant .pcw-msg-content { background: var(--surface-dim, #f5f5f5); color: var(--ink, #333); border-bottom-left-radius: 4px; }

/* 输入区 */
.pcw-input {
  display: flex; gap: 6px; padding: 8px 10px; border-top: 1px solid var(--border, #e5e5e5);
  background: var(--surface, #fff); flex-shrink: 0;
}
.pcw-input input {
  flex: 1; border: 1.5px solid var(--border, #e5e5e5); border-radius: 8px;
  padding: 6px 10px; font-size: 12px; color: var(--ink, #333);
  background: var(--surface-dim, #f8f8f8); outline: none;
  transition: border-color 150ms ease;
}
.pcw-input input:focus { border-color: var(--ink, #0f0f14); }
.pcw-input input::placeholder { color: var(--ink-faint, #bbb); }
.pcw-btn-send {
  width: 32px; height: 32px; border-radius: 8px;
  background: var(--ink, #0f0f14); color: var(--gold, #c9a84c); border: none;
  cursor: pointer; font-size: 14px;
  display: flex; align-items: center; justify-content: center;
  transition: all 150ms ease; flex-shrink: 0;
}
.pcw-btn-send:disabled { opacity: 0.4; cursor: not-allowed; }
.pcw-btn-send:hover:not(:disabled) { transform: scale(1.05); }
</style>
