/**
 * RAG Agent API 客户端
 * 调用 Python RAG Agent 服务（通过 /agent 代理到 localhost:8000）
 */

const AGENT_BASE = '/agent'

/**
 * 获取请求头（带 JWT Token）
 */
function agentHeaders() {
  const token = localStorage.getItem('access_token')
  const headers = {
    'Content-Type': 'application/json',
    'X-Request-ID': `web-${crypto.randomUUID()}`
  }
  if (token) {
    headers['Authorization'] = `Bearer ${token}`
  }
  return headers
}

/**
 * 解析 SSE 事件流
 */
async function* parseSSEStream(response) {
  const reader = response.body.getReader()
  const decoder = new TextDecoder('utf-8')
  let buffer = ''

  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })
    const chunks = buffer.split(/\n\n/)
    buffer = chunks.pop() || ''
    for (const chunk of chunks) {
      if (chunk.trim()) yield parseSSEChunk(chunk)
    }
  }
  if (buffer.trim()) yield parseSSEChunk(buffer)
}

function parseSSEChunk(chunk) {
  const lines = chunk.split(/\r?\n/)
  const event = lines.find(line => line.startsWith('event:'))?.slice(6).trim() || 'message'
  const data = lines
    .filter(line => line.startsWith('data:'))
    .map(line => line.slice(5).trim())
    .join('\n')
  let payload = data
  try {
    payload = JSON.parse(data)
  } catch {}
  return { event, payload }
}

