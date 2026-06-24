<template>
  <div class="login-page">
    <div class="auth-layout">
      <!-- Left decoration -->
      <div class="auth-deco">
        <div class="auth-deco-content">
          <div class="deco-logo">
            <span class="logo-mark-lg">L</span>
            <span class="logo-text-lg">LUXE</span>
          </div>
          <h2 class="deco-title">品味生活<br /><em>从一件好物开始</em></h2>
          <p class="deco-desc">精选全球优质品牌，将最好的带到你身边</p>
        </div>
        <div class="deco-blob"></div>
      </div>

      <!-- Right form -->
      <div class="auth-form-wrap">
        <div class="auth-form-inner">
          <div class="auth-form-header">
            <h1 class="auth-title">欢迎回来</h1>
            <p class="auth-sub">登录您的账户，享受专属体验</p>
          </div>

          <form @submit.prevent="handleSubmit" class="auth-form">
            <div class="form-group">
              <label class="form-label">用户名</label>
              <input
                v-model="form.username"
                type="text"
                class="form-input"
                :class="{ error: errors.username }"
                placeholder="请输入用户名"
                autocomplete="username"
              />
              <div class="form-error" v-if="errors.username">{{ errors.username }}</div>
            </div>

            <div class="form-group">
              <label class="form-label">密码</label>
              <div class="input-with-suffix">
                <input
                  v-model="form.password"
                  :type="showPwd ? 'text' : 'password'"
                  class="form-input"
                  :class="{ error: errors.password }"
                  placeholder="请输入密码"
                  autocomplete="current-password"
                />
                <button type="button" class="input-suffix-btn" @click="showPwd = !showPwd">
                  {{ showPwd ? '隐藏' : '显示' }}
                </button>
              </div>
              <div class="form-error" v-if="errors.password">{{ errors.password }}</div>
            </div>

            <div class="form-error global-error" v-if="globalError">{{ globalError }}</div>

            <button type="submit" class="btn btn-primary btn-lg btn-block" :disabled="loading">
              <span v-if="loading" class="spinner spinner-gold"></span>
              {{ loading ? '登录中...' : '登 录' }}
            </button>
          </form>

          <div class="auth-footer">
            <span>还没有账户？</span>
            <RouterLink to="/register">立即注册</RouterLink>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useCartStore } from '@/stores/cart'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()
const cartStore = useCartStore()

const form = reactive({ username: '', password: '' })
const errors = reactive({ username: '', password: '' })
const globalError = ref('')
const loading = ref(false)
const showPwd = ref(false)

function validate() {
  errors.username = form.username.trim() ? '' : '请输入用户名'
  errors.password = form.password.length >= 6 ? '' : '密码至少6位'
  return !errors.username && !errors.password
}

async function handleSubmit() {
  globalError.value = ''
  if (!validate()) return
  loading.value = true
  try {
    await authStore.login({ username: form.username, password: form.password })
    cartStore.fetchCart().catch(() => {})
    const redirect = route.query.redirect || '/'
    router.push(redirect)
  } catch (e) {
    globalError.value = e.message || '登录失败'
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-page {
  min-height: 100vh;
  display: flex;
}

.auth-layout {
  display: grid;
  grid-template-columns: 1fr 1fr;
  width: 100%;
}

@media (max-width: 768px) {
  .auth-layout { grid-template-columns: 1fr; }
  .auth-deco { display: none; }
}

/* Left Deco */
.auth-deco {
  background: var(--ink);
  position: relative;
  overflow: hidden;
  display: flex;
  align-items: center;
  padding: 60px;
}

.auth-deco-content {
  position: relative;
  z-index: 1;
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.deco-logo {
  display: flex;
  align-items: center;
  gap: 12px;
}

.logo-mark-lg {
  width: 48px;
  height: 48px;
  background: var(--gold);
  color: var(--ink);
  display: flex;
  align-items: center;
  justify-content: center;
  font-family: var(--font-display);
  font-size: 28px;
  font-weight: 700;
  border-radius: 10px;
}

.logo-text-lg {
  font-family: var(--font-display);
  font-size: 28px;
  font-weight: 700;
  letter-spacing: 0.12em;
  color: var(--surface);
}

.deco-title {
  font-size: 40px;
  font-weight: 700;
  color: var(--surface);
  line-height: 1.15;
}

.deco-title em {
  font-style: italic;
  color: var(--gold);
}

.deco-desc {
  font-size: 15px;
  color: rgba(255,255,255,0.45);
  line-height: 1.7;
  max-width: 360px;
}

.deco-blob {
  position: absolute;
  width: 400px;
  height: 400px;
  background: radial-gradient(circle, var(--gold) 0%, transparent 70%);
  opacity: 0.08;
  bottom: -100px;
  right: -100px;
  border-radius: 50%;
}

/* Right Form */
.auth-form-wrap {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 60px 40px;
  background: var(--surface);
}

.auth-form-inner {
  width: 100%;
  max-width: 400px;
  display: flex;
  flex-direction: column;
  gap: 32px;
}

.auth-form-header {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.auth-title {
  font-size: 32px;
  font-weight: 700;
  color: var(--ink);
}

.auth-sub {
  font-size: 15px;
  color: var(--ink-muted);
}

.auth-form {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

/* Input with suffix */
.input-with-suffix {
  position: relative;
}

.input-with-suffix .form-input {
  padding-right: 60px;
}

.input-suffix-btn {
  position: absolute;
  right: 12px;
  top: 50%;
  transform: translateY(-50%);
  font-size: 12px;
  color: var(--ink-muted);
  cursor: pointer;
  background: none;
  border: none;
}

.input-suffix-btn:hover {
  color: var(--ink);
}

.global-error {
  padding: 10px 14px;
  background: #fef2f2;
  border: 1px solid rgba(224,82,82,0.25);
  border-radius: var(--radius-sm);
}

.auth-footer {
  text-align: center;
  font-size: 14px;
  color: var(--ink-muted);
  display: flex;
  gap: 8px;
  justify-content: center;
}

.auth-footer a {
  color: var(--gold-dark);
  font-weight: 500;
}

.auth-footer a:hover {
  text-decoration: underline;
}
</style>
