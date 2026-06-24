<template>
  <div class="checkout-page">
    <div class="container-narrow">
      <h1 class="page-title">确认订单</h1>

      <div class="checkout-layout" v-if="!loading">
        <div class="checkout-left">
          <div class="checkout-section">
            <div class="section-hd">
              <h2 class="section-title-sm">收货地址</h2>
              <button class="btn btn-ghost btn-sm" @click="showAddressModal = true">更换地址</button>
            </div>
            <div v-if="selectedAddress" class="address-card selected-address">
              <div class="address-name">{{ selectedAddress.receiverName }} {{ selectedAddress.receiverMobile }}</div>
              <div class="address-detail">{{ fullAddress(selectedAddress) }}</div>
            </div>
            <div v-else class="address-empty">
              <button class="btn btn-outline btn-sm" @click="showAddressModal = true">+ 添加收货地址</button>
            </div>
          </div>

          <div class="checkout-section">
            <h2 class="section-title-sm">商品清单</h2>
            <div class="checkout-items">
              <div v-for="item in preview?.items || []" :key="item.skuId" class="checkout-item">
                <img :src="item.skuImage || placeholderImg(item.spuName)" class="checkout-item-img" />
                <div class="checkout-item-info">
                  <div class="checkout-item-name">{{ item.spuName }}</div>
                  <div class="checkout-item-attr" v-if="item.skuAttrText">{{ item.skuAttrText }}</div>
                  <div class="checkout-item-sku">{{ item.skuName }}</div>
                  <div v-if="hasItemPromotion(item)" class="checkout-item-promo">
                    <span class="promo-badge">{{ item.promotionActivityName || '活动价' }}</span>
                    <span class="promo-text">已比原价优惠 {{ formatPrice(item.promotionAmount) }}</span>
                  </div>
                </div>
                <div class="checkout-item-right">
                  <div class="price-sale">{{ formatPrice(item.salePrice) }}</div>
                  <div v-if="hasItemPromotion(item)" class="checkout-item-origin">{{ formatPrice(item.originalPrice) }}</div>
                  <div class="checkout-item-qty">x {{ item.quantity }}</div>
                </div>
              </div>
            </div>
          </div>

          <div class="checkout-section">
            <div class="section-hd">
              <h2 class="section-title-sm">优惠券</h2>
              <div v-if="previewRefreshing" class="section-refresh">
                <span class="spinner spinner-inline"></span>
                正在刷新优惠金额...
              </div>
            </div>
            <div v-if="recommendedCoupon" class="coupon-tip">
              系统已为你默认推荐最优优惠券，当前最多可省 {{ formatPrice(recommendedCoupon.couponAmount) }}。
            </div>
            <div v-if="availableCoupons.length" class="coupon-select">
              <label v-for="coupon in availableCoupons" :key="coupon.userCouponId" class="coupon-option">
                <input
                  type="radio"
                  :checked="selectedCouponId === coupon.userCouponId"
                  :disabled="previewRefreshing"
                  @change="applyCoupon(coupon.userCouponId)"
                />
                <div class="coupon-card" :class="{ 'coupon-card--recommended': recommendedCoupon?.userCouponId === coupon.userCouponId }">
                  <div class="coupon-main">
                    <div class="coupon-name">
                      {{ coupon.couponName }}
                      <span v-if="recommendedCoupon?.userCouponId === coupon.userCouponId" class="badge badge-gold">推荐</span>
                    </div>
                    <div class="coupon-condition">满 {{ formatPrice(coupon.thresholdAmount) }} 可用</div>
                  </div>
                  <div class="coupon-meta">
                    <div class="coupon-discount">-{{ formatPrice(coupon.couponAmount) }}</div>
                    <div class="coupon-expire">截至 {{ formatCouponDate(coupon.validTo) }}</div>
                  </div>
                </div>
              </label>
              <label class="coupon-option">
                <input
                  type="radio"
                  :checked="selectedCouponId === null"
                  :disabled="previewRefreshing"
                  @change="applyCoupon(null)"
                />
                <div class="coupon-card coupon-card--none">不使用优惠券</div>
              </label>
            </div>
            <div v-else class="coupon-empty">
              当前订单暂无可用优惠券，商品活动价已自动生效。
            </div>
          </div>

          <div class="checkout-section">
            <h2 class="section-title-sm">备注</h2>
            <textarea
              v-model="remark"
              class="form-textarea"
              placeholder="选填：给商家的留言，最多 500 字"
              maxlength="500"
            ></textarea>
          </div>
        </div>

        <div class="checkout-right">
          <div class="order-summary">
            <div class="summary-title">价格明细</div>
            <div class="summary-note">
              秒杀/活动价先参与结算，再按活动后金额匹配优惠券；单笔订单仅可使用一张优惠券。
            </div>
            <div class="summary-row">
              <span>商品合计</span>
              <span class="price">{{ formatPrice(preview?.totalAmount) }}</span>
            </div>
            <div class="summary-row" v-if="preview?.promotionAmount">
              <span>活动优惠</span>
              <span class="text-success">-{{ formatPrice(preview.promotionAmount) }}</span>
            </div>
            <div class="summary-row" v-if="preview?.couponAmount">
              <span>优惠券</span>
              <span class="text-success">-{{ formatPrice(preview.couponAmount) }}</span>
            </div>
            <div class="summary-row" v-if="selectedCoupon">
              <span>已选优惠券</span>
              <span class="summary-coupon-name">{{ selectedCoupon.couponName }}</span>
            </div>
            <div class="summary-row" v-if="totalSavings > 0">
              <span>累计已省</span>
              <span class="text-success">-{{ formatPrice(totalSavings) }}</span>
            </div>
            <hr class="divider" />
            <div class="summary-payable">
              <span>实付款</span>
              <span class="price-sale payable-amount">{{ formatPrice(preview?.payableAmount) }}</span>
            </div>
            <div v-if="previewRefreshing" class="summary-refreshing">
              <span class="spinner spinner-inline"></span>
              应付金额已根据当前优惠实时刷新
            </div>
            <button
              class="btn btn-gold btn-lg btn-block"
              :disabled="!selectedAddress || submitting || previewRefreshing"
              @click="handleSubmit"
            >
              <span v-if="submitting" class="spinner"></span>
              {{ submitting ? '提交中...' : '提交订单' }}
            </button>
            <div class="summary-tip">提交订单后请及时完成支付</div>
          </div>
        </div>
      </div>

      <div class="empty-state" v-if="loading">
        <div class="spinner" style="width: 32px; height: 32px; border-width: 3px"></div>
        <div class="empty-state__title">加载订单信息...</div>
      </div>
    </div>

    <Teleport to="body">
      <Transition name="fade">
        <div class="modal-backdrop" v-if="showAddressModal" @click.self="showAddressModal = false">
          <div class="modal">
            <div class="modal-hd">
              <h3 class="modal-title">选择收货地址</h3>
              <button class="btn btn-ghost btn-icon" @click="showAddressModal = false">x</button>
            </div>
            <div class="modal-body">
              <div
                v-for="addr in addresses"
                :key="addr.id"
                class="address-option"
                :class="{ selected: selectedAddress?.id === addr.id }"
                @click="selectAddress(addr)"
              >
                <div class="address-name">
                  {{ addr.receiverName }} {{ addr.receiverMobile }}
                  <span v-if="addr.defaultAddress" class="badge badge-gold">默认</span>
                </div>
                <div class="address-detail">{{ fullAddress(addr) }}</div>
              </div>
              <div class="empty-state" v-if="!addresses.length" style="padding: 32px">
                <div class="empty-state__title">暂无收货地址</div>
                <RouterLink to="/user/addresses" class="btn btn-outline btn-sm">去添加地址</RouterLink>
              </div>
            </div>
          </div>
        </div>
      </Transition>
    </Teleport>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import dayjs from 'dayjs'
