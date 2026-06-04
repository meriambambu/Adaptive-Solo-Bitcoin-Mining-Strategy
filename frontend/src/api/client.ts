import axios from 'axios'

const BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

export const api = axios.create({
  baseURL: BASE_URL,
  timeout: 15_000,
})

export const WS_URL = BASE_URL.replace(/^http/, 'ws') + '/ws'
