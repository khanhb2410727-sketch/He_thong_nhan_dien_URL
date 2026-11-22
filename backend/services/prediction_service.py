"""Quản lý tải mô hình và chạy dự đoán.

Chiến lược VRAM:
- Các mô hình được cache trên CPU (RAM).
- Tại một thời điểm chỉ có DUY NHẤT một mô hình được đưa lên GPU để inference.
- Sau khi inference xong, mô hình được đưa trở lại CPU và giải phóng cache CUDA.
- Nhờ vậy, dù người dùng chọn 3 mô hình thì VRAM đỉnh vẫn xấp xỉ mô hình lớn
  nhất, không phải tổng VRAM của cả 3 mô hình.
"""

from __future__ import annotations

import gc
import logging
import os
import threading
import time
from typing import Any

import torch

from backend.config import (
    BERT_MODEL_NAME,
    DEFAULT_DEVICE,
    DEFAULT_MAX_TOKENS,
    DEFAULT_MC_SAMPLES,
    DEFAULT_VRAM_RESERVE_GB,
    MODEL_IDS,
    MODEL_SPECS,
    MODELS_DIR,
)

logger = logging.getLogger(__name__)

BYTES_PER_GB = 1024 ** 3


def _is_oom_error(exc: BaseException) -> bool:
    if isinstance(exc, torch.cuda.OutOfMemoryError):
        return True
    return "out of memory" in str(exc).lower()


