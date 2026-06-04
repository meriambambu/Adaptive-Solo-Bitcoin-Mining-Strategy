<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { api } from '../api/client'

interface Settings {
  top_n: number
  max_bid_price: string
  min_bid_price: string
  upper_buffer: string
  lower_margin: string
  price_step: string
  poll_interval: number
  strategy_enabled: boolean
}

interface LogEntry {
  id: number
  timestamp: string
  order_id: string
  action: string
  old_price: string | null
  new_price: string | null
  market_p_n: string | null
  reason: string
}

const settings = ref<Settings>({
  top_n: 5,
  max_bid_price: '0.60',
  min_bid_price: '0.10',
  upper_buffer: '0.01',
  lower_margin: '0.005',
  price_step: '0.005',
  poll_interval: 60,
  strategy_enabled: true,
})
const logs = ref<LogEntry[]>([])
const saving = ref(false)
const evaluating = ref(false)
const saveMsg = ref('')
const countdown = ref(0)
let countdownTimer: ReturnType<typeof setInterval> | null = null

const actionColor: Record<string, string> = {
  RAISE: 'text-green-400',
  LOWER: 'text-yellow-400',
  HOLD: 'text-gray-500',
  IDLE: 'text-gray-600',
  ERROR: 'text-red-400',
  DISABLED: 'text-gray-600',
}

async function fetchSettings() {
  const { data } = await api.get<Settings>('/api/settings')
  settings.value = data
  resetCountdown()
}

async function fetchLogs() {
  const { data } = await api.get<LogEntry[]>('/api/strategy/logs?limit=20')
  logs.value = data
}

async function save() {
  saving.value = true
  saveMsg.value = ''
  try {
    await api.patch('/api/settings', settings.value)
    saveMsg.value = 'Saved!'
    resetCountdown()
  } catch {
    saveMsg.value = 'Error saving'
  } finally {
    saving.value = false
    setTimeout(() => (saveMsg.value = ''), 2000)
  }
}

async function evaluateNow() {
  evaluating.value = true
  try {
    await api.post('/api/strategy/evaluate')
    await fetchLogs()
    resetCountdown()
  } finally {
    evaluating.value = false
  }
}

function resetCountdown() {
  countdown.value = settings.value.poll_interval
  if (countdownTimer) clearInterval(countdownTimer)
  countdownTimer = setInterval(() => {
    if (countdown.value > 0) {
      countdown.value--
    } else {
      fetchLogs()
      resetCountdown()
    }
  }, 1000)
}

onMounted(async () => {
  await fetchSettings()
  await fetchLogs()
  setInterval(fetchLogs, 30_000)
})
</script>

<template>
  <div class="space-y-4">
    <!-- Settings card -->
    <div class="card">
      <div class="flex items-center justify-between mb-4">
        <h2 class="text-sm font-semibold text-gray-200">Strategy Settings</h2>
        <div class="flex items-center gap-3">
          <span class="text-xs text-gray-500">Next eval in <span class="font-mono text-gray-300">{{ countdown }}s</span></span>
          <label class="flex items-center gap-2 cursor-pointer">
            <span class="text-xs" :class="settings.strategy_enabled ? 'text-green-400' : 'text-gray-500'">
              {{ settings.strategy_enabled ? 'ON' : 'OFF' }}
            </span>
            <div
              class="relative w-9 h-5 rounded-full transition-colors"
              :class="settings.strategy_enabled ? 'bg-brand-purple' : 'bg-surface-500'"
              @click="settings.strategy_enabled = !settings.strategy_enabled"
            >
              <div
                class="absolute top-0.5 left-0.5 w-4 h-4 rounded-full bg-white transition-transform"
                :class="settings.strategy_enabled ? 'translate-x-4' : 'translate-x-0'"
              />
            </div>
          </label>
        </div>
      </div>

      <div class="grid grid-cols-2 gap-3 text-xs">
        <div>
          <label class="block text-gray-500 mb-1">Stay in top N bids</label>
          <input v-model.number="settings.top_n" type="number" min="1" max="20" class="input" />
        </div>
        <div>
          <label class="block text-gray-500 mb-1">Poll interval (seconds)</label>
          <input v-model.number="settings.poll_interval" type="number" min="30" class="input" />
        </div>
        <div>
          <label class="block text-gray-500 mb-1">Max bid price (BTC/EH/day)</label>
          <input v-model="settings.max_bid_price" type="number" step="0.00001" class="input" />
        </div>
        <div>
          <label class="block text-gray-500 mb-1">Min bid price (BTC/EH/day)</label>
          <input v-model="settings.min_bid_price" type="number" step="0.00001" class="input" />
        </div>
        <div>
          <label class="block text-gray-500 mb-1">Upper buffer (BTC)</label>
          <input v-model="settings.upper_buffer" type="number" step="0.001" class="input" />
        </div>
        <div>
          <label class="block text-gray-500 mb-1">Lower margin (BTC)</label>
          <input v-model="settings.lower_margin" type="number" step="0.001" class="input" />
        </div>
        <div>
          <label class="block text-gray-500 mb-1">Price step (BTC)</label>
          <input v-model="settings.price_step" type="number" step="0.001" class="input" />
        </div>
      </div>

      <div class="flex items-center gap-3 mt-4">
        <button @click="save" :disabled="saving" class="btn-primary text-xs">
          {{ saving ? 'Saving…' : 'Save Settings' }}
        </button>
        <button @click="evaluateNow" :disabled="evaluating" class="btn-ghost text-xs">
          {{ evaluating ? 'Running…' : '▶ Evaluate Now' }}
        </button>
        <span v-if="saveMsg" class="text-xs text-green-400">{{ saveMsg }}</span>
      </div>
    </div>

    <!-- Strategy log -->
    <div class="card">
      <h2 class="text-sm font-semibold text-gray-200 mb-3">Strategy Log</h2>
      <div v-if="logs.length === 0" class="text-xs text-gray-600 py-4 text-center">No log entries yet</div>
      <div v-else class="space-y-1 max-h-64 overflow-y-auto pr-1">
        <div
          v-for="log in logs"
          :key="log.id"
          class="flex items-start gap-2 text-xs py-1.5 border-b border-surface-700 last:border-0"
        >
          <span class="font-bold w-14 flex-shrink-0" :class="actionColor[log.action] || 'text-gray-400'">
            {{ log.action }}
          </span>
          <span class="text-gray-600 flex-shrink-0 font-mono">{{ log.timestamp.slice(11, 19) }}</span>
          <span class="text-gray-400 truncate">{{ log.reason }}</span>
        </div>
      </div>
    </div>
  </div>
</template>
