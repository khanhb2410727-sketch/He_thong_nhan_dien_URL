<template>
  <div class="model-card" :class="isLegit ? 'safe' : 'danger'">
    <div class="model-name">{{ modelName }}</div>
    <div class="status-text">
      {{ isLegit ? 'HỢP PHÁP' : 'KHÔNG HỢP PHÁP' }}
    </div>
  </div>
</template>

<script setup>
defineProps({
  modelName: {
    type: String,
    required: true
  },
  isLegit: {
    type: Boolean,
    required: true
  }
})
</script>

<style scoped>
.model-card {
  padding: 24px 12px; /* Giảm padding ngang một chút để vừa 3 cột */
  border-radius: 8px;
  text-align: center;
  display: flex;
  flex-direction: column;
  justify-content: center;
  gap: 12px;
  height: 100%;
  min-width: 0; /* Quan trọng: Ngăn chặn grid bị tràn */
}

.model-card.safe {
  background-color: #f0fdf4;
  border: 1px solid #86efac;
}

.model-card.danger {
  background-color: #fef2f2;
  border: 1px solid #fca5a5;
}

.model-name {
  font-size: 13px;
  font-weight: 600;
  color: #64748b;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  border-bottom: 1px dashed #cbd5e1;
  padding-bottom: 12px;
  margin-bottom: 8px;
  /* Cho phép xuống dòng nếu tên model quá dài */
  word-wrap: break-word; 
}

.status-text {
  font-size: 16px; /* Giảm từ 18px xuống 16px cho vừa khung */
  font-weight: 700;
}

.safe .status-text {
  color: #166534;
}

.danger .status-text {
  color: #991b1b;
}
</style>