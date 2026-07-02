"""
main.py

FastAPI backend tích hợp ONLYOFFICE Document Server và AI Editor.

Endpoints:
  GET  /                          → Giao diện Editor (frontend)
  GET  /api/documents             → Danh sách file .docx hiện có
  GET  /api/files/{filename}      → Phục vụ file .docx cho ONLYOFFICE
  POST /api/upload                → Upload file .docx mới
  POST /api/callback              → ONLYOFFICE Callback Handler
  POST /api/ai-edit               → Kích hoạt AI chỉnh sửa thủ công
  GET  /api/editor-config/{name}  → Lấy cấu hình ONLYOFFICE cho file

Chạy:
    uvicorn main:app --reload --port 8000

Dependencies:
    pip install fastapi uvicorn python-multipart httpx python-docx lxml openai
"""

from __future__ import annotations

import hashlib
import json
import logging
import time
import uuid
from pathlib import Path
from typing import Any, Dict, Optional

import httpx
from fastapi import (
    BackgroundTasks,
    FastAPI,
    File,
    HTTPException,
    Request,
    UploadFile,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse

import config
from ai_editor import generate_ai_edit
from docx_xml_processor import DocxXmlProcessor

# ── Logging ─────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s │ %(levelname)-7s │ %(name)s │ %(message)s",
)
logger = logging.getLogger("onlyoffice-ai")

# ── FastAPI App ─────────────────────────────────────────────────────
app = FastAPI(
    title="ONLYOFFICE AI Editor",
    description="Backend tích hợp ONLYOFFICE Document Server với AI editing",
    version="1.0.0",
)

# CORS — cho phép ONLYOFFICE Document Server và frontend truy cập
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Shared instances ───────────────────────────────────────────────
processor = DocxXmlProcessor()

# Lưu trạng thái AI edit (in-memory, thay bằng DB cho production)
_ai_edit_tasks: Dict[str, Dict[str, Any]] = {}


# ================================================================
#  UTILITIES
# ================================================================


def _generate_document_key(file_path: Path) -> str:
    """
    Tạo key duy nhất cho document dựa trên nội dung và thời gian sửa đổi.

    ONLYOFFICE yêu cầu key thay đổi mỗi khi nội dung file thay đổi,
    nếu không editor sẽ dùng cache cũ.
    """
    stat = file_path.stat()
    raw = f"{file_path.name}_{stat.st_size}_{stat.st_mtime_ns}"
    return hashlib.md5(raw.encode()).hexdigest()[:20]


def _build_editor_config(filename: str, doc_key: str) -> Dict[str, Any]:
    """Xây dựng cấu hình JSON cho DocsAPI.DocEditor."""
    file_url = f"{config.BACKEND_URL}/api/files/{filename}"
    callback_url = f"{config.BACKEND_URL}/api/callback"

    return {
        "document": {
            "fileType": "docx",
            "key": doc_key,
            "title": filename,
            "url": file_url,
            "permissions": {
                "edit": True,
                "download": True,
                "print": True,
                "review": True,
            },
        },
        "editorConfig": {
            "mode": "edit",
            "callbackUrl": callback_url,
            "lang": "vi",
            "user": {
                "id": "user-1",
                "name": "Editor User",
            },
            "customization": {
                "autosave": True,
                "forcesave": True,
                "chat": False,
                "compactToolbar": False,
            },
        },
        "documentType": "word",
        "height": "100%",
        "width": "100%",
    }


# ================================================================
#  BACKGROUND TASK: AI PROCESSING
# ================================================================


