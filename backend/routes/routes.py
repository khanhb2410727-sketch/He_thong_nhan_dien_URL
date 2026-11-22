"""Định nghĩa các API endpoint."""

from typing import Any

from fastapi import APIRouter

from backend.config import MAX_MODELS_PER_REQUEST
from backend.controllers.predict_controller import analyze_url
from backend.schemas import ModelsResponse, PredictRequest
from backend.services.prediction_service import model_manager

router = APIRouter(prefix="/api", tags=["url-analysis"])


@router.get("/models", response_model=ModelsResponse)
def get_models() -> dict[str, Any]:
    """Danh sách mô hình hiện có và trạng thái VRAM/thiết bị."""
    return {
        "models": model_manager.list_models(),
        "max_models_per_request": MAX_MODELS_PER_REQUEST,
        "vram": model_manager.vram_snapshot(),
    }


@router.post("/predict")
def predict(payload: PredictRequest) -> dict[str, Any]:
    """Phân tích URL bằng các mô hình được chọn (1 - 3 mô hình)."""
    return analyze_url(payload.url, payload.models)


@router.get("/vram")
def get_vram() -> dict[str, Any]:
    """Thông tin VRAM hiện tại của GPU."""
    return model_manager.vram_snapshot()


@router.get("/health")
def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "models_loaded": model_manager.loaded_models,
        "vram": model_manager.vram_snapshot(),
    }
