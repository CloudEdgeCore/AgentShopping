<template>
  <div class="order-detail-page">
    <div class="back-row">
      <RouterLink to="/user/orders" class="btn btn-ghost btn-sm">← 返回订单列表</RouterLink>
    </div>

    <div v-if="loading" class="empty-state">
      <div class="spinner" style="width:32px;height:32px;border-width:3px"></div>
    </div>

    <div v-else-if="order" class="order-detail">
      <!-- Status Banner -->
      <div class="status-banner" :class="statusInfo.bannerClass">
        <div class="status-icon">{{ statusInfo.icon }}</div>
        <div>
          <div class="status-text">{{ statusInfo.label }}</div>
          <div class="status-sub">{{ statusInfo.sub }}</div>
        </div>
        <div class="status-actions">
          <RouterLink v-if="order.status === 10" :to="`/pay/${order.orderNo}`" class="btn btn-gold btn-sm">去支付</RouterLink>
          <button v-if="order.status === 10" class="btn btn-outline btn-sm" @click="cancelOrder">取消订单</button>
        </div>
      </div>

      <div class="detail-grid">
        <!-- Address -->
        <div class="detail-card">
          <div class="detail-card-title">收货信息</div>
          <div class="detail-row">
            <span class="detail-label">收货人</span>
            <span>{{ order.receiverName }}</span>
          </div>
          <div class="detail-row">
            <span class="detail-label">手机号</span>
            <span class="font-mono">{{ order.receiverMobile }}</span>
          </div>
          <div class="detail-row">
            <span class="detail-label">地址</span>
            <span>{{ [order.provinceName, order.cityName, order.districtName, order.detailAddress].filter(Boolean).join(' ') }}</span>
          </div>
          <div v-if="order.remark" class="detail-row">
            <span class="detail-label">备注</span>
            <span>{{ order.remark }}</span>
          </div>
        </div>

        <!-- Order Info -->
        <div class="detail-card">
          <div class="detail-card-title">订单信息</div>
          <div class="detail-row">
            <span class="detail-label">订单号</span>
            <span class="font-mono">{{ order.orderNo }}</span>
          </div>
          <div class="detail-row">
            <span class="detail-label">创建时间</span>
            <span>{{ formatDate(order.createTime) }}</span>
          </div>
          <div class="detail-row" v-if="order.payTime">
            <span class="detail-label">支付时间</span>
            <span>{{ formatDate(order.payTime) }}</span>
          </div>
          <div class="detail-row" v-if="order.cancelTime">
            <span class="detail-label">取消时间</span>
            <span>{{ formatDate(order.cancelTime) }}</span>
          </div>
          <div class="detail-row" v-if="order.cancelReason">
            <span class="detail-label">取消原因</span>
            <span>{{ order.cancelReason }}</span>
          </div>
        </div>
      </div>

      <!-- Items -->
      <div class="detail-card">
        <div class="detail-card-title">商品清单</div>
        <div class="order-items">
          <div v-for="item in order.items" :key="item.skuId" class="order-item">
            <img :src="item.skuImage || placeholderImg(item.spuName)" class="order-item-img" />
            <div class="order-item-info">
              <div class="order-item-name">{{ item.spuName }}</div>
              <div class="order-item-sku">{{ item.skuName }}</div>
              <div class="order-item-attr" v-if="item.skuAttrText">{{ item.skuAttrText }}</div>
            </div>
            <div class="order-item-right">
              <div class="price">{{ formatPrice(item.salePrice) }}</div>
              <div class="order-item-qty">× {{ item.quantity }}</div>
              <div class="price-sale" style="font-size:13px">= {{ formatPrice(item.totalAmount) }}</div>
            </div>
          </div>
        </div>

        <!-- Price breakdown -->
        <div class="price-breakdown">
          <div class="price-row">
            <span>商品合计</span>
            <span class="price">{{ formatPrice(order.totalAmount) }}</span>
          </div>
          <div class="price-row" v-if="order.promotionAmount">
            <span>活动优惠</span>
            <span class="text-success">-{{ formatPrice(order.promotionAmount) }}</span>
          </div>
          <div class="price-row" v-if="order.couponAmount">
            <span>优惠券 ({{ order.couponName }})</span>
            <span class="text-success">-{{ formatPrice(order.couponAmount) }}</span>
          </div>
          <div class="price-row price-row--total">
            <span>实付款</span>
            <span class="price-sale" style="font-size:22px">{{ formatPrice(order.payableAmount) }}</span>
          </div>
        </div>
      </div>
    </div>

    <div class="empty-state" v-else>
      <div class="empty-state__icon">🔍</div>
      <div class="empty-state__title">订单不存在</div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { orderApi } from '@/api'
