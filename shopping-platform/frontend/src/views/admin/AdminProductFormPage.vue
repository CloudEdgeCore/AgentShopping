<template>
  <div class="admin-page">
    <div class="admin-page-header">
      <div>
        <RouterLink to="/admin/products" class="back-link">返回商品列表</RouterLink>
        <h2 class="admin-page-title">{{ isEdit ? '编辑商品' : '新增商品' }}</h2>
      </div>
      <button class="btn btn-primary" :disabled="saving" @click="handleSave">
        <span v-if="saving" class="spinner spinner-gold"></span>
        {{ saving ? '保存中...' : '保存商品' }}
      </button>
    </div>

    <div v-if="pageLoading" class="empty-state">
      <div class="spinner" style="width: 28px; height: 28px; border-width: 2px"></div>
    </div>

    <div v-else class="form-sections">
      <div class="form-section">
        <div class="form-section-title">基本信息</div>
        <div class="form-grid-3">
          <div class="form-group form-group--full">
            <label class="form-label">商品名称 *</label>
            <input
              v-model="form.spuName"
              type="text"
              class="form-input"
              :class="{ error: errors.spuName }"
              placeholder="请输入商品名称"
            />
            <div v-if="errors.spuName" class="form-error">{{ errors.spuName }}</div>
          </div>

          <div class="form-group form-group--full">
            <label class="form-label">副标题</label>
            <input
              v-model="form.subtitle"
              type="text"
              class="form-input"
              placeholder="选填，例如卖点、简短说明"
            />
          </div>

          <div class="form-group">
            <label class="form-label">所属分类 *</label>
            <select v-model="form.categoryId" class="form-select" :class="{ error: errors.categoryId }">
              <option :value="null">请选择分类</option>
              <option v-for="category in categories" :key="category.id" :value="category.id">
                {{ category.label }}
              </option>
            </select>
            <div v-if="errors.categoryId" class="form-error">{{ errors.categoryId }}</div>
          </div>

          <div class="form-group">
            <label class="form-label">所属品牌 *</label>
            <select v-model="form.brandId" class="form-select" :class="{ error: errors.brandId }">
              <option :value="null">请选择品牌</option>
              <option v-for="brand in brands" :key="brand.id" :value="brand.id">
                {{ brand.name }}
              </option>
            </select>
            <div v-if="errors.brandId" class="form-error">{{ errors.brandId }}</div>
          </div>

          <div class="form-group">
            <label class="form-label">排序</label>
            <input v-model.number="form.sort" type="number" min="0" class="form-input" />
          </div>

          <div class="form-group form-group--full">
            <label class="form-label">商品主图</label>
            <input
              v-model="form.coverImage"
              type="text"
              class="form-input"
              placeholder="请输入主图 URL"
            />
            <img v-if="form.coverImage" :src="form.coverImage" class="image-preview" />
          </div>

          <div class="form-group form-group--full">
            <label class="form-label">相册图（每行一个 URL）</label>
            <textarea
              v-model="albumText"
              class="form-textarea"
              rows="4"
              placeholder="每行填写一个图片 URL"
            ></textarea>
          </div>

          <div class="form-group form-group--full">
            <label class="form-label">商品详情（HTML）</label>
            <textarea
              v-model="form.detail"
              class="form-textarea"
              rows="6"
              placeholder="请输入商品详情内容"
            ></textarea>
          </div>
        </div>
      </div>

      <div class="form-section">
        <div class="form-section-header">
          <div>
            <div class="form-section-title">规格列表 *</div>
            <div class="form-section-tip">规格编码自动生成；规格图片选填，只有颜色、外观不同时才建议单独填写。</div>
          </div>
          <button type="button" class="btn btn-outline btn-sm" @click="addSku">+ 添加规格</button>
        </div>

        <div v-if="form.skuList.length" class="sku-table-wrap">
          <table class="sku-table">
            <thead>
              <tr>
                <th>规格编码</th>
                <th>规格名称 *</th>
                <th>规格描述</th>
                <th>规格图片</th>
                <th>销售价 *</th>
                <th>市场价 *</th>
                <th>库存 *</th>
                <th>默认</th>
                <th>状态</th>
                <th style="width: 60px">删除</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(sku, index) in form.skuList" :key="index">
                <td>
                  <div v-if="sku.skuCode" class="auto-code">{{ sku.skuCode }}</div>
                  <div v-else class="auto-code auto-code--pending">保存后自动生成</div>
                </td>
                <td>
                  <input
                    v-model="sku.skuName"
                    type="text"
                    class="form-input form-input--sm"
                    :class="{ error: skuErrors[index]?.skuName }"
                    placeholder="例如：黑色 256G"
                  />
                </td>
                <td>
                  <input
                    v-model="sku.attrText"
                    type="text"
                    class="form-input form-input--sm"
                    placeholder="例如：黑色 / 256G / 标准版"
                  />
                </td>
                <td>
                  <input
                    v-model="sku.imageUrl"
                    type="text"
                    class="form-input form-input--sm"
                    placeholder="选填，只有颜色或外观不同时才建议填写"
                  />
                </td>
                <td>
                  <input
                    v-model.number="sku.salePrice"
                    type="number"
                    step="0.01"
                    min="0"
                    class="form-input form-input--sm"
                    :class="{ error: skuErrors[index]?.salePrice }"
                  />
                </td>
                <td>
                  <input
                    v-model.number="sku.marketPrice"
                    type="number"
                    step="0.01"
                    min="0"
                    class="form-input form-input--sm"
                    :class="{ error: skuErrors[index]?.marketPrice }"
                  />
                </td>
                <td>
                  <input
                    v-model.number="sku.totalStock"
                    type="number"
                    step="1"
                    min="0"
                    class="form-input form-input--sm"
                    :class="{ error: skuErrors[index]?.totalStock }"
                  />
                </td>
                <td class="center">
                  <input type="radio" name="defaultSku" :checked="sku.defaultSku" @change="setDefaultSku(index)" />
                </td>
                <td>
                  <select v-model.number="sku.status" class="form-select form-input--sm">
                    <option :value="1">启用</option>
                    <option :value="0">禁用</option>
                  </select>
                </td>
                <td>
                  <button type="button" class="btn btn-ghost btn-sm text-danger" @click="removeSku(index)">×</button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <div v-else class="empty-cell">请至少添加一个规格</div>
      </div>

      <div v-if="globalError" class="form-error global-error">{{ globalError }}</div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { adminBrandApi, adminCategoryApi, adminProductApi } from '@/api'

