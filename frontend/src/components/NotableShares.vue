<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { api } from '../api/client'

interface NotableShare {
  timestamp: number
  diff: number
  worker: string
  hashrate5m: number
}

const props = defineProps<{ btcDifficulty: number }>()

const shares = ref<NotableShare[]>([])
const bestshare = ref(0)
const bestever = ref(0)
const loading = ref(true)

function fmtDiff(d: number): string {
  if (d >= 1e12) return (d / 1e12).toFixed(2) + 'T'
  if (d >= 1e9) return (d / 1e9).toFixed(2) + 'B'
  if (d >= 1e6) return (d / 1e6).toFixed(2) + 'M'
  return d.toLocaleString()
}

function fmtHashrate(raw: number): string {
  // solo.braiins.com returns raw hashes/s
  if (raw <= 0) return '—'
  if (raw >= 1e18) return (raw / 1e18).toFixed(2) + ' EH/s'
  if (raw >= 1e15) return (raw / 1e15).toFixed(2) + ' PH/s'
  if (raw >= 1e12) return (raw / 1e12).toFixed(2) + ' TH/s'
  if (raw >= 1e9)  return (raw / 1e9).toFixed(2) + ' GH/s'
  return raw.toFixed(0) + ' H/s'
}

function fmtTime(ts: number): string {
  const d = new Date(ts * 1000)
  const dd = String(d.getDate()).padStart(2, '0')
  const mm = String(d.getMonth() + 1).padStart(2, '0')
  const hh = String(d.getHours()).padStart(2, '0')
  const min = String(d.getMinutes()).padStart(2, '0')
  const ss = String(d.getSeconds()).padStart(2, '0')
  return `${dd}/${mm} ${hh}:${min}:${ss}`
}

function isBlock(diff: number): boolean {
  return props.btcDifficulty > 0 && diff >= props.btcDifficulty
}

// Returns a 0-100 progress relative to current difficulty
function diffProgress(diff: number): number {
  if (!props.btcDifficulty) return 0
  return Math.min(100, (diff / props.btcDifficulty) * 100)
}

async function fetchStats() {
  try {
    const res = await api.get<{
      notable_shares: NotableShare[]
      bestshare: number
      bestever: number
    }>('/api/pool/stats')
    // Sort newest first
    shares.value = [...(res.data.notable_shares || [])].sort((a, b) => b.timestamp - a.timestamp)
    bestshare.value = res.data.bestshare
    bestever.value = res.data.bestever
  } catch {
    // silent
  } finally {
    loading.value = false
  }
}

onMounted(fetchStats)
setInterval(fetchStats, 60_000)
</script>

<template>
  <div class="card">
    <div class="flex items-center justify-between mb-3">
      <h2 class="text-sm font-semibold text-gray-200">Notable Shares</h2>
      <div class="text-xs text-gray-500 font-mono">
        Best: <span class="text-yellow-400">{{ fmtDiff(bestever) }}</span>
      </div>
    </div>

    <div v-if="loading" class="py-4 text-center text-gray-500 text-xs">Loading…</div>

    <div v-else-if="shares.length === 0" class="py-4 text-center text-gray-500 text-xs">
      No notable shares yet.
    </div>

    <div v-else class="space-y-1 max-h-72 overflow-y-auto">
      <!-- Column headers -->
      <div class="grid grid-cols-12 gap-1 px-2 pb-1">
        <span class="col-span-4 table-header">Time</span>
        <span class="col-span-4 table-header">Worker</span>
        <span class="col-span-4 table-header text-right">Difficulty</span>
      </div>

      <div
        v-for="share in shares"
        :key="share.timestamp + share.diff"
        class="grid grid-cols-12 gap-1 px-2 py-1 rounded text-xs transition-colors"
        :class="isBlock(share.diff)
          ? 'bg-yellow-900/40 border border-yellow-500/60'
          : 'bg-surface-700/20 border border-surface-600/20'"
      >
        <!-- Time -->
        <span class="col-span-4 font-mono text-gray-500">{{ fmtTime(share.timestamp) }}</span>

        <!-- Worker — show only the part after the first dot (strips wallet address) -->
        <span class="col-span-4 font-mono truncate" :class="isBlock(share.diff) ? 'text-yellow-300' : 'text-gray-400'"
              :title="share.worker">{{ share.worker.includes('.') ? share.worker.split('.').slice(1).join('.') : share.worker }}</span>

        <!-- Difficulty + progress bar -->
        <div class="col-span-4 text-right">
          <div class="flex items-center justify-end gap-1">
            <span
              class="font-mono font-semibold"
              :class="isBlock(share.diff) ? 'text-yellow-300' : 'text-orange-400'"
            >{{ fmtDiff(share.diff) }}</span>
            <span v-if="isBlock(share.diff)" class="text-[9px] font-bold text-yellow-300 bg-yellow-900 px-1 rounded">BLOCK!</span>
          </div>
          <!-- Progress bar: share diff vs current BTC difficulty -->
          <div v-if="btcDifficulty > 0" class="mt-0.5 h-0.5 rounded bg-surface-600 overflow-hidden">
            <div
              class="h-full rounded transition-all"
              :class="isBlock(share.diff) ? 'bg-yellow-400' : 'bg-orange-600'"
              :style="{ width: diffProgress(share.diff) + '%' }"
            ></div>
          </div>
        </div>
      </div>
    </div>

    <!-- Best share vs difficulty footer -->
    <div v-if="btcDifficulty > 0 && !loading" class="mt-3 pt-2 border-t border-surface-600/40 text-[10px] text-gray-600 flex justify-between">
      <span>Network difficulty: <span class="font-mono text-gray-500">{{ fmtDiff(btcDifficulty) }}</span></span>
      <span>Best ever: <span class="font-mono text-gray-500">{{ (diffProgress(bestever)).toFixed(2) }}% of diff</span></span>
    </div>
  </div>
</template>
