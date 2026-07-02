# AI Word Document Editor (.docx)

Một ứng dụng web được xây dựng bằng **FastAPI (Python)** ở Backend và **Vanilla JS/HTML/CSS** ở Frontend, hỗ trợ trích xuất, hiển thị hình ảnh gốc, biên tập văn bản bằng **Gemini AI**, và duyệt thay đổi trực quan theo phong cách **Accept/Reject Track Changes** giống Microsoft Word.

---

## 🌟 Tính năng nổi bật

1. **Hiển thị tài liệu trực quan (Word Online Look-and-Feel)**:
   * Hiển thị văn bản dạng trang giấy **A4** trên giao diện làm việc hiện đại.
   * **Phân trang tự động (Pagination)**: Tự động tính toán chiều cao văn bản, ngắt trang và đánh số trang (Footer) chính xác giống phần mềm Microsoft Word Desktop.
   * **Hiển thị hình ảnh gốc inline**: Tự động giải nén thư mục `word/media/` từ file `.docx` và render chính xác hình ảnh tĩnh cùng văn bản gốc.
   * Định dạng cơ bản: Nhận diện chữ in đậm (`bold`), in nghiêng (`italic`), gạch chân (`underline`), căn lề (`justify`, `center`, `right`, `left`), và thụt đầu dòng từ XML gốc để ánh xạ thành CSS tương ứng.

2. **Chỉnh sửa linh hoạt (Manual & AI Edit)**:
   * **Biên tập bằng Gemini AI**: Tích hợp SDK `google-genai` (model `gemini-3.5-flash`) để tự động chỉnh sửa tài liệu hàng loạt theo yêu cầu bất kỳ (VD: *Sửa lỗi chính tả*, *Viết trang trọng hơn*). AI được cấu hình không lạm dụng bôi đậm, chỉ bôi đậm các từ khóa/đầu mục quan trọng.
   * **Chỉnh sửa thủ công (Manual Edit)**: Cho phép người dùng trực tiếp gõ/sửa nội dung văn bản ngay trên mặt giấy ảo. Hệ thống tự động ghi nhận là "Có thay đổi thủ công" để lưu vào file.

3. **Duyệt/Từ chối Thay đổi (Track Changes)**:
   * Bộ so khớp từ trực tiếp ở Client (Word-level Diff) hiển thị trực quan các phần bị xóa (nền đỏ gạch ngang) và các phần thêm mới (nền xanh lá gạch chân).
   * Hỗ trợ duyệt từng đoạn với các nút **✓ Đồng ý (Accept)**, **✕ Từ chối (Reject)**, và **↩ Hoàn tác (Undo)**.
   * Cung cấp tính năng **Đồng ý tất cả (Accept All)** và **Từ chối tất cả (Reject All)** giúp thao tác nhanh chóng trên tài liệu dài.

4. **Quản lý Tài liệu tham khảo đa nền tảng**:
   * Người dùng có thể upload và gửi **nhiều tài liệu tham khảo cùng lúc** (hỗ trợ các định dạng `.docx`, `.pdf`, `.txt`, `.md`).
   * Hệ thống truyền toàn bộ nội dung tham khảo này làm ngữ cảnh chuyên sâu (Context) cho AI trong quá trình biên tập.
   * Hỗ trợ thao tác **Xóa file** tài liệu làm việc và tài liệu tham khảo trực tiếp trên giao diện một cách nhanh chóng.

5. **Biên dịch XML bảo toàn định dạng tuyệt đối**:
   * Can thiệp trực tiếp cấu trúc XML của Word thông qua sự kết hợp giữa thư viện `python-docx` API chuẩn và `lxml`.
   * Xóa nội dung, thêm đoạn văn, thay thế chữ nhưng **giữ nguyên 100% hình vẽ hình ảnh (`w:drawing`, `v:shape`)**, định dạng đoạn (`w:pPr`), định dạng inline.
   * Được lập trình cực kỳ cẩn thận với OpenXML Schema (rPr, pPr) để **đảm bảo không bao giờ gặp lỗi "Word found unreadable content"** khi mở tài liệu tải xuống.

