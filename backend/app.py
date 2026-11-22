"""Điểm khởi chạy ứng dụng backend."""

from __future__ import annotations

import logging
import os
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.routes import routes
from backend.services.prediction_service import model_manager


# ============================================================
# 1. CẤU HÌNH ENCODING CHO CONSOLE
# ============================================================

# Đảm bảo log tiếng Việt được hiển thị đúng trên console Windows.
# Một số terminal Windows sử dụng bảng mã mặc định không hỗ trợ UTF-8,
# có thể gây lỗi khi ghi log chứa ký tự tiếng Việt.
#
# reconfigure() chuyển encoding của stdout và stderr sang UTF-8.
# errors="backslashreplace" giúp thay thế các ký tự không thể mã hóa
# bằng dạng escape thay vì làm chương trình phát sinh lỗi.
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="backslashreplace")


# ============================================================
# 2. CẤU HÌNH HỆ THỐNG LOGGING
# ============================================================

# Thiết lập cấu hình logging chung cho toàn bộ ứng dụng.
logging.basicConfig(
    level=logging.INFO,  # Chỉ ghi nhận các log từ mức INFO trở lên.
    format=(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
    ),
)

# Tạo logger riêng cho module khởi chạy ứng dụng.
# Logger này được sử dụng để ghi nhận trạng thái hoạt động của backend.
logger = logging.getLogger(__name__)


# ============================================================
# 3. CẤU HÌNH CORS
# ============================================================

def _cors_origins() -> list[str]:
    """
    Xác định danh sách các origin được phép truy cập backend.

    Ưu tiên lấy danh sách origin từ biến môi trường URL_CORS_ORIGINS.
    Nếu biến môi trường chưa được thiết lập, sử dụng danh sách
    origin mặc định phục vụ quá trình phát triển frontend.

    Returns:
        list[str]: Danh sách các origin được phép gửi request.
    """

    # Đọc danh sách origin từ biến môi trường.
    # Các origin được phân tách bằng dấu phẩy.
    configured = os.getenv("URL_CORS_ORIGINS")

    if configured:
        # Tách chuỗi thành danh sách, loại bỏ khoảng trắng
        # và bỏ qua những phần tử rỗng.
        return [
            origin.strip()
            for origin in configured.split(",")
            if origin.strip()
        ]

    # Danh sách origin mặc định dành cho môi trường development.
    # Bao gồm các cổng thường được Vite và các frontend development server
    # sử dụng.
    return [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]


# ============================================================
# 4. QUẢN LÝ VÒNG ĐỜI ỨNG DỤNG (LIFESPAN)
# ============================================================

@asynccontextmanager
async def lifespan(_: FastAPI):
    """
    Quản lý các tác vụ được thực hiện khi backend khởi động
    và khi backend kết thúc hoạt động.

    Startup:
        - Ghi nhận trạng thái khởi động backend.
        - Kiểm tra và ghi log thông tin sử dụng VRAM.

    Shutdown:
        - Giải phóng tài nguyên của các mô hình.
        - Ghi nhận trạng thái dừng backend.

    Args:
        _: Đối tượng FastAPI hiện tại (không sử dụng trực tiếp).
    """

    # -------------------- STARTUP --------------------

    # Ghi nhận thông báo backend đã khởi động thành công.
    logger.info("Backend nhận diện URL độc hại đã khởi động.")

    # Lấy thông tin sử dụng VRAM hiện tại thông qua model_manager.
    # Giúp theo dõi tài nguyên GPU trong quá trình vận hành.
    logger.info("VRAM: %s", model_manager.vram_snapshot())

    # Cho phép ứng dụng tiếp tục hoạt động và xử lý request.
    yield

    # -------------------- SHUTDOWN --------------------

    # Giải phóng các mô hình và tài nguyên liên quan
    # trước khi backend kết thúc hoạt động.
    model_manager.release()

    # Ghi nhận thông báo backend đã dừng.
    logger.info("Backend đã dừng.")


# ============================================================
# 5. KHỞI TẠO FASTAPI APPLICATION
# ============================================================

app = FastAPI(
    # Tên hệ thống hiển thị trên giao diện Swagger UI.
    title="Hệ thống nhận diện URL độc hại",

    # Mô tả chức năng và kiến trúc xử lý của hệ thống.
    description=(
        "API phân tích URL bằng Bayesian BERT, BERT Phishing và "
        "Neural Symbolic BERT. Các mô hình được chạy tuần tự trên GPU "
        "để tránh tràn VRAM."
    ),

    # Phiên bản hiện tại của API.
    version="1.0.0",

    # Đăng ký lifespan để quản lý tài nguyên khi khởi động
    # và khi tắt ứng dụng.
    lifespan=lifespan,
)


# ============================================================
# 6. CẤU HÌNH CORS MIDDLEWARE
# ============================================================

# Đăng ký CORS Middleware để cho phép frontend truy cập backend
# từ các origin đã được cấu hình trong _cors_origins().
app.add_middleware(
    CORSMiddleware,

    # Danh sách domain được phép gửi request đến backend.
    allow_origins=_cors_origins(),

    # Cho phép gửi thông tin xác thực như cookies hoặc credentials.
    allow_credentials=True,

    # Cho phép tất cả các HTTP methods: GET, POST, PUT, DELETE,...
    allow_methods=["*"],

    # Cho phép tất cả các HTTP headers trong request.
    allow_headers=["*"],
)


# ============================================================
# 7. ĐĂNG KÝ API ROUTERS
# ============================================================

# Đưa toàn bộ các endpoint được định nghĩa trong routes vào ứng dụng.
# Giúp tách biệt phần định nghĩa API khỏi file khởi chạy chính.
app.include_router(router=routes.router)


# ============================================================
# 8. ROOT ENDPOINT - KIỂM TRA THÔNG TIN BACKEND
# ============================================================

@app.get("/", tags=["meta"])
def root() -> dict[str, str]:
    """
    Endpoint gốc cung cấp thông tin cơ bản về backend.

    Returns:
        dict[str, str]: Thông tin tên dịch vụ và các endpoint quan trọng.
    """

    return {
        # Tên dịch vụ backend.
        "service": "Malicious URL Detection API",

        # Đường dẫn truy cập tài liệu API Swagger UI.
        "docs": "/docs",

        # Đường dẫn endpoint kiểm tra trạng thái hoạt động.
        "health": "/api/health",
    }