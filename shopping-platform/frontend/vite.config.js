import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { fileURLToPath, URL } from 'node:url'

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url))
    }
  },
  server: {
    port: 5173,
    proxy: {
      // 购物车/订单/支付 → Agent（兼容 Java 格式）
      '/api/cart': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      '/api/orders': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      '/api/auth': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      // Python RAG Agent 静态文件（图片等）
      '/agent/static': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/agent/, '')
      },
      // Python RAG Agent API
      '/agent': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/agent/, '/api')
      },
      // Java 电商平台 API（兜底）
      '/api': {
        target: 'http://localhost:8080',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, '')
      }
    }
  }
})
