<template>
  <div class="product-detail-page">
    <!-- Loading -->
    <div class="container" v-if="loading">
      <div class="detail-skeleton">
        <div class="skeleton-gallery"></div>
        <div class="skeleton-info">
          <div class="skeleton-line w60"></div>
          <div class="skeleton-line w90"></div>
          <div class="skeleton-line w40"></div>
          <div class="skeleton-line w70"></div>
        </div>
      </div>
    </div>

    <!-- Content -->
    <div class="container" v-else-if="product">
      <div class="detail-layout">
        <!-- Gallery -->
        <div class="gallery">
          <div class="gallery-main">
            <img :src="activeImage || product.coverImage || placeholderImg(product.spuName)" :alt="product.spuName" />
          </div>
          <div class="gallery-thumbs" v-if="allImages.length > 1">
            <button
              v-for="(img, i) in allImages"
              :key="i"
              class="thumb"
              :class="{ active: activeImage === img }"
              @click="activeImage = img"
            >
              <img :src="img" :alt="`图片${i+1}`" />
            </button>
          </div>
        </div>

        <!-- Product Info -->
        <div class="product-info">
          <div class="info-brand">{{ product.brandName }}</div>
          <h1 class="info-name">{{ product.spuName }}</h1>
          <p class="info-sub" v-if="product.subtitle">{{ product.subtitle }}</p>

          <!-- Price -->
          <div class="price-block" :class="{ 'has-promo': activeSku?.promotionPrice }">
            <template v-if="activeSku?.promotionPrice && activeSku.promotionPrice < activeSku.salePrice">
              <div class="price-main price-sale">{{ formatPrice(activeSku.promotionPrice) }}</div>
              <div class="price-detail">
                <span class="price-original">原价 {{ formatPrice(activeSku.salePrice) }}</span>
                <span class="badge badge-gold">{{ activeSku.promotionActivityName }}</span>
              </div>
            </template>
            <template v-else>
              <div class="price-main price">{{ formatPrice(activeSku?.salePrice || product.minSalePrice) }}</div>
              <div v-if="activeSku?.marketPrice && activeSku.marketPrice > activeSku.salePrice" class="price-detail">
                <span class="price-original">市场价 {{ formatPrice(activeSku.marketPrice) }}</span>
              </div>
            </template>
          </div>

          <!-- SKU Selection -->
          <div class="sku-section" v-if="product.skuList?.length">
            <div class="sku-label">规格选择</div>
            <div class="sku-list">
              <button
                v-for="sku in product.skuList"
                :key="sku.skuId"
                class="sku-btn"
                :class="{ active: activeSku?.skuId === sku.skuId, disabled: sku.status === 0 }"
                :disabled="sku.status === 0"
                @click="activeSku = sku; activeImage = sku.imageUrl || activeImage"
              >
                <img v-if="sku.imageUrl" :src="sku.imageUrl" class="sku-thumb" />
                <span>{{ sku.attrText || sku.skuName }}</span>
              </button>
            </div>
          </div>

          <!-- Quantity -->
          <div class="quantity-section">
            <div class="sku-label">数量</div>
            <div class="quantity-control">
              <button class="qty-btn" @click="quantity = Math.max(1, quantity - 1)">−</button>
              <input type="number" v-model.number="quantity" min="1" max="999" class="qty-input" />
              <button class="qty-btn" @click="quantity = Math.min(999, quantity + 1)">+</button>
            </div>
          </div>

          <!-- Actions -->
          <div class="action-row">
            <button class="btn btn-primary btn-lg" @click="handleAddToCart" :disabled="addingToCart || !activeSku">
              <span v-if="addingToCart" class="spinner spinner-gold"></span>
              {{ addingToCart ? '加入中...' : '加入购物车' }}
            </button>
            <button class="btn btn-gold btn-lg" @click="handleBuyNow" :disabled="!activeSku">
              立即购买
            </button>
          </div>

          <!-- Success tip -->
          <Transition name="slide-up">
            <div class="add-success" v-if="showSuccess">
              ✓ 已加入购物车
            </div>
          </Transition>

          <!-- Meta -->
          <div class="product-meta">
            <div class="meta-item">
              <span class="meta-label">分类</span>
              <RouterLink :to="`/products?categoryId=${product.categoryId}`" class="meta-value meta-link">
                {{ product.categoryName }}
              </RouterLink>
            </div>
            <div class="meta-item">
              <span class="meta-label">品牌</span>
              <RouterLink :to="`/products?brandId=${product.brandId}`" class="meta-value meta-link">
                {{ product.brandName }}
              </RouterLink>
            </div>
            <div class="meta-item" v-if="activeSku">
              <span class="meta-label">SKU</span>
              <span class="meta-value font-mono">{{ activeSku.skuCode }}</span>
            </div>
          </div>
        </div>
      </div>

      <!-- Detail Content -->
      <div class="detail-content" v-if="product.detail">
        <div class="detail-content-title">商品详情</div>
        <div class="detail-content-body" v-html="product.detail"></div>
      </div>
    </div>

    <!-- Error -->
    <div class="container" v-else>
      <div class="empty-state">
        <div class="empty-state__icon">🔍</div>
        <div class="empty-state__title">商品不存在</div>
        <RouterLink to="/products" class="btn btn-outline">返回商品列表</RouterLink>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { productApi } from '@/api'
