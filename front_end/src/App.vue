<template>
  <div class="desktop-layout">
    <!-- Thanh Header -->
    <header class="app-header">
      <div class="logo-area">
        <h1>URL Checker</h1>
      </div>
      <div class="status-area">
        <span class="status-dot"></span> Online
      </div>
    </header>

    <!-- Khu vực làm việc chính -->
    <main class="workspace">
      
      <!-- CỘT TRÁI: Nhập liệu -->
      <section class="panel left-panel">
        <div class="panel-header">
          <h2>Kiểm tra URL</h2>
        </div>
        
        <form @submit.prevent="checkUrl" class="input-form">
          <label for="url-input">Nhập đường dẫn cần kiểm tra:</label>
          <textarea 
            id="url-input"
            v-model="url" 
            placeholder="VD: https://google.com" 
            rows="4"
            :disabled="isLoading"
            @keyup.enter.exact.prevent="checkUrl"
          ></textarea>
          
          <button type="submit" class="btn-primary" :disabled="isLoading || !url">
            {{ isLoading ? 'Đang kiểm tra...' : 'Kiểm tra' }}
          </button>
        </form>

        <div v-if="error" class="alert error">
          {{ error }}
        </div>
      </section>

      <!-- CỘT PHẢI: Kết quả & Lịch sử -->
      <section class="panel right-panel">
        <div class="panel-header">
          <h2>Kết quả phân tích từ các Mô hình</h2>
        </div>

        <!-- Trạng thái chưa có dữ liệu -->
        <div v-if="!results.length && !isLoading" class="empty-state">
          <p>Chưa có dữ liệu. Vui lòng nhập URL để kiểm tra.</p>
        </div>

        <!-- Trạng thái đang load -->
        <div v-if="isLoading" class="loading-state">
          <div class="spinner"></div>
          <p>Đang xử lý dữ liệu qua 3 mô hình AI...</p>
        </div>

        <!-- Khu vực hiển thị kết quả 3 mô hình -->
        <div v-if="results.length && !isLoading" class="result-content">
          
          <div class="current-url-display">
            <strong>URL đang kiểm tra:</strong> 
            <span>{{ currentUrl }}</span>
          </div>

          <!-- Grid 3 cột -->
          <div class="model-grid">
            <ModelResultCard 
              v-for="(model, index) in results" 
              :key="index"
              :model-name="model.name"
              :is-legit="model.is_legit"
            />
          </div>

          <!-- Bảng lịch sử -->
          <div class="history-section">
            <h4>Lịch sử kiểm tra</h4>
            <table class="history-table">
              <thead>
                <tr>
                  <th>URL</th>
                  <th>Kết quả tổng hợp</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="(item, index) in history" :key="index">
                  <td class="truncate">{{ item.url }}</td>
                  <td>
                    <span :class="item.is_legit ? 'text-safe' : 'text-danger'">
                      {{ item.is_legit ? 'Hợp pháp' : 'Không hợp pháp' }}
                    </span>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </section>
      
    </main>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import ModelResultCard from './components/ModelResultCard.vue'

const url = ref('')
const currentUrl = ref('')
const isLoading = ref(false)
const results = ref([])
const error = ref(null)
const history = ref([]) 

const checkUrl = async () => {
  if (!url.value || isLoading.value) return
  
  isLoading.value = true
  error.value = null
  results.value = []
  currentUrl.value = url.value

  try {
    // --- KHI NỐI API FASTAPI ---
    /*
    const response = await fetch('http://localhost:8000/api/v1/predict-all', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ url: url.value })
    })
    if (!response.ok) throw new Error('Lỗi kết nối đến server')
    results.value = await response.json()
    */

    // --- MOCK DATA ---
    await new Promise(resolve => setTimeout(resolve, 800)) 
    
    const isSuspicious = url.value.includes('hack') || url.value.includes('free-gift')
    
    // Cập nhật tên 3 model theo yêu cầu
    results.value = [
      { name: 'Deterministic model', is_legit: !isSuspicious },
      { name: 'Probabilistic model', is_legit: !isSuspicious },
      { name: 'Deterministic Symbolic model', is_legit: isSuspicious ? false : (Math.random() > 0.2) } 
    ]

    const finalDecision = results.value[0].is_legit
    history.value.unshift({
      url: url.value,
      is_legit: finalDecision
    })

  } catch (err) {
    error.value = err.message || 'Có lỗi xảy ra, vui lòng thử lại.'
  } finally {
    isLoading.value = false
  }
}
</script>

