"""
ai_editor.py

Hàm gọi Google Gemini API để chỉnh sửa văn bản theo yêu cầu người dùng.
Sử dụng google-genai SDK (mới nhất) với response_mime_type="application/json"
để đảm bảo kết quả luôn là JSON hợp lệ.
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
1. Nhận một đối tượng JSON chứa các đoạn văn bản của tài liệu gốc (mỗi key là ID đoạn, value là nội dung).
2. Chỉnh sửa nội dung tài liệu gốc theo yêu cầu của người dùng.
3. Nếu người dùng cung cấp thông tin tài liệu tham khảo, hãy kết hợp/đối chiếu thông tin từ tài liệu tham khảo để cập nhật vào tài liệu gốc.
4. Bạn có quyền sửa đổi nội dung đoạn gốc, xóa đoạn gốc, hoặc chèn thêm đoạn mới sau một đoạn gốc bất kỳ để tài liệu hoàn chỉnh nhất.

## QUY TẮC QUAN TRỌNG VỀ BỐ CỤC (TRÁNH VIẾT DÀY ĐẶC, DI DÍT)
1. **Chia nhỏ đoạn văn**:
   - TUYỆT ĐỐI KHÔNG gộp nhiều phần thông tin khác nhau (ví dụ: Tiêu đề mục, Mô tả, Thiết kế cấu hình, Thiết kế hiển thị, v.v.) vào chung một đoạn văn dài.
   - Hãy tách chúng thành các đoạn văn riêng biệt. Tạo nhiều phần tử hành động chỉnh sửa liên tiếp trong mảng `edits` (ví dụ: dùng `modify` để sửa tiêu đề, sau đó dùng liên tiếp các `insert_after` để chèn các đoạn mô tả, thiết kế cấu hình, thiết kế hiển thị riêng lẻ phía sau).
2. **Cách trình bày danh sách rõ ràng**:
   - Khi có nhiều ý liệt kê hoặc các bước thực hiện, mỗi ý phải là một đoạn độc lập bắt đầu bằng ký tự đầu dòng thích hợp (như `- `, `+ `, `• `, `1. `, `a) `).
   - Tuyệt đối không viết nối tiếp các gạch đầu dòng trong cùng một khối text của một edit.
3. **Độ dài đoạn văn tối ưu**:
   - Mỗi đoạn văn chỉ nên dài từ 2 đến 4 dòng thông thường để tạo khoảng trống thoáng đãng cho tài liệu chuẩn Word.
4. **Sử dụng in đậm hợp lý**:
   - Chỉ sử dụng cú pháp in đậm `**từ khóa**` cho các ĐẦU MỤC, các TỪ ĐẶC BIỆT cần nhấn mạnh, hoặc các TỪ CẦN NỔI BẬT.
   - Tuyệt đối không in đậm toàn bộ đoạn văn hay lạm dụng in đậm vô tội vạ.

## ĐỊNH DẠNG ĐẦU RA BẮT BUỘC (JSON SCHEMA)
Trả về DUY NHẤT một đối tượng JSON có khóa "edits" chứa danh sách các hành động chỉnh sửa. Mỗi hành động là một đối tượng có cấu trúc:
- "id": ID đoạn văn gốc chịu tác động (ví dụ: "p_1", "p_2",...).
- "action": Một trong ba hành động sau:
  - "modify": Chỉnh sửa nội dung của đoạn gốc đó. (Phải đi kèm trường "text")
  - "delete": Xóa hoàn toàn đoạn gốc đó khỏi tài liệu.
  - "insert_after": Chèn một đoạn văn mới hoàn toàn ngay phía sau đoạn gốc này. (Phải đi kèm trường "text")
- "text": Nội dung văn bản mới (chỉ bắt buộc đối với hành động "modify" và "insert_after").

Ví dụ kết quả trả về:
{
  "edits": [
    { "id": "p_1", "action": "modify", "text": "3.1.1.1 Nâng cấp Chế độ Slideshow cho Repeater" },
    { "id": "p_1", "action": "insert_after", "text": "- Mô tả: Tích hợp tính năng hiển thị danh sách dưới dạng băng chuyền trượt ngang." },
    { "id": "p_1", "action": "insert_after", "text": "- Thiết kế cấu hình (Design-time): Bổ sung thuộc tính showAsSlider (kiểu boolean) vào cấu hình." },
    { "id": "p_2", "action": "delete" }
  ]
}

## QUY TẮC KHÁC & CẤM TUYỆT ĐỐI SỬ DỤNG BẢNG MARKDOWN:
1. **Cấm sử dụng ký pháp bảng của Markdown**:
   - TUYỆT ĐỐI KHÔNG trả về các ký tự vẽ bảng như `|---|---|` hay `| Cột 1 | Cột 2 |` trong trường `text` của bất kỳ hành động nào.
   - File Word XML không hỗ trợ tự động chuyển đổi ký pháp Markdown này thành bảng thực tế, dẫn đến hiển thị chuỗi ký tự thô rất xấu (`|---|---|`).
2. **Cách cập nhật dữ liệu trong bảng**:
   - Để chỉnh sửa nội dung bên trong một bảng có sẵn, bạn phải sửa đổi trực tiếp từng đoạn văn trong ô của bảng đó thông qua ID tương ứng (ví dụ: `p_10`, `p_11`...) bằng hành động `modify`.
3. **Mô tả danh sách thay vì vẽ bảng**:
   - Nếu cần trình bày thông tin chi tiết, thay vì vẽ bảng Markdown, hãy diễn giải dưới dạng danh sách gạch đầu dòng rõ ràng (mỗi dòng là một hành động `insert_after` riêng biệt có tiền tố `- ` hoặc `• `).
4. KHÔNG trả về bất kỳ văn bản giải thích hoặc định dạng markdown nào khác ngoài đối tượng JSON.
5. Các khóa ID được sử dụng trong danh sách edits phải tồn tại trong tài liệu gốc.
6. Nếu một đoạn văn không cần thay đổi gì, KHÔNG đưa nó vào danh sách "edits".
"""


