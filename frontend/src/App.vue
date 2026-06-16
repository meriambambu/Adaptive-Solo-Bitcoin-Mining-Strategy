<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'
import StatsBar from './components/StatsBar.vue'
import BidsTable from './components/BidsTable.vue'
import BidHistory from './components/BidHistory.vue'
import WorkerCards from './components/WorkerCards.vue'
import NotableShares from './components/NotableShares.vue'
import RecentBlocks from './components/RecentBlocks.vue'
import CreateBidModal from './components/CreateBidModal.vue'
import MarketOverview from './components/MarketOverview.vue'
import StrategyPanel from './components/StrategyPanel.vue'
import { useBids } from './composables/useBids'
import { useWebSocket } from './composables/useWebSocket'
import { api } from './api/client'
import type { Order } from './composables/useBids'

const { orders, loading, fetchOrders, cancelOrder } = useBids()
const showCreate = ref(false)
const editOrder = ref<Order | null>(null)
const marketOverview = ref<InstanceType<typeof MarketOverview> | null>(null)

// ── BTC difficulty ──────────────────────────────────────────────────────────
const btcDifficulty = ref(0)

function fmtDifficulty(d: number): string {
  if (d <= 0) return '…'
  if (d >= 1e15) return (d / 1e15).toFixed(2) + 'P'
  if (d >= 1e12) return (d / 1e12).toFixed(2) + 'T'
  if (d >= 1e9)  return (d / 1e9).toFixed(2) + 'G'
  return d.toLocaleString()
}

async function fetchDifficulty() {
  try {
    const res = await api.get<{ difficulty: number }>('/api/pool/difficulty')
    btcDifficulty.value = res.data.difficulty
  } catch { /* silent */ }
}

// ── Block detection & victory music ────────────────────────────────────────
const blockFound = ref(false)
const lastBestShare = ref<number | null>(null)

// Synthesise an approximation of "We Are the Champions" opening chorus
function playChampions() {
  try {
    const audio = new Audio('/champions.mp3')
    audio.volume = 0.8
    audio.play().catch(() => synthesiseVictory())  // fallback if file missing
  } catch {
    synthesiseVictory()
  }
}

function synthesiseVictory() {
  const ctx = new AudioContext()
  const master = ctx.createGain()
  master.gain.value = 0.4
  master.connect(ctx.destination)

  // "We Are the Champions" chorus — approximate notes in C major
  const notes: [number, number, number][] = [
    // freq Hz, start s, duration s
    [392.00, 0.00, 0.28],  // G4  "We"
    [392.00, 0.32, 0.28],  // G4  "are"
    [329.63, 0.64, 0.18],  // E4  "the"
    [293.66, 0.86, 0.22],  // D4  "cham-"
    [261.63, 1.12, 0.72],  // C4  "-pions"
    [261.63, 2.00, 0.22],  // C4  "my"
    [293.66, 2.26, 0.64],  // D4  "friends"
    [329.63, 3.10, 0.18],  // E4  "and"
    [293.66, 3.32, 0.18],  // D4  "we'll"
    [261.63, 3.54, 0.18],  // C4  "keep"
    [246.94, 3.76, 0.18],  // B3  "on"
    [220.00, 3.98, 0.64],  // A3  "fight-ing"
    [261.63, 4.80, 0.18],  // C4  "till"
    [293.66, 5.02, 0.18],  // D4  "the"
    [329.63, 5.24, 0.68],  // E4  "end"
    [392.00, 6.10, 0.18],  // G4
    [392.00, 6.32, 0.18],  // G4
    [523.25, 6.56, 1.20],  // C5  (final high note)
  ]

  for (const [freq, start, dur] of notes) {
    const osc = ctx.createOscillator()
    const gain = ctx.createGain()
    osc.type = 'triangle'
    osc.frequency.value = freq
    gain.gain.setValueAtTime(0, ctx.currentTime + start)
    gain.gain.linearRampToValueAtTime(1, ctx.currentTime + start + 0.02)
    gain.gain.setValueAtTime(1, ctx.currentTime + start + dur - 0.04)
    gain.gain.linearRampToValueAtTime(0, ctx.currentTime + start + dur)
    osc.connect(gain)
    gain.connect(master)
    osc.start(ctx.currentTime + start)
    osc.stop(ctx.currentTime + start + dur + 0.05)
  }
}

function checkForBlock(bestshare: number) {
  if (btcDifficulty.value <= 0 || bestshare <= 0) return

  const prev = lastBestShare.value
  lastBestShare.value = bestshare

  // Only fire when bestshare is newly at or above network difficulty
  if (bestshare >= btcDifficulty.value && (prev === null || prev < btcDifficulty.value)) {
    blockFound.value = true
    playChampions()
  }
}

async function fetchPoolStats() {
  try {
    const res = await api.get<{ bestshare: number }>('/api/pool/stats')
    checkForBlock(res.data.bestshare)
  } catch { /* silent */ }
}

// ── WebSocket ───────────────────────────────────────────────────────────────
const { connected } = useWebSocket((msg: unknown) => {
  const payload = msg as { type: string }
  if (payload.type === 'strategy_update') {
    fetchOrders()
    marketOverview.value?.fetchBook()
  }
})

