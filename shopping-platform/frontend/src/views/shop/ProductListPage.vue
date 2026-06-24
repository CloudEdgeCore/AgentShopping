<template>
  <div class="product-list-page">
    <div class="container">
      <section class="category-explorer">
        <div class="explorer-copy">
          <div class="explorer-eyebrow">分类筛选</div>
          <h1 class="explorer-title">先锁定主分类，再用子分类和品牌把范围收窄</h1>
          <p class="explorer-desc">
            点击主分类时，会同时包含它下面的子分类商品；如果你已经知道具体品类，可以直接切到对应子分类。
          </p>
        </div>

        <div class="filter-panel">
          <div class="filter-group">
            <div class="filter-label">主分类</div>
            <div class="filter-chips filter-chips--primary">
              <button class="filter-chip" :class="{ active: !selectedCategoryId }" @click="selectParent(null)">
                全部商品
              </button>
              <button
                v-for="parent in parentCategories"
                :key="parent.id"
                class="filter-chip"
                :class="{ active: activeParentId === parent.id }"
                @click="selectParent(parent.id)"
              >
                {{ parent.name }}
              </button>
            </div>
          </div>

          <div v-if="activeChildren.length" class="filter-group filter-group--nested">
            <div class="filter-label">子分类</div>
            <div class="filter-chips">
              <button
                class="filter-chip filter-chip--sub"
                :class="{ active: selectedCategoryId === activeParentId }"
                @click="selectParent(activeParentId)"
              >
                全部{{ activeParent?.name }}
              </button>
              <button
                v-for="child in activeChildren"
                :key="child.id"
                class="filter-chip filter-chip--sub"
                :class="{ active: selectedCategoryId === child.id }"
                @click="selectChild(child.id)"
              >
                {{ child.name }}
              </button>
            </div>
          </div>

          <div v-if="brands.length" class="filter-group">
            <div class="filter-label">品牌</div>
            <div class="filter-chips">
              <button
                v-for="brand in brands.slice(0, 5)"
                :key="brand.id"
                class="filter-chip filter-chip--sub"
                :class="{ active: selectedBrandId === brand.id }"
                @click="selectBrand(selectedBrandId === brand.id ? null : brand.id)"
              >
                {{ brand.name }}
              </button>
            </div>
          </div>
        </div>
      </section>

      <div class="result-bar">
        <div class="result-count">
          共 <strong>{{ total }}</strong> 件商品
          <span v-if="keyword" class="search-tip">搜索“{{ keyword }}”</span>
        </div>

        <div v-if="selectedCategoryLabel || selectedBrandLabel" class="active-summary">
          <span v-if="selectedCategoryLabel" class="summary-pill">分类 · {{ selectedCategoryLabel }}</span>
          <span v-if="selectedBrandLabel" class="summary-pill">品牌 · {{ selectedBrandLabel }}</span>
          <button class="summary-clear" @click="resetFilters">清除筛选</button>
        </div>
      </div>

      <div class="product-grid" v-if="loading">
        <div v-for="i in 12" :key="i" class="product-card-skeleton"></div>
      </div>

      <div class="product-grid" v-else-if="products.length">
        <ProductCard v-for="product in products" :key="product.spuId" :product="product" />
      </div>

      <div v-else class="empty-state">
        <div class="empty-state__icon">🔎</div>
        <div class="empty-state__title">没有找到相关商品</div>
        <div class="empty-state__desc">换个子分类、品牌，或者直接清除筛选再看看。</div>
        <button class="btn btn-outline" @click="resetFilters">清除筛选</button>
      </div>

      <div class="pagination" v-if="total > pageSize">
        <button class="page-btn" :disabled="currentPage <= 1" @click="goPage(currentPage - 1)">上一页</button>
        <button
          v-for="pageNumber in pageNumbers"
          :key="pageNumber"
          class="page-btn"
          :class="{ active: pageNumber === currentPage }"
          @click="goPage(pageNumber)"
        >
          {{ pageNumber }}
        </button>
        <button class="page-btn" :disabled="currentPage >= totalPages" @click="goPage(currentPage + 1)">下一页</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { agentApi } from '@/api/agent'
import ProductCard from '@/components/shop/ProductCard.vue'

const route = useRoute()
const router = useRouter()

const categoryTree = ref([])
const brands = ref([])
const products = ref([])
const loading = ref(true)
const total = ref(0)
const currentPage = ref(1)
const pageSize = 12

const selectedCategoryId = ref(null)
const selectedBrandId = ref(null)
const keyword = ref('')

