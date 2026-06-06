<script setup lang="ts">
import { ref, onMounted, computed, nextTick } from 'vue'
import { api } from '../api/client'

const SAT = 100_000_000

interface BidEntry {
  price_btc: number
  price_sat: number
  amount_sat: number
  hr_matched_ph: number
  speed_limit_ph: number
}

interface AskEntry {
  price_btc: number
  price_sat: number
  hr_matched_ph: number
  hr_available_ph: number
}

const props = defineProps<{ myBidPriceSat?: number[] }>()

const bids = ref<BidEntry[]>([])
const asks = ref<AskEntry[]>([])
const topN = ref(5)
const lastPrice = ref<number | null>(null)
const loading = ref(true)
const myBidRow = ref<HTMLElement | null>(null)

function isMyBid(entry: BidEntry): boolean {
  return (props.myBidPriceSat ?? []).includes(Math.round(entry.price_sat))
}

async function fetchBook() {
  try {
    const [bookRes, settingsRes, statsRes] = await Promise.all([
      api.get<{ bids: BidEntry[]; asks: AskEntry[] }>('/api/market/orderbook'),
      api.get<{ top_n: number }>('/api/settings'),
      api.get<{ last_avg_price_btc: number }>('/api/market/stats').catch(() => null),
    ])
    bids.value = bookRes.data.bids || []
    asks.value = bookRes.data.asks || []
    topN.value = settingsRes.data.top_n
    lastPrice.value = statsRes?.data?.last_avg_price_btc ?? null
  } catch {
    // silent
  } finally {
    loading.value = false
  }
  await nextTick()
  myBidRow.value?.scrollIntoView({ block: 'nearest', behavior: 'instant' })
}

// P_N = Nth cheapest bid (ascending from backend) — shown in header only
const pN = computed((): number | null => {
  if (bids.value.length >= topN.value) return bids.value[topN.value - 1].price_btc
  return bids.value.at(-1)?.price_btc ?? null
})

// Full depth, highest bid first (Braiins order)
const displayBids = computed(() => [...bids.value].reverse())

// Full depth, cheapest ask first
const displayAsks = computed(() => [...asks.value])

const spread = computed((): number | null => {
  const bestBid = bids.value.at(-1)?.price_btc ?? null
  const bestAsk = asks.value[0]?.price_btc ?? null
  if (bestBid === null || bestAsk === null) return null
  return Math.max(0, bestAsk - bestBid)
})

function fmtSpeed(ph: number): string {
  if (ph >= 1000) return (ph / 1000).toFixed(2) + ' EH/s'
  if (ph >= 1) return ph.toFixed(2) + ' PH/s'
  if (ph >= 0.001) return (ph * 1000).toFixed(1) + ' TH/s'
  if (ph > 0) return (ph * 1_000_000).toFixed(0) + ' GH/s'
  return '0 TH/s'
}

// Bids "Limit" = budget (amount) in BTC — what Braiins shows, not the speed cap
function fmtBudget(sat: number): string {
  if (sat <= 0) return '—'
  const btc = sat / SAT
  if (btc >= 0.01) return `₿${btc.toFixed(4)}`
  if (btc >= 0.001) return `₿${btc.toFixed(5)}`
  return `₿${btc.toFixed(6)}`
}

function fmtEta(entry: BidEntry): string {
  if (entry.hr_matched_ph <= 0 || entry.price_sat <= 0) return '—'
  // price in BTC/EH/day; matched in PH/s → EH/s = /1000
  const dailyCostBtc = (entry.price_sat / SAT) * (entry.hr_matched_ph / 1000)
  if (dailyCostBtc <= 0) return '—'
  const hours = (entry.amount_sat / SAT / dailyCostBtc) * 24
  if (!isFinite(hours) || hours > 30 * 24) return '> 30d'
  const d = Math.floor(hours / 24)
  const h = Math.floor(hours % 24)
  if (d === 0) return `${h}h`
  if (h === 0) return `${d}d`
  return `${d}d ${h}h`
}

onMounted(fetchBook)
setInterval(fetchBook, 30_000)
defineExpose({ fetchBook })
</script>