onMounted(() => {
  fetchOrders()
  fetchDifficulty()
  fetchPoolStats()
})

// Difficulty auto-refresh every 5 min (covers any adjustment that occurs)
setInterval(fetchDifficulty, 300_000)
// Pool stats (block detection) every 60 s
setInterval(fetchPoolStats, 60_000)

async function handleCancel(id: string) { await cancelOrder(id) }

function handleEdit(order: Order) {
  editOrder.value = order
  showCreate.value = true
}
</script>

<template>
  <div class="min-h-screen bg-surface-900 text-gray-100">

    <!-- ── Victory overlay ──────────────────────────────────────────────── -->
    <Transition name="fade">
      <div
        v-if="blockFound"
        class="fixed inset-0 z-50 flex flex-col items-center justify-center bg-black/80 backdrop-blur-sm"
        @click="blockFound = false"
      >
        <div class="text-center px-8 animate-bounce">
          <div class="text-7xl mb-4">🏆</div>
          <div class="text-4xl font-black text-yellow-400 tracking-wide mb-2">BLOCK FOUND!</div>
          <div class="text-xl text-yellow-300 font-bold mb-6">We Are The Champions!</div>
          <div class="text-sm text-gray-400">Click anywhere to dismiss</div>
        </div>
      </div>
    </Transition>

    <!-- ── Top nav ──────────────────────────────────────────────────────── -->
    <header class="flex items-center justify-between px-6 py-3 bg-surface-800 border-b border-surface-600">
      <div class="flex items-center gap-3">
        <svg class="h-6 w-6 text-brand-purple" fill="currentColor" viewBox="0 0 24 24">
          <path d="M23.638 14.904c-1.602 6.43-8.113 10.34-14.542 8.736C2.67 22.05-1.244 15.525.362 9.105 1.962 2.67 8.475-1.243 14.9.358c6.43 1.605 10.342 8.115 8.738 14.546zM14.772 8.3c.24-1.607-.983-2.468-2.655-3.044l.542-2.174-1.323-.33-.528 2.117c-.347-.087-.705-.17-1.06-.251l.532-2.13-1.322-.33-.543 2.173c-.288-.066-.57-.13-.842-.198l.001-.007-1.824-.456-.352 1.413s.983.225.963.239c.537.134.634.49.617.772l-1.486 5.962c-.113.281-.4.703-1.048.543.023.033-.963-.24-.963-.24L4.4 13.2l1.72.43c.32.08.634.163.943.242l-.549 2.2 1.322.33.543-2.175c.36.098.71.188 1.053.273l-.541 2.165 1.322.33.549-2.195c2.263.428 3.965.255 4.679-1.792.577-1.651-.029-2.604-1.222-3.226.87-.2 1.525-.772 1.699-1.952l.003.002zm-3.044 4.267c-.41 1.651-3.183.759-4.083.535l.729-2.92c.9.225 3.787.67 3.354 2.385zm.41-4.29c-.374 1.5-2.685.737-3.437.551l.661-2.648c.752.188 3.175.538 2.776 2.097z"/>
        </svg>
        <span class="font-bold text-sm tracking-tight">Adaptive Bitcoin Mining</span>
      </div>

      <div class="flex items-center gap-4 text-xs">
        <!-- BTC Difficulty (hidden on xs screens) -->
        <div class="hidden sm:flex items-center gap-1.5 text-gray-400">
          <span class="text-gray-600">Difficulty</span>
          <span class="font-mono font-semibold text-amber-400">{{ fmtDifficulty(btcDifficulty) }}</span>
        </div>

        <!-- Live indicator -->
        <div class="flex items-center gap-2">
          <span
            class="h-2 w-2 rounded-full"
            :class="connected ? 'bg-green-500' : 'bg-red-500 animate-pulse'"
          />
          <span :class="connected ? 'text-green-400' : 'text-red-400'">
            {{ connected ? 'Live' : 'Connecting…' }}
          </span>
        </div>
      </div>
    </header>

    <!-- Balance bar -->
    <StatsBar />

    <!-- Main content -->
    <main class="max-w-7xl mx-auto px-4 py-6 grid grid-cols-1 xl:grid-cols-3 gap-6">
      <!-- Left: bids table + workers + history -->
      <div class="xl:col-span-2 space-y-6">
        <BidsTable
          :orders="orders"
          :loading="loading"
          @cancel="handleCancel"
          @edit="handleEdit"
          @create="showCreate = true"
        />
        <WorkerCards />
        <BidHistory />
      </div>

      <!-- Right: market → notable shares → strategy -->
      <div class="space-y-6">
        <NotableShares :btc-difficulty="btcDifficulty" />
        <RecentBlocks />
        <MarketOverview ref="marketOverview" :my-bid-price-sat="orders.map(o => Math.round(o.price_sat))" />
        <StrategyPanel />
      </div>
    </main>

    <!-- Create / Edit modal -->
    <CreateBidModal
      v-if="showCreate"
      @close="showCreate = false; editOrder = null"
      @created="fetchOrders"
    />
  </div>
</template>

<style scoped>
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.4s ease;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
