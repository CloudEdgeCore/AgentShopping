<template>
  <div class="admin-page">
    <div class="admin-page-header">
      <div>
        <h2 class="admin-page-title">秒杀活动管理</h2>
        <p class="admin-page-sub">管理活动时间、状态和活动商品列表</p>
      </div>
      <button class="btn btn-primary" @click="openCreate">+ 新建秒杀活动</button>
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
            <th>活动名称</th>
            <th style="width:110px">活动状态</th>
            <th style="width:150px">活动时间</th>
            <th style="width:120px">活动商品数</th>
            <th style="width:150px">最低秒杀价</th>
            <th style="width:220px">SKU 列表（前3个）</th>
            <th style="width:140px">操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="!activities.length">
            <td colspan="8" class="empty-cell">暂无秒杀活动</td>
          </tr>
          <tr v-for="row in activities" :key="row.id">
            <td class="font-mono text-muted">{{ row.id }}</td>
            <td class="act-name">{{ row.name || '-' }}</td>
            <td>
              <span class="badge" :class="row.status === 1 ? 'badge-success' : 'badge-muted'">
                {{ row.status === 1 ? '启用' : '禁用' }}
              </span>
            </td>
            <td class="text-muted date-col">
              {{ fmtDate(row.startTime) }}<br />
              至 {{ fmtDate(row.endTime) }}
            </td>
            <td class="font-mono">{{ getItems(row.id).length }}</td>
            <td class="font-mono">
              <span v-if="getItems(row.id).length">¥{{ fmtMoney(getMinDiscountPrice(row.id)) }}</span>
              <span v-else>-</span>
            </td>
            <td class="font-mono text-muted">{{ getSkuPreview(row.id) }}</td>
            <td>
              <div class="action-btns">
                <button class="btn btn-ghost btn-xs" @click="openEdit(row)">编辑</button>
                <button class="btn btn-ghost btn-xs text-danger" @click="deleteActivity(row.id)">删除</button>
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
              <h3 class="modal-title">{{ editingId ? '编辑秒杀活动' : '新建秒杀活动' }}</h3>
              <button class="btn btn-ghost btn-icon" @click="showForm = false">×</button>
            </div>
            <form class="modal-body" @submit.prevent="handleSave">
              <div class="form-group">
                <label class="form-label">活动名称 *</label>
                <input v-model="form.name" type="text" class="form-input" :class="{ error: formErrors.name }" />
                <div class="form-error" v-if="formErrors.name">{{ formErrors.name }}</div>
              </div>

              <div class="form-row">
                <div class="form-group">
                  <label class="form-label">开始时间 *</label>
                  <input v-model="form.startTime" type="datetime-local" class="form-input" />
                </div>
                <div class="form-group">
                  <label class="form-label">结束时间 *</label>
                  <input v-model="form.endTime" type="datetime-local" class="form-input" />
                </div>
              </div>

              <div class="form-group">
                <label class="form-label">活动状态</label>
                <select v-model.number="form.status" class="form-select">
                  <option :value="1">启用</option>
                  <option :value="0">禁用</option>
                </select>
              </div>

              <div class="form-error" v-if="formErrors.time">{{ formErrors.time }}</div>

              <div class="item-header">
                <div class="item-title">活动商品 *</div>
                <button type="button" class="btn btn-outline btn-xs" @click="addItem">+ 添加商品</button>
              </div>

              <div class="item-list">
                <div class="item-row" v-for="(item, index) in form.items" :key="index">
                  <div class="item-grid">
                    <div class="form-group">
                      <label class="form-label">SKU ID *</label>
                      <input v-model.number="item.skuId" type="number" class="form-input" min="1" />
                    </div>
                    <div class="form-group">
                      <label class="form-label">原价（元）*</label>
                      <input v-model.number="item.originalPrice" type="number" class="form-input" min="0.01" step="0.01" />
                    </div>
                    <div class="form-group">
                      <label class="form-label">秒杀价（元）*</label>
                      <input v-model.number="item.discountPrice" type="number" class="form-input" min="0.01" step="0.01" />
                    </div>
                    <div class="form-group">
                      <label class="form-label">活动库存 *</label>
                      <input v-model.number="item.activityStock" type="number" class="form-input" min="1" />
                    </div>
                    <div class="form-group">
                      <label class="form-label">每人限购 *</label>
                      <input v-model.number="item.perUserLimit" type="number" class="form-input" min="1" />
                    </div>
                    <div class="form-group">
                      <label class="form-label">排序</label>
                      <input v-model.number="item.sort" type="number" class="form-input" min="0" />
                    </div>
                  </div>
                  <button type="button" class="btn btn-ghost btn-xs text-danger" @click="removeItem(index)" :disabled="form.items.length <= 1">
                    删除
                  </button>
                </div>
              </div>
              <div class="form-error" v-if="formErrors.items">{{ formErrors.items }}</div>

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

