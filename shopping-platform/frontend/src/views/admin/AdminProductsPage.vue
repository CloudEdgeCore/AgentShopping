<template>
  <div class="admin-page">
    <div class="admin-page-header">
      <div>
        <h2 class="admin-page-title">商品管理</h2>
        <p class="admin-page-sub">管理平台全部商品，并维护搜索索引。</p>
      </div>
      <div class="admin-page-actions">
        <button class="btn btn-outline" :disabled="rebuilding" @click="rebuildSearchIndex">
          {{ rebuilding ? '重建中...' : '重建搜索索引' }}
        </button>
        <RouterLink to="/admin/products/new" class="btn btn-primary">+ 新增商品</RouterLink>
      </div>
    </div>

    <div class="filter-bar">
      <input
        v-model="filters.keyword"
        type="text"
        class="form-input filter-input"
        placeholder="搜索商品名称..."
        @keyup.enter="doSearch"
      />
      <select v-model="filters.categoryId" class="form-select filter-select" @change="doSearch">
        <option :value="null">全部分类</option>
        <option v-for="category in categories" :key="category.id" :value="category.id">
          {{ category.name }}
        </option>
      </select>
      <select v-model="filters.publishStatus" class="form-select filter-select" @change="doSearch">
        <option :value="null">全部状态</option>
        <option :value="1">已上架</option>
        <option :value="0">已下架</option>
      </select>
      <button class="btn btn-outline" @click="doSearch">搜索</button>
    </div>

    <div class="admin-table-wrap">
      <div v-if="loading" class="admin-loading">
        <div class="spinner" style="width:28px;height:28px;border-width:2px"></div>
      </div>

      <table v-else class="admin-table">
        <thead>
          <tr>
            <th style="width:72px">ID</th>
            <th style="width:72px">图片</th>
            <th>商品名称</th>
            <th>分类</th>
            <th>品牌</th>
            <th>价格区间</th>
            <th style="width:90px">状态</th>
            <th style="width:240px">操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="!products.length">
            <td colspan="8" class="empty-cell">暂无商品</td>
          </tr>

          <tr v-for="product in products" :key="product.spuId">
            <td class="font-mono text-muted">{{ product.spuId }}</td>
            <td>
              <img v-if="product.coverImage" :src="product.coverImage" class="product-thumb" />
              <div v-else class="product-thumb-placeholder">-</div>
            </td>
            <td>
              <div class="product-name">{{ product.spuName }}</div>
              <div class="product-sn font-mono text-muted">SKU {{ product.skuCount ?? 0 }}</div>
            </td>
            <td class="text-muted">{{ product.categoryName || '-' }}</td>
            <td class="text-muted">{{ product.brandName || '-' }}</td>
            <td class="font-mono">
              <span v-if="product.minSalePrice != null">¥{{ fmt(product.minSalePrice) }}</span>
              <span v-if="product.minSalePrice !== product.maxSalePrice && product.maxSalePrice != null">
                ~ ¥{{ fmt(product.maxSalePrice) }}
              </span>
            </td>
            <td>
              <span class="badge" :class="product.publishStatus === 1 ? 'badge-success' : 'badge-muted'">
                {{ product.publishStatus === 1 ? '上架' : '下架' }}
              </span>
            </td>
            <td>
              <div class="action-btns">
                <RouterLink :to="`/admin/products/${product.spuId}/edit`" class="btn btn-ghost btn-xs">
                  编辑
                </RouterLink>
                <button
                  class="btn btn-xs"
                  :class="product.publishStatus === 1 ? 'btn-ghost text-danger' : 'btn-outline'"
                  @click="togglePublish(product)"
                >
                  {{ product.publishStatus === 1 ? '下架' : '上架' }}
                </button>
                <button
                  class="btn btn-ghost btn-xs"
                  :disabled="syncingSpuId === product.spuId"
                  @click="syncSearchIndex(product)"
                >
                  {{ syncingSpuId === product.spuId ? '同步中...' : '同步索引' }}
                </button>
                <button class="btn btn-ghost btn-xs text-danger" @click="deleteProduct(product)">
                  删除
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
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { adminCategoryApi, adminProductApi, adminSearchApi } from '@/api'

const products = ref([])
const categories = ref([])
const loading = ref(true)
const rebuilding = ref(false)
const syncingSpuId = ref(null)
const page = ref(1)
const pageSize = 15
const total = ref(0)
const totalPages = computed(() => Math.ceil(total.value / pageSize))

const filters = ref({
  keyword: '',
  categoryId: null,
  publishStatus: null
})

function fmt(value) {
  const num = Number(value)
  return Number.isFinite(num) ? num.toFixed(2) : '--'
}

