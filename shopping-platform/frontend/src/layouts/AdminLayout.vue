<template>
  <div class="admin-layout">
    <aside class="admin-sidebar">
      <div class="admin-logo">
        <span class="logo-mark">L</span>
        <div>
          <div class="admin-logo-title">LUXE ADMIN</div>
          <div class="admin-logo-sub">管理控制台</div>
        </div>
      </div>

      <nav class="admin-nav">
        <div class="admin-nav-section" v-for="section in navSections" :key="section.label">
          <div class="admin-nav-label">{{ section.label }}</div>
          <RouterLink
            v-for="item in section.items"
            :key="item.to"
            :to="item.to"
            class="admin-nav-item"
          >
            <span class="admin-nav-icon">{{ item.icon }}</span>
            {{ item.label }}
          </RouterLink>
        </div>
      </nav>

      <div class="admin-sidebar-footer">
        <RouterLink to="/" class="admin-back-btn">
          返回商城
        </RouterLink>
        <button class="admin-logout-btn" @click="handleLogout">退出登录</button>
      </div>
    </aside>

    <div class="admin-body">
      <header class="admin-topbar">
        <div class="admin-topbar-title">
          {{ currentPageTitle }}
        </div>
        <div class="admin-topbar-user">
          <div class="admin-avatar">{{ avatarLetter }}</div>
          <span>{{ authStore.userInfo?.nickname || authStore.userInfo?.username }}</span>
        </div>
      </header>

      <main class="admin-main">
        <RouterView />
      </main>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()

const avatarLetter = computed(() => {
  const name = authStore.userInfo?.nickname || authStore.userInfo?.username || '?'
  return name.charAt(0).toUpperCase()
})

const navSections = [
  {
    label: '订单管理',
    items: [
      { to: '/admin/orders', label: '订单列表', icon: '📦' }
    ]
  },
  {
    label: '商品管理',
    items: [
      { to: '/admin/products', label: '商品列表', icon: '🛍' },
      { to: '/admin/categories', label: '商品类目', icon: '🧭' },
      { to: '/admin/brands', label: '品牌管理', icon: '🏷' },
      { to: '/admin/inventory', label: '库存管理', icon: '📊' }
    ]
  },
  {
    label: '营销管理',
    items: [
      { to: '/admin/coupons', label: '优惠券', icon: '🎟' },
      { to: '/admin/flash-sales', label: '秒杀活动', icon: '⚡' }
    ]
  }
]

const titleMap = {
  '/admin/orders': '订单列表',
  '/admin/products': '商品列表',
  '/admin/products/new': '新建商品',
  '/admin/categories': '商品类目',
  '/admin/brands': '品牌管理',
  '/admin/inventory': '库存管理',
  '/admin/coupons': '优惠券管理',
  '/admin/flash-sales': '秒杀活动'
}

const currentPageTitle = computed(() => {
  if (route.path.includes('/admin/products/') && route.path.includes('/edit')) return '编辑商品'
  return titleMap[route.path] || '管理后台'
})

async function handleLogout() {
  await authStore.logout()
  router.push('/login')
}
</script>

<style scoped>
.admin-layout {
  display: flex;
  min-height: 100vh;
  background: var(--surface-dim);
}

.admin-sidebar {
  width: 240px;
  flex-shrink: 0;
  background: var(--ink);
  display: flex;
  flex-direction: column;
  position: fixed;
  top: 0;
  left: 0;
  bottom: 0;
  z-index: 50;
}

.admin-logo {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 24px 20px;
  border-bottom: 1px solid rgba(255,255,255,0.08);
}

.logo-mark {
  width: 36px;
  height: 36px;
  background: var(--gold);
  color: var(--ink);
  display: flex;
  align-items: center;
  justify-content: center;
  font-family: var(--font-display);
  font-size: 20px;
  font-weight: 700;
  border-radius: 8px;
  flex-shrink: 0;
}

.admin-logo-title {
  font-size: 13px;
  font-weight: 700;
  letter-spacing: 0.12em;
  color: var(--surface);
}

.admin-logo-sub {
  font-size: 11px;
  color: rgba(255,255,255,0.35);
  letter-spacing: 0.06em;
}

.admin-nav {
  flex: 1;
  padding: 16px 12px;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.admin-nav-section {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.admin-nav-label {
  font-size: 10px;
  font-weight: 600;
  letter-spacing: 0.12em;
  color: rgba(255,255,255,0.3);
  text-transform: uppercase;
  padding: 0 8px 8px;
}

.admin-nav-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  border-radius: var(--radius-sm);
  font-size: 14px;
  font-weight: 400;
  color: rgba(255,255,255,0.55);
  transition: all var(--transition);
  text-decoration: none;
}

.admin-nav-item:hover {
  background: rgba(255,255,255,0.06);
  color: rgba(255,255,255,0.85);
}

.admin-nav-item.router-link-active {
  background: rgba(201,168,76,0.15);
  color: var(--gold-light);
  font-weight: 500;
}

.admin-nav-icon {
  font-size: 16px;
  line-height: 1;
  width: 20px;
  text-align: center;
}

.admin-sidebar-footer {
  padding: 16px 12px;
  border-top: 1px solid rgba(255,255,255,0.08);
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.admin-back-btn {
  display: block;
  padding: 8px 12px;
  font-size: 13px;
  color: rgba(255,255,255,0.4);
  border-radius: var(--radius-sm);
  transition: all var(--transition);
  text-decoration: none;
}

.admin-back-btn:hover {
  color: rgba(255,255,255,0.7);
  background: rgba(255,255,255,0.06);
}

.admin-logout-btn {
  padding: 8px 12px;
  font-size: 13px;
  color: rgba(255,255,255,0.35);
  border-radius: var(--radius-sm);
  transition: all var(--transition);
  text-align: left;
}

.admin-logout-btn:hover {
  color: var(--danger);
  background: rgba(224,82,82,0.1);
}

.admin-body {
  flex: 1;
  margin-left: 240px;
  display: flex;
  flex-direction: column;
  min-height: 100vh;
}

.admin-topbar {
  height: 60px;
  background: var(--surface);
  border-bottom: 1px solid var(--border);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 32px;
  position: sticky;
  top: 0;
  z-index: 40;
}

.admin-topbar-title {
  font-size: 17px;
  font-weight: 600;
  color: var(--ink);
}

.admin-topbar-user {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 14px;
  color: var(--ink-soft);
}

.admin-avatar {
  width: 32px;
  height: 32px;
  background: var(--gold);
  color: var(--ink);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  font-weight: 700;
}

.admin-main {
  flex: 1;
  padding: 32px;
}
</style>