def _background_ai_process(
    file_path: Path,
    task_id: str,
    user_requirement: str,
    reference_text: Optional[str] = None,
) -> None:
    """
    Background task: Trích xuất → Gọi AI gợi ý chỉnh sửa → Lưu gợi ý vào Task.
    """
    try:
        _ai_edit_tasks[task_id]["status"] = "processing"
        logger.info("🤖 Bắt đầu AI edit: %s (task=%s)", file_path.name, task_id)

        # Bước 1: Trích xuất đoạn văn (dạng Dict[str, Dict[str, str]])
        paragraphs_data = processor.extract_paragraphs_with_ids(str(file_path))
        paragraphs = paragraphs_data["paragraphs"]
        logger.info("  → Trích xuất %d đoạn văn", len(paragraphs))

        if not paragraphs:
            _ai_edit_tasks[task_id]["status"] = "completed"
            _ai_edit_tasks[task_id]["suggestions"] = {}
            _ai_edit_tasks[task_id]["message"] = "Không có đoạn văn nào để chỉnh sửa."
            return

        # Chỉ trích xuất text để gửi cho AI (bỏ qua các thẻ HTML/img)
        text_dict = {p_id: p_data["text"] for p_id, p_data in paragraphs.items()}

        # Bước 2: Gọi AI chỉnh sửa
        _ai_edit_tasks[task_id]["status"] = "calling_ai"
        edited = generate_ai_edit(
            text_dict,
            user_requirement,
            reference_text=reference_text,
            model=config.GEMINI_MODEL,
            api_key=config.GEMINI_API_KEY or None,
        )
        logger.info("  → AI đã đề xuất chỉnh sửa %d đoạn", len(edited))

        _ai_edit_tasks[task_id].update(
            {
                "status": "completed",
                "suggestions": edited,
                "message": f"AI đã hoàn thành đề xuất chỉnh sửa cho {len(edited)} đoạn văn.",
            }
        )

    except Exception as e:
        logger.error("❌ AI edit thất bại (task=%s): %s", task_id, e)
        _ai_edit_tasks[task_id].update(
            {
                "status": "failed",
                "message": str(e),
            }
        )


# ================================================================
#  API ENDPOINTS
# ================================================================


# ── Frontend ────────────────────────────────────────────────────────


@app.get("/", response_class=HTMLResponse)
async def serve_frontend():
    """Phục vụ trang giao diện Editor."""
    html_path = config.BASE_DIR.parent / "frontend" / "index.html"
    if not html_path.exists():
        raise HTTPException(status_code=404, detail="Frontend not found")
    return HTMLResponse(html_path.read_text(encoding="utf-8"))


# ── Document Management ────────────────────────────────────────────


@app.get("/api/documents")
async def list_documents():
    """Liệt kê tất cả file .docx hiện có trong thư mục uploads."""
    files = []
    for f in sorted(config.UPLOADS_DIR.glob("*.docx")):
        stat = f.stat()
        files.append(
            {
                "name": f.name,
                "size": stat.st_size,
                "modified": stat.st_mtime,
                "has_edited": (config.EDITED_DIR / f.name).exists(),
            }
        )
    return {"documents": files}


@app.delete("/api/documents/{filename}")
async def delete_document(filename: str):
    """Xóa file tài liệu (cả file gốc, file đã sửa, và thư mục media đi kèm)."""
    deleted_any = False
    
    # 1. File trong uploads
    upload_path = config.UPLOADS_DIR / filename
    if upload_path.exists():
        try:
            upload_path.unlink()
            deleted_any = True
        except Exception as e:
            logger.error("Lỗi khi xóa file upload %s: %s", filename, e)

    # 2. File trong edited
    edited_path = config.EDITED_DIR / filename
    if edited_path.exists():
        try:
            edited_path.unlink()
            deleted_any = True
        except Exception as e:
            logger.error("Lỗi khi xóa file edited %s: %s", filename, e)

    # 3. Thư mục media giải nén
    media_dir = config.MEDIA_DIR / filename
    if media_dir.exists() and media_dir.is_dir():
        try:
            import shutil
            shutil.rmtree(media_dir)
        except Exception as e:
            logger.error("Lỗi khi xóa thư mục media %s: %s", filename, e)

    if not deleted_any:
        raise HTTPException(status_code=404, detail=f"Không tìm thấy file '{filename}' để xóa")

    return {"message": f"Đã xóa file '{filename}' thành công"}


@app.get("/api/files/{filename}")
async def serve_file(filename: str, source: str = "auto"):
    """
    Phục vụ file .docx cho ONLYOFFICE hoặc để người dùng tải về.
    source: "uploads" (chỉ lấy file gốc), "edited" (chỉ lấy file đã sửa), "auto" (ưu tiên file đã sửa)
    """
    if source == "edited":
        file_path = config.EDITED_DIR / filename
    elif source == "uploads":
        file_path = config.UPLOADS_DIR / filename
    else:
        file_path = config.EDITED_DIR / filename
        if not file_path.exists():
            file_path = config.UPLOADS_DIR / filename

    if not file_path.exists():
        raise HTTPException(status_code=404, detail=f"File '{filename}' not found")

    if file_path.suffix.lower() != ".docx":
        raise HTTPException(status_code=400, detail="Only .docx files are supported")

    return FileResponse(
        path=str(file_path),
        filename=filename,
        media_type=(
            "application/vnd.openxmlformats-officedocument"
            ".wordprocessingml.document"
        ),
    )


