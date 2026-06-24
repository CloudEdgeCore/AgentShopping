<template>
  <div class="admin-page category-page">
    <section class="category-hero">
      <div>
        <h2 class="admin-page-title">分类管理</h2>
        <p class="admin-page-sub">
          把主分类当成入口，把子分类当成真正的商品落点。这样后台维护更清晰，前台浏览也更自然。
        </p>
      </div>

      <div class="category-hero-actions">
        <button class="btn btn-primary" @click="openForm(null, null)">+ 新增主分类</button>
      </div>
    </section>

    <section class="category-metrics">
      <div class="metric-card">
        <span>主分类</span>
        <strong>{{ rootCategories.length }}</strong>
      </div>
      <div class="metric-card">
        <span>子分类</span>
        <strong>{{ childCategoryCount }}</strong>
      </div>
      <div class="metric-card">
        <span>总分类数</span>
        <strong>{{ totalCategoryCount }}</strong>
      </div>
    </section>

    <section class="category-board">
      <div v-if="loading" class="admin-loading">
        <div class="spinner" style="width: 28px; height: 28px; border-width: 2px"></div>
      </div>

      <div v-else-if="rootCategories.length" class="category-grid">
        <article v-for="root in rootCategories" :key="root.id" class="category-panel">
          <header class="category-panel-header">
            <div class="category-panel-main">
              <div class="category-avatar">
                <img v-if="root.iconUrl" :src="root.iconUrl" :alt="root.name" />
                <span v-else>{{ root.name.charAt(0) }}</span>
              </div>
              <div>
                <div class="category-level-tag">主分类</div>
                <h3>{{ root.name }}</h3>
                <p>
                  {{ root.children?.length ? `下设 ${countDescendants(root)} 个子分类` : '当前主分类下还没有子分类' }}
                </p>
              </div>
            </div>

            <div class="category-actions">
              <button class="btn btn-ghost btn-sm" @click="openForm(root, null)">编辑</button>
              <button class="btn btn-outline btn-sm" @click="openForm(null, root.id)">添加子分类</button>
              <button class="btn btn-ghost btn-sm text-danger" @click="deleteCategory(root.id)">删除</button>
            </div>
          </header>

          <div v-if="flattenBranches(root.children).length" class="category-branch-list">
            <div
              v-for="branch in flattenBranches(root.children)"
              :key="branch.id"
              class="category-branch-row"
              :style="{ paddingLeft: `${16 + (branch.depth - 1) * 20}px` }"
            >
              <div class="category-branch-copy">
                <div class="category-branch-head">
                  <span class="category-branch-tag">{{ getDepthLabel(branch.depth) }}</span>
                  <span class="category-branch-name">{{ branch.name }}</span>
                  <span class="category-branch-meta">ID {{ branch.id }}</span>
                </div>
                <div class="category-branch-desc">
                  {{ branch.children?.length ? `还有 ${countDescendants(branch)} 个下级分类` : '已经是末级分类' }}
                </div>
              </div>

              <div class="category-actions category-actions--inline">
                <button class="btn btn-ghost btn-sm" @click="openForm(branch, null)">编辑</button>
                <button class="btn btn-outline btn-sm" @click="openForm(null, branch.id)">添加下级</button>
                <button class="btn btn-ghost btn-sm text-danger" @click="deleteCategory(branch.id)">删除</button>
              </div>
            </div>
          </div>

          <div v-else class="category-empty">
            <div class="category-empty-title">这个主分类下暂时还没有子分类</div>
            <button class="btn btn-outline btn-sm" @click="openForm(null, root.id)">先添加一个子分类</button>
          </div>
        </article>
      </div>

      <div v-else class="empty-state">
        <div class="empty-state__icon">🗂</div>
        <div class="empty-state__title">还没有分类</div>
        <div class="empty-state__desc">先创建主分类，再逐步补充子分类。</div>
      </div>
    </section>

    <Teleport to="body">
      <Transition name="fade">
        <div v-if="showForm" class="modal-backdrop" @click.self="closeForm">
          <div class="modal">
            <div class="modal-hd">
              <h3 class="modal-title">{{ editing ? '编辑分类' : '新增分类' }}</h3>
              <button class="btn btn-ghost btn-icon" @click="closeForm">×</button>
            </div>

            <form class="modal-body" @submit.prevent="handleSave">
              <div class="form-group">
                <label class="form-label">父级分类</label>
                <input :value="parentName || '无（主分类）'" type="text" class="form-input" disabled />
              </div>

              <div class="form-group">
                <label class="form-label">分类名称 *</label>
                <input
                  v-model="catForm.name"
                  type="text"
                  class="form-input"
                  :class="{ error: catErrors.name }"
                  placeholder="例如：数码、手机配件、厨房电器"
                />
                <div v-if="catErrors.name" class="form-error">{{ catErrors.name }}</div>
              </div>

              <div class="form-group">
                <label class="form-label">分类图标 URL</label>
                <input
                  v-model="catForm.iconUrl"
                  type="text"
                  class="form-input"
                  placeholder="选填，用在前台分类入口展示"
                />
                <img v-if="catForm.iconUrl" :src="catForm.iconUrl" class="category-preview" />
              </div>

              <div class="form-grid-2">
                <div class="form-group">
                  <label class="form-label">排序</label>
                  <input v-model.number="catForm.sort" type="number" min="0" class="form-input" />
                </div>

                <div class="form-group">
                  <label class="form-label">状态</label>
                  <select v-model.number="catForm.status" class="form-select">
                    <option :value="1">启用</option>
                    <option :value="0">禁用</option>
                  </select>
                </div>
              </div>

              <div class="modal-footer">
                <button type="button" class="btn btn-outline" @click="closeForm">取消</button>
                <button type="submit" class="btn btn-primary" :disabled="saving">
                  <span v-if="saving" class="spinner spinner-gold"></span>
                  {{ saving ? '保存中...' : '保存' }}
                </button>
              </div>
            </form>
          </div>
        </div>
      </Transition>
    </Teleport>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { adminCategoryApi } from '@/api'