import { useRoute, useRouter } from 'vue-router'
import { orderApi, userApi } from '@/api'
import { formatPrice, placeholderImg } from '@/utils'

const route = useRoute()
const router = useRouter()

const loading = ref(true)
const previewRefreshing = ref(false)
const submitting = ref(false)
const preview = ref(null)
const addresses = ref([])
const selectedAddress = ref(null)
const selectedCouponId = ref(null)
const couponSelectionInitialized = ref(false)
const remark = ref('')
const showAddressModal = ref(false)

const availableCoupons = computed(() => {
  const list = preview.value?.availableCoupons || []
  return [...list].sort(compareCoupons)
})

const recommendedCoupon = computed(() => availableCoupons.value[0] || null)

const selectedCoupon = computed(() => {
  if (preview.value?.selectedCoupon) {
    return preview.value.selectedCoupon
  }
  return availableCoupons.value.find((coupon) => coupon.userCouponId === selectedCouponId.value) || null
})

const totalSavings = computed(() => {
  const promotion = Number(preview.value?.promotionAmount || 0)
  const coupon = Number(preview.value?.couponAmount || 0)
  return promotion + coupon
})

function fullAddress(addr) {
  return [addr.provinceName, addr.cityName, addr.districtName, addr.detailAddress].filter(Boolean).join(' ')
}

function buildPreviewPayload() {
  const mode = route.query.mode
  if (mode === 'direct') {
    return {
      items: [
        {
          skuId: Number(route.query.skuId),
          quantity: Number(route.query.quantity) || 1
        }
      ]
    }
  }
  return {
    cartItemIds: (route.query.cartItemIds || '')
      .split(',')
      .map(Number)
      .filter(Boolean)
  }
}