class ModelManager:
    """Tải mô hình theo nhu cầu và chạy inference an toàn với VRAM."""

    def __init__(self) -> None:
        self._models: dict[str, torch.nn.Module] = {}
        self._tokenizer = None
        self._lock = threading.RLock()
        self._device_pref = DEFAULT_DEVICE
        self._max_tokens = DEFAULT_MAX_TOKENS
        self._mc_samples = max(1, DEFAULT_MC_SAMPLES)
        self._vram_reserve_gb = max(0.0, DEFAULT_VRAM_RESERVE_GB)

    # ------------------------------------------------------------------
    # Thông tin mô hình / thiết bị
    # ------------------------------------------------------------------
    @property
    def loaded_models(self) -> list[str]:
        with self._lock:
            return sorted(self._models.keys())

    def list_models(self) -> list[dict[str, Any]]:
        result = []
        for model_id in MODEL_IDS:
            spec = MODEL_SPECS[model_id]
            result.append(
                {
                    "id": model_id,
                    "name": spec["name"],
                    "description": spec["description"],
                    "file": spec["file"],
                    "available": (MODELS_DIR / spec["file"]).is_file(),
                    "estimated_vram_gb": spec["estimated_vram_gb"],
                }
            )
        return result

    def vram_snapshot(self) -> dict[str, Any]:
        info: dict[str, Any] = {
            "cuda_available": torch.cuda.is_available(),
            "preferred_device": self._device_pref,
            "strategy": "sequential_gpu",
            "max_models_on_gpu": 1,
            "reserve_gb": self._vram_reserve_gb,
        }

        if not torch.cuda.is_available():
            info.update(
                {
                    "device": "cpu",
                    "gpu_name": None,
                    "total_gb": None,
                    "free_gb": None,
                    "allocated_gb": None,
                    "reserved_gb": None,
                }
            )
            return info

        free_bytes, total_bytes = torch.cuda.mem_get_info()
        info.update(
            {
                "device": f"cuda:{torch.cuda.current_device()}",
                "gpu_name": torch.cuda.get_device_name(0),
                "total_gb": round(total_bytes / BYTES_PER_GB, 2),
                "free_gb": round(free_bytes / BYTES_PER_GB, 2),
                "allocated_gb": round(torch.cuda.memory_allocated() / BYTES_PER_GB, 2),
                "reserved_gb": round(torch.cuda.memory_reserved() / BYTES_PER_GB, 2),
            }
        )
        return info

    # ------------------------------------------------------------------
    # Tải mô hình
    # ------------------------------------------------------------------
    def _get_tokenizer(self):
        if self._tokenizer is None:
            from transformers import AutoTokenizer

            logger.info("Đang tải tokenizer '%s'...", BERT_MODEL_NAME)
            self._tokenizer = AutoTokenizer.from_pretrained(BERT_MODEL_NAME)
        return self._tokenizer

    def _instantiate(self, model_id: str) -> torch.nn.Module:
        if model_id == "bert_phishing":
            from backend.models.src.bert_base.model import BERTClassifier

            return BERTClassifier(model_name=BERT_MODEL_NAME, num_classes=2)

        if model_id == "bayesian_bert":
            from backend.models.src.bayes_model.model import BayesianBERT

            return BayesianBERT()

        if model_id == "neural_symbolic":
            from backend.models.src.neural_symbolic.model import NeuralSymbolicModel

            return NeuralSymbolicModel(model_name=BERT_MODEL_NAME, num_classes=2)

        raise ValueError(f"Mô hình không hỗ trợ: {model_id}")

    def _load_checkpoint_state(self, path) -> dict[str, torch.Tensor]:
        checkpoint = torch.load(
            path,
            map_location="cpu",
            weights_only=True,
            mmap=True,
        )

        if isinstance(checkpoint, dict) and "model_state_dict" in checkpoint:
            state_dict = checkpoint["model_state_dict"]
        else:
            state_dict = checkpoint

        if not isinstance(state_dict, dict):
            raise ValueError(f"Checkpoint không hợp lệ: {path}")

        return state_dict

    def _get_or_load(self, model_id: str) -> torch.nn.Module:
        if model_id in self._models:
            return self._models[model_id]

        spec = MODEL_SPECS[model_id]
        path = MODELS_DIR / spec["file"]

        if not path.is_file():
            raise FileNotFoundError(f"Không tìm thấy file mô hình: {path}")

        logger.info("Đang tải mô hình '%s' từ %s", spec["name"], path)
        started = time.perf_counter()

        model = self._instantiate(model_id)
        state_dict = self._load_checkpoint_state(path)
        model.load_state_dict(state_dict, strict=True)
        model.eval()

        del state_dict
        gc.collect()

        self._models[model_id] = model
        logger.info(
            "Đã tải '%s' trong %.2fs",
            spec["name"],
            time.perf_counter() - started,
        )
        return model

    # ------------------------------------------------------------------
    # Chọn thiết bị
    # ------------------------------------------------------------------
    def _select_device(self, spec: dict[str, Any]) -> tuple[str, str | None]:
        if self._device_pref == "cpu":
            return "cpu", "Cấu hình URL_DETECTOR_DEVICE=cpu nên mô hình chạy trên CPU."

        if not torch.cuda.is_available():
            return "cpu", "Không phát hiện CUDA, mô hình chạy trên CPU."

        free_bytes, _ = torch.cuda.mem_get_info()
        free_gb = free_bytes / BYTES_PER_GB
        required_gb = spec["estimated_vram_gb"] + self._vram_reserve_gb

        if free_gb < required_gb:
            return "cpu", (
                f"VRAM khả dụng {free_gb:.2f} GB nhỏ hơn mức cần khoảng "
                f"{required_gb:.2f} GB cho {spec['name']}, chuyển sang CPU."
            )

        return "cuda", None

    @staticmethod
    def _move_to_cpu(model: torch.nn.Module) -> None:
        try:
            model.to("cpu")
        except Exception:  # pragma: no cover - bảo vệ khi dọn dẹp
            logger.exception("Không thể chuyển mô hình về CPU")

    @staticmethod
    def _empty_cuda_cache() -> None:
        if torch.cuda.is_available():
            gc.collect()
            torch.cuda.empty_cache()

    # ------------------------------------------------------------------
    # Inference
    # ------------------------------------------------------------------
    def _forward(
        self,
        model_id: str,
        model: torch.nn.Module,
        encoded: dict[str, torch.Tensor],
        url: str,
    ) -> dict[str, Any]:
        input_ids = encoded["input_ids"]
        attention_mask = encoded["attention_mask"]
        token_type_ids = encoded.get("token_type_ids")

        if model_id == "bayesian_bert":
            sample_probs = []
            for _ in range(self._mc_samples):
                logits = model(input_ids=input_ids, attention_mask=attention_mask)
                sample_probs.append(torch.softmax(logits, dim=-1))

            stacked = torch.stack(sample_probs, dim=0)
            mean_probs = stacked.mean(dim=0)[0]
            std_probs = stacked.std(dim=0, unbiased=False)[0]
            probs = mean_probs
            uncertainty = float(std_probs[1].item())
            details = {
                "mc_samples": self._mc_samples,
                "std_malicious": uncertainty,
                "note": "Độ bất định được ước lượng bằng Monte-Carlo sampling.",
            }

        elif model_id == "neural_symbolic":
            output = model(
                input_ids,
                attention_mask,
                [url],
                token_type_ids,
            )
            probs = torch.softmax(output["logits"], dim=-1)[0]
            uncertainty = None

            symbolic = output["symbolic_results"][0]
            neural_probs = output["neural_probs"][0]
            details = {
                "symbolic_score": float(symbolic.score),
                "symbolic_label": int(symbolic.predicted_label),
                "active_rules": symbolic.active_rules,
                "signals": symbolic.signals,
                "metadata": symbolic.metadata,
                "feature_vector": symbolic.feature_vector,
                "neural_malicious_probability": float(neural_probs[1].item()),
            }

        else:
            output = model(
                input_ids=input_ids,
                attention_mask=attention_mask,
                token_type_ids=token_type_ids,
            )
            probs = torch.softmax(output["logits"], dim=-1)[0]
            uncertainty = None
            details = {}

        benign_prob = float(probs[0].item())
        malicious_prob = float(probs[1].item())
        label = 1 if malicious_prob >= 0.5 else 0

        return {
            "label": label,
            "label_text": "Malicious" if label == 1 else "Benign",
            "confidence": round(max(benign_prob, malicious_prob), 6),
            "probabilities": {
                "benign": round(benign_prob, 6),
                "malicious": round(malicious_prob, 6),
            },
            "uncertainty": None if uncertainty is None else round(uncertainty, 6),
            "details": details,
        }

    def _infer_one(
        self,
        model_id: str,
        model: torch.nn.Module,
        encoded: dict[str, torch.Tensor],
        url: str,
    ) -> tuple[dict[str, Any], dict[str, Any], list[str]]:
        spec = MODEL_SPECS[model_id]
        warnings: list[str] = []

        device, warning = self._select_device(spec)
        if warning:
            warnings.append(warning)

        started = time.perf_counter()
        gpu_peak_gb = 0.0
        used_cuda = device == "cuda"

        def run(target_device: str) -> dict[str, Any]:
            nonlocal gpu_peak_gb

            if target_device == "cuda":
                torch.cuda.synchronize()
                torch.cuda.reset_peak_memory_stats()

            model.to(target_device)
            device_encoded = {
                key: value.to(target_device)
                for key, value in encoded.items()
            }

            with torch.inference_mode():
                result = self._forward(model_id, model, device_encoded, url)

            if target_device == "cuda":
                torch.cuda.synchronize()
                gpu_peak_gb = torch.cuda.max_memory_allocated() / BYTES_PER_GB

            return result

        try:
            try:
                result = run(device)
            except (RuntimeError, torch.cuda.OutOfMemoryError) as exc:
                if device == "cuda" and _is_oom_error(exc):
                    logger.warning(
                        "Hết VRAM khi chạy '%s', thử lại trên CPU: %s",
                        spec["name"],
                        exc,
                    )
                    self._move_to_cpu(model)
                    self._empty_cuda_cache()
                    warnings.append(
                        f"Hết VRAM khi chạy {spec['name']} trên GPU; "
                        "đã tự động chuyển sang CPU."
                    )
                    device = "cpu"
                    used_cuda = False
                    result = run("cpu")
                else:
                    raise
        finally:
            if used_cuda:
                self._move_to_cpu(model)
                self._empty_cuda_cache()

        elapsed_ms = (time.perf_counter() - started) * 1000
        prediction = {
            "id": model_id,
            "name": spec["name"],
            **result,
            "device": device,
            "elapsed_ms": round(elapsed_ms, 2),
            "gpu_peak_gb": round(gpu_peak_gb, 3),
        }
        per_model = {
            "id": model_id,
            "name": spec["name"],
            "device": device,
            "elapsed_ms": round(elapsed_ms, 2),
            "gpu_peak_gb": round(gpu_peak_gb, 3),
        }
        return prediction, per_model, warnings

    def predict_many(
        self,
        url: str,
        model_ids: list[str],
    ) -> tuple[list[dict[str, Any]], dict[str, Any], list[str]]:
        unknown = [model_id for model_id in model_ids if model_id not in MODEL_IDS]
        if unknown:
            raise ValueError(f"Mô hình không hỗ trợ: {', '.join(unknown)}")

        warnings: list[str] = []

        with self._lock:
            tokenizer = self._get_tokenizer()
            encoded = tokenizer(
                url,
                return_tensors="pt",
                truncation=True,
                max_length=self._max_tokens,
                padding=False,
            )
            encoded = {
                key: value
                for key, value in encoded.items()
                if key in {"input_ids", "attention_mask", "token_type_ids"}
            }

            vram_before = self.vram_snapshot()
            started = time.perf_counter()

            predictions: list[dict[str, Any]] = []
            per_model: list[dict[str, Any]] = []

            for model_id in model_ids:
                model = self._get_or_load(model_id)
                prediction, model_report, model_warnings = self._infer_one(
                    model_id, model, encoded, url
                )
                predictions.append(prediction)
                per_model.append(model_report)
                warnings.extend(model_warnings)

            total_ms = (time.perf_counter() - started) * 1000
            vram_after = self.vram_snapshot()

            if len(model_ids) > 1:
                warnings.append(
                    "Các mô hình được chạy tuần tự trên GPU và giải phóng VRAM "
                    "sau mỗi lượt để tránh tràn VRAM."
                )

            vram_report = {
                "before": vram_before,
                "after": vram_after,
                "per_model": per_model,
                "peak_gpu_gb": round(
                    max((item["gpu_peak_gb"] for item in per_model), default=0.0),
                    3,
                ),
                "strategy": "sequential_gpu",
                "max_models_on_gpu": 1,
                "note": (
                    "VRAM đỉnh xấp xỉ mô hình lớn nhất, không phải tổng VRAM "
                    "của tất cả mô hình được chọn."
                ),
            }

        # Loại bỏ cảnh báo trùng lặp nhưng giữ thứ tự
        warnings = list(dict.fromkeys(warnings))

        return predictions, {
            "elapsed_ms": round(total_ms, 2),
            "vram": vram_report,
        }, warnings

    def release(self) -> None:
        with self._lock:
            self._models.clear()
            self._tokenizer = None
            gc.collect()
            self._empty_cuda_cache()
        logger.info("Đã giải phóng mô hình và cache.")


model_manager = ModelManager()