const activities = ref([])
const loading = ref(true)
const page = ref(1)
const pageSize = 15
const total = ref(0)
const totalPages = computed(() => Math.ceil(total.value / pageSize))
const statusFilter = ref(null)

const detailMap = ref({})
const showForm = ref(false)
const editingId = ref(null)
const saving = ref(false)

function createEmptyItem(sort = 0) {
  return {
    skuId: null,
    originalPrice: 0,
    discountPrice: 0,
    activityStock: 100,
    perUserLimit: 1,
    sort
  }
}

const form = reactive({
  name: '',
  startTime: '',
  endTime: '',
  status: 1,
  items: [createEmptyItem()]
})

const formErrors = reactive({
  name: '',
  time: '',
  items: ''
})

function fmtDate(val) {
  return val ? dayjs(val).format('YYYY-MM-DD HH:mm') : '--'
}

function fmtMoney(val) {
  const num = Number(val)
  return Number.isFinite(num) ? num.toFixed(2) : '--'
}

function doSearch() {
  page.value = 1
  load()
}

function getItems(activityId) {
  return detailMap.value[activityId] || []
}

function getMinDiscountPrice(activityId) {
  const items = getItems(activityId)
  if (!items.length) return null
  return Math.min(...items.map(item => Number(item.discountPrice || 0)))
}

function getSkuPreview(activityId) {
  const items = getItems(activityId)
  if (!items.length) {
    return '-'
  }
  const preview = items.slice(0, 3).map(item => item.skuId).join(', ')
  return items.length > 3 ? `${preview} ...` : preview
}

async function load() {
  loading.value = true
  try {
    const params = { current: page.value, size: pageSize }
    if (statusFilter.value !== null) {
      params.status = statusFilter.value
    }
    const res = await adminMarketingApi.getFlashSalePage(params)
    const data = res.data || {}
    activities.value = data.records || []
    total.value = data.total || 0

    const detailEntries = await Promise.all(
      activities.value.map(async (row) => {
        try {
          const detailRes = await adminMarketingApi.getFlashSaleDetail(row.id)
          return [row.id, detailRes.data?.items || []]
        } catch (_) {
          return [row.id, []]
        }
      })
    )
    detailMap.value = Object.fromEntries(detailEntries)
  } finally {
    loading.value = false
  }
}

function resetForm() {
  const start = dayjs().add(10, 'minute').second(0)
  const end = start.add(2, 'hour')
  form.name = ''
  form.startTime = start.format('YYYY-MM-DDTHH:mm')
  form.endTime = end.format('YYYY-MM-DDTHH:mm')
  form.status = 1
  form.items = [createEmptyItem()]
}

function resetErrors() {
  formErrors.name = ''
  formErrors.time = ''
  formErrors.items = ''
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
    const res = await adminMarketingApi.getFlashSaleDetail(row.id)
    const detail = res.data || {}
    form.name = detail.name || ''
    form.startTime = detail.startTime ? dayjs(detail.startTime).format('YYYY-MM-DDTHH:mm') : ''
    form.endTime = detail.endTime ? dayjs(detail.endTime).format('YYYY-MM-DDTHH:mm') : ''
    form.status = detail.status ?? 1
    form.items = (detail.items || []).map(item => ({
      skuId: item.skuId,
      originalPrice: Number(item.originalPrice || 0),
      discountPrice: Number(item.discountPrice || 0),
      activityStock: item.activityStock ?? 1,
      perUserLimit: item.perUserLimit ?? 1,
      sort: item.sort ?? 0
    }))
    if (!form.items.length) {
      form.items = [createEmptyItem()]
    }
    showForm.value = true
  } catch (e) {
    alert(e.message)
  }
}

function addItem() {
  form.items.push(createEmptyItem(form.items.length))
}

function removeItem(index) {
  if (form.items.length <= 1) {
    return
  }
  form.items.splice(index, 1)
}