import { useCartStore } from '@/stores/cart'
import { useAuthStore } from '@/stores/auth'
import { formatPrice, placeholderImg } from '@/utils'

const route = useRoute()
const router = useRouter()
const cartStore = useCartStore()
const authStore = useAuthStore()

const product = ref(null)
const loading = ref(true)
const activeSku = ref(null)
const activeImage = ref('')
const quantity = ref(1)
const addingToCart = ref(false)
const showSuccess = ref(false)

const allImages = computed(() => {
  const imgs = []
  if (product.value?.coverImage) imgs.push(product.value.coverImage)
  if (product.value?.albumImages) imgs.push(...product.value.albumImages)
  return [...new Set(imgs)]
})

async function load() {
  loading.value = true
  try {
    const res = await productApi.getDetail(route.params.spuId)
    product.value = res.data
    const skuList = product.value?.skuList || []
    activeSku.value = skuList.find(s => s.defaultSku) || skuList[0] || null
    activeImage.value = activeSku.value?.imageUrl || product.value?.coverImage || ''
  } catch (e) {
    product.value = null
  } finally {
    loading.value = false
  }
}

async function handleAddToCart() {
  if (!authStore.isLoggedIn) return router.push({ name: 'Login', query: { redirect: route.fullPath } })
  if (!activeSku.value) return
  addingToCart.value = true
  try {
    await cartStore.addItem(activeSku.value.skuId, quantity.value)
    showSuccess.value = true
    setTimeout(() => showSuccess.value = false, 2500)
  } catch (e) {
    alert(e.message)
  } finally {
    addingToCart.value = false
  }
}

async function handleBuyNow() {
  if (!authStore.isLoggedIn) return router.push({ name: 'Login', query: { redirect: route.fullPath } })
  if (!activeSku.value) return
  router.push({
    name: 'Checkout',
    query: {
      mode: 'direct',
      skuId: activeSku.value.skuId,
      quantity: quantity.value
    }
  })
}

watch(() => route.params.spuId, load)
onMounted(load)
</script>

<style scoped>
.product-detail-page {
  padding: 40px 0 80px;
}

/* Skeleton */
.detail-skeleton {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 48px;
}
.skeleton-gallery {
  aspect-ratio: 1;
  background: linear-gradient(90deg, var(--surface-dim) 25%, var(--border) 50%, var(--surface-dim) 75%);
  background-size: 200% 100%;
  animation: shimmer 1.5s infinite;
  border-radius: var(--radius-md);
}
.skeleton-info {
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding-top: 24px;
}
.skeleton-line {
  height: 16px;
  background: linear-gradient(90deg, var(--surface-dim) 25%, var(--border) 50%, var(--surface-dim) 75%);
  background-size: 200% 100%;
  animation: shimmer 1.5s infinite;
  border-radius: 4px;
}
.w60 { width: 60%; }
.w90 { width: 90%; height: 28px; }
.w40 { width: 40%; }
.w70 { width: 70%; }

@keyframes shimmer {
  from { background-position: 200% 0; }
  to { background-position: -200% 0; }
}

/* Detail Layout */
.detail-layout {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 64px;
  margin-bottom: 64px;
}

@media (max-width: 768px) {
  .detail-layout { grid-template-columns: 1fr; gap: 32px; }
  .detail-skeleton { grid-template-columns: 1fr; }
}

/* Gallery */
.gallery-main {
  aspect-ratio: 1;
  border-radius: var(--radius-md);
  overflow: hidden;
  background: var(--surface-dim);
  border: 1px solid var(--border);
  margin-bottom: 12px;
}

.gallery-main img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  transition: transform 400ms var(--ease-out);
}

.gallery-main:hover img {
  transform: scale(1.03);
}

