<script setup lang="ts">
import { ref } from 'vue'
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

function formatDate(ts: number | null): string {
  if (!ts) return '—'
  return new Date(ts).toLocaleString('en-GB', {
    month: 'short', day: '2-digit', hour: '2-digit', minute: '2-digit',
  }).toUpperCase()
}

function formatEta(seconds: number | null): string {
  if (!seconds || seconds <= 0) return 'N/A'
  const h = Math.floor(seconds / 3600)
  const m = Math.floor((seconds % 3600) / 60)
  return h > 0 ? `${h}h ${m}m` : `${m}m`
}

function progress(order: Order): number {
  const paid = Number(order.payedAmount)
  const total = Number(order.amount)
  if (!total) return 0
  return Math.min(100, Math.round((paid / total) * 100))
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

    <table v-else class="w-full text-sm">
      <thead>
        <tr class="border-b border-surface-600">
          <th class="table-header text-left pb-2 w-40">Bid ID</th>
          <th class="table-header text-right pb-2">Price<br><span class="normal-case font-normal text-gray-600">(₿/EHs/day)</span></th>
          <th class="table-header text-right pb-2">Budget<br><span class="normal-case font-normal text-gray-600">(BTC)</span></th>
          <th class="table-header text-right pb-2">Limit/Speed<br><span class="normal-case font-normal text-gray-600">(EH/s)</span></th>
          <th class="table-header text-right pb-2">Created</th>
          <th class="table-header text-right pb-2">ETA</th>
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
                :class="order.status === 'ACTIVE' ? 'bg-green-500' : 'bg-gray-600'"
              />
              <div>
                <span class="font-mono text-xs text-brand-purple-light hover:underline cursor-pointer">
                  {{ order.id.slice(0, 16) }}…
                </span>
                <div class="flex gap-1 mt-0.5">
                  <span v-if="order.meta?.isSolo" class="badge-solo">SOLO</span>
                </div>
              </div>
            </div>
          </td>

          <!-- PRICE -->
          <td class="py-3 text-right font-mono text-gray-200">
            ₿{{ Number(order.price).toFixed(5) }}
          </td>

          <!-- BUDGET -->
          <td class="py-3 text-right font-mono text-gray-200">
            ₿{{ Number(order.amount).toFixed(8) }}
          </td>

          <!-- LIMIT / SPEED -->
          <td class="py-3 text-right font-mono text-gray-400">
            {{ Number(order.limit).toFixed(4) }} /
            <span class="text-gray-200">{{ Number(order.acceptedSpeed).toFixed(4) }}</span>
          </td>

          <!-- CREATED -->
          <td class="py-3 text-right text-gray-400 text-xs">
            {{ formatDate(order.createdTs) }}
          </td>

          <!-- ETA -->
          <td class="py-3 text-right text-gray-400 text-xs">
            {{ formatEta(order.estimatedDurationInSeconds) }}
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
                    :stroke-dashoffset="69.1 * (1 - progress(order) / 100)"
                    stroke-linecap="round"
                  />
                </svg>
                <span class="absolute inset-0 flex items-center justify-center text-[9px] font-bold text-gray-300">
                  {{ progress(order) }}%
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
</template>
