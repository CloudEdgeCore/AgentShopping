<template>
  <div class="coupon-page">
    <div class="uc-section-title-row">
      <div class="uc-section-title">我的优惠券</div>
      <button class="btn btn-outline btn-sm" @click="showClaimModal = true">领取优惠券</button>
    </div>

    <!-- Status Tabs -->
    <div class="coupon-tabs">
      <button
        v-for="tab in tabs"
        :key="tab.value"
        class="coupon-tab"
        :class="{ active: activeTab === tab.value }"
        @click="activeTab = tab.value"
      >
        {{ tab.label }}
        <span v-if="tab.count" class="tab-count">{{ tab.count }}</span>
      </button>
    </div>

    <!-- Loading -->
    <div v-if="loading" class="coupon-grid">
      <div v-for="i in 4" :key="i" class="coupon-skeleton">
        <div class="skeleton-shimmer" style="height:100%;border-radius:inherit"></div>
      </div>
    </div>

    <!-- Coupon List -->
    <div v-else-if="filteredCoupons.length" class="coupon-grid">
      <div
        v-for="coupon in filteredCoupons"
        :key="coupon.id"
        class="coupon-card"
        :class="coupon.useStatus === 1 ? 'coupon-used' : coupon.useStatus === 2 ? 'coupon-expired' : ''"
      >
        <div class="coupon-left">
          <div v-if="coupon.couponType === 10" class="coupon-amount">
            <span class="amount-val">
              <span class="amount-unit">¥</span>{{ formatAmount(coupon.discountAmount) }}
            </span>
          </div>
          <div v-else class="coupon-amount">
            {{ formatDiscount(coupon.discountRate) }}<span class="amount-unit">折</span>
          </div>
          <div class="coupon-condition">
            {{ coupon.minOrderAmount > 0 ? `满¥${formatAmount(coupon.minOrderAmount)}可用` : '无门槛' }}
          </div>
        </div>
        <div class="coupon-divider">
          <div class="notch notch-top"></div>
          <div class="dash-line"></div>
          <div class="notch notch-bottom"></div>
        </div>
        <div class="coupon-right">
          <div class="coupon-name">{{ coupon.couponName }}</div>
          <div class="coupon-scope">
            {{ coupon.scopeType === 10 ? '全场通用' : coupon.scopeType === 20 ? '指定分类' : '指定商品' }}
          </div>
          <div class="coupon-expire">
            有效至 {{ formatExpire(coupon.endTime) }}
          </div>
          <div class="coupon-status-badge" v-if="coupon.useStatus !== 0">
            <span v-if="coupon.useStatus === 1" class="badge badge-muted">已使用</span>
            <span v-else class="badge badge-muted">已过期</span>
          </div>
          <RouterLink v-else to="/products" class="btn btn-gold btn-xs coupon-use-btn">立即使用</RouterLink>
        </div>
      </div>
    </div>

    <!-- Empty -->
    <div class="empty-state" v-else>
      <div class="empty-state__icon">🎟</div>
      <div class="empty-state__title">{{ emptyText }}</div>
      <button class="btn btn-outline" @click="showClaimModal = true">去领取优惠券</button>
    </div>

    <!-- Claim Modal -->
    <Teleport to="body">
      <Transition name="fade">
        <div class="modal-backdrop" v-if="showClaimModal" @click.self="showClaimModal = false">
          <div class="modal claim-modal">
            <div class="modal-hd">
              <h3 class="modal-title">领取优惠券</h3>
              <button class="btn btn-ghost btn-icon" @click="showClaimModal = false">✕</button>
            </div>
            <div class="modal-body">
              <div v-if="claimLoading" class="empty-state" style="padding:40px 0">
                <div class="spinner" style="width:24px;height:24px;border-width:2px"></div>
              </div>
              <div v-else-if="availableCoupons.length" class="claim-list">
                <div v-for="c in availableCoupons" :key="c.id" class="claim-card">
                  <div class="claim-card-left">
                    <div v-if="c.couponType === 10" class="claim-amount">
                      <span class="claim-unit">¥</span>{{ formatAmount(c.discountAmount) }}
                    </div>
                    <div v-else class="claim-amount">
                      {{ formatDiscount(c.discountRate) }}<span class="claim-unit">折</span>
                    </div>
                    <div class="claim-condition">
                      {{ c.minOrderAmount > 0 ? `满¥${formatAmount(c.minOrderAmount)}` : '无门槛' }}
                    </div>
                  </div>
                  <div class="claim-card-right">
                    <div class="claim-name">{{ c.couponName }}</div>
                    <div class="claim-expire">{{ formatExpire(c.endTime) }} 到期</div>
                    <button
                      class="btn btn-gold btn-xs"
                      :disabled="claimedIds.has(c.id) || c.remainCount <= 0"
                      @click="claimCoupon(c)"
                    >
                      <span v-if="claimedIds.has(c.id)">已领取</span>
                      <span v-else-if="c.remainCount <= 0">已抢完</span>
                      <span v-else>立即领取</span>
                    </button>
                  </div>
                </div>
              </div>
              <div v-else class="empty-state" style="padding:40px 0">
                <div class="empty-state__icon">🎫</div>
                <div class="empty-state__title">暂无可领取的优惠券</div>
              </div>
            </div>
          </div>
        </div>
      </Transition>
    </Teleport>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { marketingApi } from '@/api'
