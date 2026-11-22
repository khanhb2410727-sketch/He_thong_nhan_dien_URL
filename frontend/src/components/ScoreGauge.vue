<template>
  <div class="gauge-wrap">
    <svg viewBox="0 0 220 130" class="gauge" role="img" :aria-label="`Safety score ${score ?? 'unknown'}`">
      <path d="M 25 105 A 85 85 0 0 1 195 105" pathLength="100" class="gauge-track" />
      <path d="M 25 105 A 85 85 0 0 1 195 105" pathLength="100" class="gauge-value" :class="tone" :style="{ strokeDasharray: `${score ?? 0}, 100` }" />
      <circle cx="110" cy="105" r="7" class="gauge-dot" />
    </svg>
    <div class="gauge-number">{{ score === null ? '—' : score.toFixed(1) }}<small>/100</small></div>
    <div class="gauge-caption">Safety score</div>
  </div>
</template>
<script setup>
import { computed } from 'vue'
const props = defineProps({ score: { type: Number, default: null } })
const tone = computed(() => props.score >= 70 ? 'safe' : props.score >= 40 ? 'warning' : 'danger')
</script>
