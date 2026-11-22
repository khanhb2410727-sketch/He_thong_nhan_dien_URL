"""Controller điều phối quá trình phân tích URL."""

from __future__ import annotations

import logging
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from fastapi import HTTPException

from backend.services.analysis_service import analysis_service
from backend.services.prediction_service import model_manager
from backend.services.url_service import URLService

logger = logging.getLogger(__name__)

_url_service = URLService(timeout=5)

_URL_FLAG_LABELS = {
    "has_punycode": "Hostname sử dụng punycode (xn--)",
    "has_suspicious_tld": "Tên miền sử dụng TLD đáng ngờ",
    "has_shortened_url": "URL được rút gọn",
    "has_suspicious_file_extension": "Đường dẫn có đuôi file đáng ngờ",
    "has_ip_host": "Hostname là địa chỉ IP",
}

_RULE_LABELS = {
    "ip_address": "Hostname là địa chỉ IP",
    "punycode": "Hostname chứa punycode",
    "excessive_subdomains": "Số lượng subdomain bất thường",
    "long_url": "URL quá dài",
    "special_character_anomaly": "Nhiều ký tự đặc biệt",
    "suspicious_keywords": "Chứa từ khóa đáng ngờ",
    "brand_impersonation": "Có dấu hiệu giả mạo thương hiệu",
    "suspicious_extension": "Đuôi file đáng ngờ",
    "high_digit_ratio": "Tỷ lệ chữ số cao trong hostname",
    "encoding_anomaly": "Tỷ lệ mã hóa URL bất thường",
    "excessive_hyphens": "Nhiều dấu gạch ngang trong hostname",
    "suspicious_redirect": "Tham số chuyển hướng ra hostname khác",
}


def _build_suspicious_signals(
    url_info: dict[str, Any],
    predictions: list[dict[str, Any]],
) -> list[str]:
    """Tổng hợp các dấu hiệu đáng ngờ từ đặc trưng URL và luật phát hiện của mô hình."""
    signals: list[str] = []

    for key, label in _URL_FLAG_LABELS.items():
        if url_info.get(key):
            signals.append(label)

    redirect_count = url_info.get("redirect_count")
    if isinstance(redirect_count, int) and redirect_count >= 2:
        signals.append(f"URL chuyển hướng {redirect_count} lần")

    if (url_info.get("count_special") or 0) >= 4:
        signals.append("URL chứa nhiều ký tự đặc biệt")

    if (url_info.get("url_entropy") or 0) >= 4.5:
        signals.append("Độ ngẫu nhiên (entropy) của URL cao")

    for prediction in predictions:
        if prediction["id"] != "neural_symbolic":
            continue

        for rule in prediction.get("details", {}).get("active_rules", []):
            name = rule.get("name") if isinstance(rule, dict) else None
            if name:
                signals.append(_RULE_LABELS.get(name, name))

    # Giữ thứ tự xuất hiện và loại bỏ trùng
    return list(dict.fromkeys(signals))


def _build_summary(
    predictions: list[dict[str, Any]],
    url_info: dict[str, Any],
) -> dict[str, Any]:
    """Tổng hợp kết quả biểu quyết của các mô hình và xác định mức độ rủi ro của URL."""
    total = len(predictions)
    malicious_votes = sum(1 for item in predictions if item["label"] == 1)
    benign_votes = total - malicious_votes

    average_confidence = (
        sum(item["confidence"] for item in predictions) / total
        if total else 0.0
    )
    average_malicious_probability = (
        sum(item["probabilities"]["malicious"] for item in predictions) / total
        if total else 0.0
    )

    if malicious_votes > benign_votes:
        verdict = "malicious"
    elif benign_votes > malicious_votes:
        verdict = "benign"
    else:
        verdict = (
            "malicious" if average_malicious_probability >= 0.5 else "benign"
        )

    signals = _build_suspicious_signals(url_info, predictions)
    agreement = len({item["label"] for item in predictions}) <= 1

    if verdict == "malicious":
        risk_level = (
            "high"
            if malicious_votes >= 2 and average_malicious_probability >= 0.85
            else "medium"
        )
    else:
        risk_level = (
            "low"
            if average_malicious_probability < 0.3 and not signals
            else "medium"
        )

    notes: list[str] = []
    if not agreement:
        notes.append("Các mô hình không đồng thuận về kết quả dự đoán.")
    if any(
        item["label"] == 1
        and item.get("uncertainty") is not None
        and item["uncertainty"] >= 0.15
        for item in predictions
    ):
        notes.append("Một mô hình có độ bất định cao, nên cân nhắc kết quả.")

    return {
        "total_models": total,
        "malicious_votes": malicious_votes,
        "benign_votes": benign_votes,
        "agreement": agreement,
        "verdict": verdict,
        "risk_level": risk_level,
        "average_confidence": round(average_confidence, 6),
        "average_malicious_probability": round(
            average_malicious_probability, 6
        ),
        "suspicious_signals": signals,
        "notes": notes,
    }


def analyze_url(url: str, model_ids: list[str]) -> dict[str, Any]:
    """Điều phối quá trình chuẩn hóa URL, dự đoán bằng mô hình và thu thập thông tin phân tích."""
    normalized_url = _url_service.normalize_url(url)

    if not normalized_url or not _url_service.validate_url(normalized_url):
        raise HTTPException(
            status_code=400,
            detail="URL không hợp lệ. Vui lòng nhập URL dạng http/https.",
        )

    started = time.perf_counter()

    with ThreadPoolExecutor(max_workers=2) as executor:
        prediction_future = executor.submit(
            model_manager.predict_many, normalized_url, model_ids
        )
        analysis_future = executor.submit(
            analysis_service.collect, normalized_url
        )

        try:
            predictions, timing, prediction_warnings = prediction_future.result()
        except FileNotFoundError as exc:
            logger.exception("Thiếu file mô hình")
            raise HTTPException(
                status_code=500,
                detail=str(exc),
            ) from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except Exception as exc:  # pragma: no cover - lỗi runtime của mô hình
            logger.exception("Lỗi khi chạy mô hình")
            raise HTTPException(
                status_code=500,
                detail=f"Lỗi khi chạy mô hình: {exc}",
            ) from exc

        analysis_warnings: list[str] = []
        try:
            analysis = analysis_future.result()
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except Exception as exc:  # pragma: no cover - lỗi mạng không mong đợi
            logger.exception("Lỗi khi thu thập thông tin URL")
            analysis = {
                "url_info": {
                    "url": normalized_url,
                    "registered_domain": None,
                },
                "redirect_info": {},
                "domain_info": {},
                "warnings": [],
            }
            analysis_warnings.append(
                f"Không thu thập được thông tin bổ sung: {exc}"
            )

    analysis_warnings.extend(analysis.pop("warnings", []))
    warnings = list(
        dict.fromkeys(prediction_warnings + analysis_warnings)
    )

    summary_info = {
        **analysis["url_info"],
        **analysis["redirect_info"],
    }
    summary = _build_summary(predictions, summary_info)

    return {
        "input_url": url,
        "normalized_url": normalized_url,
        "models_requested": model_ids,
        "predictions": predictions,
        "summary": summary,
        "url_info": analysis["url_info"],
        "redirect_info": analysis["redirect_info"],
        "domain_info": analysis["domain_info"],
        "timings": {
            "prediction_ms": timing["elapsed_ms"],
            "total_ms": round((time.perf_counter() - started) * 1000, 2),
        },
        "vram": timing["vram"],
        "warnings": warnings,
    }