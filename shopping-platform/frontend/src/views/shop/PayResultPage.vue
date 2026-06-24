<template>
  <div class="pay-result-page">
    <div class="container-narrow">
      <div class="result-card">
        <div v-if="isSuccess" class="result-icon result-icon--success">✓</div>
        <div v-else class="result-icon result-icon--fail">✕</div>
        <h1 class="result-title">{{ isSuccess ? '支付成功！' : '支付失败' }}</h1>
        <p class="result-desc">{{ isSuccess ? '您的订单已成功支付，感谢您的购买' : '支付未完成，请重试或联系客服' }}</p>
        <div class="result-order-no">订单号：<span class="font-mono">{{ orderNo }}</span></div>
        <div class="result-actions">
          <RouterLink :to="`/user/orders/${orderNo}`" class="btn btn-primary btn-lg">查看订单</RouterLink>
          <RouterLink to="/products" class="btn btn-outline btn-lg">继续购物</RouterLink>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'

const route = useRoute()
const isSuccess = computed(() => route.query.success === '1')
const orderNo = computed(() => route.query.orderNo || '')
</script>

<style scoped>
.pay-result-page {
  padding: 80px 0;
}

.result-card {
  max-width: 440px;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 20px;
  text-align: center;
  padding: 48px;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-lg);
}

.result-icon {
  width: 72px;
  height: 72px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 32px;
  font-weight: 700;
}

.result-icon--success {
  background: #f0faf5;
  color: var(--success);
  border: 2px solid rgba(45,158,110,0.25);
}

.result-icon--fail {
  background: #fef2f2;
  color: var(--danger);
  border: 2px solid rgba(224,82,82,0.25);
}

.result-title {
  font-size: 26px;
  font-weight: 700;
}

.result-desc {
  font-size: 14px;
  color: var(--ink-muted);
  line-height: 1.6;
}

.result-order-no {
  font-size: 13px;
  color: var(--ink-muted);
  padding: 10px 16px;
  background: var(--surface-dim);
  border-radius: var(--radius-sm);
}

.result-actions {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
  justify-content: center;
}
</style>
