<template>
  <div class="address-page">
    <div class="uc-section-title-row">
      <div class="uc-section-title">收货地址</div>
      <button class="btn btn-primary btn-sm" @click="openForm(null)">+ 新增地址</button>
    </div>

    <div v-if="loading" class="empty-state">
      <div class="spinner" style="width:24px;height:24px;border-width:2px"></div>
    </div>

    <div class="address-list" v-else-if="addresses.length">
      <div v-for="addr in addresses" :key="addr.id" class="address-card">
        <div class="address-card-hd">
          <div class="address-tags">
            <span v-if="addr.defaultAddress" class="badge badge-gold">默认</span>
          </div>
          <div class="address-card-actions">
            <button class="btn btn-ghost btn-sm" @click="openForm(addr)">编辑</button>
            <button class="btn btn-ghost btn-sm text-danger" @click="deleteAddress(addr.id)">删除</button>
            <button v-if="!addr.defaultAddress" class="btn btn-outline btn-sm" @click="setDefault(addr.id)">设为默认</button>
          </div>
        </div>
        <div class="address-name">{{ addr.receiverName }} <span class="font-mono">{{ addr.receiverMobile }}</span></div>
        <div class="address-detail">{{ [addr.provinceName, addr.cityName, addr.districtName, addr.detailAddress].filter(Boolean).join(' ') }}</div>
        <div v-if="addr.postalCode" class="address-postal">邮编：{{ addr.postalCode }}</div>
      </div>
    </div>

    <div class="empty-state" v-else>
      <div class="empty-state__icon">📍</div>
      <div class="empty-state__title">暂无收货地址</div>
      <button class="btn btn-outline" @click="openForm(null)">添加地址</button>
    </div>

    <!-- Address Form Modal -->
    <Teleport to="body">
      <Transition name="fade">
        <div class="modal-backdrop" v-if="showForm" @click.self="showForm = false">
          <div class="modal">
            <div class="modal-hd">
              <h3 class="modal-title">{{ editing ? '编辑地址' : '新增地址' }}</h3>
              <button class="btn btn-ghost btn-icon" @click="showForm = false">✕</button>
            </div>
            <form class="modal-body" @submit.prevent="handleSave">
              <div class="form-row">
                <div class="form-group">
                  <label class="form-label">收货人 *</label>
                  <input v-model="addrForm.receiverName" type="text" class="form-input" :class="{ error: addrErrors.receiverName }" placeholder="收货人姓名" required />
                  <div class="form-error" v-if="addrErrors.receiverName">{{ addrErrors.receiverName }}</div>
                </div>
                <div class="form-group">
                  <label class="form-label">手机号 *</label>
                  <input v-model="addrForm.receiverMobile" type="text" class="form-input" :class="{ error: addrErrors.receiverMobile }" placeholder="1开头11位" required />
                  <div class="form-error" v-if="addrErrors.receiverMobile">{{ addrErrors.receiverMobile }}</div>
                </div>
              </div>
              <div class="form-row">
                <div class="form-group">
                  <label class="form-label">省份</label>
                  <input v-model="addrForm.provinceName" type="text" class="form-input" placeholder="省份" />
                </div>
                <div class="form-group">
                  <label class="form-label">城市</label>
                  <input v-model="addrForm.cityName" type="text" class="form-input" placeholder="城市" />
                </div>
                <div class="form-group">
                  <label class="form-label">区/县</label>
                  <input v-model="addrForm.districtName" type="text" class="form-input" placeholder="区/县" />
                </div>
              </div>
              <div class="form-group">
                <label class="form-label">详细地址 *</label>
                <input v-model="addrForm.detailAddress" type="text" class="form-input" :class="{ error: addrErrors.detailAddress }" placeholder="街道、楼栋门牌号" required />
                <div class="form-error" v-if="addrErrors.detailAddress">{{ addrErrors.detailAddress }}</div>
              </div>
              <div class="form-group">
                <label class="form-label">邮政编码</label>
                <input v-model="addrForm.postalCode" type="text" class="form-input" placeholder="选填" maxlength="16" />
              </div>
              <label class="checkbox-label">
                <input type="checkbox" v-model="addrForm.defaultAddress" />
                设为默认地址
              </label>
              <div class="modal-footer">
                <button type="button" class="btn btn-outline" @click="showForm = false">取消</button>
                <button type="submit" class="btn btn-primary" :disabled="saving">
                  <span v-if="saving" class="spinner spinner-gold"></span>
                  {{ saving ? '保存中...' : '保存' }}
                </button>
              </div>
            </form>
          </div>
        </div>
      </Transition>
    </Teleport>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { userApi } from '@/api'

