<template>
  <div class="admin-page">
    <div class="admin-page-header">
      <div>
        <h2 class="admin-page-title">优惠券管理</h2>
        <p class="admin-page-sub">管理优惠券模板、状态和发放规则</p>
      </div>
      <button class="btn btn-primary" @click="openCreate">+ 新建优惠券</button>
    </div>

    <div class="filter-bar">
      <select v-model="statusFilter" class="form-select filter-select" @change="doSearch">
        <option :value="null">全部状态</option>
        <option :value="1">启用</option>
        <option :value="0">禁用</option>
      </select>
      <button class="btn btn-outline" @click="doSearch">查询</button>
    </div>

    <div class="admin-table-wrap">
      <div v-if="loading" class="admin-loading">
        <div class="spinner" style="width:28px;height:28px;border-width:2px"></div>
      </div>
      <table v-else class="admin-table">
        <thead>
          <tr>
            <th style="width:72px">ID</th>
            <th>名称</th>
            <th style="width:110px">类型</th>
            <th style="width:140px">优惠值</th>
            <th style="width:110px">门槛</th>
            <th style="width:130px">总量 / 已领 / 剩余</th>
            <th style="width:150px">适用范围</th>
            <th style="width:170px">领取时间</th>
            <th style="width:170px">使用时间</th>
            <th style="width:80px">状态</th>
            <th style="width:140px">操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="!coupons.length">
            <td colspan="11" class="empty-cell">暂无优惠券模板</td>
          </tr>
          <tr v-for="row in coupons" :key="row.id">
            <td class="font-mono text-muted">{{ row.id }}</td>
            <td class="coupon-name">{{ row.name }}</td>
            <td>{{ getCouponTypeLabel(row.couponType) }}</td>
            <td class="font-mono">
              <span v-if="row.couponType === 10">减 ¥{{ fmtMoney(row.discountAmount) }}</span>
              <span v-else>{{ fmtMoney(row.discountRate) }} 折</span>
            </td>
            <td>{{ Number(row.thresholdAmount || 0) > 0 ? `满 ¥${fmtMoney(row.thresholdAmount)}` : '无门槛' }}</td>
            <td class="font-mono">
              {{ row.totalCount || 0 }} / {{ row.claimedCount || 0 }} / {{ remainCount(row) }}
            </td>
            <td>{{ getScopeLabel(row.scopeType) }}</td>
            <td class="text-muted date-col">
              {{ fmtDate(row.receiveStartTime) }}<br />
              至 {{ fmtDate(row.receiveEndTime) }}
            </td>
            <td class="text-muted date-col">
              {{ fmtDate(row.validFrom) }}<br />
              至 {{ fmtDate(row.validTo) }}
            </td>
            <td>
              <span class="badge" :class="row.status === 1 ? 'badge-success' : 'badge-muted'">
                {{ row.status === 1 ? '启用' : '禁用' }}
              </span>
            </td>
            <td>
              <div class="action-btns">
                <button class="btn btn-ghost btn-xs" @click="openEdit(row)">编辑</button>
                <button
                  class="btn btn-xs"
                  :class="row.status === 1 ? 'btn-ghost text-danger' : 'btn-outline'"
                  @click="toggleEnable(row)"
                >
                  {{ row.status === 1 ? '禁用' : '启用' }}
                </button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <div class="pagination" v-if="total > pageSize">
      <button class="btn btn-ghost btn-sm" :disabled="page <= 1" @click="page--; load()">上一页</button>
      <span class="page-info">{{ page }} / {{ totalPages }}</span>
      <button class="btn btn-ghost btn-sm" :disabled="page >= totalPages" @click="page++; load()">下一页</button>
    </div>

    <Teleport to="body">
      <Transition name="fade">
        <div class="modal-backdrop" v-if="showForm" @click.self="showForm = false">
          <div class="modal">
            <div class="modal-hd">
              <h3 class="modal-title">{{ editingId ? '编辑优惠券模板' : '新建优惠券模板' }}</h3>
              <button class="btn btn-ghost btn-icon" @click="showForm = false">×</button>
            </div>

            <form class="modal-body" @submit.prevent="handleSave">
              <div class="form-group">
                <label class="form-label">名称 *</label>
                <input v-model="couponForm.name" type="text" class="form-input" :class="{ error: formErrors.name }" placeholder="如：新人满减券" />
                <div class="form-error" v-if="formErrors.name">{{ formErrors.name }}</div>
              </div>

              <div class="form-row">
                <div class="form-group">
                  <label class="form-label">优惠类型 *</label>
                  <select v-model.number="couponForm.couponType" class="form-select">
                    <option :value="10">满减券</option>
                    <option :value="20">折扣券</option>
                  </select>
                </div>
                <div class="form-group">
                  <label class="form-label">使用门槛（元）*</label>
                  <input v-model.number="couponForm.thresholdAmount" type="number" class="form-input" min="0" step="0.01" />
                </div>
              </div>

              <div class="form-row">
                <div class="form-group" v-if="couponForm.couponType === 10">
                  <label class="form-label">减免金额（元）*</label>
                  <input v-model.number="couponForm.discountAmount" type="number" class="form-input" min="0.01" step="0.01" />
                </div>
                <div class="form-group" v-else>
                  <label class="form-label">折扣值（0-10）*</label>
                  <input v-model.number="couponForm.discountRate" type="number" class="form-input" min="0.1" max="10" step="0.1" />
                </div>
                <div class="form-group">
                  <label class="form-label">每人限领 *</label>
                  <input v-model.number="couponForm.perUserLimit" type="number" class="form-input" min="1" max="100" />
                </div>
              </div>

              <div class="form-row">
                <div class="form-group">
                  <label class="form-label">发放总量 *</label>
                  <input v-model.number="couponForm.totalCount" type="number" class="form-input" min="1" />
                </div>
                <div class="form-group">
                  <label class="form-label">状态</label>
                  <select v-model.number="couponForm.status" class="form-select">
                    <option :value="1">启用</option>
                    <option :value="0">禁用</option>
                  </select>
                </div>
              </div>

              <div class="form-row">
                <div class="form-group">
                  <label class="form-label">适用范围 *</label>
                  <select v-model.number="couponForm.scopeType" class="form-select">
                    <option :value="10">全场通用</option>
                    <option :value="20">指定类目</option>
                    <option :value="30">指定商品（SPU）</option>
                    <option :value="40">指定 SKU</option>
                  </select>
                </div>
                <div class="form-group" v-if="couponForm.scopeType !== 10">
                  <label class="form-label">范围ID（逗号分隔）*</label>
                  <input
                    v-model="couponForm.scopeIdsText"
                    type="text"
                    class="form-input"
                    :class="{ error: formErrors.scopeIds }"
                    placeholder="例如：1001,1002"
                  />
                  <div class="form-error" v-if="formErrors.scopeIds">{{ formErrors.scopeIds }}</div>
                </div>
              </div>

              <div class="form-row">
                <div class="form-group">
                  <label class="form-label">领取开始时间 *</label>
                  <input v-model="couponForm.receiveStartTime" type="datetime-local" class="form-input" />
                </div>
                <div class="form-group">
                  <label class="form-label">领取结束时间 *</label>
                  <input v-model="couponForm.receiveEndTime" type="datetime-local" class="form-input" />
                </div>
              </div>

              <div class="form-row">
                <div class="form-group">
                  <label class="form-label">生效开始时间 *</label>
                  <input v-model="couponForm.validFrom" type="datetime-local" class="form-input" />
                </div>
                <div class="form-group">
                  <label class="form-label">生效结束时间 *</label>
                  <input v-model="couponForm.validTo" type="datetime-local" class="form-input" />
                </div>
              </div>

              <div class="form-error" v-if="formErrors.time">{{ formErrors.time }}</div>

              <div class="form-group">
                <label class="form-label">说明</label>
                <textarea v-model="couponForm.description" class="form-input" rows="3" placeholder="可选，最多 500 字"></textarea>
              </div>

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
import { computed, onMounted, reactive, ref } from 'vue'
import dayjs from 'dayjs'
import { adminMarketingApi } from '@/api'

