<template>
  <div class="ai-chat-widget" :class="{ open: isOpen }">
    <button class="widget-trigger" @click="toggle" :title="isOpen ? '关闭' : 'AI 导购'">
      <span v-if="isOpen" class="trigger-close">×</span>
      <span v-else class="trigger-icon">🤖</span>
    </button>

    <Transition name="panel">
      <div v-if="isOpen" class="widget-panel">
        <div class="panel-header">
          <span class="panel-title">🤖 AI 导购</span>
          <RouterLink to="/ai-chat" class="panel-expand" title="全屏打开">⤢</RouterLink>
        </div>

        <div ref="messagesEl" class="panel-messages">
          <div v-if="chat.messages.length === 0" class="panel-welcome">
            <p>你好！我是 AI 导购助手，告诉我你想找什么商品？</p>
            <div class="quick-tags">
              <button v-for="q in quickPrompts" :key="q" @click="sendQuick(q)">{{ q }}</button>
            </div>
          </div>

          <div v-for="msg in chat.messages" :key="msg.id" class="msg" :class="msg.role">
            <div class="msg-content" v-html="renderMd(msg.content)"></div>
            <div v-if="msg.cards?.length" class="msg-cards">
              <div v-for="card in msg.cards" :key="card.product_id" class="mini-card" @click="goProduct(card)">
                <img v-if="card.image_url" :src="fixImg(card.image_url)" />
                <div class="mini-card-info">
                  <div class="mini-card-title">{{ card.title }}</div>
                  <div class="mini-card-price">¥{{ (card.price / 100).toFixed(0) }}</div>
                </div>
              </div>
            </div>
          </div>

          <div v-if="chat.streaming && chat.streamText" class="msg assistant">
            <div class="msg-content" v-html="renderMd(chat.streamText)"></div>
          </div>
        </div>

        <div class="panel-input">
          <input
            ref="inputEl"
            v-model="inputText"
            placeholder="说说你的需求..."
            @keydown.enter.exact.prevent="send"
            :disabled="chat.streaming"
          />
          <button class="btn-send" :disabled="!inputText.trim() || chat.streaming" @click="send">➤</button>
        </div>
      </div>
    </Transition>
  </div>
</template>

<script setup>
import { ref, nextTick, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useChatStore } from '@/stores/chat'

const router = useRouter()
const authStore = useAuthStore()
const chat = useChatStore()

const isOpen = ref(false)
const inputText = ref('')
const messagesEl = ref(null)
const inputEl = ref(null)

const quickPrompts = ['推荐降噪耳机', '3000元手机', '运动蓝牙耳机', '护肤品推荐']

function fixImg(url) {
  if (!url) return ''
  return url.startsWith('/static/') ? '/agent' + url : url
}

function goProduct(card) {
  const id = card.product_id || card.id
  if (id) router.push({ name: 'AgentProduct', params: { productId: id } })
}

function toggle() {
  if (!authStore.isLoggedIn) { router.push('/login'); return }
  isOpen.value = !isOpen.value
  if (isOpen.value) {
    chat.syncFromServer()
    nextTick(() => { inputEl.value?.focus(); scrollToBottom() })
  }
}

async function send() {
  const text = inputText.value.trim()
  if (!text || chat.streaming) return
  inputText.value = ''
  await chat.sendMessage(text)
  scrollToBottom()
}

function sendQuick(q) { inputText.value = q; send() }

// 消息变化时自动滚到底部
watch(() => chat.messages.length, () => nextTick(scrollToBottom))
watch(() => chat.streamText, () => nextTick(scrollToBottom))

function scrollToBottom() {
  if (messagesEl.value) messagesEl.value.scrollTop = messagesEl.value.scrollHeight
}

function renderMd(text) {
  if (!text) return ''
  return text.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>').replace(/\n/g, '<br>')
}
</script>

<style scoped>
.ai-chat-widget { position: fixed; bottom: 24px; right: 24px; z-index: 999; }

