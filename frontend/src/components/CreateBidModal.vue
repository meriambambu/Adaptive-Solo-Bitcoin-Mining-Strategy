<script setup lang="ts">
import { ref } from 'vue'
import { api } from '../api/client'

const emit = defineEmits<{ (e: 'created'): void; (e: 'close'): void }>()

const form = ref({
  price_btc: '',
  amount_btc: '',
  speed_limit_ph: '0',
  pool_url: 'stratum+tcp://public.stratum.braiins.com:3333',
  pool_identity: '',
  memo: '',
})
const submitting = ref(false)
const error = ref<string | null>(null)

async function submit() {
  error.value = null
  submitting.value = true
  try {
    await api.post('/api/orders', {
      price_btc: Number(form.value.price_btc),
      amount_btc: Number(form.value.amount_btc),
      speed_limit_ph: Number(form.value.speed_limit_ph) || 0,
      pool_url: form.value.pool_url,
      pool_identity: form.value.pool_identity,
      memo: form.value.memo,
    })
    emit('created')
    emit('close')
  } catch (e: unknown) {
    error.value = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail || (e as Error).message
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <div class="fixed inset-0 z-50 flex items-center justify-center bg-black/70">
    <div class="w-full max-w-lg rounded-lg bg-surface-800 border border-surface-600 shadow-2xl">
      <!-- Header -->
      <div class="flex items-center justify-between px-6 py-4 border-b border-surface-600">
        <h2 class="text-base font-semibold">Create Bid</h2>
        <button @click="emit('close')" class="text-gray-500 hover:text-white text-xl leading-none">&times;</button>
      </div>

      <!-- Form -->
      <form @submit.prevent="submit" class="px-6 py-4 space-y-4">
        <div class="grid grid-cols-2 gap-4">
          <div>
            <label class="block text-xs text-gray-400 mb-1">Price (BTC/EH/Day)</label>
            <input v-model="form.price_btc" type="number" step="0.00001" min="0" placeholder="0.4" class="input" required />
          </div>
          <div>
            <label class="block text-xs text-gray-400 mb-1">Budget (BTC)</label>
            <input v-model="form.amount_btc" type="number" step="0.00000001" min="0" placeholder="0.0001" class="input" required />
          </div>
        </div>

        <div>
          <label class="block text-xs text-gray-400 mb-1">Speed Limit (PH/s) <span class="text-gray-600">— 0 for unlimited</span></label>
          <input v-model="form.speed_limit_ph" type="number" step="1" min="0" placeholder="0" class="input" />
        </div>

        <div>
          <label class="block text-xs text-gray-400 mb-1">Mining Pool URL <span class="text-gray-600">stratum+tcp://host:port</span></label>
          <input v-model="form.pool_url" type="text" placeholder="stratum+tcp://public.stratum.braiins.com:3333" class="input" required />
        </div>

        <div>
          <label class="block text-xs text-gray-400 mb-1">Pool Identity <span class="text-gray-600">wallet.worker</span></label>
          <input v-model="form.pool_identity" type="text" placeholder="bc1q…address.worker" class="input" required />
        </div>

        <div>
          <label class="block text-xs text-gray-400 mb-1">Memo (Optional)</label>
          <textarea v-model="form.memo" rows="2" placeholder="Optional note for this bid" class="input resize-none" />
        </div>

        <div v-if="error" class="rounded bg-red-900/30 border border-red-700/40 px-3 py-2 text-sm text-red-400">
          {{ error }}
        </div>
      </form>

      <!-- Footer -->
      <div class="flex justify-between px-6 py-4 border-t border-surface-600">
        <button type="button" @click="emit('close')" class="btn-ghost">Cancel</button>
        <button type="button" @click="submit" :disabled="submitting" class="btn-primary">
          {{ submitting ? 'Creating…' : 'Create Bid' }}
        </button>
      </div>
    </div>
  </div>
</template>