import { formatDate } from '@/utils'
import dayjs from 'dayjs'

const coupons = ref([])
const availableCoupons = ref([])
const loading = ref(true)
const claimLoading = ref(false)
const showClaimModal = ref(false)
const activeTab = ref(0)
const claimedIds = ref(new Set())

const tabs = computed(() => [
  { label: '未使用', value: 0, count: coupons.value.filter(c => c.useStatus === 0).length || null },
  { label: '已使用', value: 1, count: null },
  { label: '已过期', value: 2, count: null }
])

const filteredCoupons = computed(() => coupons.value.filter(c => c.useStatus === activeTab.value))

const emptyText = computed(() => {
  if (activeTab.value === 0) return '暂无可用优惠券'
  if (activeTab.value === 1) return '暂无已使用优惠券'
  return '暂无已过期优惠券'
})

function formatAmount(val) {
  return Number(val || 0).toFixed(2).replace(/\.00$/, '')
}

function formatDiscount(val) {
  return Number(val || 0).toFixed(1).replace(/\.0$/, '')
}

function formatExpire(dateStr) {
  if (!dateStr) return '长期有效'
  return dayjs(dateStr).format('YYYY.MM.DD')
}

// Java 平台用户券字段 → 组件字段
function mapUserCoupon(c) {
  return {
    ...c,
    couponType: c.couponType || 10,
    // 10=未用, 15=锁定(视为未用), 20=已用, 30=过期
    useStatus: c.status === 20 ? 1 : c.status === 30 ? 2 : 0,
    minOrderAmount: c.thresholdAmount || 0,
    discountRate: c.discountRate || 10,
    endTime: c.validTo || '',
    scopeType: c.scopeType || 10
  }
}

// Java 平台可领券模板字段 → 组件字段
function mapAvailableCoupon(c) {
  return {
    ...c,
    couponType: c.couponType || 10,
    minOrderAmount: c.thresholdAmount || 0,
    discountRate: c.discountRate || 10,
    endTime: c.receiveEndTime || c.validTo || '',
    remainCount: c.remainCount ?? 0
  }
}

async function loadCoupons() {
  loading.value = true
  try {
    const res = await marketingApi.getMyCoupons({ current: 1, size: 100 })
    coupons.value = (res.data?.records || []).map(mapUserCoupon)
  } catch (e) {
    coupons.value = []
  } finally {
    loading.value = false
  }
}

async function loadAvailable() {
  claimLoading.value = true
  try {
    const res = await marketingApi.getAvailableCoupons()
    const list = (res.data || []).map(mapAvailableCoupon)
    availableCoupons.value = list
    claimedIds.value = new Set(list.filter(c => (c.userClaimedCount || 0) > 0).map(c => c.id))
  } catch (e) {
    availableCoupons.value = []
  } finally {
    claimLoading.value = false
  }
}

async function claimCoupon(c) {
  try {
    await marketingApi.claimCoupon(c.id)
    claimedIds.value = new Set([...claimedIds.value, c.id])
    c.remainCount = Math.max(0, (c.remainCount || 0) - 1)
    c.userClaimedCount = (c.userClaimedCount || 0) + 1
    await loadCoupons()
  } catch (e) {
    alert(e.message || '领取失败')
  }
}

watch(showClaimModal, (val) => {
  if (val && !availableCoupons.value.length) loadAvailable()
})

onMounted(loadCoupons)
</script>

<style scoped>
.coupon-page { display: flex; flex-direction: column; gap: 16px; }
.uc-section-title-row { display: flex; justify-content: space-between; align-items: center; }
.uc-section-title { font-size: 20px; font-weight: 700; color: var(--ink); }

/* Tabs */
.coupon-tabs { display: flex; gap: 4px; border-bottom: 1px solid var(--border); }
.coupon-tab { padding: 10px 20px; font-size: 14px; font-weight: 500; color: var(--ink-muted); background: none; border: none; border-bottom: 2px solid transparent; cursor: pointer; transition: all var(--transition); display: flex; align-items: center; gap: 6px; margin-bottom: -1px; }
.coupon-tab:hover { color: var(--ink); }
.coupon-tab.active { color: var(--ink); border-bottom-color: var(--gold); }
.tab-count { background: var(--gold); color: var(--ink); font-size: 11px; font-weight: 700; min-width: 18px; height: 18px; border-radius: 9px; display: inline-flex; align-items: center; justify-content: center; padding: 0 5px; }

