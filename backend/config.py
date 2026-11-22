"""Cấu hình chung cho backend nhận diện URL độc hại."""

import os
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent
MODELS_DIR = Path(os.getenv("URL_MODELS_DIR", str(BACKEND_DIR / "models")))

BERT_MODEL_NAME = os.getenv("URL_BERT_MODEL", "bert-base-uncased")

# Số mô hình tối đa cho một yêu cầu (theo README: 1 - 3)
MAX_MODELS_PER_REQUEST = 3
MIN_MODELS_PER_REQUEST = 1

MAX_URL_LENGTH = 4096

# Giới hạn token khi đưa URL vào BERT
DEFAULT_MAX_TOKENS = int(os.getenv("URL_MAX_TOKENS", "128"))

# Số lần lấy mẫu Monte-Carlo cho Bayesian BERT
DEFAULT_MC_SAMPLES = int(os.getenv("URL_BAYES_MC_SAMPLES", "20"))

# Khoảng VRAM dự phòng (GB) trước khi quyết định đưa một mô hình lên GPU
DEFAULT_VRAM_RESERVE_GB = float(os.getenv("URL_VRAM_RESERVE_GB", "0.5"))

# Chế độ thiết bị: auto | cuda | cpu
DEFAULT_DEVICE = os.getenv("URL_DETECTOR_DEVICE", "auto").strip().lower()

# Định nghĩa các mô hình hiện có.
# estimated_vram_gb dùng để ước lượng VRAM cần cho MỘT mô hình khi chạy inference.
# Giá trị đã bao gồm tham số, activation và phần dự phòng cho CUDA context.
MODEL_SPECS = {
    "bayesian_bert": {
        "id": "bayesian_bert",
        "name": "Bayesian BERT",
        "file": "bayesian_bert_checkpoint.pth",
        "description": "BERT với lớp Bayesian, hỗ trợ ước lượng độ bất định.",
        "estimated_vram_gb": 1.0,
    },
    "bert_phishing": {
        "id": "bert_phishing",
        "name": "BERT Phishing",
        "file": "bert_phishing_final.pth",
        "description": "BERT-base-uncased phân loại URL phishing.",
        "estimated_vram_gb": 1.0,
    },
    "neural_symbolic": {
        "id": "neural_symbolic",
        "name": "Neural Symbolic BERT",
        "file": "neural_symbolic_bert.pth",
        "description": "Kết hợp BERT với suy luận luật Symbolic trên URL.",
        "estimated_vram_gb": 0.8,
    },
}

MODEL_IDS = tuple(MODEL_SPECS.keys())