.gallery-thumbs {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.thumb {
  width: 72px;
  height: 72px;
  border-radius: var(--radius-sm);
  overflow: hidden;
  border: 2px solid var(--border);
  cursor: pointer;
  transition: all var(--transition);
  background: var(--surface-dim);
  padding: 0;
}

.thumb:hover { border-color: var(--ink-faint); }
.thumb.active { border-color: var(--ink); }

.thumb img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

/* Product Info */
.info-brand {
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.12em;
  color: var(--ink-faint);
  text-transform: uppercase;
  margin-bottom: 8px;
}

.info-name {
  font-size: 28px;
  font-weight: 700;
  color: var(--ink);
  line-height: 1.2;
  margin-bottom: 8px;
}

.info-sub {
  font-size: 14px;
  color: var(--ink-muted);
  margin-bottom: 24px;
  line-height: 1.6;
}

/* Price */
.price-block {
  background: var(--surface-dim);
  border-radius: var(--radius-md);
  padding: 20px 24px;
  margin-bottom: 28px;
  border: 1px solid var(--border);
}

.price-block.has-promo {
  background: var(--gold-pale);
  border-color: rgba(201,168,76,0.3);
}

.price-main {
  font-size: 32px;
  font-weight: 700;
  letter-spacing: -0.02em;
}

.price-detail {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-top: 6px;
}

/* SKU */
.sku-section {
  margin-bottom: 24px;
}

.sku-label {
  font-size: 13px;
  font-weight: 600;
  color: var(--ink-soft);
  margin-bottom: 10px;
}

.sku-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.sku-btn {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 16px;
  border-radius: var(--radius-sm);
  font-size: 13px;
  color: var(--ink-soft);
  background: var(--surface);
  border: 1.5px solid var(--border);
  cursor: pointer;
  transition: all var(--transition);
}

.sku-btn:hover {
  border-color: var(--ink-faint);
  color: var(--ink);
}

.sku-btn.active {
  border-color: var(--ink);
  color: var(--ink);
  background: var(--surface-dim);
  font-weight: 500;
}

.sku-btn.disabled {
  opacity: 0.4;
  cursor: not-allowed;
  text-decoration: line-through;
}

.sku-thumb {
  width: 24px;
  height: 24px;
  border-radius: 4px;
  object-fit: cover;
}

/* Quantity */
.quantity-section {
  margin-bottom: 28px;
}

.quantity-control {
  display: flex;
  align-items: center;
  border: 1.5px solid var(--border);
  border-radius: var(--radius-sm);
  width: fit-content;
  overflow: hidden;
}

.qty-btn {
  width: 40px;
  height: 40px;
  font-size: 18px;
  color: var(--ink-muted);
  background: var(--surface-dim);
  border: none;
  cursor: pointer;
  transition: all var(--transition);
}

.qty-btn:hover {
  background: var(--border);
  color: var(--ink);
}

.qty-input {
  width: 56px;
  height: 40px;
  text-align: center;
  border: none;
  border-left: 1.5px solid var(--border);
  border-right: 1.5px solid var(--border);
  font-size: 14px;
  font-weight: 600;
  color: var(--ink);
  outline: none;
  -moz-appearance: textfield;
}

.qty-input::-webkit-outer-spin-button,
.qty-input::-webkit-inner-spin-button {
  -webkit-appearance: none;
}

/* Action Row */
.action-row {
  display: flex;
  gap: 12px;
  margin-bottom: 16px;
}

.action-row .btn {
  flex: 1;
}

/* Success tip */
.add-success {
  padding: 10px 16px;
  background: #f0faf5;
  border: 1px solid rgba(45,158,110,0.25);
  border-radius: var(--radius-sm);
  font-size: 14px;
  color: var(--success);
  font-weight: 500;
  margin-bottom: 12px;
}

/* Meta */
.product-meta {
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding-top: 24px;
  border-top: 1px solid var(--border);
  margin-top: 8px;
}

.meta-item {
  display: flex;
  align-items: center;
  gap: 16px;
  font-size: 13px;
}

.meta-label {
  color: var(--ink-faint);
  width: 40px;
  flex-shrink: 0;
}

.meta-value {
  color: var(--ink-soft);
}

.meta-link {
  color: var(--ink-muted);
  text-decoration: underline;
  text-underline-offset: 2px;
}

.meta-link:hover {
  color: var(--gold-dark);
}

/* Detail Content */
.detail-content {
  border-top: 1px solid var(--border);
  padding-top: 48px;
}

.detail-content-title {
  font-size: 22px;
  font-family: var(--font-display);
  font-weight: 700;
  color: var(--ink);
  margin-bottom: 24px;
}

.detail-content-body {
  font-size: 15px;
  color: var(--ink-soft);
  line-height: 1.8;
}
</style>
