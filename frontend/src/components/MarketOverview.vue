<script setup lang="ts">
import { ref, onMounted, computed, nextTick } from 'vue'
import { api } from '../api/client'

interface BidEntry {
  price_btc: number
  price_sat: number
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

const bids = ref<BidEntry[]>([])   // ascending from backend
const asks = ref<AskEntry[]>([])   // ascending from backend
const topN = ref(5)
const loading = ref(true)
const myBidRow = ref<HTMLElement | null>(null)

function isMyBid(entry: BidEntry): boolean {
  return (props.myBidPriceSat ?? []).includes(Math.round(entry.price_sat))
}

async function fetchBook() {
  try {
    const [bookRes, settingsRes] = await Promise.all([
      api.get<{ bids: BidEntry[]; asks: AskEntry[] }>('/api/market/orderbook'),
      api.get<{ top_n: number }>('/api/settings'),
    ])
    bids.value = bookRes.data.bids || []
    asks.value = bookRes.data.asks || []
    topN.value = settingsRes.data.top_n
  } catch {
    // silent
  } finally {
    loading.value = false
  }
  await nextTick()
  myBidRow.value?.scrollIntoView({ block: 'nearest', behavior: 'instant' })
}

// P_N = Nth cheapest bid price (bids sorted ascending from backend)
const pN = computed((): number | null => {
  if (bids.value.length >= topN.value) return bids.value[topN.value - 1].price_btc
  return bids.value.at(-1)?.price_btc ?? null
})

// Display bids highest-first (Braiins order — best bid at top)
const displayBids = computed(() => [...bids.value].reverse())

// Display asks lowest-first (cheapest ask at top, nearest to spread above)
const displayAsks = computed(() => [...asks.value])

function inTopN(entry: BidEntry): boolean {
  return pN.value !== null && entry.price_btc <= pN.value
}

function fmtSpeed(ph: number): string {
  if (ph === 0) return '—'
  if (ph >= 1000) return (ph / 1000).toFixed(2) + ' EH/s'
  return ph.toFixed(2) + ' PH/s'
}

const spread = computed((): number | null => {
  const bestBid = bids.value.at(-1)?.price_btc ?? null   // highest bid = last in ascending
  const bestAsk = asks.value[0]?.price_btc ?? null        // lowest ask  = first in ascending
  if (bestBid === null || bestAsk === null) return null
  return Math.max(0, bestAsk - bestBid)
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

    <div v-else class="max-h-[28rem] overflow-y-auto">

      <!-- ── Bids (green) ── -->
      <div class="mb-1">
        <div class="grid grid-cols-3 gap-1 px-2 pb-1">
          <span class="table-header" style="color:rgb(74 222 128 / 0.7)">Price (₿/EH/day)</span>
          <span class="table-header text-right" style="color:rgb(74 222 128 / 0.7)">Limit</span>
          <span class="table-header text-right" style="color:rgb(74 222 128 / 0.7)">Matched</span>
        </div>
        <div
          v-for="(entry, i) in displayBids"
          :key="'b' + i"
          :ref="(el) => { if (isMyBid(entry) && el) myBidRow = el as HTMLElement }"
          class="grid grid-cols-3 gap-1 px-2 py-0.5 rounded text-xs transition-colors mb-px"
          :class="{
            'ring-1 ring-brand-purple bg-brand-purple/10': isMyBid(entry),
            'bg-green-900/25 border border-green-800/40': !isMyBid(entry) && inTopN(entry),
            'bg-green-900/10 border border-green-900/20': !isMyBid(entry) && !inTopN(entry),
          }"
        >
          <span class="font-mono flex items-center gap-1">
            <span
              :class="{
                'text-brand-purple-light': isMyBid(entry),
                'text-green-400': !isMyBid(entry) && inTopN(entry),
                'text-green-700': !isMyBid(entry) && !inTopN(entry),
              }"
            >{{ entry.price_btc.toFixed(5) }}</span>
            <span v-if="isMyBid(entry)" class="text-brand-purple-light text-[9px] font-bold">YOU</span>
          </span>
          <span
            class="text-right font-mono"
            :class="{
              'text-brand-purple-light/70': isMyBid(entry),
              'text-green-400/60': !isMyBid(entry) && inTopN(entry),
              'text-green-900': !isMyBid(entry) && !inTopN(entry),
            }"
          >{{ fmtSpeed(entry.speed_limit_ph) }}</span>
          <span
            class="text-right font-mono"
            :class="{
              'text-brand-purple-light/70': isMyBid(entry),
              'text-green-400/60': !isMyBid(entry) && inTopN(entry),
              'text-green-900': !isMyBid(entry) && !inTopN(entry),
            }"
          >{{ fmtSpeed(entry.hr_matched_ph) }}</span>
        </div>
      </div>

      <!-- ── Spread bar ── -->
      <div class="flex items-center gap-2 px-2 py-1 my-1 text-[10px]"
           style="border-top:1px solid rgb(75 85 99 / 0.3); border-bottom:1px solid rgb(75 85 99 / 0.3); background:rgb(17 24 39 / 0.4)">
        <span class="text-gray-600 uppercase tracking-wide">Spread</span>
        <span class="ml-auto font-mono text-gray-400">
          {{ spread !== null ? `₿${spread.toFixed(5)}` : '—' }}
        </span>
      </div>

      <!-- ── Asks (red) ── -->
      <div v-if="asks.length > 0" class="mt-1">
        <div class="grid grid-cols-3 gap-1 px-2 pb-1">
          <span class="table-header" style="color:rgb(248 113 113 / 0.7)">Price (₿/EH/day)</span>
          <span class="table-header text-right" style="color:rgb(248 113 113 / 0.7)">Used</span>
          <span class="table-header text-right" style="color:rgb(248 113 113 / 0.7)">Available</span>
        </div>
        <div
          v-for="(ask, i) in displayAsks"
          :key="'a' + i"
          class="grid grid-cols-3 gap-1 px-2 py-0.5 rounded text-xs mb-px"
          style="background:rgb(127 29 29 / 0.12); border:1px solid rgb(127 29 29 / 0.25)"
        >
          <span class="font-mono text-red-400">{{ ask.price_btc.toFixed(5) }}</span>
          <span class="text-right font-mono text-red-300/60">{{ fmtSpeed(ask.hr_matched_ph) }}</span>
          <span class="text-right font-mono text-red-300/60">{{ fmtSpeed(ask.hr_available_ph) }}</span>
        </div>
      </div>

    </div>
  </div>
</template>
