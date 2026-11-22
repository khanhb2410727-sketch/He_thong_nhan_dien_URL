# SafeLink Scanner – Vue.js Frontend

Frontend Vue 3 + Vite cho hệ thống nhận diện URL độc hại. Giao diện gồm trang nhập URL/chọn mô hình và Dashboard kết quả, theo phong cách tham khảo trong ảnh đính kèm.

## 1. Yêu cầu
- Node.js 20+ (khuyến nghị Node.js 22 LTS)
- Backend Python đang chạy và cho phép CORS từ frontend

## 2. Cài đặt và chạy

```bash
npm install
cp .env.example .env
npm run dev
```

Windows PowerShell có thể sao chép file môi trường bằng:

```powershell
Copy-Item .env.example .env
```

Mở URL Vite hiển thị trong terminal, thường là `http://localhost:5173`.

## 3. Cấu hình Backend

Trong `.env`:

```env
VITE_API_BASE_URL=http://localhost:8000
VITE_ANALYZE_ENDPOINT=/api/analyze
```

Frontend hiện gửi request:

```http
POST /api/analyze
Content-Type: application/json
```

```json
{
  "url": "https://example.com",
  "models": ["bayesian_bert", "bert_phishing", "neural_symbolic_bert"]
}
```

### Response đề xuất

```json
{
  "url": "https://example.com",
  "analyzed_at": "2026-11-22T10:30:00+07:00",
  "safety_score": 82.5,
  "summary": "Potentially safe",
  "predictions": [
    {"model_id":"bayesian_bert","model_name":"Bayesian BERT","label":"Safe","confidence":0.985},
    {"model_id":"bert_phishing","model_name":"BERT Phishing","label":"Malicious","confidence":0.91},
    {"model_id":"neural_symbolic_bert","model_name":"Neural Symbolic BERT","label":"Safe","confidence":0.963}
  ],
  "url_info": {
    "domain":"example.com", "subdomain":"www", "tld":".com", "ip_address":"93.184.216.34",
    "country":"United States", "registrar":"Example Registrar", "creation_date":"2020-01-01",
    "ssl_status":"Valid", "redirect_count":0, "final_url":"https://example.com"
  },
  "security_sources": [
    {"name":"Google Safe Browsing","status":"Clean","message":"No threats detected"},
    {"name":"VirusTotal","status":"Suspicious","message":"1 security vendor flagged this URL"}
  ]
}
```

`predictions` cũng có thể được trả về dưới tên `results` hoặc `model_results`. Frontend đã có adapter trong `src/utils/analysis.js` để chuẩn hóa một số tên field phổ biến. Nếu response Backend khác, chỉnh adapter tại file này.

## 4. Cấu trúc thư mục

```text
src/
├── assets/
│   └── main.css                 # Design system và responsive styles
├── components/
│   ├── AppHeader.vue            # Header điều hướng
│   ├── ModelSelector.vue        # Chọn 1–3 mô hình
│   ├── PredictionCard.vue       # Kết quả từng mô hình
│   └── ScoreGauge.vue           # Đồng hồ Safety Score
├── router/
│   └── index.js                 # Vue Router
├── services/
│   └── api.js                   # Axios và cấu hình API
├── stores/
│   └── analysis.js               # Chia sẻ kết quả giữa các trang
├── utils/
│   └── analysis.js              # Model options, chuẩn hóa response
├── views/
│   ├── HomeView.vue             # Nhập URL và chọn mô hình
│   └── DashboardView.vue        # Dashboard kết quả
├── App.vue
└── main.js
```

## 5. Lưu ý tích hợp
- Tên endpoint và payload là hợp đồng API đề xuất vì mô tả hiện tại chưa cung cấp endpoint Backend cụ thể. Đồng bộ `VITE_ANALYZE_ENDPOINT`, payload và adapter với API thật.
- Backend cần bật CORS cho địa chỉ frontend, ví dụ `http://localhost:5173`.
- Kết quả đang lưu trong state phía client; refresh trang Dashboard sẽ mất kết quả. Nếu cần chia sẻ link báo cáo hoặc lưu lịch sử, nên bổ sung API lưu kết quả và route theo `analysis_id`.
- Safety Score chỉ dùng `safety_score` Backend trả về. Nếu Backend chưa có trường này, giao diện tạm tính tỷ lệ mô hình dự đoán Safe trên tổng số mô hình; đây là chỉ số đồng thuận đơn giản, không phải xác suất an toàn đã hiệu chuẩn.
- Frontend không tự truy cập URL người dùng cung cấp. Việc phân tích, DNS lookup, redirect inspection và gọi dịch vụ threat-intelligence cần thực hiện an toàn ở Backend.
