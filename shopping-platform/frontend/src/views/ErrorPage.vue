<template>
  <div class="error-page">
    <div class="error-inner">
      <div class="error-code">{{ is403 ? '403' : '404' }}</div>
      <div class="error-glyph">{{ is403 ? '⊘' : '◌' }}</div>
      <h1 class="error-title">{{ is403 ? '访问受限' : '页面不存在' }}</h1>
      <p class="error-desc">
        {{ is403
          ? '您没有权限访问该页面。如有疑问，请联系管理员。'
          : '您访问的页面已飞走了，或许从未存在过。' }}
      </p>
      <div class="error-actions">
        <RouterLink to="/" class="btn btn-primary">返回首页</RouterLink>
        <button v-if="is403" class="btn btn-outline" @click="goBack">返回上一页</button>
      </div>
    </div>
    <!-- Decorative -->
    <div class="error-deco">
      <div class="deco-ring ring-1"></div>
      <div class="deco-ring ring-2"></div>
      <div class="deco-ring ring-3"></div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'

const route = useRoute()
const router = useRouter()
const is403 = computed(() => route.path === '/403')

function goBack() {
  if (window.history.length > 1) {
    router.back()
  } else {
    router.push('/')
  }
}
</script>

<style scoped>
.error-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--surface);
  position: relative;
  overflow: hidden;
}

.error-inner {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 16px;
  text-align: center;
  position: relative;
  z-index: 1;
  padding: 48px 32px;
}

.error-code {
  font-family: var(--font-display);
  font-size: clamp(80px, 16vw, 160px);
  font-weight: 700;
  color: transparent;
  -webkit-text-stroke: 2px var(--border);
  line-height: 1;
  letter-spacing: -0.02em;
  user-select: none;
}

.error-glyph {
  font-size: 48px;
  color: var(--gold);
  line-height: 1;
  margin-top: -16px;
  animation: spin-slow 8s linear infinite;
}

@keyframes spin-slow {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.error-title {
  font-family: var(--font-display);
  font-size: clamp(24px, 4vw, 36px);
  font-weight: 700;
  color: var(--ink);
  letter-spacing: -0.01em;
}

.error-desc {
  font-size: 15px;
  color: var(--ink-muted);
  max-width: 380px;
  line-height: 1.7;
}

.error-actions {
  display: flex;
  gap: 12px;
  margin-top: 12px;
}

/* Decorative rings */
.error-deco {
  position: absolute;
  inset: 0;
  pointer-events: none;
}

.deco-ring {
  position: absolute;
  border-radius: 50%;
  border: 1px solid var(--border);
}

.ring-1 {
  width: 600px;
  height: 600px;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  opacity: 0.5;
}

.ring-2 {
  width: 400px;
  height: 400px;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  opacity: 0.4;
}

.ring-3 {
  width: 240px;
  height: 240px;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  opacity: 0.3;
}
</style>