function compareCoupons(a, b) {
  const amountDiff = Number(b.couponAmount || 0) - Number(a.couponAmount || 0)
  if (amountDiff !== 0) {
    return amountDiff
  }
  const thresholdDiff = Number(a.thresholdAmount || 0) - Number(b.thresholdAmount || 0)
  if (thresholdDiff !== 0) {
    return thresholdDiff
  }
  return dayjs(a.validTo).valueOf() - dayjs(b.validTo).valueOf()
}

function hasItemPromotion(item) {
  return Number(item?.promotionAmount || 0) > 0 && Number(item?.originalPrice || 0) > Number(item?.salePrice || 0)
}

function formatCouponDate(value) {
  return value ? dayjs(value).format('MM-DD HH:mm') : '--'
}

async function loadPreview(options = {}) {
  const { initializeCoupon = false } = options
  if (!loading.value) {
    previewRefreshing.value = true
  }

  const payload = buildPreviewPayload()
  if (selectedCouponId.value !== null && selectedCouponId.value !== undefined) {
    payload.userCouponId = selectedCouponId.value
  }

  try {
    const res = await orderApi.preview(payload)
    preview.value = res.data

    if (selectedCouponId.value !== null && !preview.value?.selectedCoupon) {
      const stillAvailable = (preview.value?.availableCoupons || []).some(
        (coupon) => coupon.userCouponId === selectedCouponId.value
      )
      if (!stillAvailable) {
        selectedCouponId.value = null
      }
    }

    if (initializeCoupon && !couponSelectionInitialized.value) {
      couponSelectionInitialized.value = true
      if (selectedCouponId.value === null && recommendedCoupon.value) {
        selectedCouponId.value = recommendedCoupon.value.userCouponId
        await loadPreview()
      }
    }
  } catch (e) {
    console.error(e)
    if (!preview.value) {
      alert(e.message)
    }
  } finally {
    previewRefreshing.value = false
  }
}

async function applyCoupon(couponId) {
  selectedCouponId.value = couponId
  couponSelectionInitialized.value = true
  await loadPreview()
}

function selectAddress(addr) {
  selectedAddress.value = addr
  showAddressModal.value = false
}

async function handleSubmit() {
  if (!selectedAddress.value) {
    return
  }
  submitting.value = true
  try {
    const payload = {
      addressId: selectedAddress.value.id,
      remark: remark.value || undefined,
      ...buildPreviewPayload()
    }
    if (selectedCouponId.value !== null && selectedCouponId.value !== undefined) {
      payload.userCouponId = selectedCouponId.value
    }
    const res = await orderApi.submit(payload)
    router.push({ name: 'Pay', params: { orderNo: res.data.orderNo } })
  } catch (e) {
    alert(e.message)
  } finally {
    submitting.value = false
  }
}

