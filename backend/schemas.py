"""Pydantic schemas cho API."""

from pydantic import BaseModel, Field, field_validator

from backend.config import (
    MAX_MODELS_PER_REQUEST,
    MAX_URL_LENGTH,
    MIN_MODELS_PER_REQUEST,
    MODEL_IDS,
)


class PredictRequest(BaseModel):
    url: str = Field(
        ...,
        min_length=1,
        max_length=MAX_URL_LENGTH,
        description="URL cần phân tích",
        examples=["https://www.example.com/login"],
    )
    models: list[str] = Field(
        ...,
        min_length=MIN_MODELS_PER_REQUEST,
        max_length=MAX_MODELS_PER_REQUEST,
        description="Danh sách id mô hình được chọn (1 - 3 mô hình)",
        examples=[["bert_phishing", "neural_symbolic"]],
    )

    @field_validator("url")
    @classmethod
    def _strip_url(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("URL không được để trống.")
        return value

    @field_validator("models")
    @classmethod
    def _validate_models(cls, value: list[str]) -> list[str]:
        # Loại bỏ khoảng trắng và kiểm tra trùng lặp
        cleaned = [item.strip() for item in value if item and item.strip()]

        if not cleaned:
            raise ValueError("Phải chọn ít nhất một mô hình.")

        if len(set(cleaned)) != len(cleaned):
            raise ValueError("Danh sách mô hình không được trùng lặp.")

        invalid = [item for item in cleaned if item not in MODEL_IDS]
        if invalid:
            raise ValueError(
                f"Mô hình không hợp lệ: {', '.join(invalid)}. "
                f"Các mô hình hỗ trợ: {', '.join(MODEL_IDS)}."
            )

        return cleaned


class ModelInfo(BaseModel):
    id: str
    name: str
    description: str
    file: str
    available: bool
    estimated_vram_gb: float


class ModelsResponse(BaseModel):
    models: list[ModelInfo]
    max_models_per_request: int
    vram: dict
