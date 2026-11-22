<template>
  <article class="prediction-card" :class="danger ? 'prediction-danger' : 'prediction-safe'">
    <div class="prediction-card-header">
      <h3>MODEL {{ index + 1 }}: {{ item.modelName }}</h3>
      <span class="prediction-state">{{ danger ? 'PHISHING' : 'SAFE' }}</span>
    </div>

    <div class="prediction-url">
      <span class="prediction-link-icon"><Link2 :size="20" /></span>
      <span>{{ url }}</span>
    </div>

    <div class="prediction-confidence">
      <span>Confidence: {{ item.confidence === null ? 'N/A' : `${item.confidence}%` }}</span>
      <div class="progress-track">
        <span :style="{ width: `${Math.min(item.confidence ?? 0, 100)}%` }"></span>
      </div>
    </div>
  </article>
</template>
<script setup>
import { computed } from 'vue'
import { Link2 } from 'lucide-vue-next'
import { isMalicious } from '../utils/analysis'
const props = defineProps({
  item: { type: Object, required: true },
  index: { type: Number, required: true },
  url: { type: String, required: true },
})
const danger = computed(() => isMalicious(props.item.label))
</script>
