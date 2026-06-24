import http from '@/utils/http'

export const authApi = {
  login: (data) => http.post('/auth/login', data),
  register: (data) => http.post('/auth/register', data),
  logout: () => http.post('/auth/logout'),
  me: () => http.get('/auth/me')
}

export const userApi = {
  getProfile: () => http.get('/user/profile'),
  updateProfile: (data) => http.put('/user/profile', data),
  getAddresses: () => http.get('/user/address/list'),
  addAddress: (data) => http.post('/user/address', data),
  updateAddress: (id, data) => http.put(`/user/address/${id}`, data),
  deleteAddress: (id) => http.delete(`/user/address/${id}`),
  setDefaultAddress: (id) => http.put(`/user/address/${id}/default`)
}

export const productApi = {
  getCategories: () => http.get('/product/categories'),
  getBrands: () => http.get('/product/brands'),
  getPage: (params) => http.get('/search/product/page', { params }),
  getDetail: (spuId) => http.get(`/product/${spuId}`),
  getSku: (skuId) => http.get(`/product/sku/${skuId}`)
}

export const cartApi = {
  addItem: (data) => http.post('/cart/items', data),
  getItems: () => http.get('/cart/items'),
  updateQuantity: (cartItemId, data) => http.put(`/cart/items/${cartItemId}/quantity`, data),
  updateChecked: (cartItemId, data) => http.put(`/cart/items/${cartItemId}/checked`, data),
  deleteItem: (cartItemId) => http.delete(`/cart/items/${cartItemId}`),
  clearCart: () => http.delete('/cart/items/clear')
}

export const orderApi = {
  preview: (data) => http.post('/orders/preview', data),
  submit: (data) => http.post('/orders/submit', data),
  getDetail: (orderNo) => http.get(`/orders/${orderNo}`),
  getPage: (params) => http.get('/orders/page', { params }),
  cancel: (orderNo, data) => http.post(`/orders/${orderNo}/cancel`, data || {})
}

export const paymentApi = {
  create: (data) => http.post('/payments/mock/create', data),
  getByNo: (paymentNo) => http.get(`/payments/${paymentNo}`),
  getByOrderNo: (orderNo) => http.get(`/payments/order/${orderNo}`),
  confirmSuccess: (paymentNo) => http.post(`/payments/${paymentNo}/success`)
}

export const marketingApi = {
  getFlashSaleDiscounts: (params) => http.get('/marketing/flash-sale/sku-discounts', { params }),
  claimCoupon: (templateId) => http.post(`/marketing/coupons/claim/${templateId}`),
  getMyCoupons: (params) => http.get('/marketing/coupons/my', { params })
}

// ===== Admin APIs =====

export const adminBrandApi = {
  getList: (params) => http.get('/admin/brand/list', { params }),
  create: (data) => http.post('/admin/brand', data),
  update: (id, data) => http.put(`/admin/brand/${id}`, data),
  delete: (id) => http.delete(`/admin/brand/${id}`)
}

export const adminCategoryApi = {
  getTree: () => http.get('/admin/category/tree'),
  getList: () => http.get('/admin/category/list'),
  create: (data) => http.post('/admin/category', data),
  update: (id, data) => http.put(`/admin/category/${id}`, data),
  delete: (id) => http.delete(`/admin/category/${id}`)
}

export const adminProductApi = {
  getPage: (params) => http.get('/admin/product/page', { params }),
  getDetail: (id) => http.get(`/admin/product/${id}`),
  create: (data) => http.post('/admin/product', data),
  update: (id, data) => http.put(`/admin/product/${id}`, data),
  publish: (id, publishStatus = 1) => http.put(`/admin/product/${id}/publish`, { publishStatus }),
  unpublish: (id) => http.put(`/admin/product/${id}/unpublish`),
  delete: (id) => http.delete(`/admin/product/${id}`)
}

export const adminInventoryApi = {
  getPage: (params) => http.get('/admin/inventory/sku-stock/page', { params }),
  updateStock: (skuId, data) => http.put(`/admin/inventory/sku-stock/${skuId}`, data),
  getStock: (skuId) => http.get(`/admin/inventory/sku-stock/${skuId}`)
}

export const adminOrderApi = {
  getPage: (params) => http.get('/admin/orders/page', { params }),
  getDetail: (orderNo) => http.get(`/admin/orders/${orderNo}`),
  cancel: (orderNo, data) => http.post(`/admin/orders/${orderNo}/cancel`, data || {})
}

export const adminMarketingApi = {
  // Coupon templates
  getCouponPage: (params) => http.get('/admin/marketing/coupon-template/page', { params }),
  getCouponDetail: (id) => http.get(`/admin/marketing/coupon-template/${id}`),
  createCoupon: (data) => http.post('/admin/marketing/coupon-template', data),
  updateCoupon: (id, data) => http.put(`/admin/marketing/coupon-template/${id}`, data),
  enableCoupon: (id) => http.put(`/admin/marketing/coupon-template/${id}/enable`),
  disableCoupon: (id) => http.put(`/admin/marketing/coupon-template/${id}/disable`),
  // Flash sales
  getFlashSalePage: (params) => http.get('/admin/marketing/flash-sale/page', { params }),
  getFlashSaleDetail: (id) => http.get(`/admin/marketing/flash-sale/${id}`),
  createFlashSale: (data) => http.post('/admin/marketing/flash-sale', data),
  updateFlashSale: (id, data) => http.put(`/admin/marketing/flash-sale/${id}`, data),
  deleteFlashSale: (id) => http.delete(`/admin/marketing/flash-sale/${id}`)
}

export const adminSearchApi = {
  rebuildProductIndex: () => http.post('/admin/search/product/rebuild'),
  syncProductIndex: (spuId) => http.post(`/admin/search/product/sync/${spuId}`)
}
