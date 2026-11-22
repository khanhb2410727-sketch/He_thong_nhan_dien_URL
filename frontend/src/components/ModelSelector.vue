<template>
  <div class="model-grid">
    <label v-for="model in availableModels" :key="model.id" class="model-option" :class="{ selected: selected.includes(model.id), disabled: !selected.includes(model.id) && selected.length >= 3 }">
      <input type="checkbox" :value="model.id" :checked="selected.includes(model.id)" :disabled="!selected.includes(model.id) && selected.length >= 3" @change="toggle(model.id)" />
      <span class="fake-check"><Check :size="13" /></span>
      <span class="model-content">
        <strong>{{ model.name }}</strong>
        <!-- <small>{{ model.description }}</small>
        <code>{{ model.file }}</code> -->
      </span>
      <span class="model-number">0{{ availableModels.indexOf(model) + 1 }}</span>
    </label>
  </div>
  <div class="selection-meta"><span>{{ selected.length }}/3 mô hình được chọn</span><span>Chọn ít nhất 1 mô hình</span></div>
</template>
<script setup>
import { computed } from 'vue'
import { Check } from 'lucide-vue-next'
import { MODEL_OPTIONS as models } from '../utils/analysis'
const props = defineProps({
  selected: { type: Array, required: true },
  apiModels: { type: Array, default: () => [] },
})
const emit = defineEmits(['update:selected'])
const availableModels = computed(() => {
  if (!props.apiModels.length) return models
  return props.apiModels.map(apiModel => ({
    ...apiModel,
    available: apiModel.available !== false,
  }))
})
function toggle(id) {
  if (!props.selected.includes(id) && props.selected.length >= 3) return
  const next = props.selected.includes(id)
    ? props.selected.filter(x => x !== id)
    : [...props.selected, id]
  emit('update:selected', next)
}
</script>