<template>
  <div class="card">

    <!-- ── Header ── -->
    <div class="flex items-center justify-between mb-2">
      <h2 class="text-sm font-semibold text-gray-200">
        Order Book
        <span class="text-gray-600 font-normal text-[10px] ml-1">(₿/EHs/day)</span>
      </h2>
      <div class="text-xs text-gray-500">
        P<sub>{{ topN }}</sub> =
        <span class="text-green-400 font-mono">{{ pN !== null ? `₿${pN.toFixed(5)}` : '—' }}</span>
      </div>
    </div>

    <!-- ── Last Price ── -->
    <div class="flex items-center justify-between px-2 py-1 mb-2 rounded text-xs"
         style="background:rgb(20 20 30 / 0.7)">
      <span class="text-gray-500">Last Price</span>
      <span class="font-mono font-semibold"
            :class="lastPrice ? 'text-gray-100' : 'text-gray-600'">
        {{ lastPrice ? `₿${lastPrice.toFixed(5)}` : 'N/A' }}
      </span>
    </div>

    <div v-if="loading" class="py-6 text-center text-gray-500 text-sm">Loading…</div>

    <div v-else class="max-h-[34rem] overflow-y-auto">

      <!-- ══ BIDS (green) ════════════════════════════════════════════════════ -->
      <div class="mb-1">
        <!-- Column headers -->
        <div class="grid gap-x-1 px-2 pb-1 text-[10px]"
             style="grid-template-columns: 1.6fr 1fr 1.3fr 0.9fr">
          <span class="table-header" style="color:rgb(74 222 128 / 0.65)">Price</span>
          <span class="table-header text-right" style="color:rgb(74 222 128 / 0.65)">Limit</span>
          <span class="table-header text-right" style="color:rgb(74 222 128 / 0.65)">Current</span>
          <span class="table-header text-right" style="color:rgb(74 222 128 / 0.65)">ETA</span>
        </div>

        <div
          v-for="(entry, i) in displayBids"
          :key="'b' + i"
          :ref="(el) => { if (isMyBid(entry) && el) myBidRow = el as HTMLElement }"
          class="grid gap-x-1 px-2 py-0.5 rounded text-xs mb-px transition-colors"
          style="grid-template-columns: 1.6fr 1fr 1.3fr 0.9fr"
          :class="isMyBid(entry)
            ? 'ring-1 ring-brand-purple bg-brand-purple/10'
            : 'bg-green-900/15 border border-green-900/20 hover:bg-green-900/25'"
        >
          <!-- Price -->
          <span class="font-mono flex items-center gap-1 min-w-0">
            <span :class="isMyBid(entry) ? 'text-brand-purple-light' : 'text-green-400'">
              {{ entry.price_btc.toFixed(5) }}
            </span>
            <span v-if="isMyBid(entry)"
                  class="text-brand-purple-light text-[8px] font-bold flex-shrink-0">
              YOU
            </span>
          </span>
          <!-- Limit = order budget in BTC (what Braiins shows, not the speed cap) -->
          <span class="text-right font-mono"
                :class="isMyBid(entry) ? 'text-brand-purple-light/70' : 'text-green-400/55'">
            {{ fmtBudget(entry.amount_sat) }}
          </span>
          <!-- Current matched hashrate — always show value, 0 TH/s when unmatched -->
          <span class="text-right font-mono whitespace-nowrap overflow-hidden"
                :class="isMyBid(entry) ? 'text-brand-purple-light/70' : entry.hr_matched_ph > 0 ? 'text-green-400/70' : 'text-green-400/35'">
            {{ fmtSpeed(entry.hr_matched_ph) }}
          </span>
          <!-- ETA based on budget / burn rate -->
          <span class="text-right font-mono whitespace-nowrap overflow-hidden"
                :class="isMyBid(entry) ? 'text-brand-purple-light/60' : 'text-green-400/45'">
            {{ fmtEta(entry) }}
          </span>
        </div>
      </div>

      <!-- ══ SPREAD ══════════════════════════════════════════════════════════ -->
      <div class="flex items-center gap-2 px-2 py-1 my-1 text-[10px]"
           style="border-top:1px solid rgb(55 65 81 / 0.4);
                  border-bottom:1px solid rgb(55 65 81 / 0.4);
                  background:rgb(10 15 25 / 0.5)">
        <span class="text-gray-600 uppercase tracking-wide">Spread</span>
        <span class="ml-auto font-mono text-gray-400">
          {{ spread !== null ? `₿${spread.toFixed(5)}` : '—' }}
        </span>
      </div>

      <!-- ══ ASKS (red) ══════════════════════════════════════════════════════ -->
      <div v-if="asks.length > 0" class="mt-1">
        <!-- Column headers -->
        <div class="grid gap-x-1 px-2 pb-1 text-[10px]"
             style="grid-template-columns: 2.2fr 1fr 1fr 1fr">
          <span class="table-header" style="color:rgb(248 113 113 / 0.65)">Price</span>
          <span class="table-header text-right" style="color:rgb(248 113 113 / 0.65)">Limit</span>
          <span class="table-header text-right" style="color:rgb(248 113 113 / 0.65)">Used</span>
          <span class="table-header text-right" style="color:rgb(248 113 113 / 0.65)">Available</span>
        </div>

        <div
          v-for="(ask, i) in displayAsks"
          :key="'a' + i"
          class="grid gap-x-1 px-2 py-0.5 rounded text-xs mb-px hover:opacity-80 transition-opacity"
          style="grid-template-columns: 2.2fr 1fr 1fr 1fr;
                 background:rgb(127 29 29 / 0.12);
                 border:1px solid rgb(127 29 29 / 0.22)"
        >
          <!-- Price -->
          <span class="font-mono text-red-400">{{ ask.price_btc.toFixed(5) }}</span>
          <!-- Limit = total capacity (used + available) -->
          <span class="text-right font-mono text-red-300/60">
            {{ fmtSpeed(ask.hr_matched_ph + ask.hr_available_ph) }}
          </span>
          <!-- Used (currently matched) -->
          <span class="text-right font-mono"
                :class="ask.hr_matched_ph > 0 ? 'text-red-300/70' : 'text-red-900/70'">
            {{ fmtSpeed(ask.hr_matched_ph) }}
          </span>
          <!-- Available (remaining) -->
          <span class="text-right font-mono text-red-300/60">
            {{ fmtSpeed(ask.hr_available_ph) }}
          </span>
        </div>
      </div>

    </div>
  </div>
</template>
