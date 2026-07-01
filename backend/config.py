"""
config.py

Cấu hình tập trung cho ứng dụng ONLYOFFICE + AI Editor.
Tất cả giá trị có thể override qua biến môi trường.
"""

from __future__ import annotations

import os
from pathlib import Path

# ── Đường dẫn thư mục ──────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent
STORAGE_DIR = BASE_DIR / "storage"
UPLOADS_DIR = STORAGE_DIR / "uploads"
EDITED_DIR = STORAGE_DIR / "edited"
MEDIA_DIR = STORAGE_DIR / "media"

# Tạo thư mục nếu chưa tồn tại
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
EDITED_DIR.mkdir(parents=True, exist_ok=True)
MEDIA_DIR.mkdir(parents=True, exist_ok=True)

# ── URL cấu hình ───────────────────────────────────────────────────
# URL của ONLYOFFICE Document Server (truy cập từ BROWSER)
ONLYOFFICE_URL: str = os.environ.get(
    "ONLYOFFICE_URL", "http://localhost:8080"
)

# URL của Backend (truy cập từ cả BROWSER và ONLYOFFICE Document Server)
# QUAN TRỌNG: Không dùng localhost nếu ONLYOFFICE chạy trong Docker —
# dùng IP thực hoặc hostname mà container có thể resolve được.
BACKEND_URL: str = os.environ.get(
    "BACKEND_URL", "http://localhost:8000"
)

# ── Google Gemini ───────────────────────────────────────────────────
# Lấy API key miễn phí tại: https://aistudio.google.com/apikey
GEMINI_API_KEY: str = os.environ.get(
    "GEMINI_API_KEY", os.environ.get("GOOGLE_API_KEY", "")
)
GEMINI_MODEL: str = os.environ.get("GEMINI_MODEL", "gemini-3.5-flash")

# ── ONLYOFFICE JWT (tùy chọn, khuyến nghị bật cho production) ──────
# Đặt JWT_SECRET = "" để tắt JWT (chỉ dành cho dev/testing)
JWT_SECRET: str = os.environ.get("JWT_SECRET", "")
JWT_HEADER: str = os.environ.get("JWT_HEADER", "Authorization")
