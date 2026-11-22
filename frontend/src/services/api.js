import axios from 'axios'

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000',
  timeout: 120000,
  headers: { 'Content-Type': 'application/json' },
})

export async function analyzeUrl(payload) {
  const endpoint = import.meta.env.VITE_ANALYZE_ENDPOINT || '/api/predict'
  const { data } = await api.post(endpoint, payload)
  return data
}

export async function getModels() {
  const { data } = await api.get('/api/models')
  return data
}

export async function getHealth() {
  const { data } = await api.get('/api/health')
  return data
}

export default api
