<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { api } from '../api/client'
import { api as settingsApi } from '../api/client'

interface BookEntry {
  price_btc: number
  price_sat: number
  hr_matched_ph: number
  speed_limit_ph: number
}

const props = defineProps<{ myOrderIds?: string[] }>()

const entries = ref<BookEntry[]>([])
const topN = ref(5)
const loading = ref(true)

async function fetchBook() {
  try {
    const [bookRes, settingsRes] = await Promise.all([
      api.get<{ bids: BookEntry[] }>('/api/market/orderbook'),
      settingsApi.get<{ top_n: number }>('/api/settings'),
    ])
    entries.value = (bookRes.data.bids || [])
    topN.value = settingsRes.data.top_n
  } catch {
    // silent
  } finally {
    loading.value = false
  }
}

const pN = computed(() => {
  if (entries.value.length >= topN.value) return entries.value[topN.value - 1].price_btc
  return entries.value.at(-1)?.price_btc ?? null
})

onMounted(fetchBook)
setInterval(fetchBook, 30_000)
</script>

<template>
  <div class="card">
    <div class="flex items-center justify-between mb-3">
      <h2 class="text-sm font-semibold text-gray-200">Order Book</h2>
      <div class="text-xs text-gray-500">
        P<sub>{{ topN }}</sub> =
        <span class="text-green-400 font-mono">{{ pN !== null ? `₿${pN.toFixed(5)}` : '—' }}</span>
      </div>
    </div>

    <div v-if="loading" class="py-6 text-center text-gray-500 text-sm">Loading…</div>

    <div v-else>
      <div class="grid grid-cols-3 gap-1 mb-1 px-2">
        <span class="table-header">Rank</span>
        <span class="table-header text-right">Price (₿/EH/day)</span>
        <span class="table-header text-right">Speed (EH/s)</span>
      </div>
      <div
        v-for="(entry, i) in entries.slice(0, 20)"
        :key="i"
        class="grid grid-cols-3 gap-1 px-2 py-1 rounded text-xs transition-colors"
        :class="{
          'bg-green-900/20 border border-green-800/30': i < topN,
          'bg-surface-700/30': i >= topN,
        }"
      >
        <span class="text-gray-500 font-mono">
          <span v-if="i < topN" class="text-green-500">#{{ i + 1 }}</span>
          <span v-else class="text-gray-600">#{{ i + 1 }}</span>
        </span>
        <span class="text-right font-mono" :class="i < topN ? 'text-green-300' : 'text-gray-400'">
          {{ entry.price_btc.toFixed(5) }}
        </span>
        <span class="text-right font-mono text-gray-500">{{ entry.hr_matched_ph.toFixed(2) }} PH/s</span>
      </div>
    </div>
  </div>
</template>
