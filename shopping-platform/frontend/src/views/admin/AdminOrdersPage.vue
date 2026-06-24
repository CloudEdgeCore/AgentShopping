<template>
  <div class="admin-page">
    <div class="admin-page-header">
      <div>
        <h2 class="admin-page-title">订单管理</h2>
        <p class="admin-page-sub">查看全量订单，支持按状态筛选与后台取消待支付订单</p>
      </div>
    </div>

    <div class="filter-bar">
      <select v-model="statusFilter" class="form-select filter-select" @change="doSearch">
        <option :value="null">全部状态</option>
        <option :value="10">待支付</option>
        <option :value="20">已支付</option>
        <option :value="30">已取消</option>
      </select>
      <button class="btn btn-outline" @click="doSearch">查询</button>
    </div>

    <div class="admin-table-wrap">
      <div v-if="loading" class="admin-loading">
        <div class="spinner" style="width:28px;height:28px;border-width:2px"></div>
      </div>
      <table v-else class="admin-table">
        <thead>
          <tr>
            <th style="width:210px">订单号</th>
            <th style="width:90px">状态</th>
            <th style="width:80px">件数</th>
            <th style="width:110px">应付金额</th>
            <th>首件商品</th>
            <th style="width:150px">下单时间</th>
            <th style="width:160px">操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="!orders.length">
            <td colspan="7" class="empty-cell">暂无订单数据</td>
          </tr>
          <tr v-for="row in orders" :key="row.orderNo">
            <td class="font-mono text-muted">{{ row.orderNo }}</td>
            <td>
              <span class="badge" :class="statusClass(row.status)">
                {{ statusLabel(row.status) }}
              </span>
            </td>
            <td class="font-mono">{{ row.totalQuantity || 0 }}</td>
            <td class="font-mono">¥{{ fmtMoney(row.payableAmount) }}</td>
            <td class="ellipsis" :title="row.firstSkuName || '-'">{{ row.firstSkuName || '-' }}</td>
            <td class="text-muted">{{ fmtDate(row.createTime) }}</td>
            <td>
              <div class="action-btns">
                <button class="btn btn-ghost btn-xs" @click="openDetail(row.orderNo)">详情</button>
                <button
                  v-if="row.status === 10"
                  class="btn btn-ghost btn-xs text-danger"
                  @click="cancelOrder(row.orderNo)"
                >
                  取消
                </button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <div class="pagination" v-if="total > pageSize">
      <button class="btn btn-ghost btn-sm" :disabled="page <= 1" @click="page--; load()">上一页</button>
      <span class="page-info">{{ page }} / {{ totalPages }}</span>
      <button class="btn btn-ghost btn-sm" :disabled="page >= totalPages" @click="page++; load()">下一页</button>
    </div>

    <Teleport to="body">
      <Transition name="fade">
        <div class="modal-backdrop" v-if="showDetail" @click.self="showDetail = false">
          <div class="modal">
            <div class="modal-hd">
              <h3 class="modal-title">订单详情</h3>
              <button class="btn btn-ghost btn-icon" @click="showDetail = false">×</button>
            </div>
            <div class="modal-body" v-if="detail">
              <div class="detail-grid">
                <div><span class="label">订单号：</span><span class="font-mono">{{ detail.orderNo }}</span></div>
                <div><span class="label">状态：</span>{{ statusLabel(detail.status) }}</div>
                <div><span class="label">总件数：</span>{{ detail.totalQuantity }}</div>
                <div><span class="label">应付金额：</span>¥{{ fmtMoney(detail.payableAmount) }}</div>
                <div><span class="label">优惠金额：</span>¥{{ fmtMoney(detail.promotionAmount) }}</div>
                <div><span class="label">优惠券抵扣：</span>¥{{ fmtMoney(detail.couponAmount) }}</div>
                <div><span class="label">下单时间：</span>{{ fmtDate(detail.createTime) }}</div>
                <div><span class="label">支付时间：</span>{{ fmtDate(detail.payTime) }}</div>
                <div><span class="label">取消时间：</span>{{ fmtDate(detail.cancelTime) }}</div>
                <div><span class="label">取消原因：</span>{{ detail.cancelReason || '-' }}</div>
              </div>

              <div class="section-title">收货信息</div>
              <div class="address-block">
                {{ detail.receiverName || '-' }} / {{ detail.receiverMobile || '-' }}
                <br />
                {{ detail.provinceName || '' }}{{ detail.cityName || '' }}{{ detail.districtName || '' }}{{ detail.detailAddress || '' }}
                <span v-if="detail.postalCode">（{{ detail.postalCode }}）</span>
              </div>

              <div class="section-title">商品明细</div>
              <table class="detail-table">
                <thead>
                  <tr>
                    <th>SKU</th>
                    <th>商品</th>
                    <th>单价</th>
                    <th>数量</th>
                    <th>小计</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-if="!detail.items?.length">
                    <td colspan="5" class="empty-cell">无商品明细</td>
                  </tr>
                  <tr v-for="item in detail.items || []" :key="`${item.skuId}-${item.skuName}`">
                    <td class="font-mono">{{ item.skuId }}</td>
                    <td>{{ item.spuName }} / {{ item.skuName }}</td>
                    <td class="font-mono">¥{{ fmtMoney(item.salePrice) }}</td>
                    <td class="font-mono">{{ item.quantity }}</td>
                    <td class="font-mono">¥{{ fmtMoney(item.totalAmount) }}</td>
                  </tr>
                </tbody>
              </table>
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
import { adminOrderApi } from '@/api'