.widget-trigger {
  width: 56px; height: 56px; border-radius: 50%;
  background: var(--ink); color: var(--gold); border: none;
  cursor: pointer; font-size: 24px;
  display: flex; align-items: center; justify-content: center;
  box-shadow: 0 4px 20px rgba(0,0,0,0.25);
  transition: all 300ms ease;
  position: absolute; bottom: 0; right: 0;
}
.widget-trigger:hover { transform: scale(1.08); box-shadow: 0 6px 28px rgba(0,0,0,0.3); }
.ai-chat-widget.open .widget-trigger { background: #555; }
.trigger-close { font-size: 28px; line-height: 1; }
.trigger-icon { font-size: 24px; }

.widget-panel {
  position: absolute; bottom: 72px; right: 0;
  width: 380px; height: 520px;
  background: var(--surface); border: 1px solid var(--border);
  border-radius: 16px; box-shadow: 0 12px 48px rgba(0,0,0,0.18);
  display: flex; flex-direction: column; overflow: hidden;
}
.panel-enter-active, .panel-leave-active { transition: all 300ms ease; }
.panel-enter-from, .panel-leave-to { opacity: 0; transform: translateY(16px) scale(0.95); }

.panel-header {
  display: flex; align-items: center; justify-content: space-between;
  padding: 14px 16px; border-bottom: 1px solid var(--border); background: var(--surface-dim);
}
.panel-title { font-size: 15px; font-weight: 600; color: var(--ink); }
.panel-expand {
  width: 28px; height: 28px; display: flex; align-items: center; justify-content: center;
  border-radius: 6px; font-size: 18px; color: var(--ink-muted); text-decoration: none;
  transition: all var(--transition);
}
.panel-expand:hover { background: var(--surface); color: var(--ink); }

.panel-messages {
  flex: 1; overflow-y: auto; padding: 16px;
  display: flex; flex-direction: column; gap: 12px;
}
.panel-welcome { text-align: center; padding: 24px 12px; color: var(--ink-muted); font-size: 14px; }
.quick-tags { display: flex; flex-wrap: wrap; gap: 6px; justify-content: center; margin-top: 14px; }
.quick-tags button {
  padding: 6px 12px; border-radius: 100px; font-size: 12px;
  background: var(--surface-dim); border: 1px solid var(--border); color: var(--ink-soft);
  cursor: pointer; transition: all var(--transition);
}
.quick-tags button:hover { background: var(--ink); color: var(--gold); border-color: var(--ink); }

.msg { max-width: 88%; }
.msg.user { align-self: flex-end; }
.msg.assistant { align-self: flex-start; }
.msg-content {
  padding: 10px 14px; border-radius: 14px; font-size: 13px; line-height: 1.6; word-break: break-word;
}
.msg.user .msg-content { background: var(--ink); color: var(--gold); border-bottom-right-radius: 4px; }
.msg.assistant .msg-content { background: var(--surface-dim); color: var(--ink); border-bottom-left-radius: 4px; }

.msg-cards { display: flex; gap: 8px; margin-top: 8px; overflow-x: auto; padding-bottom: 4px; }
.mini-card {
  flex-shrink: 0; width: 140px; border: 1px solid var(--border); border-radius: 10px;
  overflow: hidden; cursor: pointer; background: var(--surface); transition: all var(--transition);
}
.mini-card:hover { box-shadow: var(--shadow-sm); transform: translateY(-2px); }
.mini-card img { width: 100%; height: 100px; object-fit: cover; }
.mini-card-info { padding: 8px; }
.mini-card-title { font-size: 11px; color: var(--ink); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.mini-card-price { font-size: 13px; font-weight: 700; color: var(--danger); margin-top: 2px; }

.panel-input {
  display: flex; gap: 8px; padding: 12px; border-top: 1px solid var(--border); background: var(--surface);
}
.panel-input input {
  flex: 1; border: 1.5px solid var(--border); border-radius: 10px;
  padding: 8px 12px; font-size: 13px; color: var(--ink); background: var(--surface-dim);
  outline: none; transition: border-color var(--transition);
}
.panel-input input:focus { border-color: var(--ink); }
.panel-input input::placeholder { color: var(--ink-faint); }
.btn-send {
  width: 36px; height: 36px; border-radius: 10px;
  background: var(--ink); color: var(--gold); border: none;
  cursor: pointer; font-size: 16px;
  display: flex; align-items: center; justify-content: center;
  transition: all var(--transition); flex-shrink: 0;
}
.btn-send:disabled { opacity: 0.4; cursor: not-allowed; }
.btn-send:hover:not(:disabled) { transform: scale(1.05); }

@media (max-width: 480px) {
  .widget-panel { width: calc(100vw - 32px); right: -8px; height: 460px; }
}
</style>
