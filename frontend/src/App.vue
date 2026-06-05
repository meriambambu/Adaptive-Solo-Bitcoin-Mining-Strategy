<script setup lang="ts">
import { ref, onMounted } from 'vue'
import StatsBar from './components/StatsBar.vue'
import BidsTable from './components/BidsTable.vue'
import BidHistory from './components/BidHistory.vue'
import CreateBidModal from './components/CreateBidModal.vue'
import MarketOverview from './components/MarketOverview.vue'
import StrategyPanel from './components/StrategyPanel.vue'
import { useBids } from './composables/useBids'
import { useWebSocket } from './composables/useWebSocket'
import type { Order } from './composables/useBids'

const { orders, loading, fetchOrders, cancelOrder } = useBids()
const showCreate = ref(false)
const editOrder = ref<Order | null>(null)

// Real-time updates pushed from backend strategy cycles
const { connected } = useWebSocket((msg: unknown) => {
  const payload = msg as { type: string }
  if (payload.type === 'strategy_update') {
    fetchOrders()
  }
})

onMounted(fetchOrders)

async function handleCancel(id: string) {
  await cancelOrder(id)
}

function handleEdit(order: Order) {
  editOrder.value = order
  showCreate.value = true
}
</script>

<template>
  <div class="min-h-screen bg-surface-900 text-gray-100">
    <!-- Top nav -->
    <header class="flex items-center justify-between px-6 py-3 bg-surface-800 border-b border-surface-600">
      <div class="flex items-center gap-3">
        <svg class="h-6 w-6 text-brand-purple" fill="currentColor" viewBox="0 0 24 24">
          <path d="M11.944 17.97L4.58 13.62 11.943 24l7.37-10.38-7.372 4.35h.003zM12.056 0L4.69 12.223l7.365 4.354 7.365-4.35L12.056 0z"/>
        </svg>
        <span class="font-bold text-sm tracking-tight">Adaptive Bitcoin Mining</span>
      </div>
      <div class="flex items-center gap-2 text-xs">
        <span
          class="h-2 w-2 rounded-full"
          :class="connected ? 'bg-green-500' : 'bg-red-500 animate-pulse'"
        />
        <span :class="connected ? 'text-green-400' : 'text-red-400'">
          {{ connected ? 'Live' : 'Connecting…' }}
        </span>
      </div>
    </header>

    <!-- Balance bar -->
    <StatsBar />

    <!-- Main content -->
    <main class="max-w-7xl mx-auto px-4 py-6 grid grid-cols-1 xl:grid-cols-3 gap-6">
      <!-- Left: bids table (full width on mobile, 2/3 on xl) -->
      <div class="xl:col-span-2 space-y-6">
        <BidsTable
          :orders="orders"
          :loading="loading"
          @cancel="handleCancel"
          @edit="handleEdit"
          @create="showCreate = true"
        />
        <BidHistory />
      </div>

      <!-- Right: market + strategy -->
      <div class="space-y-6">
        <MarketOverview :my-bid-price-sat="orders.map(o => Math.round(o.price_sat))" />
        <StrategyPanel />
      </div>
    </main>

    <!-- Create / Edit modal -->
    <CreateBidModal
      v-if="showCreate"
      @close="showCreate = false; editOrder = null"
      @created="fetchOrders"
    />
  </div>
</template>