def _extract_docx_media(file_path: Path, filename: str):
    """
    Giải nén thư mục 'word/media/' từ file docx sang thư mục media tĩnh để hiển thị trên web.
    """
    import zipfile
    dest_dir = config.MEDIA_DIR / filename
    dest_dir.mkdir(parents=True, exist_ok=True)
    try:
        with zipfile.ZipFile(file_path) as z:
            for member in z.namelist():
                if member.startswith("word/media/"):
                    image_name = Path(member).name
                    if image_name:
                        image_data = z.read(member)
                        (dest_dir / image_name).write_bytes(image_data)
        logger.info("Đã giải nén media từ '%s' sang '%s'", filename, dest_dir)
    except Exception as e:
        logger.error("Lỗi giải nén media từ '%s': %s", filename, e)


@app.post("/api/upload")
async def upload_file(file: UploadFile = File(...)):
    """Upload một file .docx mới và giải nén hình ảnh đi kèm."""
    if not file.filename or not file.filename.lower().endswith(".docx"):
        raise HTTPException(
            status_code=400,
            detail="Chỉ chấp nhận file .docx",
        )

    safe_name = file.filename.replace(" ", "_")
    save_path = config.UPLOADS_DIR / safe_name

    try:
        content = await file.read()
        save_path.write_bytes(content)
        logger.info("📄 Uploaded: %s (%d bytes)", safe_name, len(content))
        
        # Giải nén hình ảnh từ file .docx
        _extract_docx_media(save_path, safe_name)
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Lỗi khi lưu file: {e}",
        )

    return {
        "message": "Upload thành công",
        "filename": safe_name,
        "size": len(content),
    }


# ── Reference File Upload & Extraction ─────────────────────────────

REFERENCE_DIR = config.STORAGE_DIR / "references"
REFERENCE_DIR.mkdir(parents=True, exist_ok=True)


def _extract_reference_text(file_path: Path) -> str:
    """Trích xuất văn bản thuần từ file tham khảo (.md, .txt, .pdf, .docx)."""
    suffix = file_path.suffix.lower()
    
    if suffix in (".md", ".txt"):
        return file_path.read_text(encoding="utf-8", errors="replace")
    
    elif suffix == ".pdf":
        try:
            import fitz  # PyMuPDF
            doc = fitz.open(str(file_path))
            text_parts = []
            for page in doc:
                text_parts.append(page.get_text())
            doc.close()
            return "\n".join(text_parts)
        except ImportError:
            # Fallback nếu chưa cài PyMuPDF
            logger.warning("PyMuPDF (fitz) chưa cài. Thử pdfplumber...")
            try:
                import pdfplumber
                text_parts = []
                with pdfplumber.open(str(file_path)) as pdf:
                    for page in pdf.pages:
                        t = page.extract_text()
                        if t:
                            text_parts.append(t)
                return "\n".join(text_parts)
            except ImportError:
                raise RuntimeError(
                    "Cần cài PyMuPDF hoặc pdfplumber để đọc file PDF. "
                    "Chạy: pip install PyMuPDF hoặc pip install pdfplumber"
                )
    
    elif suffix == ".docx":
        data = processor.extract_paragraphs_with_ids(str(file_path))
        return "\n".join(p_data["text"] for p_data in data["paragraphs"].values())
    
    else:
        raise ValueError(f"Định dạng '{suffix}' chưa được hỗ trợ")


