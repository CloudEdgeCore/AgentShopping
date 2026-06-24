<template>
  <div class="admin-page">
    <div class="admin-page-header">
      <div>
        <h2 class="admin-page-title">品牌管理</h2>
        <p class="admin-page-sub">管理平台合作品牌</p>
      </div>
      <button class="btn btn-primary" @click="openForm(null)">+ 新增品牌</button>
    </div>

    <div class="filter-bar">
      <input v-model="keyword" type="text" class="form-input filter-input" placeholder="搜索品牌名称..." @keyup.enter="doSearch" />
      <button class="btn btn-outline" @click="doSearch">搜索</button>
    </div>

    <div class="admin-table-wrap">
      <div v-if="loading" class="admin-loading">
        <div class="spinner" style="width:28px;height:28px;border-width:2px"></div>
      </div>
      <table v-else class="admin-table">
        <thead>
          <tr>
            <th style="width:60px">ID</th>
            <th style="width:64px">Logo</th>
            <th>品牌名称</th>
            <th>描述</th>
            <th>排序</th>
            <th>状态</th>
            <th style="width:120px">操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="!brands.length">
            <td colspan="7" class="empty-cell">暂无品牌数据</td>
          </tr>
          <tr v-for="b in brands" :key="b.id">
            <td class="font-mono text-muted">{{ b.id }}</td>
            <td>
              <img v-if="b.logoUrl" :src="b.logoUrl" class="brand-logo" />
              <div v-else class="brand-logo-placeholder">{{ (b.name || '?').charAt(0).toUpperCase() }}</div>
            </td>
            <td class="brand-name">{{ b.name }}</td>
            <td class="text-muted">{{ b.description || '-' }}</td>
            <td class="text-muted">{{ b.sort ?? 0 }}</td>
            <td>
              <span class="badge" :class="b.status === 1 ? 'badge-success' : 'badge-muted'">{{ b.status === 1 ? '启用' : '禁用' }}</span>
            </td>
            <td>
              <div class="action-btns">
                <button class="btn btn-ghost btn-xs" @click="openForm(b)">编辑</button>
                <button class="btn btn-ghost btn-xs text-danger" @click="deleteBrand(b.id)">删除</button>
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
              <h3 class="modal-title">{{ editing ? '编辑品牌' : '新增品牌' }}</h3>
              <button class="btn btn-ghost btn-icon" @click="showForm = false">✕</button>
            </div>
            <form class="modal-body" @submit.prevent="handleSave">
              <div class="form-group">
                <label class="form-label">品牌名称 *</label>
                <input v-model="brandForm.name" type="text" class="form-input" :class="{ error: formErrors.name }" placeholder="品牌名称" />
                <div class="form-error" v-if="formErrors.name">{{ formErrors.name }}</div>
              </div>
              <div class="form-row">
                <div class="form-group">
                  <label class="form-label">排序</label>
                  <input v-model.number="brandForm.sort" type="number" class="form-input" min="0" />
                </div>
                <div class="form-group">
                  <label class="form-label">状态</label>
                  <select v-model.number="brandForm.status" class="form-select">
                    <option :value="1">启用</option>
                    <option :value="0">禁用</option>
                  </select>
                </div>
              </div>
              <div class="form-group">
                <label class="form-label">Logo URL</label>
                <input v-model="brandForm.logoUrl" type="text" class="form-input" placeholder="品牌 LOGO 图片 URL（选填）" />
                <img v-if="brandForm.logoUrl" :src="brandForm.logoUrl" style="margin-top:8px;height:40px;object-fit:contain" />
              </div>
              <div class="form-group">
                <label class="form-label">品牌描述</label>
                <textarea v-model="brandForm.description" class="form-textarea" rows="3" placeholder="品牌介绍（选填）"></textarea>
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
import { ref, reactive, computed, onMounted } from 'vue'
import { adminBrandApi } from '@/api'

const brands = ref([])
const loading = ref(true)
const page = ref(1)
const pageSize = 20
const total = ref(0)
const totalPages = computed(() => Math.ceil(total.value / pageSize))
const keyword = ref('')

const showForm = ref(false)
const editing = ref(null)
const saving = ref(false)
const brandForm = reactive({ name: '', logoUrl: '', description: '', sort: 0, status: 1 })
const formErrors = reactive({ name: '' })

function doSearch() {
  page.value = 1
  load()
}