const route = useRoute()
const router = useRouter()

const isEdit = computed(() => !!route.params.id)
const pageLoading = ref(false)
const saving = ref(false)
const globalError = ref('')

const categories = ref([])
const brands = ref([])
const skuErrors = ref([])

const form = reactive({
  spuName: '',
  subtitle: '',
  categoryId: null,
  brandId: null,
  coverImage: '',
  albumImages: [],
  detail: '',
  sort: 0,
  skuList: []
})

const errors = reactive({
  spuName: '',
  categoryId: '',
  brandId: ''
})

const albumText = computed({
  get: () => (form.albumImages || []).join('\n'),
  set: (value) => {
    form.albumImages = value
      .split('\n')
      .map((item) => item.trim())
      .filter(Boolean)
  }
})

function createEmptySku() {
  return {
    skuCode: '',
    skuName: '',
    imageUrl: '',
    salePrice: 0,
    marketPrice: 0,
    totalStock: 0,
    attrText: '',
    defaultSku: form.skuList.length === 0,
    status: 1
  }
}

function addSku() {
  form.skuList.push(createEmptySku())
}

function removeSku(index) {
  form.skuList.splice(index, 1)
  if (form.skuList.length && !form.skuList.some((item) => item.defaultSku)) {
    form.skuList[0].defaultSku = true
  }
}

function setDefaultSku(index) {
  form.skuList.forEach((item, currentIndex) => {
    item.defaultSku = currentIndex === index
  })
}

async function loadMeta() {
  try {
    const [categoryRes, brandRes] = await Promise.all([adminCategoryApi.getTree(), adminBrandApi.getList({})])
    const flattenCategories = (list, depth = 0) =>
      list.flatMap((item) => {
        const prefix = depth === 0 ? '主分类 · ' : `${'　'.repeat(Math.max(depth - 1, 0))}└ `
        const current = {
          ...item,
          label: `${prefix}${item.name}`
        }
        return [current, ...(item.children ? flattenCategories(item.children, depth + 1) : [])]
      })

    categories.value = flattenCategories(categoryRes.data || [])
    brands.value = brandRes.data?.records || brandRes.data || []
  } catch (error) {
    globalError.value = '加载分类和品牌失败'
  }
}

async function loadDetail() {
  pageLoading.value = true
  try {
    const response = await adminProductApi.getDetail(route.params.id)
    const data = response.data || {}

    form.spuName = data.spuName || ''
    form.subtitle = data.subtitle || ''
    form.categoryId = data.categoryId || null
    form.brandId = data.brandId || null
    form.coverImage = data.coverImage || ''
    form.albumImages = data.albumImages || []
    form.detail = data.detail || ''
    form.sort = data.sort ?? 0
    form.skuList = (data.skuList || []).map((item) => ({
      skuCode: item.skuCode || '',
      skuName: item.skuName || '',
      imageUrl: item.imageUrl || '',
      salePrice: Number(item.salePrice ?? 0),
      marketPrice: Number(item.marketPrice ?? 0),
      totalStock: Number(item.totalStock ?? 0),
      attrText: item.attrText || '',
      defaultSku: !!item.defaultSku,
      status: item.status ?? 1
    }))

    if (!form.skuList.length) {
      addSku()
    }
    if (!form.skuList.some((item) => item.defaultSku)) {
      form.skuList[0].defaultSku = true
    }
  } catch (error) {
    globalError.value = error.message || '加载商品详情失败'
  } finally {
    pageLoading.value = false
  }
}