/* Coupon Grid */
.coupon-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 16px; }

/* Coupon Card */
.coupon-card { display: flex; border-radius: var(--radius-md); overflow: visible; filter: drop-shadow(0 2px 8px rgba(0,0,0,0.08)); transition: filter var(--transition), transform var(--transition); background: transparent; }
.coupon-card:hover { filter: drop-shadow(0 4px 16px rgba(0,0,0,0.14)); transform: translateY(-2px); }
.coupon-used, .coupon-expired { opacity: 0.55; filter: grayscale(0.6) drop-shadow(0 2px 6px rgba(0,0,0,0.06)); }
.coupon-used:hover, .coupon-expired:hover { transform: none; }

.coupon-left { background: var(--ink); color: var(--surface); padding: 20px 16px; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 6px; min-width: 110px; border-radius: var(--radius-md) 0 0 var(--radius-md); }
.coupon-amount { display: flex; align-items: baseline; gap: 1px; }
.amount-val { font-family: var(--font-display); font-size: 32px; font-weight: 700; color: var(--gold); line-height: 1; }
.amount-unit { font-size: 14px; font-weight: 500; color: var(--gold); }
.coupon-condition { font-size: 11px; color: rgba(255,255,255,0.5); text-align: center; }

/* Divider with notch */
.coupon-divider { position: relative; width: 16px; background: var(--surface); display: flex; flex-direction: column; align-items: center; justify-content: center; flex-shrink: 0; }
.coupon-divider::before, .coupon-divider::after { content: ''; position: absolute; left: 0; width: 16px; height: 16px; background: var(--surface-dim); z-index: 1; }
.coupon-divider::before { top: -8px; border-radius: 0 0 8px 8px; }
.coupon-divider::after { bottom: -8px; border-radius: 8px 8px 0 0; }
.notch { width: 14px; height: 14px; background: var(--surface-dim); border-radius: 50%; position: absolute; left: 1px; z-index: 2; }
.notch-top { top: -7px; }
.notch-bottom { bottom: -7px; }
.dash-line { width: 1px; height: 100%; background: repeating-linear-gradient(to bottom, var(--border) 0, var(--border) 4px, transparent 4px, transparent 8px); }

.coupon-right { flex: 1; background: var(--surface); padding: 16px 18px; border-radius: 0 var(--radius-md) var(--radius-md) 0; border: 1px solid var(--border); border-left: none; display: flex; flex-direction: column; gap: 5px; justify-content: center; }
.coupon-name { font-size: 14px; font-weight: 600; color: var(--ink); }
.coupon-scope { font-size: 12px; color: var(--ink-muted); }
.coupon-expire { font-size: 11px; color: var(--ink-faint); margin-top: 4px; }
.coupon-use-btn { align-self: flex-start; margin-top: 6px; padding: 4px 12px; }
.coupon-status-badge { margin-top: 6px; }

/* Skeleton */
.coupon-skeleton { height: 120px; border-radius: var(--radius-md); background: var(--surface-dim); overflow: hidden; position: relative; }

/* Claim Modal */
.claim-modal { max-width: 520px; }
.claim-list { display: flex; flex-direction: column; gap: 12px; }
.claim-card { display: flex; border: 1px solid var(--border); border-radius: var(--radius-md); overflow: hidden; }
.claim-card-left { background: var(--ink); color: var(--surface); padding: 16px; min-width: 100px; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 4px; }
.claim-amount { font-family: var(--font-display); font-size: 26px; font-weight: 700; color: var(--gold); line-height: 1; display: flex; align-items: baseline; gap: 1px; }
.claim-unit { font-size: 13px; }
.claim-condition { font-size: 10px; color: rgba(255,255,255,0.5); }
.claim-card-right { flex: 1; padding: 14px 16px; display: flex; flex-direction: column; gap: 4px; justify-content: center; }
.claim-name { font-size: 14px; font-weight: 600; color: var(--ink); }
.claim-expire { font-size: 12px; color: var(--ink-muted); }
.claim-card-right .btn { align-self: flex-start; margin-top: 8px; padding: 4px 14px; }

/* Modal shared */
.modal-backdrop { position: fixed; inset: 0; background: rgba(0,0,0,0.45); backdrop-filter: blur(4px); z-index: 500; display: flex; align-items: center; justify-content: center; padding: 24px; }
.modal { background: var(--surface); border-radius: var(--radius-lg); width: 100%; max-width: 540px; max-height: 90vh; display: flex; flex-direction: column; box-shadow: var(--shadow-lg); }
.modal-hd { display: flex; align-items: center; justify-content: space-between; padding: 20px 24px; border-bottom: 1px solid var(--border); }
.modal-title { font-size: 17px; font-weight: 700; }
.modal-body { overflow-y: auto; padding: 20px 24px; display: flex; flex-direction: column; gap: 16px; }

/* btn-xs */
.btn-xs { padding: 4px 12px; font-size: 12px; }
</style>