const addresses = ref([])
const loading = ref(true)
const showForm = ref(false)
const editing = ref(null)
const saving = ref(false)
const addrForm = reactive({ receiverName: '', receiverMobile: '', provinceName: '', cityName: '', districtName: '', detailAddress: '', postalCode: '', defaultAddress: false })
const addrErrors = reactive({ receiverName: '', receiverMobile: '', detailAddress: '' })

async function loadAddresses() {
  loading.value = true
  try {
    const res = await userApi.getAddresses()
    addresses.value = res.data || []
  } finally {
    loading.value = false
  }
}

function openForm(addr) {
  editing.value = addr
  if (addr) {
    Object.assign(addrForm, addr)
  } else {
    Object.assign(addrForm, { receiverName: '', receiverMobile: '', provinceName: '', cityName: '', districtName: '', detailAddress: '', postalCode: '', defaultAddress: false })
  }
  addrErrors.receiverName = ''
  addrErrors.receiverMobile = ''
  addrErrors.detailAddress = ''
  showForm.value = true
}

function validateAddr() {
  addrErrors.receiverName = addrForm.receiverName.trim() ? '' : '请填写收货人'
  addrErrors.receiverMobile = /^1\d{10}$/.test(addrForm.receiverMobile) ? '' : '手机号格式不正确'
  addrErrors.detailAddress = addrForm.detailAddress.trim() ? '' : '请填写详细地址'
  return !addrErrors.receiverName && !addrErrors.receiverMobile && !addrErrors.detailAddress
}

async function handleSave() {
  if (!validateAddr()) return
  saving.value = true
  try {
    const payload = { ...addrForm }
    if (editing.value) {
      await userApi.updateAddress(editing.value.id, payload)
    } else {
      await userApi.addAddress(payload)
    }
    showForm.value = false
    await loadAddresses()
  } catch (e) {
    alert(e.message)
  } finally {
    saving.value = false
  }
}

async function deleteAddress(id) {
  if (!confirm('确定删除该地址？')) return
  try {
    await userApi.deleteAddress(id)
    await loadAddresses()
  } catch (e) {
    alert(e.message)
  }
}

async function setDefault(id) {
  try {
    await userApi.setDefaultAddress(id)
    await loadAddresses()
  } catch (e) {
    alert(e.message)
  }
}

onMounted(loadAddresses)
</script>

<style scoped>
.address-page { display: flex; flex-direction: column; gap: 16px; }
.uc-section-title-row { display: flex; justify-content: space-between; align-items: center; }
.uc-section-title { font-size: 20px; font-weight: 700; color: var(--ink); }
.address-list { display: flex; flex-direction: column; gap: 12px; }
.address-card { background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius-md); padding: 20px; display: flex; flex-direction: column; gap: 8px; transition: box-shadow var(--transition); }
.address-card:hover { box-shadow: var(--shadow-sm); }
.address-card-hd { display: flex; justify-content: space-between; align-items: center; }
.address-card-actions { display: flex; gap: 4px; }
.address-tags { display: flex; gap: 6px; }
.address-name { font-size: 15px; font-weight: 600; color: var(--ink); display: flex; gap: 10px; }
.address-detail { font-size: 14px; color: var(--ink-muted); }
.address-postal { font-size: 12px; color: var(--ink-faint); }
.text-danger { color: var(--danger) !important; }
/* Modal */
.modal-backdrop { position: fixed; inset: 0; background: rgba(0,0,0,0.45); backdrop-filter: blur(4px); z-index: 500; display: flex; align-items: center; justify-content: center; padding: 24px; }
.modal { background: var(--surface); border-radius: var(--radius-lg); width: 100%; max-width: 540px; max-height: 90vh; display: flex; flex-direction: column; box-shadow: var(--shadow-lg); }
.modal-hd { display: flex; align-items: center; justify-content: space-between; padding: 20px 24px; border-bottom: 1px solid var(--border); }
.modal-title { font-size: 17px; font-weight: 700; font-family: var(--font-body); }
.modal-body { overflow-y: auto; padding: 20px 24px; display: flex; flex-direction: column; gap: 16px; }
.modal-footer { display: flex; justify-content: flex-end; gap: 10px; padding-top: 8px; border-top: 1px solid var(--border); }
.form-row { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
.checkbox-label { display: flex; align-items: center; gap: 8px; font-size: 14px; color: var(--ink-soft); cursor: pointer; }
.checkbox-label input { accent-color: var(--ink); cursor: pointer; }
</style>
