<template>
  <div class="shop-layout">
    <header class="shop-header" :class="{ scrolled: isScrolled }">
      <div class="container">
        <nav class="header-nav">
          <!-- Logo -->
          <RouterLink to="/" class="logo">
            <span class="logo-mark">L</span>
            <span class="logo-text">LUXE</span>
          </RouterLink>

          <!-- Main Nav -->
          <div class="nav-links">
            <RouterLink to="/" class="nav-link" :class="{ active: $route.path === '/' }">首页</RouterLink>
            <RouterLink to="/products" class="nav-link" :class="{ active: $route.path.startsWith('/products') }">全部商品</RouterLink>
            <RouterLink to="/ai-chat" class="nav-link nav-link--ai" :class="{ active: $route.path === '/ai-chat' }">
              🤖 AI 导购
            </RouterLink>
          </div>

          <!-- Search -->
          <div class="search-bar" :class="{ focused: searchFocused }">
            <svg class="search-icon" viewBox="0 0 20 20" fill="none">
              <circle cx="9" cy="9" r="6" stroke="currentColor" stroke-width="1.5"/>
              <path d="m13.5 13.5 3 3" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
            </svg>
            <input
              v-model="searchKeyword"
              type="text"
              placeholder="搜索商品..."
              @focus="searchFocused = true"
              @blur="searchFocused = false"
              @keyup.enter="doSearch"
            />
          </div>

          <!-- Right Actions -->
          <div class="nav-actions">
            <!-- Cart -->
            <RouterLink to="/cart" class="nav-action-btn" title="购物车">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                <path d="M6 2 3 6v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V6l-3-4z"/>
                <line x1="3" y1="6" x2="21" y2="6"/>
                <path d="M16 10a4 4 0 0 1-8 0"/>
              </svg>
              <span v-if="cartStore.totalCount > 0" class="cart-badge">{{ cartStore.totalCount }}</span>
            </RouterLink>

            <!-- User -->
            <div v-if="authStore.isLoggedIn" class="user-menu" @mouseenter="showUserMenu = true" @mouseleave="showUserMenu = false">
              <button class="nav-action-btn user-btn">
                <div class="avatar">{{ avatarLetter }}</div>
              </button>
              <Transition name="fade">
                <div v-if="showUserMenu" class="user-dropdown">
                  <div class="dropdown-header">
                    <div class="dropdown-avatar">{{ avatarLetter }}</div>
                    <div>
                      <div class="dropdown-name">{{ authStore.userInfo?.nickname || authStore.userInfo?.username }}</div>
                      <div class="dropdown-meta">{{ authStore.isAdmin ? '管理员' : '普通用户' }}</div>
                    </div>
                  </div>
                  <hr class="divider" />
                  <RouterLink to="/user/profile" class="dropdown-item">个人资料</RouterLink>
                  <RouterLink to="/user/orders" class="dropdown-item">我的订单</RouterLink>
                  <RouterLink to="/user/coupons" class="dropdown-item">我的优惠券</RouterLink>
                  <RouterLink to="/user/addresses" class="dropdown-item">收货地址</RouterLink>
                  <template v-if="authStore.isAdmin">
                    <hr class="divider" />
                    <RouterLink to="/admin" class="dropdown-item dropdown-item--admin">
                      <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5" style="width:14px;height:14px">
                        <rect x="2" y="2" width="5" height="5" rx="1"/><rect x="9" y="2" width="5" height="5" rx="1"/>
                        <rect x="2" y="9" width="5" height="5" rx="1"/><rect x="9" y="9" width="5" height="5" rx="1"/>
                      </svg>
                      管理后台
                    </RouterLink>
                  </template>
                  <hr class="divider" />
                  <button class="dropdown-item dropdown-item--danger" @click="handleLogout">退出登录</button>
                </div>
              </Transition>
            </div>
            <template v-else>
              <RouterLink to="/login" class="btn btn-outline btn-sm">登录</RouterLink>
              <RouterLink to="/register" class="btn btn-primary btn-sm">注册</RouterLink>
            </template>
          </div>
        </nav>
      </div>
    </header>

    <main class="shop-main">
      <RouterView />
    </main>

    <!-- AI 导购聊天组件（登录后、非聊天页、非商品详情页显示） -->
    <AiChatWidget v-if="authStore.isLoggedIn && $route.path !== '/ai-chat' && !$route.path.startsWith('/agent-product/')" />

    <footer class="shop-footer">
      <div class="container">
        <div class="footer-inner">
          <div class="footer-brand">
            <span class="logo-mark">L</span>
            <span class="footer-tagline">品味非凡，精选至上</span>
          </div>
          <div class="footer-meta">
            <span>© 2026 LUXE SHOP</span>
            <span>·</span>
            <span>高端购物平台</span>
          </div>
        </div>
      </div>
    </footer>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useCartStore } from '@/stores/cart'
