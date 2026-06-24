<template>
  <div class="order-list-page">
    <div class="uc-section-title">我的订单</div>

    <!-- Status Tabs -->
    <div class="order-tabs">
      <button
        v-for="tab in tabs"
        :key="tab.value"
        class="order-tab"
        :class="{ active: currentStatus === tab.value }"
        @click="currentStatus = tab.value; loadOrders()"
      >{{ tab.label }}</button>
    </div>

    <!-- List -->
    <div v-if="loading" class="order-skeleton-list">
      <div v-for="i in 3" :key="i" class="order-skeleton"></div>
    </div>

    <div v-else-if="orders.length" class="order-list">
      <div v-for="order in orders" :key="order.orderNo" class="order-card">
        <div class="order-card-hd">
          <div class="order-no">
            <span class="font-mono">{{ order.orderNo }}</span>
          </div>
          <div class="order-status" :class="ORDER_STATUS[order.status]?.class">
            {{ ORDER_STATUS[order.status]?.label || order.status }}
          </div>
        </div>
        <div class="order-card-body">
          <div class="order-product-preview">
            <img :src="order.firstSkuImage || placeholderImg(order.firstSkuName)" class="order-preview-img" />
            <div class="order-preview-info">
              <div class="order-preview-name">{{ order.firstSkuName }}</div>
              <div class="order-preview-qty">共 {{ order.totalQuantity }} 件</div>
            </div>
          </div>
          <div class="order-card-right">
            <div class="order-amount price-sale">{{ formatPrice(order.payableAmount) }}</div>
            <div class="order-date">{{ formatDate(order.createTime) }}</div>
          </div>
        </div>
        <div class="order-card-ft">
          <RouterLink :to="`/user/orders/${order.orderNo}`" class="btn btn-outline btn-sm">查看详情</RouterLink>
          <RouterLink v-if="order.status === 10" :to="`/pay/${order.orderNo}`" class="btn btn-gold btn-sm">去支付</RouterLink>
          <button v-if="order.status === 10" class="btn btn-ghost btn-sm" @click="cancelOrder(order.orderNo)">取消订单</button>
        </div>
      </div>
    </div>

    <div class="empty-state" v-else>
      <div class="empty-state__icon">📋</div>
      <div class="empty-state__title">暂无订单</div>
      <RouterLink to="/products" class="btn btn-outline">去购物</RouterLink>
    </div>

    <!-- Pagination -->
    <div class="pagination" v-if="total > pageSize">
      <button class="page-btn" :disabled="currentPage <= 1" @click="goPage(currentPage - 1)">← 上一页</button>
      <span class="page-info">{{ currentPage }} / {{ Math.ceil(total / pageSize) }}</span>
      <button class="page-btn" :disabled="currentPage >= Math.ceil(total / pageSize)" @click="goPage(currentPage + 1)">下一页 →</button>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { orderApi } from '@/api'
import { formatPrice, formatDate, ORDER_STATUS, placeholderImg } from '@/utils'

const tabs = [
  { label: '全部', value: null },
  { label: '待付款', value: 10 },
  { label: '已付款', value: 20 },
  { label: '已取消', value: 30 }
]

const orders = ref([])
const loading = ref(true)
const currentStatus = ref(null)
const currentPage = ref(1)
const pageSize = 10
const total = ref(0)

async function loadOrders() {
  loading.value = true
  try {
    const params = { current: currentPage.value, size: pageSize }
    if (currentStatus.value) params.status = currentStatus.value
    const res = await orderApi.getPage(params)
    orders.value = res.data?.records || []
    total.value = res.data?.total || 0
  } finally {
    loading.value = false
  }
}

async function cancelOrder(orderNo) {
  if (!confirm('确定取消订单？')) return
  try {
    await orderApi.cancel(orderNo, { cancelReason: '用户主动取消' })
    loadOrders()
  } catch (e) {
    alert(e.message)
  }
}

function goPage(p) {
  currentPage.value = p
  loadOrders()
}

onMounted(loadOrders)
</script>

<style scoped>
.order-list-page {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.uc-section-title {
  font-size: 20px;
  font-weight: 700;
  color: var(--ink);
}

.order-tabs {
  display: flex;
  gap: 4px;
  border-bottom: 1px solid var(--border);
  padding-bottom: 0;
}

.order-tab {
  padding: 8px 18px;
  font-size: 14px;
  font-weight: 500;
  color: var(--ink-muted);
  border-bottom: 2px solid transparent;
  margin-bottom: -1px;
  transition: all var(--transition);
  cursor: pointer;
  background: none;
  border-top: none;
  border-left: none;
  border-right: none;
}

.order-tab:hover { color: var(--ink); }
.order-tab.active {
  color: var(--ink);
  border-bottom-color: var(--ink);
  font-weight: 600;
}

.order-skeleton-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.order-skeleton {
  height: 140px;
  background: linear-gradient(90deg, var(--surface-dim) 25%, var(--border) 50%, var(--surface-dim) 75%);
  background-size: 200% 100%;
  animation: shimmer 1.5s infinite;
  border-radius: var(--radius-md);
}

@keyframes shimmer {
  from { background-position: 200% 0; }
  to { background-position: -200% 0; }
}

.order-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.order-card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  overflow: hidden;
  transition: box-shadow var(--transition);
}

.order-card:hover {
  box-shadow: var(--shadow-sm);
}

.order-card-hd {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  background: var(--surface-dim);
  border-bottom: 1px solid var(--border);
}

.order-no {
  font-size: 13px;
  color: var(--ink-muted);
}

.order-status {
  font-size: 12px;
  font-weight: 600;
  padding: 3px 10px;
  border-radius: 100px;
}

.badge-gold {
  background: var(--gold-pale);
  color: var(--gold-dark);
}

.badge-success {
  background: #f0faf5;
  color: var(--success);
}

.badge-muted {
  background: var(--surface-dim);
  color: var(--ink-muted);
}

.order-card-body {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px;
  gap: 16px;
}

.order-product-preview {
  display: flex;
  align-items: center;
  gap: 12px;
}

.order-preview-img {
  width: 56px;
  height: 56px;
  border-radius: var(--radius-sm);
  object-fit: cover;
  border: 1px solid var(--border);
  flex-shrink: 0;
}

.order-preview-name {
  font-size: 14px;
  font-weight: 500;
  color: var(--ink);
}

.order-preview-qty {
  font-size: 12px;
  color: var(--ink-muted);
  margin-top: 4px;
}

.order-card-right {
  text-align: right;
  flex-shrink: 0;
}

.order-amount {
  font-size: 18px;
  font-weight: 700;
}

.order-date {
  font-size: 12px;
  color: var(--ink-faint);
  margin-top: 4px;
}

.order-card-ft {
  display: flex;
  justify-content: flex-end;
  align-items: center;
  gap: 8px;
  padding: 12px 16px;
  border-top: 1px solid var(--border);
}

.pagination {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 16px;
}

.page-btn {
  padding: 8px 16px;
  border-radius: var(--radius-sm);
  font-size: 13px;
  color: var(--ink-muted);
  background: var(--surface);
  border: 1px solid var(--border);
  cursor: pointer;
  transition: all var(--transition);
}

.page-btn:hover:not(:disabled) {
  border-color: var(--ink);
  color: var(--ink);
}

.page-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.page-info {
  font-size: 14px;
  color: var(--ink-muted);
  font-family: var(--font-mono);
}
</style>