async function load() {
  loading.value = true
  try {
    const res = await adminBrandApi.getList({
      current: page.value,
      size: pageSize,
      keyword: keyword.value || undefined
    })
    const data = res.data || {}
    brands.value = data.records || data.list || data || []
    total.value = data.total || brands.value.length
  } finally {
    loading.value = false
  }
}

function openForm(brand) {
  editing.value = brand
  formErrors.name = ''
  if (!brand) {
    Object.assign(brandForm, { name: '', logoUrl: '', description: '', sort: 0, status: 1 })
    showForm.value = true
    return
  }
  Object.assign(brandForm, {
    name: brand.name || '',
    logoUrl: brand.logoUrl || '',
    description: brand.description || '',
    sort: brand.sort ?? 0,
    status: brand.status ?? 1
  })
  showForm.value = true
}

async function handleSave() {
  formErrors.name = brandForm.name.trim() ? '' : '请填写品牌名称'
  if (formErrors.name) return

  saving.value = true
  try {
    const payload = {
      name: brandForm.name.trim(),
      logoUrl: brandForm.logoUrl?.trim() || undefined,
      description: brandForm.description?.trim() || undefined,
      sort: brandForm.sort ?? 0,
      status: brandForm.status ?? 1
    }
    if (editing.value) {
      await adminBrandApi.update(editing.value.id, payload)
    } else {
      await adminBrandApi.create(payload)
    }
    showForm.value = false
    await load()
  } catch (e) {
    alert(e.message)
  } finally {
    saving.value = false
  }
}

async function deleteBrand(id) {
  if (!confirm('确定删除该品牌？')) return
  try {
    await adminBrandApi.delete(id)
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
.filter-bar { display: flex; gap: 10px; }
.filter-input { max-width: 320px; }
.admin-table-wrap { border: 1px solid var(--border); border-radius: var(--radius-md); overflow: hidden; min-height: 100px; position: relative; }
.admin-loading { display: flex; align-items: center; justify-content: center; padding: 60px; }
.admin-table { width: 100%; border-collapse: collapse; }
.admin-table th { padding: 12px 14px; background: var(--surface-dim); font-size: 12px; font-weight: 600; color: var(--ink-muted); text-align: left; border-bottom: 1px solid var(--border); }
.admin-table td { padding: 12px 14px; border-bottom: 1px solid var(--border); font-size: 14px; color: var(--ink-soft); vertical-align: middle; }
.admin-table tr:last-child td { border-bottom: none; }
.admin-table tr:hover td { background: var(--surface-dim); }
.empty-cell { text-align: center; color: var(--ink-faint); padding: 48px !important; font-size: 13px; }
.brand-logo { width: 44px; height: 44px; object-fit: contain; border-radius: var(--radius-sm); border: 1px solid var(--border); }
.brand-logo-placeholder { width: 44px; height: 44px; background: var(--ink); color: var(--gold); border-radius: var(--radius-sm); display: flex; align-items: center; justify-content: center; font-weight: 700; font-size: 18px; }
.brand-name { font-weight: 500; color: var(--ink); }
.font-mono { font-family: var(--font-mono); }
.text-muted { color: var(--ink-muted); }
.text-danger { color: var(--danger) !important; }
.action-btns { display: flex; gap: 4px; }
.btn-xs { padding: 4px 10px; font-size: 12px; }
.pagination { display: flex; align-items: center; gap: 12px; justify-content: center; }
.page-info { font-size: 13px; color: var(--ink-muted); min-width: 60px; text-align: center; }
.modal-backdrop { position: fixed; inset: 0; background: rgba(0,0,0,0.45); backdrop-filter: blur(4px); z-index: 500; display: flex; align-items: center; justify-content: center; padding: 24px; }
.modal { background: var(--surface); border-radius: var(--radius-lg); width: 100%; max-width: 480px; max-height: 90vh; display: flex; flex-direction: column; box-shadow: var(--shadow-lg); }
.modal-hd { display: flex; align-items: center; justify-content: space-between; padding: 20px 24px; border-bottom: 1px solid var(--border); }
.modal-title { font-size: 17px; font-weight: 700; }
.modal-body { overflow-y: auto; padding: 20px 24px; display: flex; flex-direction: column; gap: 16px; }
.modal-footer { display: flex; justify-content: flex-end; gap: 10px; padding-top: 8px; border-top: 1px solid var(--border); }
.form-row { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
</style>