const orders = ref([])
const loading = ref(true)
const page = ref(1)
const pageSize = 15
const total = ref(0)
const totalPages = computed(() => Math.ceil(total.value / pageSize))
const statusFilter = ref(null)

const showDetail = ref(false)
const detail = ref(null)

function statusLabel(status) {
  if (status === 10) return '待支付'
  if (status === 20) return '已支付'
  if (status === 30) return '已取消'
  return '-'
}

function statusClass(status) {
  if (status === 10) return 'badge-gold'
  if (status === 20) return 'badge-success'
  return 'badge-muted'
}

function fmtMoney(val) {
  const num = Number(val)
  return Number.isFinite(num) ? num.toFixed(2) : '0.00'
}

function fmtDate(val) {
  return val ? dayjs(val).format('YYYY-MM-DD HH:mm:ss') : '-'
}

function doSearch() {
  page.value = 1
  load()
}

async function load() {
  loading.value = true
  try {
    const params = { current: page.value, size: pageSize }
    if (statusFilter.value !== null) {
      params.status = statusFilter.value
    }
    const res = await adminOrderApi.getPage(params)
    const data = res.data || {}
    orders.value = data.records || []
    total.value = data.total || 0
  } finally {
    loading.value = false
  }
}

async function openDetail(orderNo) {
  try {
    const res = await adminOrderApi.getDetail(orderNo)
    detail.value = res.data || null
    showDetail.value = true
  } catch (e) {
    alert(e.message)
  }
}

async function cancelOrder(orderNo) {
  const cancelReason = prompt('请输入取消原因（可选）') || ''
  try {
    await adminOrderApi.cancel(orderNo, { cancelReason })
    await load()
    if (showDetail.value && detail.value?.orderNo === orderNo) {
      await openDetail(orderNo)
    }
  } catch (e) {
    alert(e.message)
  }
}

onMounted(load)
</script>

<style scoped>
.admin-page { display: flex; flex-direction: column; gap: 20px; }
.admin-page-header { display: flex; justify-content: space-between; align-items: flex-start; }
.admin-page-title { font-size: 22px; font-weight: 700; color: var(--ink); }
.admin-page-sub { font-size: 13px; color: var(--ink-muted); margin-top: 4px; }
.filter-bar { display: flex; gap: 10px; align-items: center; }
.filter-select { min-width: 120px; }
.admin-table-wrap { border: 1px solid var(--border); border-radius: var(--radius-md); overflow: hidden; min-height: 100px; position: relative; }
.admin-loading { display: flex; align-items: center; justify-content: center; padding: 60px; }
.admin-table { width: 100%; border-collapse: collapse; }
.admin-table th { padding: 12px 14px; background: var(--surface-dim); font-size: 12px; font-weight: 600; color: var(--ink-muted); text-align: left; border-bottom: 1px solid var(--border); white-space: nowrap; }
.admin-table td { padding: 12px 14px; border-bottom: 1px solid var(--border); font-size: 13px; color: var(--ink-soft); vertical-align: middle; }
.admin-table tr:last-child td { border-bottom: none; }
.admin-table tr:hover td { background: var(--surface-dim); }
.empty-cell { text-align: center; color: var(--ink-faint); padding: 48px !important; font-size: 13px; }
.font-mono { font-family: var(--font-mono); }
.text-muted { color: var(--ink-muted); }
.text-danger { color: var(--danger) !important; }
.ellipsis { max-width: 220px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.action-btns { display: flex; gap: 4px; }
.btn-xs { padding: 4px 10px; font-size: 12px; }
.pagination { display: flex; align-items: center; gap: 12px; justify-content: center; }
.page-info { font-size: 13px; color: var(--ink-muted); min-width: 60px; text-align: center; }
.modal-backdrop { position: fixed; inset: 0; background: rgba(0,0,0,0.45); backdrop-filter: blur(4px); z-index: 500; display: flex; align-items: center; justify-content: center; padding: 24px; }
.modal { background: var(--surface); border-radius: var(--radius-lg); width: 100%; max-width: 960px; max-height: 90vh; display: flex; flex-direction: column; box-shadow: var(--shadow-lg); }
.modal-hd { display: flex; align-items: center; justify-content: space-between; padding: 20px 24px; border-bottom: 1px solid var(--border); }
.modal-title { font-size: 17px; font-weight: 700; }
.modal-body { overflow-y: auto; padding: 20px 24px; display: flex; flex-direction: column; gap: 16px; }
.detail-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 8px 24px; font-size: 13px; }
.label { color: var(--ink-muted); }
.section-title { margin-top: 8px; font-size: 14px; font-weight: 700; color: var(--ink); }
.address-block { font-size: 13px; color: var(--ink-soft); line-height: 1.6; }
.detail-table { width: 100%; border-collapse: collapse; }
.detail-table th { padding: 10px 12px; background: var(--surface-dim); border-bottom: 1px solid var(--border); text-align: left; font-size: 12px; color: var(--ink-muted); }
.detail-table td { padding: 10px 12px; border-bottom: 1px solid var(--border); font-size: 13px; color: var(--ink-soft); }
</style>