const totalPages = computed(() => Math.ceil(total.value / pageSize))
const pageNumbers = computed(() => {
  const pages = []
  const start = Math.max(1, currentPage.value - 2)
  const end = Math.min(totalPages.value || 1, currentPage.value + 2)
  for (let pageNumber = start; pageNumber <= end; pageNumber += 1) {
    pages.push(pageNumber)
  }
  return pages
})

const parentCategories = computed(() => categoryTree.value || [])

const categoryLookup = computed(() => {
  const map = new Map()

  const visit = (nodes, parentId = null, depth = 0) => {
    nodes.forEach((node) => {
      const normalizedNode = {
        ...node,
        parentId,
        depth,
        children: node.children || []
      }
      map.set(node.id, normalizedNode)
      if (normalizedNode.children.length) {
        visit(normalizedNode.children, node.id, depth + 1)
      }
    })
  }

  visit(categoryTree.value || [])
  return map
})

const activeParentId = computed(() => {
  if (!selectedCategoryId.value) {
    return null
  }

  let current = categoryLookup.value.get(selectedCategoryId.value)
  if (!current) {
    return null
  }

  while (current.parentId && current.parentId !== 0) {
    const parent = categoryLookup.value.get(current.parentId)
    if (!parent) {
      break
    }
    current = parent
  }

  return current.id
})

const activeParent = computed(() => {
  if (!activeParentId.value) {
    return null
  }
  return categoryLookup.value.get(activeParentId.value) || null
})

const activeChildren = computed(() => activeParent.value?.children || [])

const selectedCategoryLabel = computed(() => {
  if (!selectedCategoryId.value) {
    return ''
  }
  return categoryLookup.value.get(selectedCategoryId.value)?.name || ''
})

const selectedBrandLabel = computed(() => {
  if (!selectedBrandId.value) {
    return ''
  }
  return brands.value.find((brand) => brand.id === selectedBrandId.value)?.name || ''
})

async function loadMeta() {
  try {
    const [catRes, brandRes] = await Promise.all([agentApi.getCategories(), agentApi.getBrands(5)])
    categoryTree.value = catRes.data || []
    brands.value = brandRes.data || []
  } catch (e) {
    console.warn('Failed to load categories/brands:', e)
  }
}

async function loadBrands() {
  try {
    const res = await agentApi.getBrands(5, selectedCategoryId.value || '')
    brands.value = res.data || []
  } catch (e) {
    console.warn('Failed to load brands:', e)
  }
}

async function loadProducts() {
  loading.value = true
  try {
    const params = {
      current: currentPage.value,
      size: pageSize
    }
    if (selectedCategoryId.value) {
      params.categoryId = selectedCategoryId.value
    }
    if (selectedBrandId.value) {
      params.brandId = selectedBrandId.value
    }
    if (keyword.value) {
      params.keyword = keyword.value
    }
    const res = await agentApi.getProductPage(params)
    products.value = res.data?.records || []
    total.value = res.data?.total || 0
  } finally {
    loading.value = false
  }
}

function syncFromRoute() {
  selectedCategoryId.value = route.query.categoryId || null
  selectedBrandId.value = route.query.brandId || null
  keyword.value = route.query.keyword || ''
  currentPage.value = route.query.page ? Number(route.query.page) : 1
}

function updateRoute() {
  const query = {}
  if (selectedCategoryId.value) {
    query.categoryId = selectedCategoryId.value
  }
  if (selectedBrandId.value) {
    query.brandId = selectedBrandId.value
  }
  if (keyword.value) {
    query.keyword = keyword.value
  }
  if (currentPage.value > 1) {
    query.page = currentPage.value
  }
  router.push({ query })
}

function selectParent(parentId) {
  selectedCategoryId.value = parentId
  selectedBrandId.value = null
  currentPage.value = 1
  updateRoute()
}

function selectChild(childId) {
  selectedCategoryId.value = childId
  selectedBrandId.value = null
  currentPage.value = 1
  updateRoute()
}

function selectBrand(brandId) {
  selectedBrandId.value = brandId
  currentPage.value = 1
  updateRoute()
}

function goPage(pageNumber) {
  currentPage.value = pageNumber
  updateRoute()
  window.scrollTo({ top: 0, behavior: 'smooth' })
}

function resetFilters() {
  selectedCategoryId.value = null
  selectedBrandId.value = null
  keyword.value = ''
  currentPage.value = 1
  router.push({ query: {} })
}

