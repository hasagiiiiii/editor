"""
ai_editor.py

Hàm gọi Google Gemini API để chỉnh sửa văn bản theo yêu cầu người dùng.
Sử dụng google-genai SDK (mới nhất) với response_mime_type="application/json"
để đảm bảo kết quả luôn là JSON hợp lệ.

Cách dùng:
    from ai_editor import generate_ai_edit

    paragraphs = {"p_1": "Văn bản gốc...", "p_2": "Đoạn hai..."}
    edited = generate_ai_edit(paragraphs, "Sửa lỗi chính tả và viết trang trọng hơn")

Dependencies:
    pip install google-genai
"""

from __future__ import annotations

import json
import logging
import os
from typing import Dict, Optional

from google import genai
from google.genai import types

__all__ = ["generate_ai_edit"]

logger = logging.getLogger(__name__)

# ── System Prompt ───────────────────────────────────────────────────
_SYSTEM_PROMPT = """\
Bạn là một biên tập viên văn bản cao cấp, chuyên nghiệp và cực kỳ tỉ mỉ.

## NHIỆM VỤ
Nhận một đối tượng JSON chứa các đoạn văn bản (mỗi key là ID đoạn, value là nội dung).
Chỉnh sửa nội dung từng đoạn theo yêu cầu của người dùng.

## QUY TẮC BẮT BUỘC — KHÔNG ĐƯỢC VI PHẠM
1. Kết quả trả về PHẢI là một JSON object hợp lệ, KHÔNG kèm bất kỳ lời giải thích, \
ghi chú, hoặc markdown nào khác.
2. GIỮ NGUYÊN tất cả các key gốc (p_1, p_2, ...). KHÔNG thêm key mới, KHÔNG xóa key.
3. Số lượng key trong kết quả PHẢI BẰNG ĐÚNG số lượng key đầu vào.
4. CHỈ chỉnh sửa phần value (nội dung văn bản). Key phải giữ nguyên tên và thứ tự.
5. Nếu một đoạn văn đã hoàn hảo và không cần sửa, giữ nguyên nội dung gốc.

## ĐỊNH DẠNG ĐẦU RA
Trả về DUY NHẤT một JSON object. Ví dụ:
{"p_1": "Nội dung đã chỉnh sửa", "p_2": "Nội dung đã chỉnh sửa"}
"""


