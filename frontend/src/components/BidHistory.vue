<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { api } from '../api/client'

interface HistoryOrder {
  id: string
  price_btc: number
  amount_btc: number
  avg_speed_ph: number
  speed_limit_ph: number
  progress_pct: number
  status: string
  created: string | null
  shares_purchased_m: number
  amount_consumed_btc: number
}

type Filter = 'ALL' | 'FULFILLED' | 'CANCELED'

const orders = ref<HistoryOrder[]>([])
const loading = ref(true)
const filter = ref<Filter>('ALL')
const copied = ref<string | null>(null)
const visibleCount = ref(5)

async function fetchHistory() {
  try {
    const { data } = await api.get<HistoryOrder[]>('/api/orders/history')
    orders.value = data
  } catch {
    // silent
  } finally {
    loading.value = false
  }
}

const filtered = computed(() => {
  if (filter.value === 'ALL') return orders.value
  return orders.value.filter(o => o.status === `BID_STATUS_${filter.value}`)
})

const visible = computed(() => filtered.value.slice(0, visibleCount.value))

function formatDate(iso: string | null): string {
  if (!iso) return '—'
  return new Date(iso).toLocaleString('en-GB', {
    month: 'short', day: '2-digit', hour: '2-digit', minute: '2-digit',
  }).toUpperCase()
}

function formatDuration(order: HistoryOrder): string {
  const speedEhs = order.avg_speed_ph / 1000
  if (!speedEhs || !order.price_btc) return '—'
  const durationMinutes = (order.amount_btc / (order.price_btc * speedEhs)) * 24 * 60
  if (durationMinutes < 1) return '< 1m'
  if (durationMinutes < 60) return `${Math.round(durationMinutes)}m`
  const hours = Math.floor(durationMinutes / 60)
  const minutes = Math.round(durationMinutes % 60)
  return minutes > 0 ? `${hours}h ${minutes}m` : `${hours}h`
}

function formatBest(sharesM: number): string {
  if (!sharesM || sharesM <= 0) return ''
  if (sharesM >= 1_000_000) return `${(sharesM / 1_000_000).toFixed(1)}T`
  if (sharesM >= 1_000) return `${(sharesM / 1_000).toFixed(1)}G`
  return `${Math.round(sharesM)}M`
}

function statusLabel(status: string): string {
  return status.replace('BID_STATUS_', '')
}

function statusClass(status: string): string {
  if (status === 'BID_STATUS_FULFILLED') return 'text-cyan-400 bg-cyan-900/30 border border-cyan-700/40'
  if (status === 'BID_STATUS_CANCELED') return 'text-gray-400 bg-surface-600 border border-surface-500'
  return 'text-gray-400 bg-surface-600 border border-surface-500'
}

async function copyId(id: string) {
  await navigator.clipboard.writeText(id)
  copied.value = id
  setTimeout(() => { copied.value = null }, 1500)
}

onMounted(fetchHistory)
</script>

<template>
  <div class="card">
    <div class="flex items-center justify-between mb-4">
      <h2 class="text-sm font-semibold text-gray-200">Bid History</h2>
      <div class="flex gap-1">
        <button
          v-for="f in (['ALL', 'FULFILLED', 'CANCELED'] as Filter[])"
          :key="f"
          @click="filter = f; visibleCount = 5"
          class="text-xs px-3 py-1 rounded font-medium transition-colors"
          :class="filter === f
            ? 'bg-brand-purple text-white'
            : 'text-gray-400 hover:text-gray-200 bg-surface-600'"
        >
          {{ f }}
        </button>
      </div>
    </div>

    <div v-if="loading" class="py-10 text-center text-gray-500 text-sm">Loading…</div>

    <div v-else-if="filtered.length === 0" class="py-10 text-center text-gray-500 text-sm">
      No history entries.
    </div>

    <div v-else class="overflow-x-auto">
    <table class="w-full text-sm whitespace-nowrap">
      <thead>
        <tr class="border-b border-surface-600">
          <th class="table-header text-left pb-2 w-40">Bid ID</th>
          <th class="table-header text-right pb-2">Price<br><span class="normal-case font-normal text-gray-600">(₿/EHs/day)</span></th>
          <th class="table-header text-right pb-2">Budget<br><span class="normal-case font-normal text-gray-600">(BTC)</span></th>
          <th class="table-header text-right pb-2">Speed<br><span class="normal-case font-normal text-gray-600">(EH/s)</span></th>
          <th class="table-header text-center pb-2">Status</th>
          <th class="table-header text-right pb-2 hidden sm:table-cell">Created</th>
          <th class="table-header text-right pb-2 hidden sm:table-cell">Duration</th>
          <th class="table-header text-right pb-2">Progress</th>
          <th class="table-header text-right pb-2">Actions</th>
        </tr>
      </thead>
      <tbody>
        <tr
          v-for="order in visible"
          :key="order.id"
          class="border-b border-surface-700 hover:bg-surface-700/30 transition-colors"
        >
          <!-- BID ID -->
          <td class="py-3 pr-4">
            <div>
              <span class="font-mono text-xs text-brand-purple-light hover:underline cursor-pointer">
                {{ order.id }}
              </span>
              <div class="flex gap-1 mt-0.5 flex-wrap">
                <span class="badge-solo">SOLO</span>
                <span v-if="formatBest(order.shares_purchased_m)" class="badge text-xs text-gray-400">
                  Shares: {{ formatBest(order.shares_purchased_m) }}
                </span>
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

          <!-- SPEED -->
          <td class="py-3 text-right font-mono text-gray-400">
            {{ order.avg_speed_ph > 0 ? (order.avg_speed_ph / 1000).toFixed(4) : '—' }}
          </td>

          <!-- STATUS -->
          <td class="py-3 text-center">
            <span class="text-xs px-2 py-0.5 rounded font-medium" :class="statusClass(order.status)">
              {{ statusLabel(order.status) }}
            </span>
          </td>

          <!-- CREATED -->
          <td class="py-3 text-right text-gray-400 text-xs hidden sm:table-cell">
            {{ formatDate(order.created) }}
          </td>

          <!-- DURATION -->
          <td class="py-3 text-right text-gray-400 text-xs font-mono hidden sm:table-cell">
            {{ formatDuration(order) }}
          </td>

          <!-- PROGRESS -->
          <td class="py-3 text-right">
            <div class="flex items-center justify-end">
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
            <button
              @click="copyId(order.id)"
              class="text-gray-500 hover:text-brand-purple-light transition-colors relative"
              :title="copied === order.id ? 'Copied!' : 'Copy bid ID'"
            >
              <svg v-if="copied !== order.id" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                <rect x="9" y="9" width="13" height="13" rx="2" ry="2"/>
                <path d="M5 15H4a2 2 0 01-2-2V4a2 2 0 012-2h9a2 2 0 012 2v1"/>
              </svg>
              <svg v-else class="h-4 w-4 text-green-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                <polyline points="20 6 9 17 4 12"/>
              </svg>
            </button>
          </td>
        </tr>
      </tbody>
    </table>
    </div>

    <div v-if="filtered.length > visibleCount" class="mt-3 text-center">
      <button @click="visibleCount += 5" class="btn-ghost text-xs">
        Show More ({{ filtered.length - visibleCount }} remaining)
      </button>
    </div>
  </div>
</template>
