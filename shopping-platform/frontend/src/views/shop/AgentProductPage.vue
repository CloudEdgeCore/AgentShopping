<template>
  <div class="agent-product-page">
    <div v-if="loading" class="loading">加载中...</div>
    <div v-else-if="error" class="error">{{ error }}</div>
    <template v-else-if="product">
      <!-- 面包屑 -->
      <div class="breadcrumb">
        <RouterLink to="/ai-chat">AI 导购</RouterLink>
        <span>/</span>
        <span>{{ product.category }}</span>
        <span>/</span>
        <span>{{ product.subcategory }}</span>
      </div>

      <div class="product-main">
        <!-- 商品图片 -->
        <div class="product-gallery">
          <img :src="fixImageUrl(product.image_url)" :alt="product.title" class="main-image" />
        </div>

        <!-- 商品信息 -->
        <div class="product-info">
          <div class="product-brand">{{ product.brand }}</div>
          <h1 class="product-title">{{ product.title }}</h1>

          <div class="product-meta">
            <span class="rating">⭐ {{ product.rating }}</span>
            <span class="sales">已售 {{ product.sales }}</span>
            <span class="stock" :class="{ low: product.stock < 50 }">
              {{ product.stock > 0 ? `库存 ${product.stock}` : '暂时缺货' }}
            </span>
          </div>

          <div class="product-price">
            <span class="price-label">价格</span>
            <span class="price-value">¥{{ (product.price / 100).toFixed(2) }}</span>
          </div>

          <!-- SKU 选择 -->
          <div v-if="skus.length > 0" class="sku-section">
            <div class="sku-label">规格</div>
            <div class="sku-options">
              <button
                v-for="sku in skus"
                :key="sku.id"
                class="sku-btn"
                :class="{ active: selectedSku?.id === sku.id }"
                @click="selectedSku = sku"
              >
                {{ sku.sku_name }}
                <span class="sku-price">¥{{ (sku.price / 100).toFixed(2) }}</span>
              </button>
            </div>
          </div>

          <!-- 商品描述 -->
          <div class="product-desc">
            <h3>商品介绍</h3>
            <p>{{ product.description }}</p>
          </div>

          <!-- 操作按钮 -->
          <div class="product-actions">
            <button class="btn-back" @click="$router.back()">← 返回对话</button>
            <button class="btn-chat" @click="openChat">🤖 问问 AI</button>
          </div>
        </div>
      </div>

      <!-- 商品专属 AI 聊天浮窗 -->
      <ProductChatWidget
        ref="chatWidget"
        :product-id="product.id"
        :product-title="product.title"
        :product-category="product.category"
        :product-brand="product.brand"
        :show-trigger="false"
      />
    </template>
  </div>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { agentApi } from '@/api/agent'
import ProductChatWidget from '@/components/shop/ProductChatWidget.vue'

const route = useRoute()
const router = useRouter()

const chatWidget = ref(null)

function openChat() {
  chatWidget.value?.open()
}

const product = ref(null)
const skus = ref([])
const selectedSku = ref(null)
const loading = ref(true)
const error = ref(null)

// 将 Agent 的图片路径转为代理路径
function fixImageUrl(url) {
  if (!url) return ''
  if (url.startsWith('/static/')) return '/agent' + url
  return url
}

async function loadProduct(productId) {
  loading.value = true
  error.value = null
  try {
    const resp = await fetch(`/agent/products/${encodeURIComponent(productId)}`)
    if (!resp.ok) throw new Error(`${resp.status} ${resp.statusText}`)
    product.value = await resp.json()

    // 加载 SKU
    if (product.value.specs_json) {
      try {
        const specs = JSON.parse(product.value.specs_json)
        // SKU 信息从 specs 中获取
      } catch {}
    }
  } catch (e) {
    error.value = `加载失败: ${e.message}`
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  loadProduct(route.params.productId)
})

watch(() => route.params.productId, (id) => {
  if (id) loadProduct(id)
})
</script>

<style scoped>
.agent-product-page {
  max-width: 1100px;
  margin: 0 auto;
  padding: 24px 20px;
}

.breadcrumb {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  color: var(--ink-muted);
  margin-bottom: 24px;
}

.breadcrumb a {
  color: var(--ink-soft);
  text-decoration: none;
}

.breadcrumb a:hover { color: var(--ink); }

.product-main {
  display: flex;
  gap: 40px;
}

.product-gallery {
  flex-shrink: 0;
  width: 400px;
}

.main-image {
  width: 100%;
  border-radius: 12px;
  object-fit: cover;
  aspect-ratio: 1;
  background: var(--surface-dim);
}

.product-info {
  flex: 1;
  min-width: 0;
}

.product-brand {
  font-size: 13px;
  color: var(--ink-muted);
  font-weight: 500;
  margin-bottom: 8px;
}

.product-title {
  font-size: 22px;
  font-weight: 700;
  color: var(--ink);
  line-height: 1.4;
  margin-bottom: 16px;
}

.product-meta {
  display: flex;
  gap: 16px;
  font-size: 13px;
  color: var(--ink-muted);
  margin-bottom: 24px;
}

.product-meta .rating { color: var(--gold); font-weight: 600; }
.product-meta .stock.low { color: var(--danger); }

.product-price {
  display: flex;
  align-items: baseline;
  gap: 12px;
  margin-bottom: 24px;
  padding: 16px;
  background: var(--surface-dim);
  border-radius: 10px;
}

.price-label {
  font-size: 14px;
  color: var(--ink-muted);
}

.price-value {
  font-size: 28px;
  font-weight: 800;
  color: var(--danger);
}

.sku-section {
  margin-bottom: 24px;
}

.sku-label {
  font-size: 14px;
  font-weight: 600;
  color: var(--ink);
  margin-bottom: 10px;
}

.sku-options {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.sku-btn {
  padding: 8px 16px;
  border-radius: 8px;
  font-size: 13px;
  color: var(--ink-soft);
  background: var(--surface);
  border: 1.5px solid var(--border);
  cursor: pointer;
  transition: all var(--transition);
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
}

.sku-btn:hover { border-color: var(--ink); }
.sku-btn.active {
  border-color: var(--ink);
  background: var(--ink);
  color: var(--gold);
}

.sku-price {
  font-size: 12px;
  font-weight: 600;
  color: var(--danger);
}

.sku-btn.active .sku-price { color: var(--gold); }

.product-desc {
  margin-bottom: 32px;
}

.product-desc h3 {
  font-size: 15px;
  font-weight: 600;
  margin-bottom: 10px;
  color: var(--ink);
}

.product-desc p {
  font-size: 14px;
  line-height: 1.8;
  color: var(--ink-soft);
}

.product-actions {
  display: flex;
  gap: 12px;
}

.btn-back, .btn-chat {
  padding: 12px 24px;
  border-radius: 10px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all var(--transition);
}

.btn-back {
  background: var(--surface);
  border: 1.5px solid var(--border);
  color: var(--ink-soft);
}

.btn-back:hover { border-color: var(--ink); color: var(--ink); }

.btn-chat {
  background: var(--ink);
  color: var(--gold);
  border: none;
}

.btn-chat:hover { transform: scale(1.02); }

.loading, .error {
  text-align: center;
  padding: 80px 20px;
  font-size: 15px;
  color: var(--ink-muted);
}

.error { color: var(--danger); }

@media (max-width: 768px) {
  .product-main { flex-direction: column; gap: 24px; }
  .product-gallery { width: 100%; }
}
</style>
