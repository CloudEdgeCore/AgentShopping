<template>
  <div class="home-page">
    <section class="hero">
      <div class="hero-bg">
        <div class="hero-blob blob-1"></div>
        <div class="hero-blob blob-2"></div>
        <div class="hero-grain"></div>
      </div>
      <div class="container">
        <div class="hero-content">
          <div class="hero-badge badge badge-gold">NEW SEASON 2026</div>
          <h1 class="hero-title">
            品味生活<br />
            <em>从一件好物开始</em>
          </h1>
          <p class="hero-desc">
            精选全球优质品牌，每一件商品都经过严选，只把真正值得买的好东西带到你面前。
          </p>
          <div class="hero-actions">
            <RouterLink to="/products" class="btn btn-primary btn-lg">探索全部商品</RouterLink>
            <RouterLink to="/products" class="btn btn-outline btn-lg">按分类挑选</RouterLink>
          </div>
        </div>
      </div>
      <div class="hero-scroll-hint">
        <div class="scroll-line"></div>
        <span>向下探索</span>
      </div>
    </section>

    <section class="section category-section">
      <div class="container">
        <div class="section-header section-header--stack">
          <div>
            <div class="section-eyebrow">分类导览</div>
            <h2 class="section-title">先选主分类，再快速进入你真正想买的子分类</h2>
            <p class="section-desc">
              主分类负责帮你定方向，子分类负责帮你缩小范围。这样挑商品会更快，也更符合用户直觉。
            </p>
          </div>
          <RouterLink to="/products" class="section-more">查看全部商品 →</RouterLink>
        </div>

        <div v-if="categoryLoading" class="category-skeleton-grid">
          <div v-for="i in 4" :key="i" class="category-skeleton"></div>
        </div>

        <div v-else-if="featuredCategories.length" class="category-showcase">
          <article v-for="category in featuredCategories" :key="category.id" class="category-stage">
            <div class="category-stage-top">
              <RouterLink :to="getCategoryLink(category.id)" class="category-stage-main">
                <div class="category-stage-icon">
                  <img v-if="category.iconUrl" :src="category.iconUrl" :alt="category.name" />
                  <span v-else>{{ category.name.charAt(0) }}</span>
                </div>
                <div class="category-stage-copy">
                  <div class="category-stage-kicker">主分类</div>
                  <h3>{{ category.name }}</h3>
                  <p>{{ getCategoryDescription(category) }}</p>
                </div>
              </RouterLink>
              <RouterLink :to="getCategoryLink(category.id)" class="category-stage-link">浏览该分类</RouterLink>
            </div>

            <div v-if="category.children?.length" class="category-stage-children">
              <RouterLink
                v-for="child in category.children.slice(0, 6)"
                :key="child.id"
                :to="getCategoryLink(child.id)"
                class="child-link"
              >
                <span>{{ child.name }}</span>
                <small>子分类</small>
              </RouterLink>
            </div>

            <div v-else class="category-stage-empty">
              当前主分类下还没有拆分子分类，可以直接进入分类页浏览商品。
            </div>
          </article>
        </div>

        <div v-else class="empty-state empty-state--light">
          <div class="empty-state__icon">📁</div>
          <div class="empty-state__title">分类整理中</div>
          <div class="empty-state__desc">很快就会有更完整的分类导航。</div>
        </div>
      </div>
    </section>

    <section class="flash-sale-banner" v-if="hasFlashSale">
      <div class="container">
        <div class="flash-inner">
          <div class="flash-left">
            <div class="flash-tag">限时秒杀</div>
            <div class="flash-title">今日特惠</div>
            <div class="flash-desc">限时折扣，抢完即止</div>
          </div>
          <RouterLink to="/products" class="btn btn-gold">立即抢购</RouterLink>
        </div>
      </div>
    </section>

    <section class="section">
      <div class="container">
        <div class="section-header">
          <h2 class="section-title">精选好物</h2>
          <RouterLink to="/products" class="section-more">查看更多 →</RouterLink>
        </div>

        <div class="product-grid" v-if="loading">
          <div v-for="i in 8" :key="i" class="product-card-skeleton"></div>
        </div>

        <div class="product-grid" v-else-if="products.length">
          <ProductCard v-for="product in products" :key="product.spuId" :product="product" />
        </div>

        <div class="empty-state" v-else>
          <div class="empty-state__icon">🛍</div>
          <div class="empty-state__title">暂时没有商品</div>
        </div>
      </div>
    </section>

    <section class="brands-section" v-if="brands.length">
      <div class="container">
        <div class="section-header">
          <h2 class="section-title">合作品牌</h2>
        </div>
        <div class="brands-track">
          <div class="brands-row">
            <div v-for="brand in marqueeBrands" :key="brand.key" class="brand-chip">
              <img v-if="brand.logoUrl" :src="brand.logoUrl" :alt="brand.name" />
              <span v-else>{{ brand.name }}</span>
            </div>
          </div>
        </div>
      </div>
    </section>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { productApi } from '@/api'