watch(
  () => route.query,
  () => {
    syncFromRoute()
    loadProducts()
    loadBrands()
  }
)

onMounted(async () => {
  syncFromRoute()
  await loadMeta()
  loadProducts()
})
</script>

<style scoped>
.product-list-page {
  padding: 40px 0 80px;
}

.category-explorer {
  margin-bottom: 28px;
  padding: 28px;
  border: 1px solid rgba(201, 168, 76, 0.22);
  border-radius: 32px;
  background:
    radial-gradient(circle at top right, rgba(201, 168, 76, 0.14), transparent 32%),
    linear-gradient(180deg, rgba(255, 249, 236, 0.82), rgba(255, 255, 255, 0.98));
  box-shadow: 0 24px 56px rgba(18, 24, 38, 0.05);
}

.explorer-copy {
  max-width: 760px;
}

.explorer-eyebrow {
  margin-bottom: 10px;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--gold-dark);
}

.explorer-title {
  font-size: clamp(28px, 4vw, 42px);
  font-weight: 700;
  line-height: 1.15;
  color: var(--ink);
}

.explorer-desc {
  margin-top: 12px;
  font-size: 14px;
  line-height: 1.8;
  color: var(--ink-muted);
}

.filter-panel {
  margin-top: 24px;
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.filter-group {
  display: flex;
  gap: 18px;
  align-items: flex-start;
}

.filter-group--nested {
  padding-top: 18px;
  border-top: 1px solid rgba(18, 24, 38, 0.08);
}

.filter-label {
  min-width: 52px;
  padding-top: 8px;
  font-size: 13px;
  font-weight: 700;
  color: var(--ink-soft);
}

.filter-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.filter-chips--primary .filter-chip {
  background: rgba(255, 255, 255, 0.9);
}

.filter-chip {
  padding: 9px 16px;
  border-radius: 999px;
  border: 1px solid rgba(18, 24, 38, 0.08);
  background: rgba(255, 255, 255, 0.7);
  color: var(--ink-muted);
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: all var(--transition);
}

.filter-chip:hover {
  color: var(--ink);
  border-color: rgba(201, 168, 76, 0.35);
  transform: translateY(-1px);
}

.filter-chip.active {
  color: var(--surface);
  background: var(--ink);
  border-color: var(--ink);
  box-shadow: 0 10px 18px rgba(18, 24, 38, 0.15);
}

.filter-chip--sub.active {
  background: var(--gold-dark);
  border-color: var(--gold-dark);
}

.result-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 24px;
}

.result-count {
  font-size: 14px;
  color: var(--ink-muted);
}

.result-count strong {
  color: var(--ink);
}

.search-tip {
  margin-left: 6px;
  color: var(--gold-dark);
}

.active-summary {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
}

.summary-pill {
  padding: 7px 12px;
  border-radius: 999px;
  background: var(--surface-dim);
  font-size: 12px;
  color: var(--ink-soft);
}

.summary-clear {
  border: none;
  background: transparent;
  color: var(--ink-muted);
  font-size: 13px;
  cursor: pointer;
}

.summary-clear:hover {
  color: var(--danger);
}

.product-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 24px;
  margin-bottom: 48px;
}

.product-card-skeleton {
  height: 340px;
  border-radius: var(--radius-md);
  background: linear-gradient(90deg, var(--surface-dim) 25%, var(--border) 50%, var(--surface-dim) 75%);
  background-size: 200% 100%;
  animation: shimmer 1.5s infinite;
}

.pagination {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
}

.page-btn {
  padding: 8px 16px;
  border-radius: var(--radius-sm);
  border: 1px solid var(--border);
  background: var(--surface);
  color: var(--ink-muted);
  font-size: 14px;
  cursor: pointer;
  transition: all var(--transition);
}

.page-btn:hover:not(:disabled) {
  color: var(--ink);
  border-color: var(--ink);
}

.page-btn.active {
  background: var(--ink);
  color: var(--surface);
  border-color: var(--ink);
  font-weight: 600;
}

.page-btn:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

@keyframes shimmer {
  from {
    background-position: 200% 0;
  }

  to {
    background-position: -200% 0;
  }
}

@media (max-width: 1024px) {
  .product-grid {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
}

@media (max-width: 768px) {
  .category-explorer {
    padding: 22px;
    border-radius: 24px;
  }

  .filter-group,
  .result-bar {
    flex-direction: column;
    align-items: flex-start;
  }

  .filter-label {
    min-width: auto;
    padding-top: 0;
  }

  .product-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 16px;
  }
}
</style>