export const agentApi = {
  /**
   * 健康检查
   */
  async health(deep = false) {
    const resp = await fetch(`${AGENT_BASE}${deep ? '/health/deep' : '/health'}`)
    return resp.json()
  },

  /**
   * 用户登录
   */
  async login(username, password) {
    const resp = await fetch(`${AGENT_BASE}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password })
    })
    if (!resp.ok) throw new Error(`${resp.status} ${resp.statusText}`)
    return resp.json()
  },

  /**
   * 用户注册
   */
  async register(username, password, nickname = '') {
    const resp = await fetch(`${AGENT_BASE}/auth/register`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password, nickname })
    })
    if (!resp.ok) throw new Error(`${resp.status} ${resp.statusText}`)
    return resp.json()
  },

  /**
   * 获取会话列表
   */
  async getSessions() {
    const resp = await fetch(`${AGENT_BASE}/sessions`, { headers: agentHeaders() })
    if (!resp.ok) throw new Error(`${resp.status} ${resp.statusText}`)
    return resp.json()
  },

  /**
   * 创建新会话
   */
  async createSession(title = '导购会话') {
    const resp = await fetch(`${AGENT_BASE}/sessions`, {
      method: 'POST',
      headers: agentHeaders(),
      body: JSON.stringify({ title })
    })
    if (!resp.ok) throw new Error(`${resp.status} ${resp.statusText}`)
    return resp.json()
  },

  /**
   * 获取会话消息历史
   */
  async getMessages(sessionId) {
    const resp = await fetch(`${AGENT_BASE}/sessions/${encodeURIComponent(sessionId)}/messages`, {
      headers: agentHeaders()
    })
    if (!resp.ok) throw new Error(`${resp.status} ${resp.statusText}`)
    return resp.json()
  },

  /**
   * 删除会话
   */
  async deleteSession(sessionId) {
    const resp = await fetch(`${AGENT_BASE}/sessions/${encodeURIComponent(sessionId)}`, {
      method: 'DELETE',
      headers: agentHeaders()
    })
    if (!resp.ok) throw new Error(`${resp.status} ${resp.statusText}`)
    return resp.json()
  },

  /**
   * 上传图片
   */
  async uploadImage(file) {
    const form = new FormData()
    form.append('file', file)
    const headers = agentHeaders()
    delete headers['Content-Type'] // 让浏览器自动设置 multipart boundary
    const resp = await fetch(`${AGENT_BASE}/upload/image`, {
      method: 'POST',
      headers,
      body: form
    })
    if (!resp.ok) throw new Error(`${resp.status} ${resp.statusText}`)
    return resp.json()
  },

  /**
   * 流式聊天（SSE）
   * @param {Object} payload - { message, session_id?, upload_id?, memory? }
   * @param {Object} handlers - { onStatus, onMessageDelta, onMessage, onProducts, onCart, onError, onDone }
   */
  async streamChat(payload, handlers) {
    const resp = await fetch(`${AGENT_BASE}/chat/stream`, {
      method: 'POST',
      headers: agentHeaders(),
      body: JSON.stringify(payload)
    })
    if (!resp.ok || !resp.body) {
      const text = await resp.text().catch(() => '')
      throw new Error(`${resp.status} ${resp.statusText}: ${text}`)
    }

    for await (const { event, payload: data } of parseSSEStream(resp)) {
      switch (event) {
        case 'status':
          handlers.onStatus?.(data)
          break
        case 'message_start':
          handlers.onMessageStart?.(data)
          break
        case 'message_delta':
          handlers.onMessageDelta?.(data)
          break
        case 'message':
          handlers.onMessage?.(data)
          break
        case 'product_cards':
          handlers.onProducts?.(data)
          break
        case 'cart_state':
          handlers.onCart?.(data)
          break
        case 'trace':
          handlers.onTrace?.(data)
          break
        case 'vision_analysis':
          handlers.onVision?.(data)
          break
        case 'error':
          handlers.onError?.(typeof data === 'object' ? data.message : String(data))
          break
        case 'done':
          handlers.onDone?.(data)
          break
      }
    }
  },

  /**
   * 获取购物车
   */
  async getCart() {
    const resp = await fetch(`${AGENT_BASE}/commerce/cart`, { headers: agentHeaders() })
    if (!resp.ok) throw new Error(`${resp.status} ${resp.statusText}`)
    return resp.json()
  },

  /**
   * 获取分类树（降级用）
   */
  async getCategories() {
    const resp = await fetch(`${AGENT_BASE}/products/categories`)
    if (!resp.ok) throw new Error(`${resp.status} ${resp.statusText}`)
    return resp.json()
  },

  /**
   * 获取品牌列表（降级用，支持按分类过滤）
   */
  async getBrands(limit = 5, categoryId = '') {
    let url = `${AGENT_BASE}/products/brands?limit=${limit}`
    if (categoryId) url += `&categoryId=${encodeURIComponent(categoryId)}`
    const resp = await fetch(url)
    if (!resp.ok) throw new Error(`${resp.status} ${resp.statusText}`)
    return resp.json()
  },

  /**
   * 分页查询商品（降级用）
   */
  async getProductPage(params = {}) {
    const qs = new URLSearchParams()
    if (params.current) qs.set('current', params.current)
    if (params.size) qs.set('size', params.size)
    if (params.categoryId) qs.set('categoryId', params.categoryId)
    if (params.brandId) qs.set('brandId', params.brandId)
    if (params.keyword) qs.set('keyword', params.keyword)
    const resp = await fetch(`${AGENT_BASE}/products/page?${qs}`)
    if (!resp.ok) throw new Error(`${resp.status} ${resp.statusText}`)
    return resp.json()
  },

  /**
   * 提交反馈
   */
  async submitFeedback(messageId, rating, reason = '') {
    const resp = await fetch(`${AGENT_BASE}/feedback`, {
      method: 'POST',
      headers: agentHeaders(),
      body: JSON.stringify({ message_id: messageId, rating, reason })
    })
    if (!resp.ok) throw new Error(`${resp.status} ${resp.statusText}`)
    return resp.json()
  },

  /**
   * 导入 JSON 数据集（100 个商品，4 个类目）
   */
  async importDataset(datasetRoot = '') {
    const form = new FormData()
    if (datasetRoot) form.append('dataset_root', datasetRoot)
    const headers = agentHeaders()
    delete headers['Content-Type']
    const resp = await fetch(`${AGENT_BASE}/catalog/import-dataset`, {
      method: 'POST',
      headers,
      body: form
    })
    if (!resp.ok) throw new Error(`${resp.status} ${resp.statusText}`)
    return resp.json()
  },

  /**
   * 重建搜索索引
   */
  async reindex() {
    const resp = await fetch(`${AGENT_BASE}/catalog/reindex`, {
      method: 'POST',
      headers: agentHeaders()
    })
    if (!resp.ok) throw new Error(`${resp.status} ${resp.statusText}`)
    return resp.json()
  }
}
