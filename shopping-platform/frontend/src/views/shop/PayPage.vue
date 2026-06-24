<template>
  <div class="pay-page">
    <div class="container-narrow">
      <div class="pay-card" v-if="!loading">
        <div class="pay-header">
          <div class="pay-lock-icon">🔒</div>
          <h1 class="pay-title">安全支付</h1>
          <p class="pay-subtitle">请在 <strong class="pay-countdown">{{ countdown }}</strong> 秒内完成支付</p>
        </div>

        <div class="pay-order-info">
          <div class="pay-info-row">
            <span>订单编号</span>
            <span class="font-mono">{{ orderNo }}</span>
          </div>
          <div class="pay-info-row">
            <span>支付金额</span>
            <span class="price-sale pay-amount">{{ formatPrice(payment?.amount) }}</span>
          </div>
          <div class="pay-info-row" v-if="payment?.subject">
            <span>商品描述</span>
            <span>{{ payment.subject }}</span>
          </div>
        </div>

        <div class="pay-method">
          <div class="pay-method-title">支付方式</div>
          <div class="pay-method-option selected">
            <div class="pay-method-icon">💳</div>
            <div>
              <div class="pay-method-name">模拟支付</div>
              <div class="pay-method-desc">仅用于测试，点击即完成支付</div>
            </div>
            <div class="pay-method-check">✓</div>
          </div>
        </div>

        <button
          class="btn btn-gold btn-lg btn-block"
          @click="handlePay"
          :disabled="paying"
        >
          <span v-if="paying" class="spinner"></span>
          {{ paying ? '支付处理中...' : `确认支付 ${formatPrice(payment?.amount)}` }}
        </button>

        <div class="pay-cancel">
          <button class="btn btn-ghost btn-sm" @click="handleCancel">取消订单</button>
        </div>
      </div>

      <div class="empty-state" v-if="loading">
        <div class="spinner" style="width:32px;height:32px;border-width:3px"></div>
        <div class="empty-state__title">加载支付信息...</div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { paymentApi, orderApi } from '@/api'
import { formatPrice } from '@/utils'

const route = useRoute()
const router = useRouter()
const orderNo = route.params.orderNo

const loading = ref(true)
const paying = ref(false)
const payment = ref(null)
const countdown = ref(600)
let timer = null

async function loadPayment() {
  try {
    // Create payment if not exists
    const createRes = await paymentApi.create({ orderNo })
    payment.value = createRes.data
  } catch (e) {
    // Maybe already created, try to get
    try {
      const res = await paymentApi.getByOrderNo(orderNo)
      payment.value = res.data
    } catch (e2) {
      console.error(e2)
    }
  }
}

async function handlePay() {
  if (!payment.value) return
  paying.value = true
  try {
    await paymentApi.confirmSuccess(payment.value.paymentNo)
    router.push({ name: 'PayResult', query: { orderNo, success: '1' } })
  } catch (e) {
    alert(e.message)
  } finally {
    paying.value = false
  }
}

async function handleCancel() {
  if (!confirm('确定要取消订单吗？')) return
  try {
    await orderApi.cancel(orderNo, { cancelReason: '用户主动取消' })
    router.push({ name: 'UserOrders' })
  } catch (e) {
    alert(e.message)
  }
}

onMounted(async () => {
  loading.value = true
  await loadPayment()
  loading.value = false
  timer = setInterval(() => {
    if (countdown.value <= 0) {
      clearInterval(timer)
      router.push({ name: 'UserOrders' })
    } else {
      countdown.value--
    }
  }, 1000)
})

onUnmounted(() => clearInterval(timer))
</script>

<style scoped>
.pay-page {
  padding: 60px 0 80px;
}

.pay-card {
  max-width: 480px;
  margin: 0 auto;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  padding: 40px;
  box-shadow: var(--shadow-lg);
  display: flex;
  flex-direction: column;
  gap: 28px;
}

.pay-header {
  text-align: center;
}

.pay-lock-icon {
  font-size: 40px;
  margin-bottom: 12px;
}

.pay-title {
  font-size: 24px;
  font-weight: 700;
  margin-bottom: 8px;
}

.pay-subtitle {
  font-size: 14px;
  color: var(--ink-muted);
}

.pay-countdown {
  color: var(--danger);
  font-family: var(--font-mono);
}

.pay-order-info {
  background: var(--surface-dim);
  border-radius: var(--radius-md);
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.pay-info-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 14px;
}

.pay-info-row > span:first-child {
  color: var(--ink-muted);
}

.pay-amount {
  font-size: 24px;
  font-weight: 700;
}

.pay-method {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.pay-method-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--ink-soft);
}

.pay-method-option {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 16px;
  border: 1.5px solid var(--border);
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: all var(--transition);
}

.pay-method-option.selected {
  border-color: var(--gold);
  background: var(--gold-pale);
}

.pay-method-icon {
  font-size: 24px;
}

.pay-method-name {
  font-size: 14px;
  font-weight: 600;
  color: var(--ink);
}

.pay-method-desc {
  font-size: 12px;
  color: var(--ink-muted);
  margin-top: 2px;
}

.pay-method-check {
  margin-left: auto;
  color: var(--gold-dark);
  font-weight: 700;
  font-size: 16px;
}

.pay-cancel {
  text-align: center;
}
</style>
