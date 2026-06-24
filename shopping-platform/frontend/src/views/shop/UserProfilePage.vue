<template>
  <div class="profile-page">
    <div class="uc-section-title">个人资料</div>
    <div class="profile-card" v-if="!loading">
      <form @submit.prevent="handleSave" class="profile-form">
        <div class="profile-avatar-row">
          <div class="profile-avatar-big">{{ avatarLetter }}</div>
          <div class="profile-avatar-info">
            <div class="profile-username">{{ authStore.userInfo?.username }}</div>
            <div class="profile-role">{{ authStore.isAdmin ? '管理员' : '普通用户' }}</div>
          </div>
        </div>
        <hr class="divider" />
        <div class="form-grid">
          <div class="form-group">
            <label class="form-label">昵称</label>
            <input v-model="form.nickname" type="text" class="form-input" placeholder="设置昵称" maxlength="64" />
          </div>
          <div class="form-group">
            <label class="form-label">性别</label>
            <select v-model="form.gender" class="form-select">
              <option :value="0">保密</option>
              <option :value="1">男</option>
              <option :value="2">女</option>
            </select>
          </div>
          <div class="form-group">
            <label class="form-label">手机号</label>
            <input v-model="form.mobile" type="text" class="form-input" :class="{ error: errors.mobile }" placeholder="1开头11位" maxlength="11" />
            <div class="form-error" v-if="errors.mobile">{{ errors.mobile }}</div>
          </div>
          <div class="form-group">
            <label class="form-label">邮箱</label>
            <input v-model="form.email" type="email" class="form-input" :class="{ error: errors.email }" placeholder="请输入邮箱" maxlength="128" />
            <div class="form-error" v-if="errors.email">{{ errors.email }}</div>
          </div>
          <div class="form-group form-group--full">
            <label class="form-label">头像链接</label>
            <input v-model="form.avatarUrl" type="url" class="form-input" placeholder="图片URL（选填）" maxlength="255" />
          </div>
        </div>
        <div class="form-error global-error" v-if="globalError">{{ globalError }}</div>
        <div class="global-success" v-if="successMsg">{{ successMsg }}</div>
        <div class="profile-actions">
          <button type="submit" class="btn btn-primary" :disabled="saving">
            <span v-if="saving" class="spinner spinner-gold"></span>
            {{ saving ? '保存中...' : '保存修改' }}
          </button>
        </div>
      </form>
    </div>
    <div class="empty-state" v-else>
      <div class="spinner" style="width:24px;height:24px;border-width:2px"></div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { userApi } from '@/api'

const authStore = useAuthStore()
const loading = ref(false)
const saving = ref(false)
const globalError = ref('')
const successMsg = ref('')
const errors = reactive({ mobile: '', email: '' })

const form = reactive({ nickname: '', gender: 0, mobile: '', email: '', avatarUrl: '' })

const avatarLetter = computed(() => {
  const name = authStore.userInfo?.nickname || authStore.userInfo?.username || '?'
  return name.charAt(0).toUpperCase()
})

function validate() {
  errors.mobile = !form.mobile || /^1\d{10}$/.test(form.mobile) ? '' : '手机号格式不正确'
  errors.email = !form.email || /^[^@]+@[^@]+\.[^@]+$/.test(form.email) ? '' : '邮箱格式不正确'
  return !errors.mobile && !errors.email
}

async function handleSave() {
  globalError.value = ''
  successMsg.value = ''
  if (!validate()) return
  saving.value = true
  try {
    const payload = { nickname: form.nickname || undefined, gender: form.gender }
    if (form.mobile) payload.mobile = form.mobile
    if (form.email) payload.email = form.email
    if (form.avatarUrl) payload.avatarUrl = form.avatarUrl
    const res = await userApi.updateProfile(payload)
    authStore.updateUserInfo(res.data)
    successMsg.value = '资料已更新！'
    setTimeout(() => successMsg.value = '', 3000)
  } catch (e) {
    globalError.value = e.message
  } finally {
    saving.value = false
  }
}

onMounted(() => {
  const info = authStore.userInfo
  if (info) {
    form.nickname = info.nickname || ''
    form.gender = info.gender || 0
    form.mobile = info.mobile || ''
    form.email = info.email || ''
    form.avatarUrl = info.avatarUrl || ''
  }
})
</script>

<style scoped>
.profile-page { display: flex; flex-direction: column; gap: 16px; }
.uc-section-title { font-size: 20px; font-weight: 700; color: var(--ink); }
.profile-card { background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius-md); padding: 32px; }
.profile-form { display: flex; flex-direction: column; gap: 24px; }
.profile-avatar-row { display: flex; align-items: center; gap: 16px; }
.profile-avatar-big { width: 64px; height: 64px; background: var(--ink); color: var(--gold); border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 28px; font-weight: 700; font-family: var(--font-display); flex-shrink: 0; }
.profile-username { font-size: 18px; font-weight: 700; color: var(--ink); }
.profile-role { font-size: 13px; color: var(--ink-muted); margin-top: 3px; }
.form-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
.form-group--full { grid-column: 1 / -1; }
.global-error { padding: 10px 14px; background: #fef2f2; border: 1px solid rgba(224,82,82,0.25); border-radius: var(--radius-sm); font-size: 13px; color: var(--danger); }
.global-success { padding: 10px 14px; background: #f0faf5; border: 1px solid rgba(45,158,110,0.25); border-radius: var(--radius-sm); font-size: 13px; color: var(--success); }
.profile-actions { display: flex; justify-content: flex-end; }
</style>
