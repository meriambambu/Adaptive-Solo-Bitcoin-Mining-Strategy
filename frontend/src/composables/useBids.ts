import { ref } from 'vue'
import { api } from '../api/client'

export interface Order {
  id: string
  price: string
  limit: string
  amount: string
  availableAmount: string
  payedAmount: string
  status: string
  acceptedSpeed: string
  estimatedDurationInSeconds: number | null
  createdTs: number | null
  pool: { host: string; port: number; username: string } | null
  meta: { isSolo: boolean; notes: string | null } | null
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

  async function updateOrder(id: string, payload: { price?: string; limit?: string; amount?: string }) {
    const { data } = await api.put<Order>(`/api/orders/${id}`, payload)
    const idx = orders.value.findIndex((o) => o.id === id)
    if (idx !== -1) orders.value[idx] = data
  }

  return { orders, loading, error, fetchOrders, cancelOrder, updateOrder }
}