import { formatPrice, formatDate, placeholderImg } from '@/utils'

const route = useRoute()
const router = useRouter()
const order = ref(null)
const loading = ref(true)

const statusMap = {
  10: { label: '待付款', sub: '请及时完成支付', icon: '⏰', bannerClass: 'banner-gold' },
  20: { label: '已支付', sub: '订单已完成支付', icon: '✓', bannerClass: 'banner-success' },
  30: { label: '已取消', sub: '订单已取消', icon: '✕', bannerClass: 'banner-muted' }
}

const statusInfo = computed(() => statusMap[order.value?.status] || { label: '未知', sub: '', icon: '?', bannerClass: '' })

async function load() {
  loading.value = true
  try {
    const res = await orderApi.getDetail(route.params.orderNo)
    order.value = res.data
  } catch (e) {
    order.value = null
  } finally {
    loading.value = false
  }
}

async function cancelOrder() {
  if (!confirm('确定取消订单？')) return
  try {
    await orderApi.cancel(order.value.orderNo, { cancelReason: '用户主动取消' })
    await load()
  } catch (e) {
    alert(e.message)
  }
}

onMounted(load)
</script>

<style scoped>
.order-detail-page {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.back-row {
  margin-bottom: 4px;
}

.order-detail {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

/* Status Banner */
.status-banner {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 20px 24px;
  border-radius: var(--radius-md);
  border: 1.5px solid;
}

.banner-gold { background: var(--gold-pale); border-color: rgba(201,168,76,0.35); }
.banner-success { background: #f0faf5; border-color: rgba(45,158,110,0.3); }
.banner-muted { background: var(--surface-dim); border-color: var(--border); }

.status-icon {
  font-size: 28px;
}

.status-text {
  font-size: 18px;
  font-weight: 700;
  color: var(--ink);
}

.status-sub {
  font-size: 13px;
  color: var(--ink-muted);
  margin-top: 2px;
}

.status-actions {
  margin-left: auto;
  display: flex;
  gap: 8px;
}

/* Detail Grid */
.detail-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}

@media (max-width: 640px) {
  .detail-grid { grid-template-columns: 1fr; }
}

.detail-card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.detail-card-title {
  font-size: 15px;
  font-weight: 700;
  color: var(--ink);
  margin-bottom: 4px;
  padding-bottom: 12px;
  border-bottom: 1px solid var(--border);
}

.detail-row {
  display: flex;
  gap: 16px;
  font-size: 14px;
  color: var(--ink-soft);
}

.detail-label {
  color: var(--ink-muted);
  width: 60px;
  flex-shrink: 0;
}

/* Order Items */
.order-items {
  display: flex;
  flex-direction: column;
  gap: 16px;
  margin-bottom: 20px;
}

.order-item {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 16px 0;
  border-bottom: 1px solid var(--border);
}

.order-item:last-child { border-bottom: none; }

.order-item-img {
  width: 60px;
  height: 60px;
  object-fit: cover;
  border-radius: var(--radius-sm);
  border: 1px solid var(--border);
  flex-shrink: 0;
}

.order-item-info {
  flex: 1;
  min-width: 0;
}

.order-item-name {
  font-size: 14px;
  font-weight: 500;
  color: var(--ink);
}

.order-item-sku, .order-item-attr {
  font-size: 12px;
  color: var(--ink-muted);
  margin-top: 3px;
}

.order-item-right {
  text-align: right;
  flex-shrink: 0;
}

.order-item-qty {
  font-size: 12px;
  color: var(--ink-muted);
  margin: 4px 0;
}

/* Price breakdown */
.price-breakdown {
  border-top: 1px solid var(--border);
  padding-top: 16px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.price-row {
  display: flex;
  justify-content: space-between;
  font-size: 14px;
  color: var(--ink-soft);
}

.price-row--total {
  align-items: baseline;
  margin-top: 4px;
  padding-top: 12px;
  border-top: 1px solid var(--border);
}

.price-row--total > span:first-child {
  font-size: 15px;
  font-weight: 700;
  color: var(--ink);
}
</style>