onMounted(async () => {
  loading.value = true
  try {
    const [_, addrRes] = await Promise.all([
      loadPreview({ initializeCoupon: true }),
      userApi.getAddresses()
    ])
    addresses.value = addrRes.data || []
    selectedAddress.value = addresses.value.find((addr) => addr.defaultAddress) || addresses.value[0] || null
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.checkout-page {
  padding: 40px 0 80px;
}

.page-title {
  font-size: 28px;
  font-weight: 700;
  margin-bottom: 32px;
}

.checkout-layout {
  display: grid;
  grid-template-columns: 1fr 320px;
  gap: 32px;
  align-items: start;
}

@media (max-width: 900px) {
  .checkout-layout {
    grid-template-columns: 1fr;
  }
}

.checkout-section {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  padding: 24px;
  margin-bottom: 16px;
}

.section-hd {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
}

.section-title-sm {
  font-size: 16px;
  font-weight: 700;
  font-family: var(--font-body);
  color: var(--ink);
}

.section-refresh {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  color: var(--ink-muted);
}

.address-card {
  padding: 16px;
  border: 1.5px solid var(--border);
  border-radius: var(--radius-sm);
}

.selected-address {
  border-color: var(--ink);
  background: var(--surface-dim);
}

.address-name {
  font-size: 15px;
  font-weight: 600;
  color: var(--ink);
  margin-bottom: 6px;
  display: flex;
  align-items: center;
  gap: 8px;
}

.address-detail {
  font-size: 14px;
  color: var(--ink-muted);
  line-height: 1.5;
}

.address-empty {
  text-align: center;
  padding: 16px;
}

.checkout-items {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.checkout-item {
  display: flex;
  align-items: center;
  gap: 14px;
}

.checkout-item-img {
  width: 64px;
  height: 64px;
  border-radius: var(--radius-sm);
  object-fit: cover;
  border: 1px solid var(--border);
  flex-shrink: 0;
}

.checkout-item-info {
  flex: 1;
  min-width: 0;
}

.checkout-item-name {
  font-size: 14px;
  font-weight: 500;
  color: var(--ink);
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.checkout-item-attr,
.checkout-item-sku {
  font-size: 12px;
  color: var(--ink-muted);
  margin-top: 2px;
}

.checkout-item-promo {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 8px;
  flex-wrap: wrap;
}

.promo-badge {
  display: inline-flex;
  align-items: center;
  height: 22px;
  padding: 0 8px;
  border-radius: 999px;
  background: var(--gold-pale);
  color: var(--gold-deep);
  font-size: 12px;
  font-weight: 600;
}

.promo-text {
  font-size: 12px;
  color: var(--danger);
}

.checkout-item-right {
  text-align: right;
  flex-shrink: 0;
}

.checkout-item-origin {
  margin-top: 4px;
  font-size: 12px;
  color: var(--ink-faint);
  text-decoration: line-through;
}

.checkout-item-qty {
  font-size: 12px;
  color: var(--ink-muted);
  margin-top: 4px;
}

.coupon-tip,
.coupon-empty {
  padding: 12px 14px;
  border-radius: var(--radius-sm);
  background: var(--surface-dim);
  color: var(--ink-muted);
  font-size: 13px;
  line-height: 1.5;
}

.coupon-select {
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin-top: 12px;
}

.coupon-option {
  display: flex;
  align-items: center;
  gap: 12px;
  cursor: pointer;
}

.coupon-option input {
  cursor: pointer;
  accent-color: var(--ink);
}

.coupon-card {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 14px 16px;
  border: 1.5px solid var(--border);
  border-radius: var(--radius-sm);
  transition: border-color var(--transition), background-color var(--transition);
}

.coupon-card--recommended {
  box-shadow: 0 0 0 1px rgba(196, 151, 31, 0.15);
}

.coupon-option input:checked + .coupon-card {
  border-color: var(--gold);
  background: var(--gold-pale);
}

.coupon-card--none {
  font-size: 14px;
  color: var(--ink-muted);
}

.coupon-main {
  min-width: 0;
}

.coupon-name {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  font-weight: 600;
  color: var(--ink-soft);
}

.coupon-condition,
.coupon-expire {
  font-size: 12px;
  color: var(--ink-faint);
  margin-top: 4px;
}

.coupon-meta {
  text-align: right;
  flex-shrink: 0;
}

.coupon-discount {
  font-size: 18px;
  font-weight: 700;
  color: var(--danger);
  font-family: var(--font-mono);
}

.order-summary {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  padding: 24px;
  display: flex;
  flex-direction: column;
  gap: 14px;
  position: sticky;
  top: 88px;
}

.summary-title {
  font-size: 16px;
  font-weight: 700;
  color: var(--ink);
}

.summary-note {
  padding: 12px 14px;
  border-radius: var(--radius-sm);
  background: linear-gradient(135deg, rgba(196, 151, 31, 0.1), rgba(196, 151, 31, 0.02));
  font-size: 12px;
  line-height: 1.6;
  color: var(--ink-muted);
}

.summary-row {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  font-size: 14px;
  color: var(--ink-soft);
}

.summary-coupon-name {
  max-width: 150px;
  text-align: right;
  color: var(--ink);
  font-weight: 500;
}

.summary-payable {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
}

.summary-payable > span:first-child {
  font-size: 15px;
  font-weight: 600;
  color: var(--ink);
}

.payable-amount {
  font-size: 28px;
  font-weight: 700;
}

.summary-refreshing {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  color: var(--ink-muted);
}

.summary-tip {
  font-size: 12px;
  color: var(--ink-faint);
  text-align: center;
  margin-top: -4px;
}

.spinner-inline {
  width: 14px;
  height: 14px;
  border-width: 2px;
}

.modal-backdrop {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.45);
  backdrop-filter: blur(4px);
  z-index: 500;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
}

.modal {
  background: var(--surface);
  border-radius: var(--radius-lg);
  width: 100%;
  max-width: 560px;
  max-height: 80vh;
  display: flex;
  flex-direction: column;
  box-shadow: var(--shadow-lg);
}

.modal-hd {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 20px 24px;
  border-bottom: 1px solid var(--border);
}

.modal-title {
  font-size: 17px;
  font-weight: 700;
  font-family: var(--font-body);
}

.modal-body {
  overflow-y: auto;
  padding: 16px 24px 24px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.address-option {
  padding: 14px 16px;
  border: 1.5px solid var(--border);
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition: all var(--transition);
}

.address-option:hover {
  border-color: var(--ink-faint);
}

.address-option.selected {
  border-color: var(--ink);
  background: var(--surface-dim);
}
</style>