const tree = ref([])
const loading = ref(true)
const showForm = ref(false)
const editing = ref(null)
const parentId = ref(null)
const saving = ref(false)

const catForm = reactive({
  name: '',
  iconUrl: '',
  sort: 0,
  status: 1
})

const catErrors = reactive({
  name: ''
})

const rootCategories = computed(() => tree.value || [])
const childCategoryCount = computed(() => rootCategories.value.reduce((sum, item) => sum + countDescendants(item), 0))
const totalCategoryCount = computed(() => rootCategories.value.length + childCategoryCount.value)

const parentName = computed(() => {
  if (!parentId.value) {
    return ''
  }
  return findCategoryName(tree.value, parentId.value) || ''
})

async function load() {
  loading.value = true
  try {
    const res = await adminCategoryApi.getTree()
    tree.value = res.data || []
  } finally {
    loading.value = false
  }
}

function findCategoryName(list, targetId) {
  for (const category of list || []) {
    if (category.id === targetId) {
      return category.name
    }
    const nested = findCategoryName(category.children, targetId)
    if (nested) {
      return nested
    }
  }
  return ''
}

function flattenBranches(nodes, depth = 1) {
  return (nodes || []).flatMap((node) => [
    { ...node, depth },
    ...flattenBranches(node.children || [], depth + 1)
  ])
}

function countDescendants(node) {
  const children = node?.children || []
  return children.reduce((sum, child) => sum + 1 + countDescendants(child), 0)
}

function getDepthLabel(depth) {
  if (depth === 1) {
    return '子分类'
  }
  return `${depth + 1}级分类`
}

function openForm(node, pid) {
  editing.value = node
  parentId.value = pid !== undefined ? pid : node?.parentId || null
  catErrors.name = ''

  if (node) {
    catForm.name = node.name || ''
    catForm.iconUrl = node.iconUrl || ''
    catForm.sort = node.sort ?? 0
    catForm.status = node.status ?? 1
  } else {
    catForm.name = ''
    catForm.iconUrl = ''
    catForm.sort = 0
    catForm.status = 1
  }

  showForm.value = true
}

function closeForm() {
  showForm.value = false
}

async function handleSave() {
  catErrors.name = catForm.name.trim() ? '' : '请填写分类名称'
  if (catErrors.name) {
    return
  }

  saving.value = true
  try {
    const payload = {
      name: catForm.name.trim(),
      iconUrl: catForm.iconUrl?.trim() || undefined,
      sort: catForm.sort ?? 0,
      status: catForm.status ?? 1,
      parentId: parentId.value == null ? 0 : parentId.value
    }

    if (editing.value) {
      await adminCategoryApi.update(editing.value.id, payload)
    } else {
      await adminCategoryApi.create(payload)
    }

    closeForm()
    await load()
  } catch (error) {
    alert(error.message)
  } finally {
    saving.value = false
  }
}

async function deleteCategory(categoryId) {
  if (!confirm('删除这个分类后，它下面的子分类也会一起删除，确认继续吗？')) {
    return
  }

  try {
    await adminCategoryApi.delete(categoryId)
    await load()
  } catch (error) {
    alert(error.message)
  }
}

onMounted(load)
</script>