def generate_ai_edit(
    extracted_text_dict: Dict[str, str],
    user_requirement: str,
    *,
    model: str = "gemini-3.5-flash",
    api_key: Optional[str] = None,
    temperature: float = 0.4,
) -> Dict[str, str]:
    """
    Gọi Google Gemini API để chỉnh sửa văn bản theo yêu cầu người dùng.

    Sử dụng response_mime_type="application/json" để đảm bảo
    kết quả luôn là JSON hợp lệ.

    Args:
        extracted_text_dict: Dict ánh xạ paragraph ID → nội dung gốc.
            Ví dụ: {"p_1": "Đoạn 1", "p_2": "Đoạn 2"}
        user_requirement: Yêu cầu chỉnh sửa từ người dùng.
        model: Tên model Gemini (mặc định: "gemini-3.5-flash").
        api_key: API key. Nếu None, lấy từ GEMINI_API_KEY hoặc GOOGLE_API_KEY.
        temperature: Mức độ sáng tạo (0.0–2.0). Mặc định 0.4.

    Returns:
        Dictionary có cùng cấu trúc key với đầu vào, value là text đã sửa.

    Raises:
        ValueError: Nếu đầu vào không hợp lệ hoặc API trả về JSON sai cấu trúc.
        RuntimeError: Nếu gọi API thất bại.
    """
    # ── Validation ──────────────────────────────────────────────────
    if not extracted_text_dict:
        raise ValueError("extracted_text_dict không được rỗng.")
    if not user_requirement or not user_requirement.strip():
        raise ValueError("user_requirement không được rỗng.")

    # ── Resolve API key ─────────────────────────────────────────────
    resolved_key = (
        api_key
        or os.environ.get("GEMINI_API_KEY")
        or os.environ.get("GOOGLE_API_KEY")
    )
    if not resolved_key:
        raise ValueError(
            "Thiếu API key. Truyền qua tham số 'api_key' "
            "hoặc đặt biến môi trường GEMINI_API_KEY / GOOGLE_API_KEY.\n"
            "Lấy API key miễn phí tại: https://aistudio.google.com/apikey"
        )

    # ── Khởi tạo client ────────────────────────────────────────────
    client = genai.Client(api_key=resolved_key)

    # ── Chuẩn bị user prompt ───────────────────────────────────────
    input_json_str = json.dumps(
        extracted_text_dict, ensure_ascii=False, indent=2
    )

    user_prompt = (
        f"## YÊU CẦU CHỈNH SỬA\n{user_requirement}\n\n"
        f"## VĂN BẢN CẦN CHỈNH SỬA (JSON)\n```json\n{input_json_str}\n```"
    )

    # ── Gọi Gemini API ─────────────────────────────────────────────
    logger.info(
        "Gọi Gemini API — model=%s, paragraphs=%d, requirement='%s'",
        model,
        len(extracted_text_dict),
        user_requirement[:80],
    )

    try:
        response = client.models.generate_content(
            model=model,
            contents=user_prompt,
            config=types.GenerateContentConfig(
                system_instruction=_SYSTEM_PROMPT,
                response_mime_type="application/json",
                temperature=temperature,
            ),
        )
    except Exception as e:
        # Fallback to gemini-3.5-flash if another model failed
        if model != "gemini-3.5-flash":
            logger.warning(f"Model {model} thất bại do lỗi quota/hệ thống. Đang thử fallback sang gemini-3.5-flash...")
            try:
                response = client.models.generate_content(
                    model="gemini-3.5-flash",
                    contents=user_prompt,
                    config=types.GenerateContentConfig(
                        system_instruction=_SYSTEM_PROMPT,
                        response_mime_type="application/json",
                        temperature=temperature,
                    ),
                )
            except Exception as fallback_err:
                logger.error("Lỗi khi gọi Gemini API (Fallback cũng thất bại): %s", fallback_err)
                raise RuntimeError(
                    f"Không thể gọi Gemini API (đã thử cả {model} và gemini-3.5-flash): {fallback_err}"
                ) from fallback_err
        else:
            logger.error("Lỗi khi gọi Gemini API: %s", e)
            raise RuntimeError(f"Không thể gọi Gemini API: {e}") from e

    # ── Parse response ──────────────────────────────────────────────
    raw_content = response.text
    if not raw_content:
        raise ValueError("Gemini API trả về response rỗng.")

    logger.debug("Raw API response: %s", raw_content[:500])

    try:
        edited_dict: Dict[str, str] = json.loads(raw_content)
    except json.JSONDecodeError as e:
        logger.error("Không thể parse JSON từ API response: %s", e)
        raise ValueError(
            f"Gemini API trả về JSON không hợp lệ: {e}\n"
            f"Response: {raw_content[:300]}"
        ) from e

    # ── Validate cấu trúc kết quả ──────────────────────────────────
    if not isinstance(edited_dict, dict):
        raise ValueError(
            f"Kết quả phải là JSON object (dict), "
            f"nhận được: {type(edited_dict).__name__}"
        )

    input_keys = set(extracted_text_dict.keys())
    output_keys = set(edited_dict.keys())

    missing_keys = input_keys - output_keys
    extra_keys = output_keys - input_keys

    if missing_keys:
        logger.warning(
            "API thiếu %d key: %s — sử dụng nội dung gốc.",
            len(missing_keys),
            sorted(missing_keys),
        )
        for key in missing_keys:
            edited_dict[key] = extracted_text_dict[key]

    if extra_keys:
        logger.warning(
            "API trả về %d key thừa: %s — loại bỏ.",
            len(extra_keys),
            sorted(extra_keys),
        )
        for key in extra_keys:
            del edited_dict[key]

    # Đảm bảo tất cả value là string
    for key, value in edited_dict.items():
        if not isinstance(value, str):
            logger.warning(
                "Value của key '%s' không phải string (%s) — ép kiểu.",
                key,
                type(value).__name__,
            )
            edited_dict[key] = str(value)

    logger.info(
        "Chỉnh sửa AI hoàn tất — %d đoạn đã xử lý.",
        len(edited_dict),
    )

    return edited_dict
