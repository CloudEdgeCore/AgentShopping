import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { cartApi } from '@/api'

export const useCartStore = defineStore('cart', () => {
  const cartData = ref(null)

  const totalCount = computed(() => cartData.value?.totalItemCount || 0)
  const checkedAmount = computed(() => cartData.value?.checkedAmount || 0)
  const items = computed(() => cartData.value?.items || [])

  async function fetchCart() {
    const res = await cartApi.getItems()
    cartData.value = res.data
  }

  async function addItem(skuId, quantity = 1) {
    await cartApi.addItem({ skuId, quantity })
    await fetchCart()
  }

  async function updateQuantity(cartItemId, quantity) {
    await cartApi.updateQuantity(cartItemId, { quantity })
    await fetchCart()
  }

  async function toggleChecked(cartItemId, checked) {
    await cartApi.updateChecked(cartItemId, { checked })
    await fetchCart()
  }

  async function removeItem(cartItemId) {
    await cartApi.deleteItem(cartItemId)
    await fetchCart()
  }

  async function clearCart() {
    await cartApi.clearCart()
    cartData.value = null
  }

  function resetCart() {
    cartData.value = null
  }

  return { cartData, totalCount, checkedAmount, items, fetchCart, addItem, updateQuantity, toggleChecked, removeItem, clearCart, resetCart }
})
