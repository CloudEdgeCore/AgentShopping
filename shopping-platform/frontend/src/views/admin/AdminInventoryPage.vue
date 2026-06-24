<template>
  <div class="admin-page">
    <div class="admin-page-header">
      <div>
        <h2 class="admin-page-title">库存管理</h2>
        <p class="admin-page-sub">按 SKU 维度管理总库存、可用库存和锁定库存</p>
      </div>
    </div>

    <div class="filter-bar">
      <input
        v-model="keyword"
        type="text"
        class="form-input filter-input"
        placeholder="搜索 SPU / SKU 名称"
        @keyup.enter="doSearch"
      />
      <button class="btn btn-outline" @click="doSearch">搜索</button>
    </div>

    <div class="admin-table-wrap">
      <div v-if="loading" class="admin-loading">
        <div class="spinner" style="width:28px;height:28px;border-width:2px"></div>
      </div>
      <table v-else class="admin-table">
        <thead>
          <tr>
            <th style="width:92px">SKU ID</th>
            <th>商品名称</th>
            <th>规格</th>
            <th style="width:88px">总库存</th>
            <th style="width:88px">可用库存</th>
            <th style="width:88px">锁定库存</th>
            <th style="width:80px">状态</th>
            <th style="width:220px">操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="!stocks.length">
            <td colspan="8" class="empty-cell">暂无库存数据</td>
          </tr>
          <tr v-for="row in stocks" :key="row.skuId">
            <td class="font-mono text-muted">{{ row.skuId }}</td>
            <td>
              <div class="sku-product-name">{{ row.spuName || '-' }}</div>
            </td>
            <td class="text-muted">{{ row.skuName || '-' }}</td>
            <td>
              <template v-if="editingSkuId === row.skuId">
                <input
                  v-model.number="editForm.totalStock"
                  type="number"
                  class="form-input form-input--sm"
                  style="width:88px"
                  min="0"
                />
              </template>
              <template v-else>
                <span class="stock-val">{{ row.totalStock ?? 0 }}</span>
              </template>
            </td>
            <td>
              <span class="stock-val" :class="{ 'stock-low': (row.availableStock ?? 0) <= 5 }">
                {{ row.availableStock ?? 0 }}
              </span>
            </td>
            <td class="text-muted">{{ row.lockedStock ?? 0 }}</td>
            <td>
              <template v-if="editingSkuId === row.skuId">
                <select v-model.number="editForm.status" class="form-select form-select--sm">
                  <option :value="1">启用</option>
                  <option :value="0">禁用</option>
                </select>
              </template>
              <template v-else>
                <span class="badge" :class="row.status === 1 ? 'badge-success' : 'badge-muted'">
                  {{ row.status === 1 ? '启用' : '禁用' }}
                </span>
              </template>
            </td>
            <td>
              <div class="action-btns" v-if="editingSkuId === row.skuId">
                <button class="btn btn-gold btn-xs" @click="saveStock(row)">保存</button>
                <button class="btn btn-ghost btn-xs" @click="cancelEdit">取消</button>
              </div>
              <div class="action-btns" v-else>
                <button class="btn btn-ghost btn-xs" @click="startEdit(row)">调整</button>
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
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { adminInventoryApi } from '@/api'

const stocks = ref([])
const loading = ref(true)
const page = ref(1)
const pageSize = 20
const total = ref(0)
const totalPages = computed(() => Math.ceil(total.value / pageSize))
const keyword = ref('')

const editingSkuId = ref(null)
const editForm = reactive({
  totalStock: 0,
  status: 1
})

function doSearch() {
  page.value = 1
  load()
}

async function load() {
  loading.value = true
  try {
    const params = {
      current: page.value,
      size: pageSize,
      keyword: keyword.value?.trim() || undefined
    }
    const res = await adminInventoryApi.getPage(params)
    const data = res.data || {}
    stocks.value = data.records || []
    total.value = data.total || 0
  } finally {
    loading.value = false
  }
}

function startEdit(row) {
  editingSkuId.value = row.skuId
  editForm.totalStock = row.totalStock ?? 0
  editForm.status = row.status ?? 1
}

function cancelEdit() {
  editingSkuId.value = null
}

async function saveStock(row) {
  if (editForm.totalStock < 0) {
    alert('总库存不能小于 0')
    return
  }
  try {
    const res = await adminInventoryApi.updateStock(row.skuId, {
      totalStock: editForm.totalStock,
      status: editForm.status
    })
    const data = res.data || {}
    row.totalStock = data.totalStock
    row.availableStock = data.availableStock
    row.lockedStock = data.lockedStock
    row.status = data.status
    editingSkuId.value = null
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
.admin-table th { padding: 12px 14px; background: var(--surface-dim); font-size: 12px; font-weight: 600; color: var(--ink-muted); text-align: left; border-bottom: 1px solid var(--border); white-space: nowrap; }
.admin-table td { padding: 12px 14px; border-bottom: 1px solid var(--border); font-size: 14px; color: var(--ink-soft); vertical-align: middle; }
.admin-table tr:last-child td { border-bottom: none; }
.admin-table tr:hover td { background: var(--surface-dim); }
.empty-cell { text-align: center; color: var(--ink-faint); padding: 48px !important; font-size: 13px; }
.sku-product-name { font-size: 13px; font-weight: 500; color: var(--ink); }
.stock-val { font-family: var(--font-mono); font-size: 15px; font-weight: 600; color: var(--ink); }
.stock-low { color: var(--danger); }
.font-mono { font-family: var(--font-mono); }
.text-muted { color: var(--ink-muted); }
.action-btns { display: flex; gap: 4px; }
.form-input--sm { padding: 6px 10px; font-size: 13px; }
.form-select--sm { padding: 6px 10px; font-size: 13px; min-width: 72px; }
.btn-xs { padding: 4px 10px; font-size: 12px; }
.pagination { display: flex; align-items: center; gap: 12px; justify-content: center; }
.page-info { font-size: 13px; color: var(--ink-muted); min-width: 60px; text-align: center; }
</style>
