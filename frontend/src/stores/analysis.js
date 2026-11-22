import { reactive } from 'vue'

// Shared state between the URL form and Dashboard. Results are kept in memory only.
export const analysisState = reactive({
  result: null,
  loading: false,
  error: '',
})
