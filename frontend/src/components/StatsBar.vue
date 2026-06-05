<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { api } from '../api/client'

const balance = ref({ total_btc: 0, available_btc: 0, blocked_btc: 0 })
const loading = ref(true)

async function fetchBalance() {
  try {
    const { data } = await api.get('/api/market/balance')
    balance.value = data
  } catch {
    /* silent — backend may not be connected yet */
  } finally {
    loading.value = false
  }
}

onMounted(fetchBalance)
setInterval(fetchBalance, 60_000)
</script>

<template>
  <div class="flex flex-wrap gap-4 px-6 py-3 bg-surface-800 border-b border-surface-600">
    <div class="flex flex-col">
      <span class="text-xs text-gray-500 uppercase tracking-wider">Available Balance</span>
      <span class="text-sm font-mono text-green-400">
        {{ loading ? '...' : `₿ ${balance.available_btc.toFixed(8)}` }}
      </span>
    </div>
    <div class="flex flex-col">
      <span class="text-xs text-gray-500 uppercase tracking-wider">Total Balance</span>
      <span class="text-sm font-mono text-gray-300">
        {{ loading ? '...' : `₿ ${balance.total_btc.toFixed(8)}` }}
      </span>
    </div>
    <div class="flex flex-col">
      <span class="text-xs text-gray-500 uppercase tracking-wider">In Orders</span>
      <span class="text-sm font-mono text-yellow-400">
        {{ loading ? '...' : `₿ ${balance.blocked_btc.toFixed(8)}` }}
      </span>
    </div>
  </div>
</template>
