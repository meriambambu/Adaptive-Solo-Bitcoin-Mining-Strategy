<script setup lang="ts">
import { ref } from 'vue'

function formatBest(sharesM: number): string {
  if (!sharesM || sharesM <= 0) return ''
  if (sharesM >= 1_000_000) return `${(sharesM / 1_000_000).toFixed(1)}T`
  if (sharesM >= 1_000) return `${(sharesM / 1_000).toFixed(1)}G`
  return `${Math.round(sharesM)}M`
}
import type { Order } from '../composables/useBids'

const props = defineProps<{
  orders: Order[]
  loading: boolean
}>()

const emit = defineEmits<{
  (e: 'cancel', id: string): void
  (e: 'edit', order: Order): void
  (e: 'create'): void
}>()

function formatDate(iso: string | null): string {
  if (!iso) return '—'
  return new Date(iso).toLocaleString('en-GB', {
    month: 'short', day: '2-digit', hour: '2-digit', minute: '2-digit',
  }).toUpperCase()
}

function isActive(status: string): boolean {
  return status === 'BID_STATUS_ACTIVE' || status === 'BID_STATUS_CREATED'
}

function statusLabel(status: string): string {
  return status.replace('BID_STATUS_', '')
}

const confirmCancel = ref<string | null>(null)
</script>

<template>
  <div class="card">
    <!-- Table header row -->
    <div class="flex items-center justify-between mb-4">
      <h2 class="text-sm font-semibold text-gray-200">Current Bids</h2>
      <button @click="emit('create')" class="btn-primary text-xs px-3 py-1.5">
        + Create
      </button>
    </div>

    <div v-if="loading" class="py-12 text-center text-gray-500 text-sm">Loading…</div>

    <div v-else-if="orders.length === 0" class="py-12 text-center text-gray-500 text-sm">
      No active bids. Click <strong>+ Create</strong> to place one.
    </div>

    <div v-else class="overflow-x-auto">
    <table class="w-full text-sm whitespace-nowrap">
      <thead>
        <tr class="border-b border-surface-600">
          <th class="table-header text-left pb-2 w-40">Bid ID</th>
          <th class="table-header text-right pb-2">Price<br><span class="normal-case font-normal text-gray-600">(₿/EHs/day)</span></th>
          <th class="table-header text-right pb-2">Budget<br><span class="normal-case font-normal text-gray-600">(BTC)</span></th>
          <th class="table-header text-right pb-2">Limit/Speed<br><span class="normal-case font-normal text-gray-600">(PH/s)</span></th>
          <th class="table-header text-right pb-2 hidden sm:table-cell">Created</th>
          <th class="table-header text-right pb-2 hidden sm:table-cell">Remaining</th>
          <th class="table-header text-right pb-2">Progress</th>
          <th class="table-header text-right pb-2">Actions</th>
        </tr>
      </thead>
      <tbody>
        <tr
          v-for="order in orders"
          :key="order.id"
          class="border-b border-surface-700 hover:bg-surface-700/30 transition-colors"
        >
          <!-- BID ID -->
          <td class="py-3 pr-4">
            <div class="flex items-center gap-2">
              <span
                class="h-2 w-2 rounded-full flex-shrink-0"
                :class="isActive(order.status) ? 'bg-green-500' : 'bg-gray-600'"
              />
              <div>
                <span class="font-mono text-xs text-brand-purple-light hover:underline cursor-pointer">
                  {{ order.id }}
                </span>
                <div class="flex gap-1 mt-0.5 flex-wrap">
                  <span class="badge-solo">SOLO</span>
                  <span class="badge text-xs" :class="isActive(order.status) ? 'text-green-400' : 'text-gray-500'">
                    {{ statusLabel(order.status) }}
                  </span>
                  <span v-if="order.shares_purchased_m > 0" class="badge text-xs text-gray-400">
                    Shares: {{ formatBest(order.shares_purchased_m) }}
                  </span>
                </div>
              </div>
            </div>
          </td>

          <!-- PRICE -->
          <td class="py-3 text-right font-mono text-gray-200">
            ₿{{ order.price_btc.toFixed(5) }}
          </td>

          <!-- BUDGET -->
          <td class="py-3 text-right font-mono text-gray-200">
            ₿{{ order.amount_btc.toFixed(8) }}
          </td>

          <!-- LIMIT / SPEED (PH/s) -->
          <td class="py-3 text-right font-mono text-gray-400">
            {{ order.speed_limit_ph > 0 ? order.speed_limit_ph.toFixed(2) : '∞' }} /
            <span class="text-gray-200">{{ order.avg_speed_ph.toFixed(2) }}</span>
            <span class="text-gray-600 text-xs ml-1">PH/s</span>
          </td>

          <!-- CREATED -->
          <td class="py-3 text-right text-gray-400 text-xs hidden sm:table-cell">
            {{ formatDate(order.created) }}
          </td>

          <!-- REMAINING -->
          <td class="py-3 text-right text-gray-400 text-xs font-mono hidden sm:table-cell">
            ₿{{ order.amount_remaining_btc.toFixed(8) }}
          </td>

          <!-- PROGRESS -->
          <td class="py-3 text-right">
            <div class="flex items-center justify-end gap-2">
              <div class="relative h-7 w-7">
                <svg class="h-7 w-7 -rotate-90" viewBox="0 0 28 28">
                  <circle cx="14" cy="14" r="11" fill="none" stroke="#2e2e34" stroke-width="3" />
                  <circle
                    cx="14" cy="14" r="11" fill="none"
                    stroke="#7c3aed" stroke-width="3"
                    stroke-dasharray="69.1"
                    :stroke-dashoffset="69.1 * (1 - order.progress_pct / 100)"
                    stroke-linecap="round"
                  />
                </svg>
                <span class="absolute inset-0 flex items-center justify-center text-[9px] font-bold text-gray-300">
                  {{ Math.round(order.progress_pct) }}%
                </span>
              </div>
            </div>
          </td>

          <!-- ACTIONS -->
          <td class="py-3 text-right">
            <div class="flex items-center justify-end gap-2">
              <button @click="emit('edit', order)" class="text-gray-500 hover:text-brand-purple-light transition-colors" title="Edit">
                <svg class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                  <path d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5M18.5 2.5a2.121 2.121 0 013 3L12 15l-4 1 1-4 9.5-9.5z"/>
                </svg>
              </button>
              <button
                @click="confirmCancel === order.id ? (emit('cancel', order.id), confirmCancel = null) : confirmCancel = order.id"
                class="transition-colors"
                :class="confirmCancel === order.id ? 'text-red-400 hover:text-red-300' : 'text-gray-500 hover:text-red-400'"
                :title="confirmCancel === order.id ? 'Click again to confirm cancel' : 'Cancel bid'"
              >
                <svg class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12"/>
                </svg>
              </button>
            </div>
          </td>
        </tr>
      </tbody>
    </table>
    </div>
  </div>
</template>