function validate() {
  errors.spuName = form.spuName.trim() ? '' : '请填写商品名称'
  errors.categoryId = form.categoryId ? '' : '请选择分类'
  errors.brandId = form.brandId ? '' : '请选择品牌'

  skuErrors.value = form.skuList.map((item) => ({
    skuName: item.skuName?.trim() ? '' : '必填',
    salePrice: Number(item.salePrice) >= 0 ? '' : '非法',
    marketPrice: Number(item.marketPrice) >= 0 ? '' : '非法',
    totalStock: Number.isInteger(Number(item.totalStock)) && Number(item.totalStock) >= 0 ? '' : '非法'
  }))

  const hasSkuError = skuErrors.value.some(
    (item) => item.skuName || item.salePrice || item.marketPrice || item.totalStock
  )

  if (!form.skuList.length) {
    globalError.value = '请至少添加一个规格'
    return false
  }

  if (!form.skuList.some((item) => item.defaultSku)) {
    form.skuList[0].defaultSku = true
  }

  return !errors.spuName && !errors.categoryId && !errors.brandId && !hasSkuError
}

async function handleSave() {
  globalError.value = ''
  if (!validate()) {
    return
  }

  saving.value = true
  try {
    const payload = {
      spuName: form.spuName.trim(),
      subtitle: form.subtitle?.trim() || undefined,
      categoryId: form.categoryId,
      brandId: form.brandId,
      coverImage: form.coverImage?.trim() || undefined,
      albumImages: form.albumImages,
      detail: form.detail?.trim() || undefined,
      sort: form.sort ?? 0,
      skuList: form.skuList.map((item) => ({
        skuCode: item.skuCode?.trim() || undefined,
        skuName: item.skuName.trim(),
        imageUrl: item.imageUrl?.trim() || undefined,
        salePrice: Number(item.salePrice ?? 0),
        marketPrice: Number(item.marketPrice ?? 0),
        totalStock: Number(item.totalStock ?? 0),
        attrText: item.attrText?.trim() || undefined,
        defaultSku: !!item.defaultSku,
        status: item.status ?? 1
      }))
    }

    if (isEdit.value) {
      await adminProductApi.update(route.params.id, payload)
    } else {
      await adminProductApi.create(payload)
    }

    router.push('/admin/products')
  } catch (error) {
    globalError.value = error.message || '保存商品失败'
  } finally {
    saving.value = false
  }
}

onMounted(() => {
  loadMeta()
  if (isEdit.value) {
    loadDetail()
    return
  }
  addSku()
})
</script>

<style scoped>
.admin-page { display: flex; flex-direction: column; gap: 20px; }
.admin-page-header { display: flex; justify-content: space-between; align-items: flex-end; }
.back-link { font-size: 13px; color: var(--ink-muted); text-decoration: none; display: block; margin-bottom: 6px; }
.back-link:hover { color: var(--ink); }
.admin-page-title { font-size: 22px; font-weight: 700; color: var(--ink); }
.form-sections { display: flex; flex-direction: column; gap: 20px; }
.form-section { background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius-md); padding: 24px; display: flex; flex-direction: column; gap: 16px; }
.form-section-header { display: flex; justify-content: space-between; align-items: flex-start; gap: 16px; }
.form-section-title { font-size: 15px; font-weight: 700; color: var(--ink); }
.form-section-tip { margin-top: 6px; font-size: 12px; color: var(--ink-faint); }
.form-grid-3 { display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; }
.form-group--full { grid-column: 1 / -1; }
.image-preview { margin-top: 8px; width: 80px; height: 80px; object-fit: cover; border-radius: var(--radius-sm); border: 1px solid var(--border); }
.sku-table-wrap { overflow-x: auto; }
.sku-table { width: 100%; border-collapse: collapse; font-size: 13px; }
.sku-table th { padding: 10px 8px; background: var(--surface-dim); font-size: 12px; font-weight: 600; color: var(--ink-muted); text-align: left; border-bottom: 1px solid var(--border); white-space: nowrap; }
.sku-table td { padding: 8px 6px; border-bottom: 1px solid var(--border); vertical-align: middle; }
.sku-table tr:last-child td { border-bottom: none; }
.auto-code { display: inline-flex; align-items: center; min-height: 36px; padding: 0 10px; border-radius: var(--radius-sm); background: var(--surface-dim); color: var(--ink); white-space: nowrap; }
.auto-code--pending { color: var(--ink-faint); }
.form-input--sm { padding: 6px 10px; font-size: 13px; }
.text-danger { color: var(--danger) !important; }
.center { text-align: center; }
.empty-cell { padding: 16px; color: var(--ink-faint); text-align: center; font-size: 13px; }
.global-error { padding: 10px 14px; background: #fef2f2; border: 1px solid rgba(224, 82, 82, 0.25); border-radius: var(--radius-sm); font-size: 13px; color: var(--danger); }
@media (max-width: 768px) {
  .form-grid-3 { grid-template-columns: 1fr 1fr; }
}
</style>