<style scoped>
* {
  box-sizing: border-box;
  margin: 0;
  padding: 0;
}

body {
  font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
  background-color: #eef2f5;
  color: #333;
}

.desktop-layout {
  display: flex;
  flex-direction: column;
  height: 100vh;
  width: 100vw;
  overflow: hidden;
}

.app-header {
  height: 60px;
  background-color: #1e293b;
  color: white;
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0 24px;
  box-shadow: 0 2px 10px rgba(0,0,0,0.1);
  z-index: 10;
}

.logo-area h1 {
  font-size: 20px;
  font-weight: 600;
  letter-spacing: 0.5px;
}

.status-area {
  font-size: 14px;
  display: flex;
  align-items: center;
  gap: 8px;
  color: #a0aec0;
}

.status-dot {
  width: 8px;
  height: 8px;
  background-color: #10b981;
  border-radius: 50%;
}

.workspace {
  display: flex;
  flex: 1;
  padding: 20px;
  gap: 20px;
  overflow: hidden; 
}

.panel {
  background: white;
  border-radius: 8px;
  box-shadow: 0 4px 6px rgba(0,0,0,0.05);
  display: flex;
  flex-direction: column;
  border: 1px solid #e2e8f0;
}

.left-panel {
  flex: 1; 
  min-width: 320px;
  max-width: 400px;
}

.right-panel {
  flex: 3; 
  min-width: 600px; /* Đảm bảo cột phải đủ rộng để chứa 3 model */
}

.panel-header {
  padding: 16px 20px;
  border-bottom: 1px solid #e2e8f0;
  background-color: #f8fafc;
  border-radius: 8px 8px 0 0;
}

.panel-header h2 {
  font-size: 16px;
  color: #475569;
  font-weight: 600;
}

.input-form {
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.input-form label {
  font-size: 14px;
  font-weight: 500;
  color: #64748b;
}

textarea {
  width: 100%;
  padding: 12px;
  border: 1px solid #cbd5e1;
  border-radius: 6px;
  font-family: monospace;
  font-size: 14px;
  resize: vertical;
  outline: none;
  transition: border-color 0.2s;
}

textarea:focus {
  border-color: #3b82f6;
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
}

.btn-primary {
  background-color: #3b82f6;
  color: white;
  border: none;
  padding: 12px;
  border-radius: 6px;
  font-size: 15px;
  font-weight: 600;
  cursor: pointer;
  transition: background-color 0.2s;
}

.btn-primary:hover:not(:disabled) {
  background-color: #2563eb;
}

.btn-primary:disabled {
  background-color: #94a3b8;
  cursor: not-allowed;
}

.empty-state, .loading-state {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: #94a3b8;
  gap: 16px;
  padding: 40px;
  text-align: center;
}

.spinner {
  width: 40px;
  height: 40px;
  border: 4px solid #e2e8f0;
  border-top: 4px solid #3b82f6;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.result-content {
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 24px;
  height: 100%;
  overflow-y: auto;
}

.current-url-display {
  font-size: 14px;
  color: #475569;
  background-color: #f1f5f9;
  padding: 12px;
  border-radius: 6px;
  word-break: break-all;
}

.current-url-display span {
  font-family: monospace;
}

/* CSS QUAN TRỌNG ĐỂ CHIA 3 CỘT */
.model-grid {
  display: grid;
  /* Chia làm 3 cột bằng nhau, ép buộc không cho co lại dưới 200px */
  grid-template-columns: repeat(3, minmax(200px, 1fr)); 
  gap: 16px;
}

.history-section {
  margin-top: 10px;
}

.history-section h4 {
  margin-bottom: 10px;
  color: #475569;
  font-size: 15px;
}

.history-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 14px;
  text-align: left;
}

.history-table th {
  background-color: #f8fafc;
  padding: 12px;
  border-bottom: 2px solid #e2e8f0;
  color: #64748b;
}

.history-table td {
  padding: 12px;
  border-bottom: 1px solid #e2e8f0;
}

.truncate {
  max-width: 400px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.text-safe { color: #16a34a; font-weight: 600; }
.text-danger { color: #dc2626; font-weight: 600; }

.alert.error {
  margin: 20px;
  padding: 12px;
  background-color: #fef2f2;
  color: #b91c1c;
  border: 1px solid #fecaca;
  border-radius: 6px;
  font-size: 14px;
}
</style>