import { useChatStore } from '@/stores/chat'
import AiChatWidget from '@/components/shop/AiChatWidget.vue'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()
const cartStore = useCartStore()
const chatStore = useChatStore()

// 切换页面时重置聊天（开新对话）
watch(() => route.path, (newPath, oldPath) => {
  if (newPath !== oldPath && newPath !== '/ai-chat') {
    chatStore.clear()
  }
})

const isScrolled = ref(false)
const searchFocused = ref(false)
const searchKeyword = ref('')
const showUserMenu = ref(false)

const avatarLetter = computed(() => {
  const name = authStore.userInfo?.nickname || authStore.userInfo?.username || '?'
  return name.charAt(0).toUpperCase()
})

function doSearch() {
  if (searchKeyword.value.trim()) {
    router.push({ name: 'ProductList', query: { keyword: searchKeyword.value.trim() } })
    searchKeyword.value = ''
  }
}

async function handleLogout() {
  showUserMenu.value = false
  await authStore.logout()
  cartStore.resetCart()
  router.push('/')
}

function handleScroll() {
  isScrolled.value = window.scrollY > 40
}

onMounted(() => {
  window.addEventListener('scroll', handleScroll, { passive: true })
  if (authStore.isLoggedIn) {
    cartStore.fetchCart().catch(() => {})
  }
})
onUnmounted(() => window.removeEventListener('scroll', handleScroll))
</script>

<style scoped>
.shop-layout {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
}

/* Header */
.shop-header {
  position: sticky;
  top: 0;
  z-index: 100;
  background: rgba(255, 255, 255, 0.92);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  border-bottom: 1px solid transparent;
  transition: all 300ms var(--ease-out);
}

.shop-header.scrolled {
  border-bottom-color: var(--border);
  box-shadow: var(--shadow-sm);
}

.header-nav {
  display: flex;
  align-items: center;
  gap: 32px;
  height: 64px;
}

/* Logo */
.logo {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}

.logo-mark {
  width: 32px;
  height: 32px;
  background: var(--ink);
  color: var(--gold);
  display: flex;
  align-items: center;
  justify-content: center;
  font-family: var(--font-display);
  font-size: 18px;
  font-weight: 700;
  border-radius: 6px;
}

.logo-text {
  font-family: var(--font-display);
  font-size: 20px;
  font-weight: 700;
  letter-spacing: 0.1em;
  color: var(--ink);
}

/* Nav Links */
.nav-links {
  display: flex;
  align-items: center;
  gap: 4px;
  flex-shrink: 0;
}

.nav-link {
  padding: 6px 14px;
  border-radius: 100px;
  font-size: 14px;
  font-weight: 500;
  color: var(--ink-muted);
  transition: all var(--transition);
}

.nav-link:hover,
.nav-link.active {
  color: var(--ink);
  background: var(--surface-dim);
}

.nav-link.active {
  color: var(--ink);
  font-weight: 600;
}

