<template>
  <div class="user-center">
    <div class="container">
      <div class="uc-layout">
        <!-- Sidebar -->
        <aside class="uc-sidebar">
          <div class="uc-user-card">
            <div class="uc-avatar">{{ avatarLetter }}</div>
            <div class="uc-user-info">
              <div class="uc-username">{{ authStore.userInfo?.nickname || authStore.userInfo?.username }}</div>
              <div class="uc-uid">UID · {{ authStore.userInfo?.userId }}</div>
            </div>
          </div>
          <nav class="uc-nav">
            <RouterLink v-for="item in navItems" :key="item.to" :to="item.to" class="uc-nav-item">
              <component :is="item.icon" class="uc-nav-icon" />
              {{ item.label }}
            </RouterLink>
          </nav>
        </aside>
        <!-- Content -->
        <div class="uc-content">
          <RouterView />
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, defineComponent, h } from 'vue'
import { useAuthStore } from '@/stores/auth'

const authStore = useAuthStore()

const avatarLetter = computed(() => {
  const name = authStore.userInfo?.nickname || authStore.userInfo?.username || '?'
  return name.charAt(0).toUpperCase()
})

// Simple SVG icon components
const IconUser = defineComponent({ render: () => h('svg', { viewBox: '0 0 20 20', fill: 'none', stroke: 'currentColor', 'stroke-width': '1.5' }, [h('circle', { cx: '10', cy: '6', r: '3' }), h('path', { d: 'M3 18c0-4 3.1-7 7-7s7 3 7 7' })]) })
const IconOrders = defineComponent({ render: () => h('svg', { viewBox: '0 0 20 20', fill: 'none', stroke: 'currentColor', 'stroke-width': '1.5' }, [h('rect', { x: '3', y: '2', width: '14', height: '16', rx: '2' }), h('path', { d: 'M7 7h6M7 11h4' })]) })
const IconAddress = defineComponent({ render: () => h('svg', { viewBox: '0 0 20 20', fill: 'none', stroke: 'currentColor', 'stroke-width': '1.5' }, [h('path', { d: 'M10 2C7.24 2 5 4.24 5 7c0 4.25 5 11 5 11s5-6.75 5-11c0-2.76-2.24-5-5-5z' }), h('circle', { cx: '10', cy: '7', r: '1.5' })]) })
const IconCoupon = defineComponent({ render: () => h('svg', { viewBox: '0 0 20 20', fill: 'none', stroke: 'currentColor', 'stroke-width': '1.5' }, [h('rect', { x: '2', y: '6', width: '16', height: '8', rx: '1' }), h('path', { d: 'M7 6V5m0 10v-1M13 6V5m0 10v-1' })]) })

const navItems = [
  { to: '/user/profile', label: '个人资料', icon: IconUser },
  { to: '/user/orders', label: '我的订单', icon: IconOrders },
  { to: '/user/addresses', label: '收货地址', icon: IconAddress },
  { to: '/user/coupons', label: '我的优惠券', icon: IconCoupon }
]
</script>

<style scoped>
.user-center {
  padding: 40px 0 80px;
}

.uc-layout {
  display: grid;
  grid-template-columns: 220px 1fr;
  gap: 32px;
  align-items: start;
}

/* Sidebar */
.uc-sidebar {
  position: sticky;
  top: 88px;
}

.uc-user-card {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 20px;
  background: var(--ink);
  border-radius: var(--radius-md);
  margin-bottom: 8px;
}

.uc-avatar {
  width: 44px;
  height: 44px;
  background: var(--gold);
  color: var(--ink);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 20px;
  font-weight: 700;
  font-family: var(--font-display);
  flex-shrink: 0;
}

.uc-user-info {
  min-width: 0;
}

.uc-username {
  font-size: 15px;
  font-weight: 600;
  color: var(--surface);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.uc-uid {
  font-size: 12px;
  color: rgba(255,255,255,0.4);
  font-family: var(--font-mono);
}

.uc-nav {
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding: 8px;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
}

.uc-nav-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  border-radius: var(--radius-sm);
  font-size: 14px;
  font-weight: 500;
  color: var(--ink-muted);
  transition: all var(--transition);
}

.uc-nav-item:hover,
.uc-nav-item.router-link-active {
  background: var(--surface-dim);
  color: var(--ink);
}

.uc-nav-item.router-link-active {
  font-weight: 600;
}

.uc-nav-icon {
  width: 16px;
  height: 16px;
  flex-shrink: 0;
}

/* Content */
.uc-content {
  min-width: 0;
}

@media (max-width: 768px) {
  .uc-layout {
    grid-template-columns: 1fr;
  }
  .uc-sidebar {
    position: static;
  }
}
</style>
