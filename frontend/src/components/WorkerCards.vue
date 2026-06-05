<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { api } from '../api/client'

interface Worker {
  id: string
  name: string
  status: string
  created: string | null
  speed_now_ph: number
  speed_5m_ph: number
  speed_1h_ph: number
  speed_24h_ph: number
  shares_m: number
  price_btc: number
  progress_pct: number
}

const workers = ref<Worker[]>([])
const loading = ref(true)

function fmtHashrate(ph: number): string {
  if (ph <= 0) return '0 TH/s'
  if (ph >= 1000) return (ph / 1000).toFixed(2) + ' EH/s'
  if (ph >= 1) return ph.toFixed(2) + ' PH/s'
  if (ph >= 0.001) return (ph * 1000).toFixed(2) + ' TH/s'
  return (ph * 1_000_000).toFixed(2) + ' GH/s'
}

function fmtDate(iso: string | null): string {
  if (!iso) return '—'
  const d = new Date(iso)
  const dd = String(d.getDate()).padStart(2, '0')
  const mm = String(d.getMonth() + 1).padStart(2, '0')
  const yyyy = d.getFullYear()
  const hh = String(d.getHours()).padStart(2, '0')
  const min = String(d.getMinutes()).padStart(2, '0')
  return `${dd}.${mm}.${yyyy} ${hh}:${min}`
}

function hasHashrate(w: Worker): boolean {
  return w.speed_1h_ph > 0 || w.speed_now_ph > 0
}

async function fetchWorkers() {
  try {
    const res = await api.get<Worker[]>('/api/orders/workers')
    workers.value = res.data
  } catch {
    // silent
  } finally {
    loading.value = false
  }
}

onMounted(fetchWorkers)
setInterval(fetchWorkers, 30_000)
</script>

<template>
  <div class="card">
    <h2 class="text-sm font-semibold text-gray-200 mb-4">Active Workers</h2>

    <div v-if="loading" class="py-6 text-center text-gray-500 text-sm">Loading…</div>

    <div v-else-if="workers.length === 0" class="py-6 text-center text-gray-500 text-sm">
      No active bids found.
    </div>

    <div v-else class="grid grid-cols-1 sm:grid-cols-2 gap-3">
      <div
        v-for="worker in workers"
        :key="worker.id"
        class="rounded-lg border p-3 transition-colors"
        :class="hasHashrate(worker)
          ? 'border-surface-600 bg-surface-800'
          : 'border-surface-700 bg-surface-800/50'"
      >
        <!-- Worker name + hashrate indicator -->
        <div class="flex items-start justify-between gap-2 mb-3">
          <div
            class="text-xs font-mono font-semibold truncate"
            :class="hasHashrate(worker) ? 'text-brand-purple-light' : 'text-gray-500'"
            :title="worker.name"
          >
            {{ worker.name }}
          </div>
          <span
            class="text-[9px] font-bold px-1.5 py-0.5 rounded flex-shrink-0"
            :class="hasHashrate(worker)
              ? 'bg-green-900/50 text-green-400'
              : 'bg-surface-700 text-gray-500'"
          >
            {{ hasHashrate(worker) ? 'HR ✓' : 'No HR' }}
          </span>
        </div>

        <!-- Stats -->
        <div class="space-y-1.5 text-xs">
          <div class="flex items-center justify-between">
            <span class="text-gray-500">Status</span>
            <span class="flex items-center gap-1.5">
              <span
                class="h-2 w-2 rounded-full flex-shrink-0"
                :class="hasHashrate(worker) ? 'bg-green-500' : 'bg-gray-600'"
              ></span>
              <span :class="hasHashrate(worker) ? 'text-gray-200' : 'text-gray-500'">
                {{ worker.status }}
              </span>
            </span>
          </div>

          <div class="flex items-center justify-between">
            <span class="text-gray-500">Bid Price</span>
            <span class="font-mono text-gray-300">₿{{ worker.price_btc.toFixed(5) }}</span>
          </div>

          <div class="flex items-center justify-between">
            <span class="text-gray-500">Created</span>
            <span class="text-gray-400 font-mono">{{ fmtDate(worker.created) }}</span>
          </div>

          <div class="border-t border-surface-600/50 pt-1.5 space-y-1.5">
            <div class="flex items-center justify-between">
              <span class="text-gray-500">Hashrate (5 Min)</span>
              <span
                class="font-mono font-semibold"
                :class="worker.speed_5m_ph > 0 ? 'text-gray-200' : 'text-gray-600'"
              >{{ fmtHashrate(worker.speed_5m_ph) }}</span>
            </div>
            <div class="flex items-center justify-between">
              <span class="text-gray-500">Hashrate (1 Hour)</span>
              <span
                class="font-mono font-semibold"
                :class="worker.speed_1h_ph > 0 ? 'text-gray-200' : 'text-gray-600'"
              >{{ fmtHashrate(worker.speed_1h_ph) }}</span>
            </div>
            <div class="flex items-center justify-between">
              <span class="text-gray-500">Hashrate (24h)</span>
              <span
                class="font-mono font-semibold"
                :class="worker.speed_24h_ph > 0 ? 'text-gray-200' : 'text-gray-600'"
              >{{ fmtHashrate(worker.speed_24h_ph) }}</span>
            </div>
          </div>

          <!-- Budget progress bar -->
          <div class="pt-1">
            <div class="flex justify-between text-[10px] text-gray-600 mb-0.5">
              <span>Budget used</span>
              <span>{{ Math.round(worker.progress_pct) }}%</span>
            </div>
            <div class="h-1 rounded bg-surface-700 overflow-hidden">
              <div
                class="h-full rounded bg-brand-purple transition-all"
                :style="{ width: Math.min(100, worker.progress_pct) + '%' }"
              ></div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
