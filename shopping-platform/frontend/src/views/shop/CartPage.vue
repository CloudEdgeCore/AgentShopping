<template>
  <div class="cart-page">
    <div class="container">
      <div class="page-title-row">
        <h1 class="page-title">购物车</h1>
        <span class="cart-count">{{ cartStore.totalCount }} 件</span>
      </div>

      <div class="cart-layout" v-if="cartStore.items.length">
        <!-- Items -->
        <div class="cart-items">
          <!-- Header -->
          <div class="cart-header">
            <span>商品信息</span>
            <span>单价</span>
            <span>数量</span>
            <span>小计</span>
            <span>操作</span>
          </div>

          <TransitionGroup name="slide-up" tag="div">
            <div
              v-for="item in cartStore.items"
              :key="item.id"
              class="cart-item"
              :class="{ unavailable: !item.productAvailable }"
            >
              <!-- Checkbox -->
              <label class="cart-check">
                <input
                  type="checkbox"
                  :checked="item.checked"
                  @change="cartStore.toggleChecked(item.id, !item.checked)"
                />
              </label>

              <!-- Product -->
              <RouterLink :to="`/products/${item.spuId}`" class="cart-product">
                <img :src="item.skuImage || placeholderImg(item.spuName)" :alt="item.spuName" class="cart-img" />
                <div class="cart-product-info">
                  <div class="cart-product-name">{{ item.spuName }}</div>
                  <div class="cart-product-attr" v-if="item.skuAttrText">{{ item.skuAttrText }}</div>
                  <div class="badge badge-danger" v-if="!item.productAvailable">已下架</div>
                  <div class="badge badge-gold" v-if="item.priceChanged">价格已变动</div>
                </div>
              </RouterLink>

              <!-- Price -->
              <div class="cart-price">
                <span v-if="item.priceChanged" class="price-sale">{{ formatPrice(item.currentSalePrice) }}</span>
                <span v-else class="price">{{ formatPrice(item.salePrice) }}</span>
                <span v-if="item.priceChanged" class="price-original">{{ formatPrice(item.salePrice) }}</span>
              </div>

              <!-- Quantity -->
              <div class="cart-qty">
                <div class="quantity-control">
                  <button class="qty-btn" @click="handleQtyChange(item, item.quantity - 1)">−</button>
                  <span class="qty-num">{{ item.quantity }}</span>
                  <button class="qty-btn" @click="handleQtyChange(item, item.quantity + 1)">+</button>
                </div>
              </div>

              <!-- Subtotal -->
              <div class="cart-subtotal price">{{ formatPrice(item.lineAmount) }}</div>

              <!-- Actions -->
              <div class="cart-actions">
                <button class="btn btn-ghost btn-icon" @click="cartStore.removeItem(item.id)" title="删除">
                  <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.5" style="width:16px;height:16px">
                    <path d="M5 6h10m-1 0V16a1 1 0 01-1 1H7a1 1 0 01-1-1V6M8 6V4h4v2"/>
                  </svg>
                </button>
              </div>
            </div>
          </TransitionGroup>

          <!-- Clear -->
          <div class="cart-footer-row">
            <button class="btn btn-ghost btn-sm" @click="cartStore.clearCart">清空购物车</button>
          </div>
        </div>

        <!-- Summary -->
        <div class="cart-summary">
          <div class="summary-card">
            <div class="summary-title">订单摘要</div>
            <div class="summary-row">
              <span>已选商品</span>
              <span>{{ cartStore.cartData?.checkedItemCount || 0 }} 件</span>
            </div>
            <div class="summary-row">
              <span>商品金额</span>
              <span class="price">{{ formatPrice(cartStore.checkedAmount) }}</span>
            </div>
            <hr class="divider" />
            <div class="summary-total-row">
              <span>合计</span>
              <span class="price-sale summary-total-price">{{ formatPrice(cartStore.checkedAmount) }}</span>
            </div>
            <button
              class="btn btn-primary btn-block btn-lg"
              @click="goCheckout"
              :disabled="!cartStore.cartData?.checkedItemCount"
            >
              去结算 ({{ cartStore.cartData?.checkedItemCount || 0 }})
            </button>
            <RouterLink to="/products" class="continue-shopping">继续购物</RouterLink>
          </div>
        </div>
      </div>

      <!-- Empty -->
      <div class="empty-state" v-else>
        <div class="empty-state__icon">🛒</div>
        <div class="empty-state__title">购物车还是空的</div>
        <div class="empty-state__desc">快去挑选心仪的商品吧</div>
        <RouterLink to="/products" class="btn btn-primary">去购物</RouterLink>
      </div>
    </div>
  </div>
