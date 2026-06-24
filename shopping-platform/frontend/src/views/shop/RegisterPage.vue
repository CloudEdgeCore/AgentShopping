<template>
  <div class="login-page">
    <div class="auth-layout">
      <div class="auth-deco">
        <div class="auth-deco-content">
          <div class="deco-logo">
            <span class="logo-mark-lg">L</span>
            <span class="logo-text-lg">LUXE</span>
          </div>
          <h2 class="deco-title">加入我们<br /><em>开启品质购物之旅</em></h2>
          <p class="deco-desc">注册即可享受专属优惠、个性化推荐和极致购物体验</p>
        </div>
        <div class="deco-blob"></div>
      </div>

      <div class="auth-form-wrap">
        <div class="auth-form-inner">
          <div class="auth-form-header">
            <h1 class="auth-title">创建账户</h1>
            <p class="auth-sub">填写信息，立即开始购物</p>
          </div>

          <form @submit.prevent="handleSubmit" class="auth-form">
            <div class="form-row">
              <div class="form-group">
                <label class="form-label">用户名 <span class="required">*</span></label>
                <input v-model="form.username" type="text" class="form-input" :class="{ error: errors.username }" placeholder="4-32位字符" />
                <div class="form-error" v-if="errors.username">{{ errors.username }}</div>
              </div>
              <div class="form-group">
                <label class="form-label">昵称</label>
                <input v-model="form.nickname" type="text" class="form-input" placeholder="选填" />
              </div>
            </div>

            <div class="form-group">
              <label class="form-label">密码 <span class="required">*</span></label>
              <input v-model="form.password" type="password" class="form-input" :class="{ error: errors.password }" placeholder="6-32位密码" />
              <div class="form-error" v-if="errors.password">{{ errors.password }}</div>
            </div>

            <div class="form-row">
              <div class="form-group">
                <label class="form-label">手机号</label>
                <input v-model="form.mobile" type="text" class="form-input" :class="{ error: errors.mobile }" placeholder="选填，1开头11位" />
                <div class="form-error" v-if="errors.mobile">{{ errors.mobile }}</div>
              </div>
              <div class="form-group">
                <label class="form-label">邮箱</label>
                <input v-model="form.email" type="email" class="form-input" :class="{ error: errors.email }" placeholder="选填" />
                <div class="form-error" v-if="errors.email">{{ errors.email }}</div>
              </div>
            </div>

            <div class="form-group">
              <label class="form-label">性别</label>
              <div class="gender-options">
                <label v-for="g in genders" :key="g.value" class="gender-option" :class="{ active: form.gender === g.value }">
                  <input type="radio" :value="g.value" v-model="form.gender" />
                  {{ g.label }}
                </label>
              </div>
            </div>

            <div class="form-error global-error" v-if="globalError">{{ globalError }}</div>
            <div class="global-success" v-if="successMsg">{{ successMsg }}</div>

            <button type="submit" class="btn btn-primary btn-lg btn-block" :disabled="loading">
              <span v-if="loading" class="spinner spinner-gold"></span>
              {{ loading ? '注册中...' : '立即注册' }}
            </button>
          </form>

          <div class="auth-footer">
            <span>已有账户？</span>
            <RouterLink to="/login">立即登录</RouterLink>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const authStore = useAuthStore()

const form = reactive({ username: '', password: '', nickname: '', mobile: '', email: '', gender: 0 })
const errors = reactive({ username: '', password: '', mobile: '', email: '' })
const globalError = ref('')
const successMsg = ref('')
const loading = ref(false)

const genders = [{ value: 0, label: '保密' }, { value: 1, label: '男' }, { value: 2, label: '女' }]

function validate() {
  errors.username = form.username.length >= 4 && form.username.length <= 32 ? '' : '用户名需4-32位'
  errors.password = form.password.length >= 6 && form.password.length <= 32 ? '' : '密码需6-32位'
  errors.mobile = !form.mobile || /^1\d{10}$/.test(form.mobile) ? '' : '手机号格式不正确'
  errors.email = !form.email || /^[^@]+@[^@]+\.[^@]+$/.test(form.email) ? '' : '邮箱格式不正确'
  return !errors.username && !errors.password && !errors.mobile && !errors.email
}

