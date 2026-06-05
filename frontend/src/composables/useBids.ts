import { ref } from 'vue'
import { api } from '../api/client'

export interface Order {
  id: string
  price_btc: number
  price_sat: number
  amount_btc: number
  amount_remaining_btc: number
  amount_consumed_btc: number
  speed_limit_ph: number
  avg_speed_ph: number
  progress_pct: number
  status: string
  is_current: boolean
  created: string | null
  memo: string
  fee_rate_pct: number
  pool_url: string | null
  pool_identity: string | null
}

export function useBids() {
  const orders = ref<Order[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)

  async function fetchOrders() {
    loading.value = true
    error.value = null
    try {
      const { data } = await api.get<Order[]>('/api/orders')
      orders.value = data
    } catch (e: unknown) {
      error.value = (e as Error).message
    } finally {
      loading.value = false
    }
  }

  async function cancelOrder(id: string) {
    await api.delete(`/api/orders/${id}`)
    orders.value = orders.value.filter((o) => o.id !== id)
  }

  async function updatePrice(id: string, newPriceBtc: number) {
    await api.put(`/api/orders/${id}/price`, null, { params: { new_price_btc: newPriceBtc } })
    await fetchOrders()
  }

  return { orders, loading, error, fetchOrders, cancelOrder, updatePrice }
}