@app.post("/api/upload-reference")
async def upload_reference_file(file: UploadFile = File(...)):
    """Upload file tham khảo (.md, .pdf, .txt, .docx)."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="Thiếu tên file")
    
    allowed_exts = {".md", ".pdf", ".txt", ".docx"}
    suffix = Path(file.filename).suffix.lower()
    if suffix not in allowed_exts:
        raise HTTPException(
            status_code=400,
            detail=f"Chỉ chấp nhận file {', '.join(allowed_exts)}",
        )

    safe_name = file.filename.replace(" ", "_")
    save_path = REFERENCE_DIR / safe_name

    try:
        content = await file.read()
        save_path.write_bytes(content)
        logger.info("📎 Uploaded reference: %s (%d bytes)", safe_name, len(content))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi khi lưu file: {e}")

    return {
        "message": "Upload tài liệu tham khảo thành công",
        "filename": safe_name,
        "size": len(content),
    }


@app.get("/api/reference-files")
async def list_reference_files():
    """Liệt kê tất cả file tham khảo đã upload."""
    files = []
    for f in sorted(REFERENCE_DIR.iterdir()):
        if f.name.startswith("."):
            continue
        files.append({
            "name": f.name,
            "size": f.stat().st_size,
        })
    return {"files": files}


@app.delete("/api/reference-files/{filename}")
async def delete_reference_file(filename: str):
    """Xóa file tài liệu tham khảo."""
    file_path = REFERENCE_DIR / filename
    if not file_path.exists():
        raise HTTPException(
            status_code=404, detail=f"Không tìm thấy file tham khảo '{filename}' để xóa"
        )
    try:
        file_path.unlink()
        logger.info("🗑️ Deleted reference file: %s", filename)
        return {"message": f"Đã xóa file tham khảo '{filename}' thành công"}
    except Exception as e:
        logger.error("Lỗi khi xóa file tham khảo %s: %s", filename, e)
        raise HTTPException(
            status_code=500, detail=f"Lỗi khi xóa file tham khảo: {e}"
        )





@app.get("/api/editor-config/{filename}")
async def get_editor_config(filename: str):
    """
    Trả về cấu hình JSON cho DocsAPI.DocEditor.

    Frontend gọi endpoint này để lấy config, rồi truyền vào constructor.
    """
    file_path = config.EDITED_DIR / filename
    if not file_path.exists():
        file_path = config.UPLOADS_DIR / filename

    if not file_path.exists():
        raise HTTPException(status_code=404, detail=f"File '{filename}' not found")

    doc_key = _generate_document_key(file_path)
    editor_config = _build_editor_config(filename, doc_key)

    return editor_config


# ── ONLYOFFICE Callback Handler ────────────────────────────────────


@app.post("/api/callback")
async def onlyoffice_callback(
    request: Request,
    background_tasks: BackgroundTasks,
):
    """
    ONLYOFFICE Callback Handler.

    ONLYOFFICE Document Server gọi endpoint này khi có sự kiện:
      - status 1: Đang chỉnh sửa (user mở editor)
      - status 2: Sẵn sàng lưu (tất cả user đã đóng editor)
      - status 4: Đóng không thay đổi
      - status 6: Force save (user bấm Save hoặc autosave)
      - status 7: Lỗi force save

    Khi status = 2 hoặc 6, ONLYOFFICE cung cấp URL tải file đã sửa.
    Backend tải file, lưu lại, và (tùy chọn) chạy AI xử lý.

    QUAN TRỌNG: Phải trả về {"error": 0} nhanh chóng.
    Xử lý nặng (AI edit) chạy trong BackgroundTasks.
    """
    try:
        body = await request.json()
    except Exception:
        logger.error("Callback nhận request không hợp lệ")
        return JSONResponse({"error": 1})

    status = body.get("status")
    doc_key = body.get("key", "unknown")

    logger.info(
        "📩 ONLYOFFICE Callback — status=%s, key=%s",
        status,
        doc_key,
    )

    # ── Status 2 hoặc 6: Tải và lưu file ──────────────────────────
    if status in (2, 6):
        download_url = body.get("url")

        if not download_url:
            logger.error("Callback status=%d nhưng thiếu URL download", status)
            return JSONResponse({"error": 1})

        try:
            # Tải file từ ONLYOFFICE Document Server
            async with httpx.AsyncClient(
                timeout=30.0, verify=False
            ) as client:
                response = await client.get(download_url)
                response.raise_for_status()
                file_content = response.content

            # Xác định tên file từ key hoặc dùng tên mặc định
            # ONLYOFFICE key thường chứa thông tin file
            filename = _resolve_filename_from_key(doc_key)
            save_path = config.UPLOADS_DIR / filename

            # Lưu file đã chỉnh sửa từ ONLYOFFICE
            save_path.write_bytes(file_content)
            logger.info(
                "💾 Đã lưu file từ ONLYOFFICE: %s (%d bytes)",
                filename,
                len(file_content),
            )

        except httpx.HTTPError as e:
            logger.error(
                "❌ Không thể tải file từ ONLYOFFICE: %s", e
            )
            return JSONResponse({"error": 1})
        except Exception as e:
            logger.error("❌ Lỗi khi xử lý callback: %s", e)
            return JSONResponse({"error": 1})

    # ── Status 4: Đóng không thay đổi ──────────────────────────────
    elif status == 4:
        logger.info("📄 Document đóng không thay đổi (key=%s)", doc_key)

    # ── Các status khác ────────────────────────────────────────────
    else:
        logger.debug("Callback status=%s — không cần xử lý", status)

    # ONLYOFFICE yêu cầu response {"error": 0} để xác nhận thành công
    return JSONResponse({"error": 0})


def _resolve_filename_from_key(doc_key: str) -> str:
    """
    Tìm tên file gốc dựa trên document key.

    Duyệt qua các file trong uploads và edited để tìm file có key khớp.
    Nếu không tìm thấy, trả về tên mặc định.
    """
    for directory in (config.EDITED_DIR, config.UPLOADS_DIR):
        for f in directory.glob("*.docx"):
            if _generate_document_key(f) == doc_key:
                return f.name

    # Fallback: trả về tên dựa trên key
    return f"document_{doc_key[:8]}.docx"


# ── AI Edit Endpoint ───────────────────────────────────────────────


@app.post("/api/ai-edit")
async def trigger_ai_edit(
    request: Request,
    background_tasks: BackgroundTasks,
):
    """
    Kích hoạt AI chỉnh sửa cho một file .docx.

    Request body:
    {
        "filename": "bao_cao.docx",
        "requirement": "Sửa lỗi chính tả và viết trang trọng hơn",
        "reference_filename": "tai_lieu_tham_khao.docx" (tùy chọn)
    }

    Response:
    {
        "task_id": "abc123",
        "status": "queued",
        "message": "Đã bắt đầu xử lý AI..."
    }

    Kiểm tra tiến độ qua: GET /api/ai-edit/status/{task_id}
    """
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Request body không hợp lệ")

    filename = body.get("filename", "").strip()
    requirement = body.get("requirement", "").strip()
    reference_filename = body.get("reference_filename", "").strip()

    if not filename:
        raise HTTPException(status_code=400, detail="Thiếu 'filename'")
    if not requirement:
        raise HTTPException(
            status_code=400,
            detail="Thiếu 'requirement' (yêu cầu chỉnh sửa)",
        )

    # Tìm file (ưu tiên bản đã chỉnh sửa, rồi đến bản gốc)
    file_path = config.EDITED_DIR / filename
    if not file_path.exists():
        file_path = config.UPLOADS_DIR / filename
    if not file_path.exists():
        raise HTTPException(
            status_code=404, detail=f"File '{filename}' không tồn tại"
        )

    # Trích xuất tài liệu tham khảo nếu có (hỗ trợ nhiều tài liệu cách nhau bằng dấu phẩy)
    reference_text = None
    if reference_filename:
        reference_text_list = []
        ref_names = [r.strip() for r in reference_filename.split(",") if r.strip()]
        for ref_name in ref_names:
            ref_path = config.EDITED_DIR / ref_name
            if not ref_path.exists():
                ref_path = config.UPLOADS_DIR / ref_name
            if not ref_path.exists():
                ref_path = REFERENCE_DIR / ref_name
            if not ref_path.exists():
                raise HTTPException(
                    status_code=404, detail=f"Tài liệu tham khảo '{ref_name}' không tồn tại"
                )
            try:
                txt = _extract_reference_text(ref_path)
                reference_text_list.append(f"=== NỘI DUNG TÀI LIỆU THAM KHẢO: {ref_name} ===\n{txt}")
                logger.info("📄 Đã trích xuất %d ký tự từ tài liệu tham khảo '%s'", len(txt), ref_name)
            except Exception as e:
                raise HTTPException(
                    status_code=500, detail=f"Lỗi khi trích xuất tài liệu tham khảo '{ref_name}': {e}"
                )
        if reference_text_list:
            reference_text = "\n\n".join(reference_text_list)

    # Kiểm tra API key
    if not config.GEMINI_API_KEY:
        raise HTTPException(
            status_code=500,
            detail="Chưa cấu hình GEMINI_API_KEY / GOOGLE_API_KEY.",
        )

    # Tạo task
    task_id = uuid.uuid4().hex[:12]
    _ai_edit_tasks[task_id] = {
        "status": "queued",
        "filename": filename,
        "requirement": requirement,
        "reference_filename": reference_filename or None,
        "message": "Đang chờ xử lý...",
        "created_at": time.time(),
    }

    # Chạy AI processing trong background
    background_tasks.add_task(
        _background_ai_process, file_path, task_id, requirement, reference_text
    )

    logger.info(
        "🚀 Đã đưa vào hàng đợi AI edit: %s (task=%s, ref=%s)", filename, task_id, reference_filename or "None"
    )

    return {
        "task_id": task_id,
        "status": "queued",
        "message": f"Đã bắt đầu xử lý AI cho '{filename}'...",
    }


@app.get("/api/ai-edit/status/{task_id}")
async def get_ai_edit_status(task_id: str):
    """Kiểm tra trạng thái của một AI edit task."""
    task = _ai_edit_tasks.get(task_id)
    if not task:
        raise HTTPException(
            status_code=404, detail=f"Task '{task_id}' không tồn tại"
        )
    return {"task_id": task_id, **task}


# ── Extract Paragraphs Endpoint ────────────────────────────────────


@app.get("/api/extract/{filename}")
async def extract_paragraphs(filename: str, source: str = "uploads"):
    """
    Trích xuất đoạn văn từ file .docx, trả về JSON {paragraphs: {...}}.

    Query params:
        source: "uploads" (mặc định) hoặc "edited"
    """
    if source == "edited":
        file_path = config.EDITED_DIR / filename
    else:
        file_path = config.UPLOADS_DIR / filename

    if not file_path.exists():
        # Fallback: thử thư mục còn lại
        alt = config.UPLOADS_DIR / filename if source == "edited" else config.EDITED_DIR / filename
        if alt.exists():
            file_path = alt
        else:
            raise HTTPException(status_code=404, detail=f"File '{filename}' not found")

    try:
        data = processor.extract_paragraphs_with_ids(str(file_path))
        return {
            "filename": filename, 
            "source": source, 
            "html": data["html"], 
            "paragraphs": data["paragraphs"]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi khi trích xuất: {e}")


# ── Serve Media Endpoint ───────────────────────────────────────────


@app.get("/api/media/{filename}/{image_name}")
async def serve_media_file(filename: str, image_name: str):
    """
    Phục vụ hình ảnh tĩnh được giải nén từ file .docx.
    """
    image_path = config.MEDIA_DIR / filename / image_name
    if not image_path.exists():
        raise HTTPException(status_code=404, detail="Không tìm thấy ảnh")
    
    suffix = image_path.suffix.lower()
    media_types = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".gif": "image/gif",
        ".svg": "image/svg+xml",
        ".tiff": "image/tiff",
        ".webp": "image/webp",
    }
    media_type = media_types.get(suffix, "application/octet-stream")
    return FileResponse(path=str(image_path), media_type=media_type)


# ── Finalize Document Endpoint ─────────────────────────────────────


@app.post("/api/finalize")
async def finalize_document(request: Request):
    """
    Gộp các thay đổi được người dùng chấp nhận (Accept) vào file gốc
    và tạo file docx hoàn thiện.
    """
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Request body không hợp lệ")

    filename = body.get("filename", "").strip()
    accepted_edits = body.get("accepted_edits", {})

    if not filename:
        raise HTTPException(status_code=400, detail="Thiếu 'filename'")
    
    original_path = config.UPLOADS_DIR / filename
    if not original_path.exists():
        raise HTTPException(status_code=404, detail=f"Không tìm thấy file gốc: {filename}")
        
    output_path = config.EDITED_DIR / filename
    
    try:
        # Gộp các thay đổi đã duyệt
        processor.merge_edited_text(str(original_path), accepted_edits, str(output_path))
        logger.info("📄 Đã hoàn thiện tài liệu: %s", filename)
    except Exception as e:
        logger.error("Lỗi khi hoàn thiện tài liệu: %s", e)
        raise HTTPException(status_code=500, detail=f"Lỗi khi hoàn thiện: {e}")
        
    return {
        "message": "Đã tạo tài liệu thành công",
        "download_url": f"/api/files/{filename}?source=edited"
    }