import ProductCard from '@/components/shop/ProductCard.vue'

const categories = ref([])
const brands = ref([])
const products = ref([])
const loading = ref(true)
const categoryLoading = ref(true)
const hasFlashSale = ref(false)

const featuredCategories = computed(() => categories.value.slice(0, 6))
const marqueeBrands = computed(() =>
  [...brands.value, ...brands.value].map((brand, index) => ({
    ...brand,
    key: `${brand.id}-${index}`
  }))
)

function getCategoryLink(categoryId) {
  return `/products?categoryId=${categoryId}`
}

function getCategoryDescription(category) {
  const childCount = category.children?.length || 0
  if (childCount > 0) {
    return `下设 ${childCount} 个子分类，进入后可以继续按更细的品类快速筛选。`
  }
  return '这个分类已经可以直接进入浏览商品，不需要再多点一步。'
}

onMounted(async () => {
  try {
    const [categoryRes, brandRes, productRes] = await Promise.all([
      productApi.getCategories(),
      productApi.getBrands(),
      productApi.getPage({ current: 1, size: 8 })
    ])

    categories.value = categoryRes.data || []
    brands.value = brandRes.data || []
    products.value = productRes.data?.records || []
  } catch (error) {
    console.error(error)
  } finally {
    categoryLoading.value = false
    loading.value = false
  }
})
</script>

<style scoped>
.home-page {
  overflow: hidden;
}

.hero {
  position: relative;
  min-height: 600px;
  display: flex;
  align-items: center;
  overflow: hidden;
  padding: 100px 0 80px;
}

.hero-bg {
  position: absolute;
  inset: 0;
  z-index: 0;
}

.hero-blob {
  position: absolute;
  border-radius: 50%;
  filter: blur(80px);
  opacity: 0.12;
}

.blob-1 {
  width: 600px;
  height: 600px;
  background: radial-gradient(circle, #c9a84c, #e8c96e);
  top: -200px;
  right: -100px;
}

.blob-2 {
  width: 420px;
  height: 420px;
  background: radial-gradient(circle, #1a1a2e, #2d2d4a);
  bottom: -120px;
  left: -120px;
}

.hero-grain {
  position: absolute;
  inset: 0;
  background-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noise'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noise)' opacity='0.04'/%3E%3C/svg%3E");
  pointer-events: none;
}

.hero-content {
  position: relative;
  z-index: 1;
  max-width: 620px;
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.hero-title {
  font-size: clamp(40px, 5vw, 72px);
  font-weight: 700;
  line-height: 1.08;
  color: var(--ink);
}

.hero-title em {
  font-style: italic;
  color: var(--gold-dark);
}

.hero-desc {
  max-width: 500px;
  font-size: 16px;
  line-height: 1.75;
  color: var(--ink-muted);
}

.hero-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
}

.hero-scroll-hint {
  position: absolute;
  left: 50%;
  bottom: 32px;
  transform: translateX(-50%);
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  letter-spacing: 0.06em;
  color: var(--ink-faint);
}

.scroll-line {
  width: 1px;
  height: 40px;
  background: linear-gradient(to bottom, transparent, var(--ink-faint));
  animation: scroll-pulse 1.8s ease-in-out infinite;
}

@keyframes scroll-pulse {
  0%,
  100% {
    opacity: 0.3;
  }

  50% {
    opacity: 1;
  }
}

.section {
  padding: 64px 0;
}

.section-header {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 32px;
}

.section-header--stack {
  align-items: flex-end;
}

.section-eyebrow {
  margin-bottom: 10px;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--gold-dark);
}

.section-title {
  font-size: 28px;
  font-weight: 700;
  line-height: 1.25;
  color: var(--ink);
}

.section-desc {
  max-width: 680px;
  margin-top: 10px;
  font-size: 14px;
  line-height: 1.8;
  color: var(--ink-muted);
}

.section-more {
  font-size: 14px;
  color: var(--ink-muted);
  transition: color var(--transition);
}

.section-more:hover {
  color: var(--gold-dark);
}

.category-section {
  padding-top: 20px;
}

.category-showcase {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 18px;
}

.category-stage {
  display: flex;
  flex-direction: column;
  gap: 18px;
  padding: 24px;
  border: 1px solid rgba(201, 168, 76, 0.18);
  border-radius: 28px;
  background:
    linear-gradient(180deg, rgba(255, 249, 236, 0.88), rgba(255, 255, 255, 0.98)),
    var(--surface);
  box-shadow: 0 24px 60px rgba(18, 24, 38, 0.06);
}

.category-stage-top {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
}

.category-stage-main {
  display: flex;
  align-items: flex-start;
  gap: 16px;
  min-width: 0;
  color: inherit;
  text-decoration: none;
}

.category-stage-icon {
  width: 60px;
  height: 60px;
  flex-shrink: 0;
  border-radius: 18px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, rgba(201, 168, 76, 0.18), rgba(255, 255, 255, 0.94));
  color: var(--gold-dark);
  font-size: 24px;
  font-weight: 700;
  overflow: hidden;
}