const coupons = ref([])
const loading = ref(true)
const page = ref(1)
const pageSize = 15
const total = ref(0)
const totalPages = computed(() => Math.ceil(total.value / pageSize))
const statusFilter = ref(null)

const showForm = ref(false)
const editingId = ref(null)
const saving = ref(false)

const defaultForm = () => {
  const start = dayjs().add(5, 'minute').second(0)
  const end = start.add(7, 'day')
  return {
    name: '',
    couponType: 10,
    thresholdAmount: 0,
    discountAmount: 10,
    discountRate: 8.5,
    totalCount: 100,
    perUserLimit: 1,
    scopeType: 10,
    scopeIdsText: '',
    receiveStartTime: start.format('YYYY-MM-DDTHH:mm'),
    receiveEndTime: end.format('YYYY-MM-DDTHH:mm'),
    validFrom: start.format('YYYY-MM-DDTHH:mm'),
    validTo: end.format('YYYY-MM-DDTHH:mm'),
    description: '',
    status: 1
  }
}

const couponForm = reactive(defaultForm())
const formErrors = reactive({
  name: '',
  scopeIds: '',
  time: ''
})

function fmtMoney(val) {
  const num = Number(val)
  return Number.isFinite(num) ? num.toFixed(2) : '--'
}

function fmtDate(val) {
  return val ? dayjs(val).format('YYYY-MM-DD HH:mm') : '--'
}