function normalizeDateTime(value) {
  return value ? dayjs(value).format('YYYY-MM-DD HH:mm:ss') : null
}

function validateForm() {
  resetErrors()
  if (!form.name.trim()) {
    formErrors.name = '请输入活动名称'
    return false
  }

  const start = dayjs(form.startTime)
  const end = dayjs(form.endTime)
  if (!start.isValid() || !end.isValid()) {
    formErrors.time = '请完整填写开始和结束时间'
    return false
  }
  if (!end.isAfter(start)) {
    formErrors.time = '结束时间必须晚于开始时间'
    return false
  }

  if (!form.items.length) {
    formErrors.items = '至少添加一个活动商品'
    return false
  }

  const validItems = form.items.every(item => {
    if (!Number.isInteger(Number(item.skuId)) || Number(item.skuId) <= 0) return false
    if (Number(item.originalPrice) <= 0 || Number(item.discountPrice) <= 0) return false
    if (Number(item.discountPrice) >= Number(item.originalPrice)) return false
    if (!Number.isInteger(Number(item.activityStock)) || Number(item.activityStock) <= 0) return false
    if (!Number.isInteger(Number(item.perUserLimit)) || Number(item.perUserLimit) <= 0) return false
    if (!Number.isInteger(Number(item.sort)) || Number(item.sort) < 0) return false
    return true
  })
  if (!validItems) {
    formErrors.items = '请检查商品配置：SKU、价格、库存、限购必须合法且秒杀价小于原价'
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
    const payload = {
      name: form.name.trim(),
      startTime: normalizeDateTime(form.startTime),
      endTime: normalizeDateTime(form.endTime),
      status: form.status,
      items: form.items.map(item => ({
        skuId: Number(item.skuId),
        originalPrice: Number(item.originalPrice),
        discountPrice: Number(item.discountPrice),
        activityStock: Number(item.activityStock),
        perUserLimit: Number(item.perUserLimit),
        sort: Number(item.sort)
      }))
    }
    if (editingId.value) {
      await adminMarketingApi.updateFlashSale(editingId.value, payload)
    } else {
      await adminMarketingApi.createFlashSale(payload)
    }
    showForm.value = false
    await load()
  } catch (e) {
    alert(e.message)
  } finally {
    saving.value = false
  }
}

async function deleteActivity(id) {
  if (!confirm('确认删除该秒杀活动？')) {
    return
  }
  try {
    await adminMarketingApi.deleteFlashSale(id)
    await load()
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
.act-name { font-weight: 500; color: var(--ink); max-width: 220px; word-break: break-word; }
.date-col { font-size: 12px; line-height: 1.5; }
.font-mono { font-family: var(--font-mono); }
.text-muted { color: var(--ink-muted); }
.text-danger { color: var(--danger) !important; }
.action-btns { display: flex; gap: 4px; }
.btn-xs { padding: 4px 10px; font-size: 12px; }
.pagination { display: flex; align-items: center; gap: 12px; justify-content: center; }
.page-info { font-size: 13px; color: var(--ink-muted); min-width: 60px; text-align: center; }
.modal-backdrop { position: fixed; inset: 0; background: rgba(0,0,0,0.45); backdrop-filter: blur(4px); z-index: 500; display: flex; align-items: center; justify-content: center; padding: 24px; }
.modal { background: var(--surface); border-radius: var(--radius-lg); width: 100%; max-width: 880px; max-height: 90vh; display: flex; flex-direction: column; box-shadow: var(--shadow-lg); }
.modal-hd { display: flex; align-items: center; justify-content: space-between; padding: 20px 24px; border-bottom: 1px solid var(--border); }
.modal-title { font-size: 17px; font-weight: 700; }
.modal-body { overflow-y: auto; padding: 20px 24px; display: flex; flex-direction: column; gap: 16px; }
.modal-footer { display: flex; justify-content: flex-end; gap: 10px; padding-top: 8px; border-top: 1px solid var(--border); }
.form-row { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
.item-header { display: flex; align-items: center; justify-content: space-between; margin-top: 8px; }
.item-title { font-size: 14px; color: var(--ink); font-weight: 600; }
.item-list { display: flex; flex-direction: column; gap: 12px; }
.item-row { border: 1px solid var(--border); border-radius: var(--radius-sm); padding: 12px; display: flex; flex-direction: column; gap: 10px; }
.item-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; }
</style>
