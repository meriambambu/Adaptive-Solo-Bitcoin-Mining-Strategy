<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { api } from '../api/client'

interface RecentBlock {
  height: number
  timestamp: number
  pool: string
}

const blocks = ref<RecentBlock[]>([])
const loading = ref(true)

function fmtTime(ts: number): string {
  const d = new Date(ts * 1000)
  const dd = String(d.getDate()).padStart(2, '0')
  const mm = String(d.getMonth() + 1).padStart(2, '0')
  const hh = String(d.getHours()).padStart(2, '0')
  const min = String(d.getMinutes()).padStart(2, '0')
  const ss = String(d.getSeconds()).padStart(2, '0')
  return `${dd}/${mm} ${hh}:${min}:${ss}`
}

async function fetchBlocks() {
  try {
    const res = await api.get<{ blocks: RecentBlock[] }>('/api/pool/blocks')
    blocks.value = res.data.blocks || []
  } catch {
    // silent
  } finally {
    loading.value = false
  }
}

onMounted(fetchBlocks)
setInterval(fetchBlocks, 60_000)
</script>

<template>
  <div class="card">
    <div class="flex items-center justify-between mb-3">
      <h2 class="text-sm font-semibold text-gray-200">Recent Blocks</h2>
    </div>

    <div v-if="loading" class="py-4 text-center text-gray-500 text-xs">Loading…</div>

    <div v-else-if="blocks.length === 0" class="py-4 text-center text-gray-500 text-xs">
      No recent blocks.
    </div>

    <div v-else class="space-y-1 max-h-72 overflow-y-auto">
      <!-- Column headers -->
      <div class="grid grid-cols-12 gap-1 px-2 pb-1">
        <span class="col-span-4 table-header">Time</span>
        <span class="col-span-4 table-header">Pool</span>
        <span class="col-span-4 table-header text-right">Height</span>
      </div>

      <div
        v-for="block in blocks"
        :key="block.height"
        class="grid grid-cols-12 gap-1 px-2 py-1 rounded text-xs transition-colors bg-surface-700/20 border border-surface-600/20"
      >
        <!-- Time -->
        <span class="col-span-4 font-mono text-gray-500">{{ fmtTime(block.timestamp) }}</span>

        <!-- Pool -->
        <span class="col-span-4 font-mono text-gray-400 truncate" :title="block.pool">{{ block.pool }}</span>

        <!-- Height -->
        <span class="col-span-4 text-right font-mono font-semibold text-orange-400">{{ block.height.toLocaleString() }}</span>
      </div>
    </div>
  </div>
</template>
