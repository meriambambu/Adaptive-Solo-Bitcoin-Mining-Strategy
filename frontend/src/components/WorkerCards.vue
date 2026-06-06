<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { api } from '../api/client'

interface PoolWorker {
  name: string
  source: 'pool'
  lastshare_ts: number
  speed_now_ph: number
  speed_5m_ph: number
  speed_1h_ph: number
  speed_24h_ph: number
  shares_m: number
  bestshare: number
}

interface WorkerCard {
  key: string
  name: string
  lastshare_ts?: number
  bestshare?: number
  speed_now_ph: number
  speed_5m_ph: number
  speed_1h_ph: number
  speed_24h_ph: number
  shares_m: number
  hasHashrate: boolean
}

const cards = ref<WorkerCard[]>([])
const loading = ref(true)

function fmtHashrate(ph: number): string {
  if (ph <= 0) return '0 TH/s'
  if (ph >= 1000) return (ph / 1000).toFixed(2) + ' EH/s'
  if (ph >= 1) return ph.toFixed(2) + ' PH/s'
  if (ph >= 0.001) return (ph * 1000).toFixed(2) + ' TH/s'
  return (ph * 1_000_000).toFixed(2) + ' GH/s'
}

function fmtUnixTime(ts: number | undefined): string {
  if (!ts) return '—'
  const d = new Date(ts * 1000)
  return `${String(d.getDate()).padStart(2,'0')}.${String(d.getMonth()+1).padStart(2,'0')}.${d.getFullYear()} ${String(d.getHours()).padStart(2,'0')}:${String(d.getMinutes()).padStart(2,'0')}`
}

async function fetchAll() {
  try {
    const res = await api.get<PoolWorker[]>('/api/pool/workers')
    cards.value = res.data.map(w => ({
      key: `pool-${w.name}`,
      name: w.name,
      lastshare_ts: w.lastshare_ts,
      bestshare: w.bestshare,
      speed_now_ph: w.speed_now_ph,
      speed_5m_ph: w.speed_5m_ph,
      speed_1h_ph: w.speed_1h_ph,
      speed_24h_ph: w.speed_24h_ph,
      shares_m: w.shares_m,
      hasHashrate: w.speed_1h_ph > 0,
    }))
  } catch {
    // silent
  } finally {
    loading.value = false
  }
}

onMounted(fetchAll)
setInterval(fetchAll, 30_000)
</script>

<template>
  <div class="card">
    <h2 class="text-sm font-semibold text-gray-200 mb-4">Active Workers</h2>

    <div v-if="loading" class="py-6 text-center text-gray-500 text-sm">Loading…</div>

    <div v-else-if="cards.length === 0" class="py-6 text-center text-gray-500 text-sm">
      No solo pool workers with active hashrate.
    </div>

    <div v-else class="grid grid-cols-1 sm:grid-cols-2 gap-3">
      <div
        v-for="worker in cards"
        :key="worker.key"
        class="rounded-lg border p-3 transition-colors"
        :class="worker.hasHashrate
          ? 'border-surface-600 bg-surface-800'
          : 'border-surface-700 bg-surface-800/50'"
      >
        <!-- Name + badge row -->
        <div class="flex items-start justify-between gap-2 mb-3">
          <div
            class="text-xs font-mono font-semibold truncate"
            :class="worker.hasHashrate ? 'text-brand-purple-light' : 'text-gray-500'"
            :title="worker.name"
          >
            {{ worker.name.includes('.') ? worker.name.split('.').slice(1).join('.') : worker.name }}
          </div>
          <div class="flex items-center gap-1 flex-shrink-0">
            <span class="text-[9px] px-1.5 py-0.5 rounded font-bold bg-blue-900/50 text-blue-400">Solo</span>
            <span class="text-[9px] font-bold px-1.5 py-0.5 rounded"
              :class="worker.hasHashrate
                ? 'bg-green-900/50 text-green-400'
                : 'bg-surface-700 text-gray-500'">
              {{ worker.hasHashrate ? 'HR ✓' : 'No HR' }}
            </span>
          </div>
        </div>

        <!-- Stats -->
        <div class="space-y-1.5 text-xs">
          <div class="flex items-center justify-between">
            <span class="text-gray-500">Status</span>
            <span class="flex items-center gap-1.5">
              <span class="h-2 w-2 rounded-full bg-green-500 flex-shrink-0"></span>
              <span class="text-gray-200">Active</span>
            </span>
          </div>
          <div class="flex items-center justify-between">
            <span class="text-gray-500">Last Share</span>
            <span class="text-gray-400 font-mono">{{ fmtUnixTime(worker.lastshare_ts) }}</span>
          </div>

          <!-- Hashrate rows -->
          <div class="border-t border-surface-600/50 pt-1.5 space-y-1.5">
            <div class="flex items-center justify-between">
              <span class="text-gray-500">Hashrate (5 Min)</span>
              <span class="font-mono font-semibold"
                :class="worker.speed_5m_ph > 0 ? 'text-gray-200' : 'text-gray-600'">
                {{ fmtHashrate(worker.speed_5m_ph) }}
              </span>
            </div>
            <div class="flex items-center justify-between">
              <span class="text-gray-500">Hashrate (1 Hour)</span>
              <span class="font-mono font-semibold"
                :class="worker.speed_1h_ph > 0 ? 'text-gray-200' : 'text-gray-600'">
                {{ fmtHashrate(worker.speed_1h_ph) }}
              </span>
            </div>
            <div class="flex items-center justify-between">
              <span class="text-gray-500">Hashrate (24h)</span>
              <span class="font-mono font-semibold"
                :class="worker.speed_24h_ph > 0 ? 'text-gray-200' : 'text-gray-600'">
                {{ fmtHashrate(worker.speed_24h_ph) }}
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