async function handleSubmit() {
  globalError.value = ''
  successMsg.value = ''
  if (!validate()) return
  loading.value = true
  try {
    const payload = { username: form.username, password: form.password, gender: form.gender }
    if (form.nickname) payload.nickname = form.nickname
    if (form.mobile) payload.mobile = form.mobile
    if (form.email) payload.email = form.email
    await authStore.register(payload)
    successMsg.value = '注册成功！正在跳转登录...'
    setTimeout(() => router.push('/login'), 1500)
  } catch (e) {
    globalError.value = e.message || '注册失败'
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
/* Reuse login page styles */
.login-page { min-height: 100vh; display: flex; }
.auth-layout { display: grid; grid-template-columns: 1fr 1fr; width: 100%; }
@media (max-width: 768px) { .auth-layout { grid-template-columns: 1fr; } .auth-deco { display: none; } }
.auth-deco { background: var(--ink); position: relative; overflow: hidden; display: flex; align-items: center; padding: 60px; }
.auth-deco-content { position: relative; z-index: 1; display: flex; flex-direction: column; gap: 24px; }
.deco-logo { display: flex; align-items: center; gap: 12px; }
.logo-mark-lg { width: 48px; height: 48px; background: var(--gold); color: var(--ink); display: flex; align-items: center; justify-content: center; font-family: var(--font-display); font-size: 28px; font-weight: 700; border-radius: 10px; }
.logo-text-lg { font-family: var(--font-display); font-size: 28px; font-weight: 700; letter-spacing: 0.12em; color: var(--surface); }
.deco-title { font-size: 36px; font-weight: 700; color: var(--surface); line-height: 1.15; }
.deco-title em { font-style: italic; color: var(--gold); }
.deco-desc { font-size: 15px; color: rgba(255,255,255,0.45); line-height: 1.7; max-width: 360px; }
.deco-blob { position: absolute; width: 400px; height: 400px; background: radial-gradient(circle, var(--gold) 0%, transparent 70%); opacity: 0.08; bottom: -100px; right: -100px; border-radius: 50%; }
.auth-form-wrap { display: flex; align-items: center; justify-content: center; padding: 48px 40px; background: var(--surface); overflow-y: auto; }
.auth-form-inner { width: 100%; max-width: 480px; display: flex; flex-direction: column; gap: 28px; }
.auth-form-header { display: flex; flex-direction: column; gap: 8px; }
.auth-title { font-size: 32px; font-weight: 700; color: var(--ink); }
.auth-sub { font-size: 15px; color: var(--ink-muted); }
.auth-form { display: flex; flex-direction: column; gap: 18px; }
.form-row { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; }
.required { color: var(--danger); }
.global-error { padding: 10px 14px; background: #fef2f2; border: 1px solid rgba(224,82,82,0.25); border-radius: var(--radius-sm); font-size: 13px; color: var(--danger); }
.global-success { padding: 10px 14px; background: #f0faf5; border: 1px solid rgba(45,158,110,0.25); border-radius: var(--radius-sm); font-size: 13px; color: var(--success); }
.gender-options { display: flex; gap: 8px; }
.gender-option { display: flex; align-items: center; gap: 6px; padding: 7px 16px; border: 1.5px solid var(--border); border-radius: 100px; font-size: 13px; color: var(--ink-muted); cursor: pointer; transition: all var(--transition); }
.gender-option.active { border-color: var(--ink); color: var(--ink); font-weight: 500; }
.gender-option input { display: none; }
.auth-footer { text-align: center; font-size: 14px; color: var(--ink-muted); display: flex; gap: 8px; justify-content: center; }
.auth-footer a { color: var(--gold-dark); font-weight: 500; }
.auth-footer a:hover { text-decoration: underline; }
</style>