<style scoped>
.category-page {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.category-hero {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 20px;
  padding: 28px;
  border: 1px solid rgba(201, 168, 76, 0.2);
  border-radius: 28px;
  background:
    radial-gradient(circle at top right, rgba(201, 168, 76, 0.12), transparent 35%),
    linear-gradient(180deg, rgba(255, 249, 236, 0.86), rgba(255, 255, 255, 0.98));
}

.admin-page-title {
  font-size: 24px;
  font-weight: 700;
  color: var(--ink);
}

.admin-page-sub {
  max-width: 720px;
  margin-top: 8px;
  font-size: 14px;
  line-height: 1.8;
  color: var(--ink-muted);
}

.category-metrics {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 16px;
}

.metric-card {
  padding: 18px 20px;
  border: 1px solid var(--border);
  border-radius: 20px;
  background: var(--surface);
}

.metric-card span {
  display: block;
  font-size: 13px;
  color: var(--ink-muted);
}

.metric-card strong {
  display: block;
  margin-top: 10px;
  font-size: 28px;
  font-weight: 700;
  color: var(--ink);
}

.category-board {
  min-height: 120px;
}

.admin-loading {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 80px 0;
}

.category-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 18px;
}

.category-panel {
  display: flex;
  flex-direction: column;
  gap: 18px;
  padding: 24px;
  border: 1px solid var(--border);
  border-radius: 24px;
  background: var(--surface);
  box-shadow: 0 16px 36px rgba(18, 24, 38, 0.04);
}

.category-panel-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
}

.category-panel-main {
  display: flex;
  align-items: flex-start;
  gap: 14px;
  min-width: 0;
}

.category-avatar {
  width: 54px;
  height: 54px;
  flex-shrink: 0;
  border-radius: 16px;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
  background: linear-gradient(135deg, rgba(201, 168, 76, 0.18), rgba(255, 255, 255, 0.94));
  color: var(--gold-dark);
  font-size: 22px;
  font-weight: 700;
}

.category-avatar img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.category-level-tag {
  display: inline-flex;
  margin-bottom: 8px;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--gold-dark);
}

.category-panel-main h3 {
  font-size: 20px;
  font-weight: 700;
  color: var(--ink);
}

.category-panel-main p {
  margin-top: 8px;
  font-size: 13px;
  line-height: 1.7;
  color: var(--ink-muted);
}

.category-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.category-actions--inline {
  flex-shrink: 0;
  justify-content: flex-end;
}

.category-branch-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.category-branch-row {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 14px;
  padding: 14px 16px;
  border-radius: 18px;
  background: var(--surface-dim);
}

.category-branch-copy {
  min-width: 0;
}

.category-branch-head {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.category-branch-tag {
  padding: 4px 8px;
  border-radius: 999px;
  background: rgba(201, 168, 76, 0.12);
  color: var(--gold-dark);
  font-size: 11px;
  font-weight: 700;
}

.category-branch-name {
  font-size: 14px;
  font-weight: 600;
  color: var(--ink);
}

.category-branch-meta {
  font-size: 12px;
  color: var(--ink-faint);
}

.category-branch-desc {
  margin-top: 6px;
  font-size: 12px;
  color: var(--ink-muted);
}

.category-empty {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 18px 20px;
  border: 1px dashed rgba(18, 24, 38, 0.12);
  border-radius: 20px;
  background: rgba(250, 250, 250, 0.72);
}

.category-empty-title {
  font-size: 13px;
  color: var(--ink-muted);
}

.text-danger {
  color: var(--danger) !important;
}

.modal-backdrop {
  position: fixed;
  inset: 0;
  z-index: 500;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
  background: rgba(0, 0, 0, 0.45);
  backdrop-filter: blur(4px);
}

.modal {
  width: 100%;
  max-width: 460px;
  max-height: 90vh;
  display: flex;
  flex-direction: column;
  border-radius: var(--radius-lg);
  background: var(--surface);
  box-shadow: var(--shadow-lg);
}

.modal-hd {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 20px 24px;
  border-bottom: 1px solid var(--border);
}

.modal-title {
  font-size: 17px;
  font-weight: 700;
}

.modal-body {
  overflow-y: auto;
  padding: 20px 24px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.form-grid-2 {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px;
}

.category-preview {
  width: 72px;
  height: 72px;
  margin-top: 10px;
  object-fit: cover;
  border-radius: 16px;
  border: 1px solid var(--border);
}

.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  padding-top: 8px;
  border-top: 1px solid var(--border);
}

@media (max-width: 1024px) {
  .category-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 768px) {
  .category-hero,
  .category-panel-header,
  .category-branch-row,
  .category-empty {
    flex-direction: column;
    align-items: flex-start;
  }

  .category-metrics,
  .form-grid-2 {
    grid-template-columns: 1fr;
  }

  .category-actions,
  .category-actions--inline {
    width: 100%;
    justify-content: flex-start;
  }
}
</style>