def generate_ai_edit(
    extracted_text_dict: Dict[str, str],
    user_requirement: str,
    *,
    reference_text: Optional[str] = None,
    model: str = "gemini-3.5-flash",
    api_key: Optional[str] = None,
    temperature: float = 0.4,
) -> Dict[str, str]:
    """
    Gọi Google Gemini API để chỉnh sửa văn bản theo yêu cầu người dùng, 
    có tham khảo tài liệu phụ (nếu có).

    Args:
        extracted_text_dict: Dict ánh xạ paragraph ID → nội dung gốc.
        user_requirement: Yêu cầu chỉnh sửa từ người dùng.
        reference_text: Nội dung văn bản tham khảo (tùy chọn).
        model: Tên model Gemini.
        api_key: API key.
        temperature: Mức độ sáng tạo.

    Returns:
        Dictionary đại diện cho các thay đổi: { p_id: revised_text }
        Trong đó:
          - p_id gốc: có text mới (modify) hoặc rỗng "" (delete)
          - p_id_ins_{n}: chứa đoạn văn chèn mới sau p_id
    """
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

    user_prompt_parts = [
        f"## YÊU CẦU CHỈNH SỬA\n{user_requirement}\n"
    ]

    if reference_text and reference_text.strip():
        user_prompt_parts.append(
            f"## TÀI LIỆU THAM KHẢO\n{reference_text.strip()}\n"
        )

    user_prompt_parts.append(
        f"## TÀI LIỆU GỐC CẦN CHỈNH SỬA (JSON)\n```json\n{input_json_str}\n```"
    )

    user_prompt = "\n".join(user_prompt_parts)

    # ── Gọi Gemini API ─────────────────────────────────────────────
    logger.info(
        "Gọi Gemini API — model=%s, paragraphs=%d, has_ref=%s, requirement='%s'",
        model,
        len(extracted_text_dict),
        "Yes" if reference_text else "No",
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
        if model != "gemini-3.5-flash":
            logger.warning(f"Model {model} thất bại. Thử fallback sang gemini-3.5-flash...")
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
                logger.error("Lỗi khi gọi Gemini API (Fallback thất bại): %s", fallback_err)
                raise RuntimeError(
                    f"Không thể gọi Gemini API: {fallback_err}"
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
        edited_dict = json.loads(raw_content)
    except json.JSONDecodeError as e:
        logger.error("Không thể parse JSON từ API response: %s", e)
        raise ValueError(
            f"Gemini API trả về JSON không hợp lệ: {e}\nResponse: {raw_content[:300]}"
        ) from e

    # ── Validate cấu trúc và chuyển đổi thành Flat Dict cho Frontend ──
    if not isinstance(edited_dict, dict):
        raise ValueError("Kết quả trả về từ Gemini phải là một JSON Object.")

    edits_list = edited_dict.get("edits", [])
    if not isinstance(edits_list, list):
        raise ValueError("Khóa 'edits' trong kết quả không phải là một danh sách.")

    flat_edits: Dict[str, str] = {}
    insert_counters: Dict[str, int] = {}

    for idx_item, item in enumerate(edits_list):
        if not isinstance(item, dict):
            continue
        p_id = item.get("id")
        action = item.get("action")
        text = item.get("text", "")

        # Chỉ áp dụng các thay đổi cho ID đoạn văn gốc hợp lệ
        if not p_id or p_id not in extracted_text_dict:
            logger.warning("Bỏ qua thay đổi với ID không tồn tại: %s", p_id)
            continue

        if action == "modify":
            flat_edits[p_id] = str(text)
        elif action == "delete":
            flat_edits[p_id] = ""
        elif action == "insert_after":
            # Sinh ID chèn duy nhất, ví dụ: p_1_ins_1, p_1_ins_2
            counter = insert_counters.get(p_id, 0) + 1
            insert_counters[p_id] = counter
            ins_id = f"{p_id}_ins_{counter}"
            flat_edits[ins_id] = str(text)
        else:
            logger.warning("Hành động không hợp lệ: %s tại id %s", action, p_id)

    logger.info(
        "Chỉnh sửa AI hoàn tất — phát hiện %d chỉnh sửa từ Gemini (modify/delete/insert).",
        len(flat_edits),
    )

    return flat_edits