function getCouponTypeLabel(type) {
  return type === 10 ? '满减券' : type === 20 ? '折扣券' : '-'
}

function getScopeLabel(scopeType) {
  if (scopeType === 10) return '全场通用'
  if (scopeType === 20) return '指定类目'
  if (scopeType === 30) return '指定商品'
  if (scopeType === 40) return '指定SKU'
  return '-'
}

function remainCount(row) {
  const totalCount = Number(row.totalCount || 0)
  const claimedCount = Number(row.claimedCount || 0)
  return Math.max(0, totalCount - claimedCount)
}

function doSearch() {
  page.value = 1
  load()
}

async function load() {
  loading.value = true
  try {
    const params = { current: page.value, size: pageSize }
    if (statusFilter.value !== null) {
      params.status = statusFilter.value
    }
    const res = await adminMarketingApi.getCouponPage(params)
    const data = res.data || {}
    coupons.value = data.records || []
    total.value = data.total || 0
  } finally {
    loading.value = false
  }
}

function resetErrors() {
  formErrors.name = ''
  formErrors.scopeIds = ''
  formErrors.time = ''
}

function resetForm() {
  Object.assign(couponForm, defaultForm())
}

function openCreate() {
  editingId.value = null
  resetErrors()
  resetForm()
  showForm.value = true
}

async function openEdit(row) {
  editingId.value = row.id
  resetErrors()
  try {
    const res = await adminMarketingApi.getCouponDetail(row.id)
    const detail = res.data || {}
    Object.assign(couponForm, {
      name: detail.name || '',
      couponType: detail.couponType ?? 10,
      thresholdAmount: Number(detail.thresholdAmount || 0),
      discountAmount: Number(detail.discountAmount || 0),
      discountRate: Number(detail.discountRate || 0),
      totalCount: detail.totalCount ?? 100,
      perUserLimit: detail.perUserLimit ?? 1,
      scopeType: detail.scopeType ?? 10,
      scopeIdsText: Array.isArray(detail.scopeIds) ? detail.scopeIds.join(',') : '',
      receiveStartTime: detail.receiveStartTime ? dayjs(detail.receiveStartTime).format('YYYY-MM-DDTHH:mm') : '',
      receiveEndTime: detail.receiveEndTime ? dayjs(detail.receiveEndTime).format('YYYY-MM-DDTHH:mm') : '',
      validFrom: detail.validFrom ? dayjs(detail.validFrom).format('YYYY-MM-DDTHH:mm') : '',
      validTo: detail.validTo ? dayjs(detail.validTo).format('YYYY-MM-DDTHH:mm') : '',
      description: detail.description || '',
      status: detail.status ?? 1
    })
    showForm.value = true
  } catch (e) {
    alert(e.message)
  }
}

function parseScopeIds(scopeType, text) {
  if (scopeType === 10) {
    return []
  }
  return (text || '')
    .split(/[,，\s]+/)
    .map(item => Number(item.trim()))
    .filter(num => Number.isInteger(num) && num > 0)
}

function normalizeDateTime(value) {
  return value ? dayjs(value).format('YYYY-MM-DD HH:mm:ss') : null
}

function validateForm() {
  resetErrors()
  if (!couponForm.name.trim()) {
    formErrors.name = '请输入名称'
    return false
  }
  const receiveStart = dayjs(couponForm.receiveStartTime)
  const receiveEnd = dayjs(couponForm.receiveEndTime)
  const validFrom = dayjs(couponForm.validFrom)
  const validTo = dayjs(couponForm.validTo)
  if (!receiveStart.isValid() || !receiveEnd.isValid() || !validFrom.isValid() || !validTo.isValid()) {
    formErrors.time = '请完整填写所有时间'
    return false
  }
  if (!receiveEnd.isAfter(receiveStart) || !validTo.isAfter(validFrom)) {
    formErrors.time = '结束时间必须晚于开始时间'
    return false
  }
  const scopeIds = parseScopeIds(couponForm.scopeType, couponForm.scopeIdsText)
  if (couponForm.scopeType !== 10 && scopeIds.length === 0) {
    formErrors.scopeIds = '当前范围需要至少一个 ID'
    return false
  }
  return true
}

