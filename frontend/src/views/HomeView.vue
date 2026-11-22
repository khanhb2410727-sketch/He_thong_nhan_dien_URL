<template>
  <div class="home-page">
    <section class="hero-section">
      <div class="hero-copy">
        <!-- <div class="eyebrow"><span class="pulse-dot"></span> MALICIOUS URL DETECTION
        </div> -->
        <h1>Đừng để một cú click<br /><span>đặt bạn vào rủi ro.</span></h1>
        <div class="hero-points"><span><CheckCircle2 :size="16" /> Phân tích đa mô hình</span><span><CheckCircle2 :size="16" /> Thông tin domain</span><span><CheckCircle2 :size="16" /> Kết quả trực quan</span></div>
      </div>
      <div class="hero-art"><div class="orbit orbit-one"></div><div class="orbit orbit-two"></div><div class="shield-illustration"><ShieldCheck :size="76" stroke-width="1.45" /></div><span class="float-chip chip-top"><LockKeyhole :size="15" /> Secure scan</span><span class="float-chip chip-bottom"><Activity :size="15" /> AI powered</span></div>
    </section>

    <section class="scan-panel panel">
      <div class="section-heading"><div>
        <span class="section-kicker">BẮT ĐẦU PHÂN TÍCH</span>
        <h2>Kiểm tra một URL</h2>
        <p>Nhập địa chỉ website và chọn mô hình bạn muốn sử dụng.</p>
      </div>
      <span class="step-badge">01 <span>/ 02</span></span></div>
      <form @submit.prevent="submitAnalysis">
        <label class="field-label" for="url-input">URL cần kiểm tra</label>
        <div class="url-input-wrap" :class="{ invalid: urlError }"><Globe2 :size="19" /><input id="url-input" v-model.trim="url" type="text" placeholder="https://example.com" autocomplete="url" @input="urlError = ''" /><button v-if="url" type="button" class="clear-btn" aria-label="Xóa URL" @click="url = ''"><X :size="16" /></button></div>
        <p v-if="urlError" class="field-error">{{ urlError }}</p>
        <div class="models-heading"><div>
          <label class="field-label">Lựa chọn mô hình</label>
        </div><span class="optional-label">MULTI-MODEL</span></div>
        <ModelSelector v-model:selected="selectedModels" :api-models="apiModels" />
        <div v-if="analysisState.error" class="error-banner"><AlertCircle :size="18" /><span>{{ analysisState.error }}</span></div>
        <button class="primary-button scan-button" type="submit" :disabled="analysisState.loading"><span v-if="analysisState.loading" class="spinner"></span><ScanSearch v-else :size="18" />{{ analysisState.loading ? 'Đang phân tích URL...' : 'Phân tích URL' }}<ArrowRight v-if="!analysisState.loading" :size="17" /></button>
        <p class="privacy-note"><Lock :size="13" /> URL chỉ được gửi đến máy chủ phân tích đã cấu hình.</p>
      </form>
    </section>

    <!-- <section class="feature-section" id="about"><div class="section-heading centered"><span class="section-kicker">NỀN TẢNG PHÂN TÍCH</span><h2>Một URL. Nhiều góc nhìn.</h2><p>Kết hợp dự đoán từ nhiều mô hình cùng thông tin kỹ thuật của domain.</p></div>
      <div class="feature-grid"><article class="feature-card"><span class="feature-icon blue"><BrainCircuit :size="21" /></span><h3>Phân tích đa mô hình</h3><p>Chạy Bayesian BERT, BERT Phishing và Neural Symbolic BERT theo lựa chọn của bạn.</p></article><article class="feature-card"><span class="feature-icon purple"><Network :size="21" /></span><h3>Thông tin URL & Domain</h3><p>Tổng hợp DNS, IP, SSL/TLS, thời gian đăng ký và thông tin chuyển hướng khi có dữ liệu.</p></article><article class="feature-card"><span class="feature-icon green"><ChartNoAxesCombined :size="21" /></span><h3>Dashboard trực quan</h3><p>Đặt kết quả các mô hình cạnh nhau để quan sát và so sánh dự đoán.</p></article></div>
    </section> -->
    <section id="api" class="api-note"><Code2 :size="18" /><div><strong>Tích hợp Backend API</strong><p>Frontend gửi yêu cầu đến endpoint được cấu hình trong file <code>.env</code>.</p></div></section>
  </div>
</template>
<script setup>
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { Activity, AlertCircle, ArrowRight, BrainCircuit, ChartNoAxesCombined, CheckCircle2, Code2, Globe2, Lock, LockKeyhole, Network, ScanSearch, ShieldCheck, X } from 'lucide-vue-next'
import ModelSelector from '../components/ModelSelector.vue'
import { analyzeUrl, getModels } from '../services/api'
import { analysisState } from '../stores/analysis'
import { normalizeResult } from '../utils/analysis'
const router = useRouter()
const url = ref('')
const selectedModels = ref(['bayesian_bert', 'bert_phishing', 'neural_symbolic'])
const apiModels = ref([])
onMounted(async () => {
  try {
    const response = await getModels()
    apiModels.value = response.models ?? []
  } catch {
    apiModels.value = []
  }
})
const urlError = ref('')
function validateUrl(value) {
  try { const parsed = new URL(value); return ['http:', 'https:'].includes(parsed.protocol) && parsed.hostname.includes('.') }
  catch { return false }
}
async function submitAnalysis() {
  analysisState.error = ''
  if (!url.value) { urlError.value = 'Vui lòng nhập URL cần kiểm tra.'; return }
  if (!validateUrl(url.value)) { urlError.value = 'URL không hợp lệ. Hãy nhập địa chỉ có http:// hoặc https://.'; return }
  if (selectedModels.value.length < 1 || selectedModels.value.length > 3) { analysisState.error = 'Vui lòng chọn từ 1 đến 3 mô hình.'; return }
  analysisState.loading = true
  try {
    const raw = await analyzeUrl({ url: url.value, models: selectedModels.value })
    analysisState.result = normalizeResult(raw, { url: url.value, models: selectedModels.value })
    router.push('/dashboard')
  } catch (error) {
    const detail = error?.response?.data?.detail ?? error?.response?.data?.message
    analysisState.error = detail || (error.code === 'ECONNABORTED' ? 'Máy chủ xử lý quá lâu. Vui lòng thử lại.' : 'Không thể kết nối Backend. Kiểm tra máy chủ và cấu hình VITE_API_BASE_URL trong file .env.')
  } finally { analysisState.loading = false }
}
</script>
