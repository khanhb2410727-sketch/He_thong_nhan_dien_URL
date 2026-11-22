<template>
  <div v-if="result" class="dashboard-page wireframe-dashboard">
    <button class="dashboard-back" type="button" @click="router.push('/')">
      <ArrowLeft :size="18" /> Quét URL khác
    </button>

    <div class="dashboard-columns">
      <section class="model-results" aria-label="Kết quả từng mô hình">
        <PredictionCard
          v-for="(item, index) in result.predictions"
          :key="`${item.modelId}-${index}`"
          :item="item"
          :index="index"
          :url="result.url"
        />
        <div v-if="!result.predictions.length" class="empty-state">
          Backend chưa trả về kết quả mô hình.
        </div>
      </section>

      <section class="phishing-panel" aria-label="Thông tin URL phishing">
        <h2>PHISHING URL INFORMATION</h2>

        <div class="info-block">
          <h3>URL Details</h3>
          <div class="info-value">{{ result.url }}</div>
        </div>

        <div class="info-block">
          <h3>Domain Age</h3>
          <div class="info-value">
            <span>Domain created: {{ formatDomainDate(result.urlInfo.registeredAt) }}</span>
            <span>{{ domainAgeText }}</span>
          </div>
        </div>

        <div class="info-block">
          <h3>SSL Certificate</h3>
          <div class="info-value">
            <span>Status: {{ sslStatus }}</span>
            <span>Expiry: {{ sslExpiry }}</span>
          </div>
        </div>

        <div class="risk-layout">
          <div class="risk-factors">
            <h3>Risk Factors List</h3>
            <ul v-if="riskFactors.length">
              <li v-for="(factor, index) in riskFactors" :key="index">{{ factor }}</li>
            </ul>
            <p v-else>Không phát hiện tín hiệu rủi ro nổi bật.</p>
          </div>

          <div class="risk-chart">
            <h3>Risk Score Visualization</h3>
            <div class="chart-plot">
              <span class="chart-y-label">Risk score</span>
              <div class="chart-bars">
                <div
                  v-for="(item, index) in result.predictions"
                  :key="`bar-${item.modelId}-${index}`"
                  class="chart-bar"
                  :style="{ height: `${chartHeight(item)}%` }"
                  :title="`${item.modelName}: ${item.confidence ?? 0}%`"
                ></div>
              </div>
            </div>
          </div>
        </div>
      </section>
    </div>
  </div>
  <div v-else class="no-result panel"><span class="empty-icon"><FileSearch :size="28" /></span><h2>Chưa có kết quả phân tích</h2><p>Hãy nhập URL và chạy phân tích trước khi xem Dashboard.</p><button class="primary-button" @click="router.push('/')">Quay về trang chủ <ArrowRight :size="16" /></button></div>
</template>
<script setup>
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { ArrowLeft, ArrowRight, FileSearch } from 'lucide-vue-next'
import PredictionCard from '../components/PredictionCard.vue'
import { analysisState } from '../stores/analysis'

const router = useRouter()
const result = computed(() => analysisState.result)

const riskFactors = computed(() => {
  const factors = result.value?.summaryDetails?.suspicious_signals
  return Array.isArray(factors) ? factors : []
})

const domainAgeText = computed(() => {
  const age = result.value?.urlInfo?.domainAgeDays
  return typeof age === 'number' ? `${age} Days` : 'Not available'
})

const sslStatus = computed(() => {
  const ssl = result.value?.urlInfo?.ssl
  if (!ssl || typeof ssl !== 'object') return 'Not available'
  if (ssl.available === false) return 'Unavailable'
  return ssl.verified ? 'Valid' : 'Unverified'
})

const sslExpiry = computed(() => {
  const ssl = result.value?.urlInfo?.ssl
  if (!ssl || typeof ssl !== 'object' || !ssl.not_after) return 'Not available'
  return formatDomainDate(ssl.not_after)
})

function formatDomainDate(value) {
  if (!value || value === 'Chưa có dữ liệu') return 'Not available'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return String(value).slice(0, 10)
  return date.toISOString().slice(0, 10)
}

function chartHeight(item) {
  const confidence = item.confidence
  if (confidence === null || confidence === undefined) return 12
  return Math.max(8, Math.min(100, confidence))
}
</script>
