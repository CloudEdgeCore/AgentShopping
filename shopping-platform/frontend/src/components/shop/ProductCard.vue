<template>
  <RouterLink :to="productLink" class="product-card">
    <!-- Image -->
    <div class="product-img-wrap">
      <img
        :src="productImage"
        :alt="productName"
        class="product-img"
        loading="lazy"
      />
      <!-- Promotion badge -->
      <div v-if="hasPromotion" class="product-promo-badge">秒杀</div>
    </div>
    <!-- Info -->
    <div class="product-info">
      <div class="product-brand">{{ productBrand }}</div>
      <div class="product-name">{{ productName }}</div>
      <div class="product-sub" v-if="product.subtitle">{{ product.subtitle }}</div>
      <div class="product-price-row">
        <template v-if="hasPromotion">
          <span class="price-sale">{{ formatPrice(product.minPromotionPrice) }}</span>
          <span class="price-original">{{ formatPrice(displayPrice) }}</span>
        </template>
        <template v-else>
          <span class="price">{{ formatPrice(displayPrice) }}</span>
        </template>
      </div>
    </div>
  </RouterLink>
</template>

<script setup>
import { computed } from 'vue'
import { formatPrice, placeholderImg } from '@/utils'

const props = defineProps({
  product: { type: Object, required: true }
})

// 兼容 Java 平台和 Agent 两种数据格式
const productId = computed(() => props.product.spuId || props.product.id || '')
const productName = computed(() => props.product.spuName || props.product.title || '')
const productBrand = computed(() => props.product.brandName || props.product.brand || '')
const productImage = computed(() => {
  const img = props.product.coverImage || props.product.image_url || ''
  // Agent 图片需要加 /agent 前缀
  if (img && img.startsWith('/static/')) return '/agent' + img
  return img || placeholderImg(productName.value)
})
const displayPrice = computed(() => props.product.minSalePrice ?? props.product.price ?? 0)

const productLink = computed(() => {
  // Agent 商品（字符串 ID）跳转到 Agent 详情页
  const id = productId.value
  if (typeof id === 'string' && id.startsWith('p_')) {
    return `/agent-product/${id}`
  }
  return `/products/${id}`
})

const hasPromotion = computed(() =>
  props.product.minPromotionPrice && props.product.minPromotionPrice < displayPrice.value
)
</script>

<style scoped>
.product-card {
  display: flex;
  flex-direction: column;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  overflow: hidden;
  text-decoration: none;
  transition: all var(--transition);
  cursor: pointer;
}

.product-card:hover {
  border-color: var(--border-strong);
  box-shadow: var(--shadow-md);
  transform: translateY(-3px);
}

.product-img-wrap {
  position: relative;
  aspect-ratio: 1 / 1;
  background: var(--surface-dim);
  overflow: hidden;
}

.product-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  transition: transform 400ms var(--ease-out);
}

.product-card:hover .product-img {
  transform: scale(1.04);
}

.product-promo-badge {
  position: absolute;
  top: 12px;
  left: 12px;
  padding: 3px 10px;
  background: var(--gold);
  color: var(--ink);
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.06em;
  border-radius: 100px;
}

.product-info {
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 4px;
  flex: 1;
}

.product-brand {
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.08em;
  color: var(--ink-faint);
  text-transform: uppercase;
}

.product-name {
  font-size: 14px;
  font-weight: 500;
  color: var(--ink);
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.product-sub {
  font-size: 12px;
  color: var(--ink-muted);
  display: -webkit-box;
  -webkit-line-clamp: 1;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.product-price-row {
  margin-top: 8px;
  display: flex;
  align-items: baseline;
  gap: 8px;
}

.price-range {
  font-size: 12px;
  color: var(--ink-faint);
  font-family: var(--font-mono);
}
</style>
