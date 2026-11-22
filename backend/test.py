"""Kiểm thử nhanh backend mà không cần khởi động HTTP server.

Ví dụ (chạy từ thư mục gốc dự án):
    python -m backend.test --url https://www.example.com --models bert_phishing
    python -m backend.test --url https://paypal-login.example.xyz \
        --models bayesian_bert bert_phishing neural_symbolic
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="backslashreplace")

from backend.config import MODEL_IDS
from backend.controllers.predict_controller import analyze_url
from backend.services.prediction_service import model_manager


def main() -> int:
    parser = argparse.ArgumentParser(description="Smoke test backend")
    parser.add_argument(
        "--url",
        default="https://www.example.com",
        help="URL cần phân tích",
    )
    parser.add_argument(
        "--models",
        nargs="+",
        default=["bert_phishing"],
        choices=list(MODEL_IDS),
        help="Danh sách mô hình (1 - 3)",
    )
    parser.add_argument(
        "--vram-only",
        action="store_true",
        help="Chỉ in thông tin thiết bị/VRAM",
    )
    args = parser.parse_args()

    print("Thiết bị/VRAM:")
    print(json.dumps(model_manager.vram_snapshot(), ensure_ascii=False, indent=2))

    if args.vram_only:
        return 0

    if not 1 <= len(args.models) <= 3:
        parser.error("Số mô hình phải từ 1 đến 3.")

    started = time.perf_counter()
    result = analyze_url(args.url, args.models)
    elapsed = time.perf_counter() - started

    summary = {
        "url": result["normalized_url"],
        "summary": result["summary"],
        "predictions": [
            {
                "id": item["id"],
                "name": item["name"],
                "label": item["label"],
                "label_text": item["label_text"],
                "confidence": item["confidence"],
                "probabilities": item["probabilities"],
                "uncertainty": item["uncertainty"],
                "device": item["device"],
                "elapsed_ms": item["elapsed_ms"],
                "gpu_peak_gb": item["gpu_peak_gb"],
            }
            for item in result["predictions"]
        ],
        "vram": result["vram"],
        "warnings": result["warnings"],
    }

    print("\nKết quả:")
    print(json.dumps(summary, ensure_ascii=False, indent=2, default=str))
    print(f"\nTổng thời gian: {elapsed:.2f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
