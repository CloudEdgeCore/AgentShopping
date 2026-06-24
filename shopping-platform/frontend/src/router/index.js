import { createRouter, createWebHistory } from 'vue-router'
import NProgress from 'nprogress'
import { useAuthStore } from '@/stores/auth'

const routes = [
  // ===== SHOP LAYOUT =====
  {
    path: '/',
    component: () => import('@/layouts/ShopLayout.vue'),
    children: [
      { path: '', name: 'Home', component: () => import('@/views/shop/HomePage.vue') },
      { path: 'ai-chat', name: 'AiChat', component: () => import('@/views/shop/AiChatPage.vue'), meta: { requiresAuth: true } },
      { path: 'agent-product/:productId', name: 'AgentProduct', component: () => import('@/views/shop/AgentProductPage.vue') },
      { path: 'products', name: 'ProductList', component: () => import('@/views/shop/ProductListPage.vue') },
      { path: 'products/:spuId', name: 'ProductDetail', component: () => import('@/views/shop/ProductDetailPage.vue') },
      { path: 'cart', name: 'Cart', component: () => import('@/views/shop/CartPage.vue'), meta: { requiresAuth: true } },
      { path: 'checkout', name: 'Checkout', component: () => import('@/views/shop/CheckoutPage.vue'), meta: { requiresAuth: true } },
      { path: 'pay/:orderNo', name: 'Pay', component: () => import('@/views/shop/PayPage.vue'), meta: { requiresAuth: true } },
      { path: 'pay-result', name: 'PayResult', component: () => import('@/views/shop/PayResultPage.vue'), meta: { requiresAuth: true } },
      {
        path: 'user',
        component: () => import('@/layouts/UserCenterLayout.vue'),
        meta: { requiresAuth: true },
        children: [
          { path: '', redirect: '/user/profile' },
          { path: 'profile', name: 'UserProfile', component: () => import('@/views/shop/UserProfilePage.vue') },
          { path: 'orders', name: 'UserOrders', component: () => import('@/views/shop/OrderListPage.vue') },
          { path: 'orders/:orderNo', name: 'OrderDetail', component: () => import('@/views/shop/OrderDetailPage.vue') },
          { path: 'addresses', name: 'UserAddresses', component: () => import('@/views/shop/AddressPage.vue') },
          { path: 'coupons', name: 'UserCoupons', component: () => import('@/views/shop/CouponPage.vue') }
        ]
      }
    ]
  },
  // ===== AUTH PAGES =====
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/shop/LoginPage.vue'),
    meta: { guestOnly: true }
  },
  {
    path: '/register',
    name: 'Register',
    component: () => import('@/views/shop/RegisterPage.vue'),
    meta: { guestOnly: true }
  },
  // ===== ADMIN LAYOUT =====
  {
    path: '/admin',
    component: () => import('@/layouts/AdminLayout.vue'),
    meta: { requiresAuth: true, requiresAdmin: true },
    children: [
      { path: '', redirect: '/admin/products' },
      { path: 'orders', name: 'AdminOrders', component: () => import('@/views/admin/AdminOrdersPage.vue') },
      { path: 'products', name: 'AdminProducts', component: () => import('@/views/admin/AdminProductsPage.vue') },
      { path: 'products/new', name: 'AdminProductNew', component: () => import('@/views/admin/AdminProductFormPage.vue') },
      { path: 'products/:id/edit', name: 'AdminProductEdit', component: () => import('@/views/admin/AdminProductFormPage.vue') },
      { path: 'categories', name: 'AdminCategories', component: () => import('@/views/admin/AdminCategoriesPage.vue') },
      { path: 'brands', name: 'AdminBrands', component: () => import('@/views/admin/AdminBrandsPage.vue') },
      { path: 'inventory', name: 'AdminInventory', component: () => import('@/views/admin/AdminInventoryPage.vue') },
      { path: 'coupons', name: 'AdminCoupons', component: () => import('@/views/admin/AdminCouponsPage.vue') },
      { path: 'flash-sales', name: 'AdminFlashSales', component: () => import('@/views/admin/AdminFlashSalesPage.vue') }
    ]
  },
  // ===== 403 / 404 =====
  { path: '/403', name: 'Forbidden', component: () => import('@/views/ErrorPage.vue'), props: { code: 403, message: '无权限访问' } },
  { path: '/:pathMatch(.*)*', name: 'NotFound', component: () => import('@/views/ErrorPage.vue'), props: { code: 404, message: '页面不存在' } }
]

const router = createRouter({
  history: createWebHistory(),
  routes,
  scrollBehavior(to, from, savedPosition) {
    if (savedPosition) return savedPosition
    return { top: 0 }
  }
})

router.beforeEach((to, from, next) => {
  NProgress.start()
  const authStore = useAuthStore()

  if (to.meta.requiresAuth && !authStore.isLoggedIn) {
    return next({ name: 'Login', query: { redirect: to.fullPath } })
  }
  if (to.meta.requiresAdmin && !authStore.isAdmin) {
    return next({ name: 'Forbidden' })
  }
  if (to.meta.guestOnly && authStore.isLoggedIn) {
    return next({ name: 'Home' })
  }
  next()
})

router.afterEach(() => {
  NProgress.done()
})

export default router