.nav-link--ai {
  background: linear-gradient(135deg, var(--ink) 0%, #333 100%);
  color: var(--gold) !important;
  font-weight: 600;
  padding: 6px 16px;
}

.nav-link--ai:hover {
  background: var(--ink);
  transform: scale(1.02);
}

.nav-link--ai.active {
  background: var(--ink);
  box-shadow: 0 2px 8px rgba(0,0,0,0.2);
}

/* Search */
.search-bar {
  flex: 1;
  max-width: 360px;
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 14px;
  background: var(--surface-dim);
  border: 1.5px solid transparent;
  border-radius: 100px;
  transition: all var(--transition);
}

.search-bar.focused {
  background: var(--surface);
  border-color: var(--ink);
  box-shadow: 0 0 0 3px rgba(15,15,20,0.06);
}

.search-icon {
  width: 16px;
  height: 16px;
  color: var(--ink-muted);
  flex-shrink: 0;
}

.search-bar input {
  flex: 1;
  border: none;
  background: none;
  outline: none;
  font-size: 14px;
  color: var(--ink);
}

.search-bar input::placeholder {
  color: var(--ink-faint);
}

/* Right Actions */
.nav-actions {
  margin-left: auto;
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}

.nav-action-btn {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 40px;
  height: 40px;
  border-radius: 50%;
  color: var(--ink-soft);
  transition: all var(--transition);
  background: transparent;
}

.nav-action-btn:hover {
  background: var(--surface-dim);
  color: var(--ink);
}

.nav-action-btn svg {
  width: 20px;
  height: 20px;
}

.cart-badge {
  position: absolute;
  top: 2px;
  right: 2px;
  min-width: 18px;
  height: 18px;
  padding: 0 4px;
  background: var(--gold);
  color: var(--ink);
  font-size: 10px;
  font-weight: 700;
  border-radius: 100px;
  display: flex;
  align-items: center;
  justify-content: center;
}

/* User Menu */
.user-menu {
  position: relative;
}

.user-btn {
  width: 40px;
  height: 40px;
}

.avatar {
  width: 32px;
  height: 32px;
  background: var(--ink);
  color: var(--gold);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  font-weight: 600;
  font-family: var(--font-display);
}

.user-dropdown {
  position: absolute;
  top: calc(100% + 8px);
  right: 0;
  width: 220px;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-lg);
  padding: 8px;
  z-index: 200;
}

.dropdown-header {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 8px 8px 12px;
}

.dropdown-avatar {
  width: 40px;
  height: 40px;
  background: var(--ink);
  color: var(--gold);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 18px;
  font-weight: 700;
  font-family: var(--font-display);
  flex-shrink: 0;
}

.dropdown-name {
  font-size: 14px;
  font-weight: 600;
  color: var(--ink);
}

.dropdown-meta {
  font-size: 12px;
  color: var(--ink-muted);
}

.dropdown-item {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
  padding: 8px 10px;
  border-radius: var(--radius-sm);
  font-size: 14px;
  color: var(--ink-soft);
  transition: all var(--transition);
  text-decoration: none;
}

.dropdown-item:hover {
  background: var(--surface-dim);
  color: var(--ink);
}

.dropdown-item--admin {
  color: var(--accent);
  font-weight: 500;
}

.dropdown-item--danger {
  color: var(--danger);
}

.dropdown-item--danger:hover {
  background: #fef2f2;
  color: var(--danger);
}

/* Main */
.shop-main {
  flex: 1;
}

/* Footer */
.shop-footer {
  margin-top: 80px;
  border-top: 1px solid var(--border);
  padding: 32px 0;
}

.footer-inner {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.footer-brand {
  display: flex;
  align-items: center;
  gap: 12px;
}

.footer-tagline {
  font-size: 13px;
  color: var(--ink-muted);
  font-style: italic;
  font-family: var(--font-display);
}

.footer-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  color: var(--ink-faint);
}
</style>