</template>

<script setup>
import { onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useCartStore } from '@/stores/cart'
import { formatPrice, placeholderImg } from '@/utils'

const router = useRouter()
const cartStore = useCartStore()

onMounted(() => cartStore.fetchCart())

async function handleQtyChange(item, qty) {
  if (qty < 1) return
  if (qty > 999) return
  await cartStore.updateQuantity(item.id, qty)
}

function goCheckout() {
  const checkedIds = cartStore.items.filter(i => i.checked).map(i => i.id)
  if (!checkedIds.length) return
  router.push({ name: 'Checkout', query: { mode: 'cart', cartItemIds: checkedIds.join(',') } })
}
</script>

<style scoped>
.cart-page {
  padding: 40px 0 80px;
}

.page-title-row {
  display: flex;
  align-items: baseline;
  gap: 12px;
  margin-bottom: 32px;
}

.page-title {
  font-size: 28px;
  font-weight: 700;
}

.cart-count {
  font-size: 14px;
  color: var(--ink-muted);
}

.cart-layout {
  display: grid;
  grid-template-columns: 1fr 320px;
  gap: 32px;
  align-items: start;
}

@media (max-width: 900px) {
  .cart-layout { grid-template-columns: 1fr; }
}

/* Cart Items */
.cart-items {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  overflow: hidden;
}

.cart-header {
  display: grid;
  grid-template-columns: 36px 1fr 100px 96px 80px 48px;
  gap: 16px;
  align-items: center;
  padding: 12px 20px;
  background: var(--surface-dim);
  border-bottom: 1px solid var(--border);
  font-size: 12px;
  font-weight: 600;
  color: var(--ink-muted);
  letter-spacing: 0.04em;
}

.cart-item {
  display: grid;
  grid-template-columns: 36px 1fr 100px 96px 80px 48px;
  gap: 16px;
  align-items: center;
  padding: 20px;
  border-bottom: 1px solid var(--border);
  transition: background var(--transition);
}

.cart-item:last-of-type { border-bottom: none; }

.cart-item.unavailable {
  opacity: 0.6;
  background: var(--surface-dim);
}

.cart-check {
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
}

.cart-check input[type="checkbox"] {
  width: 18px;
  height: 18px;
  cursor: pointer;
  accent-color: var(--ink);
}

.cart-product {
  display: flex;
  align-items: center;
  gap: 14px;
  text-decoration: none;
  min-width: 0;
}

.cart-img {
  width: 72px;
  height: 72px;
  object-fit: cover;
  border-radius: var(--radius-sm);
  border: 1px solid var(--border);
  flex-shrink: 0;
}

.cart-product-info {
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 0;
}

.cart-product-name {
  font-size: 14px;
  font-weight: 500;
  color: var(--ink);
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.cart-product-attr {
  font-size: 12px;
  color: var(--ink-muted);
}

.cart-price {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

/* Quantity control */
.quantity-control {
  display: flex;
  align-items: center;
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  overflow: hidden;
}

.qty-btn {
  width: 30px;
  height: 30px;
  font-size: 16px;
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

.qty-num {
  width: 36px;
  text-align: center;
  font-size: 14px;
  font-weight: 600;
  border-left: 1px solid var(--border);
  border-right: 1px solid var(--border);
  padding: 4px 0;
}

.cart-subtotal {
  font-weight: 600;
}

.cart-actions {
  display: flex;
  justify-content: flex-end;
}

.cart-footer-row {
  padding: 12px 20px;
  display: flex;
  justify-content: flex-end;
  border-top: 1px solid var(--border);
}

/* Summary */
.cart-summary {
  position: sticky;
  top: 88px;
}

.summary-card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  padding: 24px;
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.summary-title {
  font-size: 16px;
  font-weight: 700;
  color: var(--ink);
  margin-bottom: 4px;
}

.summary-row {
  display: flex;
  justify-content: space-between;
  font-size: 14px;
  color: var(--ink-soft);
}

.summary-total-row {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
}

.summary-total-row > span:first-child {
  font-size: 15px;
  font-weight: 600;
  color: var(--ink);
}

.summary-total-price {
  font-size: 24px;
  font-weight: 700;
}

.continue-shopping {
  display: block;
  text-align: center;
  font-size: 13px;
  color: var(--ink-muted);
  margin-top: 4px;
  transition: color var(--transition);
}

.continue-shopping:hover {
  color: var(--gold-dark);
}
</style>