.category-stage-icon img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.category-stage-copy {
  min-width: 0;
}

.category-stage-kicker {
  display: inline-flex;
  margin-bottom: 8px;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--gold-dark);
}

.category-stage-copy h3 {
  font-size: 22px;
  font-weight: 700;
  color: var(--ink);
}

.category-stage-copy p {
  margin-top: 8px;
  font-size: 14px;
  line-height: 1.75;
  color: var(--ink-muted);
}

.category-stage-link {
  flex-shrink: 0;
  padding: 9px 14px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.9);
  border: 1px solid rgba(201, 168, 76, 0.2);
  font-size: 13px;
  color: var(--ink-soft);
  transition: all var(--transition);
}

.category-stage-link:hover {
  color: var(--gold-dark);
  border-color: rgba(201, 168, 76, 0.42);
}

.category-stage-children {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.child-link {
  display: inline-flex;
  flex-direction: column;
  gap: 3px;
  min-width: 120px;
  padding: 12px 14px;
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.78);
  border: 1px solid rgba(18, 24, 38, 0.08);
  color: inherit;
  text-decoration: none;
  transition: transform var(--transition), border-color var(--transition), box-shadow var(--transition);
}

.child-link span {
  font-size: 14px;
  font-weight: 600;
  color: var(--ink);
}

.child-link small {
  font-size: 12px;
  color: var(--ink-muted);
}

.child-link:hover {
  transform: translateY(-1px);
  border-color: rgba(201, 168, 76, 0.35);
  box-shadow: 0 14px 24px rgba(18, 24, 38, 0.08);
}

.category-stage-empty {
  padding: 14px 16px;
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.74);
  color: var(--ink-muted);
  font-size: 13px;
  line-height: 1.7;
}

.category-skeleton-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 18px;
}

.category-skeleton,
.product-card-skeleton {
  background: linear-gradient(90deg, var(--surface-dim) 25%, var(--border) 50%, var(--surface-dim) 75%);
  background-size: 200% 100%;
  animation: shimmer 1.5s infinite;
}

.category-skeleton {
  height: 220px;
  border-radius: 28px;
}

.flash-sale-banner {
  margin: 0 0 64px;
  padding: 40px 0;
  background: linear-gradient(135deg, var(--ink) 0%, var(--accent-mid) 100%);
}

.flash-inner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 20px;
}

.flash-left {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.flash-tag {
  font-size: 12px;
  font-weight: 600;
  letter-spacing: 0.08em;
  color: var(--gold);
}

.flash-title {
  font-size: 28px;
  font-family: var(--font-display);
  font-weight: 700;
  color: var(--surface);
}

.flash-desc {
  font-size: 14px;
  color: rgba(255, 255, 255, 0.65);
}

.product-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 24px;
}

.product-card-skeleton {
  height: 340px;
  border-radius: var(--radius-md);
}

.brands-section {
  padding: 48px 0;
  background: var(--surface-dim);
  overflow: hidden;
}

.brands-track {
  overflow: hidden;
  mask-image: linear-gradient(to right, transparent, black 10%, black 90%, transparent);
}

.brands-row {
  display: flex;
  gap: 24px;
  width: max-content;
  animation: scroll-brands 20s linear infinite;
}

.brand-chip {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 52px;
  padding: 0 24px;
  flex-shrink: 0;
  border: 1px solid var(--border);
  border-radius: 999px;
  background: var(--surface);
  color: var(--ink-soft);
  font-size: 14px;
  font-weight: 600;
  white-space: nowrap;
}

.brand-chip img {
  width: auto;
  height: 32px;
  object-fit: contain;
  filter: grayscale(1);
  opacity: 0.6;
}

.empty-state--light {
  background: linear-gradient(180deg, rgba(255, 249, 236, 0.58), rgba(255, 255, 255, 0.92));
}

@keyframes shimmer {
  from {
    background-position: 200% 0;
  }

  to {
    background-position: -200% 0;
  }
}

@keyframes scroll-brands {
  from {
    transform: translateX(0);
  }

  to {
    transform: translateX(-50%);
  }
}

@media (max-width: 1100px) {
  .category-showcase,
  .category-skeleton-grid {
    grid-template-columns: 1fr;
  }

  .product-grid {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
}

@media (max-width: 768px) {
  .hero {
    min-height: auto;
    padding: 88px 0 72px;
  }

  .section-header,
  .section-header--stack,
  .flash-inner,
  .category-stage-top {
    flex-direction: column;
    align-items: flex-start;
  }

  .hero-scroll-hint {
    display: none;
  }

  .product-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 16px;
  }
}

@media (max-width: 640px) {
  .category-stage {
    padding: 20px;
    border-radius: 22px;
  }

  .category-stage-main {
    width: 100%;
  }

  .category-stage-link {
    width: 100%;
    text-align: center;
  }

  .child-link {
    min-width: calc(50% - 5px);
  }
}
</style>
