import dayjs from 'dayjs'

// Format price: cents or float -> display string
export function formatPrice(val) {
  if (val == null) return '—'
  return '¥' + Number(val).toFixed(2)
}

// Format datetime
export function formatDate(val, fmt = 'YYYY-MM-DD HH:mm') {
  if (!val) return '—'
  return dayjs(val).format(fmt)
}

// Order status map
export const ORDER_STATUS = {
  10: { label: '待付款', class: 'badge-gold' },
  20: { label: '已付款', class: 'badge-success' },
  30: { label: '已取消', class: 'badge-muted' }
}

// Pay status map
export const PAY_STATUS = {
  10: { label: '未支付', class: 'badge-gold' },
  20: { label: '支付成功', class: 'badge-success' },
  30: { label: '已关闭', class: 'badge-muted' }
}

// Coupon status map
export const COUPON_STATUS = {
  10: { label: '未使用', class: 'badge-gold' },
  15: { label: '锁定中', class: 'badge-muted' },
  20: { label: '已使用', class: 'badge-muted' },
  30: { label: '已过期', class: 'badge-danger' }
}

// Coupon type
export const COUPON_TYPE = {
  10: '满减券',
  20: '折扣券'
}

// Gender map
export const GENDER_MAP = {
  0: '保密',
  1: '男',
  2: '女'
}

// Publish status
export const PUBLISH_STATUS = {
  0: { label: '未上架', class: 'badge-muted' },
  1: { label: '已上架', class: 'badge-success' }
}

// Flash sale status
export const FLASH_SALE_STATUS = {
  0: { label: '禁用', class: 'badge-muted' },
  1: { label: '启用', class: 'badge-success' }
}

// Scope type map
export const SCOPE_TYPE = {
  10: '全场通用',
  20: '指定类目',
  30: '指定商品(SPU)',
  40: '指定SKU'
}

// Generic status
export const ENABLE_STATUS = {
  0: { label: '禁用', class: 'badge-muted' },
  1: { label: '启用', class: 'badge-success' }
}

// Truncate text
export function truncate(str, len = 30) {
  if (!str) return ''
  return str.length > len ? str.slice(0, len) + '…' : str
}

// Debounce
export function debounce(fn, delay = 300) {
  let timer
  return function (...args) {
    clearTimeout(timer)
    timer = setTimeout(() => fn.apply(this, args), delay)
  }
}

// Placeholder image
export function placeholderImg(text = 'IMG', w = 300, h = 300) {
  return `https://via.placeholder.com/${w}x${h}/f0f0f5/b0b0c0?text=${encodeURIComponent(text)}`
}

// Build image src with fallback
export function imgSrc(url, fallback) {
  return url || fallback || placeholderImg()
}