async function load() {
  loading.value = true
  try {
    const params = {
      current: page.value,
      size: pageSize,
      keyword: filters.value.keyword || undefined
    }
    if (filters.value.categoryId !== null) params.categoryId = filters.value.categoryId
    if (filters.value.publishStatus !== null) params.publishStatus = filters.value.publishStatus

    const res = await adminProductApi.getPage(params)
    const data = res.data || {}
    products.value = data.records || []
    total.value = data.total || 0
  } finally {
    loading.value = false
  }
}

async function loadCategories() {
  try {
    const res = await adminCategoryApi.getTree()
    const flatten = (list, depth = 0) => list.flatMap(item => {
      const prefix = depth === 0 ? '主分类 · ' : `${'　'.repeat(Math.max(depth - 1, 0))}└ `
      const current = {
        ...item,
        name: `${prefix}${item.name}`
      }
      return [current, ...(item.children ? flatten(item.children, depth + 1) : [])]
    })
    categories.value = flatten(res.data || [])
  } catch (_) {
    categories.value = []
  }
}

function doSearch() {
  page.value = 1
  load()
}

async function togglePublish(product) {
  try {
    if (product.publishStatus === 1) {
      await adminProductApi.unpublish(product.spuId)
      product.publishStatus = 0
      return
    }
    await adminProductApi.publish(product.spuId, 1)
    product.publishStatus = 1
  } catch (e) {
    alert(e.message)
  }
}

async function rebuildSearchIndex() {
  if (!confirm('确定要全量重建商品搜索索引吗？')) return
  rebuilding.value = true
  try {
    await adminSearchApi.rebuildProductIndex()
    alert('商品搜索索引重建完成')
  } catch (e) {
    alert(e.message)
  } finally {
    rebuilding.value = false
  }
}

async function syncSearchIndex(product) {
  syncingSpuId.value = product.spuId
  try {
    await adminSearchApi.syncProductIndex(product.spuId)
    alert(`商品 ${product.spuId} 索引同步完成`)
  } catch (e) {
    alert(e.message)
  } finally {
    syncingSpuId.value = null
  }
}

async function deleteProduct(product) {
  if (product.publishStatus === 1) {
    alert('已上架商品不能直接删除，请先下架。')
    return
  }
  if (!confirm(`确定删除商品「${product.spuName}」吗？删除后会同步移除搜索索引。`)) return

  try {
    await adminProductApi.delete(product.spuId)
    if (products.value.length === 1 && page.value > 1) {
      page.value -= 1
    }
    await load()
  } catch (e) {
    alert(e.message)
  }
}

onMounted(() => {
  load()
  loadCategories()
})
</script>

<style scoped>
.admin-page { display: flex; flex-direction: column; gap: 20px; }
.admin-page-header { display: flex; justify-content: space-between; align-items: flex-start; gap: 16px; }
.admin-page-actions { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
.admin-page-title { font-size: 22px; font-weight: 700; color: var(--ink); }
.admin-page-sub { font-size: 13px; color: var(--ink-muted); margin-top: 4px; }
.filter-bar { display: flex; gap: 10px; flex-wrap: wrap; align-items: center; }
.filter-input { flex: 1; min-width: 200px; max-width: 320px; }
.filter-select { min-width: 130px; }
.admin-table-wrap { border: 1px solid var(--border); border-radius: var(--radius-md); overflow: hidden; position: relative; min-height: 120px; }
.admin-loading { position: absolute; inset: 0; display: flex; align-items: center; justify-content: center; background: var(--surface); }
.admin-table { width: 100%; border-collapse: collapse; }
.admin-table th { padding: 12px 14px; background: var(--surface-dim); font-size: 12px; font-weight: 600; color: var(--ink-muted); text-align: left; border-bottom: 1px solid var(--border); white-space: nowrap; }
.admin-table td { padding: 12px 14px; border-bottom: 1px solid var(--border); font-size: 14px; color: var(--ink-soft); vertical-align: middle; }
.admin-table tr:last-child td { border-bottom: none; }
.admin-table tr:hover td { background: var(--surface-dim); }
.empty-cell { text-align: center; color: var(--ink-faint); padding: 48px !important; }
.product-thumb { width: 44px; height: 44px; object-fit: cover; border-radius: var(--radius-sm); border: 1px solid var(--border); }
.product-thumb-placeholder { width: 44px; height: 44px; background: var(--surface-dim); border-radius: var(--radius-sm); display: flex; align-items: center; justify-content: center; color: var(--ink-faint); font-size: 18px; }
.product-name { font-size: 13px; font-weight: 500; color: var(--ink); }
.product-sn { font-size: 11px; margin-top: 2px; }
.font-mono { font-family: var(--font-mono); }
.text-muted { color: var(--ink-muted); }
.text-danger { color: var(--danger) !important; }
.action-btns { display: flex; gap: 4px; flex-wrap: wrap; }
.btn-xs { padding: 4px 10px; font-size: 12px; }
.pagination { display: flex; align-items: center; gap: 12px; justify-content: center; }
.page-info { font-size: 13px; color: var(--ink-muted); min-width: 60px; text-align: center; }
</style>