async function handleSave() {
  if (!validateForm()) {
    return
  }

  saving.value = true
  try {
    const scopeIds = parseScopeIds(couponForm.scopeType, couponForm.scopeIdsText)
    const payload = {
      name: couponForm.name.trim(),
      couponType: couponForm.couponType,
      thresholdAmount: Number(couponForm.thresholdAmount || 0),
      discountAmount: couponForm.couponType === 10 ? Number(couponForm.discountAmount || 0) : 0,
      discountRate: couponForm.couponType === 20 ? Number(couponForm.discountRate || 0) : null,
      totalCount: Number(couponForm.totalCount || 0),
      perUserLimit: Number(couponForm.perUserLimit || 1),
      scopeType: couponForm.scopeType,
      scopeIds,
      receiveStartTime: normalizeDateTime(couponForm.receiveStartTime),
      receiveEndTime: normalizeDateTime(couponForm.receiveEndTime),
      validFrom: normalizeDateTime(couponForm.validFrom),
      validTo: normalizeDateTime(couponForm.validTo),
      description: couponForm.description?.trim() || null,
      status: couponForm.status
    }
    if (editingId.value) {
      await adminMarketingApi.updateCoupon(editingId.value, payload)
    } else {
      await adminMarketingApi.createCoupon(payload)
    }
    showForm.value = false
    await load()
  } catch (e) {
    alert(e.message)
  } finally {
    saving.value = false
  }
}

async function toggleEnable(row) {
  try {
    if (row.status === 1) {
      await adminMarketingApi.disableCoupon(row.id)
      row.status = 0
    } else {
      await adminMarketingApi.enableCoupon(row.id)
      row.status = 1
    }
  } catch (e) {
    alert(e.message)
  }
}

onMounted(load)
</script>

<style scoped>
.admin-page { display: flex; flex-direction: column; gap: 20px; }
.admin-page-header { display: flex; justify-content: space-between; align-items: flex-start; }
.admin-page-title { font-size: 22px; font-weight: 700; color: var(--ink); }
.admin-page-sub { font-size: 13px; color: var(--ink-muted); margin-top: 4px; }
.filter-bar { display: flex; gap: 10px; align-items: center; }
.filter-select { min-width: 120px; }
.admin-table-wrap { border: 1px solid var(--border); border-radius: var(--radius-md); overflow: hidden; min-height: 100px; position: relative; }
.admin-loading { display: flex; align-items: center; justify-content: center; padding: 60px; }
.admin-table { width: 100%; border-collapse: collapse; }
.admin-table th { padding: 12px 14px; background: var(--surface-dim); font-size: 12px; font-weight: 600; color: var(--ink-muted); text-align: left; border-bottom: 1px solid var(--border); white-space: nowrap; }
.admin-table td { padding: 12px 14px; border-bottom: 1px solid var(--border); font-size: 13px; color: var(--ink-soft); vertical-align: middle; }
.admin-table tr:last-child td { border-bottom: none; }
.admin-table tr:hover td { background: var(--surface-dim); }
.empty-cell { text-align: center; color: var(--ink-faint); padding: 48px !important; font-size: 13px; }
.coupon-name { font-weight: 500; color: var(--ink); max-width: 180px; word-break: break-word; }
.date-col { font-size: 12px; line-height: 1.5; }
.font-mono { font-family: var(--font-mono); }
.text-muted { color: var(--ink-muted); }
.text-danger { color: var(--danger) !important; }
.action-btns { display: flex; gap: 4px; }
.btn-xs { padding: 4px 10px; font-size: 12px; }
.pagination { display: flex; align-items: center; gap: 12px; justify-content: center; }
.page-info { font-size: 13px; color: var(--ink-muted); min-width: 60px; text-align: center; }
.modal-backdrop { position: fixed; inset: 0; background: rgba(0,0,0,0.45); backdrop-filter: blur(4px); z-index: 500; display: flex; align-items: center; justify-content: center; padding: 24px; }
.modal { background: var(--surface); border-radius: var(--radius-lg); width: 100%; max-width: 720px; max-height: 90vh; display: flex; flex-direction: column; box-shadow: var(--shadow-lg); }
.modal-hd { display: flex; align-items: center; justify-content: space-between; padding: 20px 24px; border-bottom: 1px solid var(--border); }
.modal-title { font-size: 17px; font-weight: 700; }
.modal-body { overflow-y: auto; padding: 20px 24px; display: flex; flex-direction: column; gap: 16px; }
.modal-footer { display: flex; justify-content: flex-end; gap: 10px; padding-top: 8px; border-top: 1px solid var(--border); }
.form-row { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
</style>