---

## 📁 Cấu trúc thư mục dự án

```text
d:\editor\
├── backend/
│   ├── main.py                 # File chạy chính FastAPI, chứa toàn bộ endpoints API
│   ├── config.py               # Cấu hình môi trường (API Key, Model, Thư mục lưu trữ)
│   ├── docx_xml_processor.py   # Bộ xử lý XML thao tác trực tiếp với file docx
│   ├── ai_editor.py            # Logic giao tiếp với Google Gemini API
│   └── storage/                # Thư mục lưu trữ nội bộ (tự động tạo)
│       ├── uploads/            # Lưu trữ file Word gốc do người dùng tải lên
│       ├── media/              # Lưu trữ hình ảnh giải nén từ file Word để hiển thị web
│       ├── references/         # Lưu trữ các file tài liệu tham khảo
│       └── edited/             # Lưu trữ file Word hoàn thiện sau khi gộp thay đổi
├── frontend/
│   └── index.html              # Trang giao diện chính (Single Page Application)
└── README.md                   # Tài liệu hướng dẫn này
```

---

## ⚙️ Hướng dẫn cài đặt và chạy ứng dụng

### 1. Yêu cầu hệ thống
* Python 3.9 trở lên.
* API Key của Google Gemini. Lấy miễn phí tại: [Google AI Studio](https://aistudio.google.com/apikey).

### 2. Cài đặt các thư viện cần thiết
Mở Terminal tại thư mục dự án và chạy lệnh sau:
```bash
pip install fastapi uvicorn python-multipart httpx python-docx lxml google-genai pymupdf markdown
```

### 3. Cấu hình khóa API Gemini
Thiết lập biến môi trường chứa API Key của bạn:

* **Windows (PowerShell)**:
  ```powershell
  $env:GEMINI_API_KEY = "Khóa_Gemini_API_Của_Bạn"
  ```
* **Linux / macOS**:
  ```bash
  export GEMINI_API_KEY="Khóa_Gemini_API_Của_Bạn"
  ```

### 4. Khởi chạy ứng dụng
Chạy Backend FastAPI (mặc định Frontend được phục vụ trực tiếp tại root URL `/`):
```bash
cd backend
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Truy cập giao diện chính tại: **[http://localhost:8000](http://localhost:8000)**

---

## 🛠️ Luồng hoạt động kỹ thuật (Dành cho nhà phát triển / AI)

1. **Khi người dùng Upload file**:
   * Endpoint `POST /api/upload` nhận file và lưu vào `storage/uploads/`. Giải nén thư mục `word/media/` chứa hình ảnh tĩnh.
2. **Khi hiển thị văn bản**:
   * Frontend gọi `GET /api/extract/{filename}`.
   * `docx_xml_processor` phân tích file, convert cấu trúc đoạn văn, ID, định dạng thành JSON và HTML. Thuật toán `paginateDocument` trên Frontend phân bổ HTML này ra các trang giấy A4 trực quan.
3. **Khi chạy AI Edit hoặc Sửa thủ công**:
   * **AI**: Nhận ngữ cảnh từ file gốc và tài liệu tham khảo, trả về JSON ép buộc (`application/json`) chứa văn bản đã sửa. Client hiển thị Word-level Diff.
   * **Thủ công**: Người dùng sửa trực tiếp trên HTML, sự kiện `blur` kích hoạt, đoạn văn được đánh dấu `status: accepted` và đưa vào hàng chờ Lưu.
4. **Khi lưu file**:
   * Gửi danh sách các đoạn văn thay đổi lên `POST /api/finalize`.
   * `docx_xml_processor` đọc lại file gốc, xóa trắng (clear) nội dung các đoạn cũ một cách an toàn nhưng giữ lại thẻ ảnh và cấu trúc bảng. Sau đó thêm các text run mới bằng API `python-docx` để đảm bảo XML hợp lệ tuyệt đối, rồi lưu vào `storage/edited/`.
