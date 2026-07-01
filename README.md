# AI Word Document Editor (.docx)

Một ứng dụng web được xây dựng bằng **FastAPI (Python)** ở Backend và **Vanilla JS/HTML/CSS** ở Frontend, hỗ trợ trích xuất, hiển thị hình ảnh gốc, biên tập văn bản bằng **Gemini AI**, và duyệt thay đổi trực quan theo phong cách **Accept/Reject Track Changes** giống Microsoft Word.

---

## 🌟 Tính năng nổi bật

1. **Hiển thị tài liệu trực quan (Word Online Look-and-Feel)**:
   * Hiển thị văn bản dạng trang giấy **A4** (đổ bóng mờ, căn giữa màn hình) trên giao diện làm việc hiện đại.
   * **Hiển thị hình ảnh gốc inline**: Tự động giải nén thư mục `word/media/` từ file `.docx` và render chính xác hình ảnh tĩnh cùng văn bản gốc.
   * Định dạng cơ bản: Nhận diện chữ in đậm (`bold`), in nghiêng (`italic`), gạch chân (`underline`), căn lề (`justify`, `center`, `right`, `left`), và thụt đầu dòng từ XML gốc để ánh xạ thành CSS tương ứng.

2. **Duyệt/Từ chối Thay đổi (Track Changes)**:
   * Bộ so khớp từ trực tiếp ở Client (Word-level Diff) hiển thị trực quan các phần bị xóa (nền đỏ gạch ngang) và các phần thêm mới (nền xanh lá gạch chân).
   * Sidebar bên phải quản lý các thẻ Đề xuất Thay đổi (Change Cards). Người dùng có thể:
     * **✓ Đồng ý (Accept)**: Áp dụng đề xuất viết lại của AI.
     * **✕ Từ chối (Reject)**: Giữ nguyên văn bản gốc.
     * **↩ Hoàn tác (Undo)**: Quay lại trạng thái trước khi quyết định.

3. **Biên tập bằng Gemini AI**:
   * Tích hợp SDK mới nhất của Google (`google-genai`) sử dụng model `gemini-3.5-flash` để chỉnh sửa tài liệu hàng loạt theo yêu cầu bất kỳ của người dùng (VD: *Sửa lỗi chính tả*, *Viết trang trọng hơn*, *Lược bỏ các phần chưa thực hiện*).
   * Sử dụng định dạng phản hồi JSON ép buộc (`response_mime_type="application/json"`) đảm bảo cấu trúc khóa ánh xạ đoạn văn không bao giờ bị hỏng.

4. **Biên dịch XML bảo toàn định dạng**:
   * Can thiệp trực tiếp cấu trúc XML của Word (`python-docx` kết hợp `lxml`).
   * Thay thế nội dung chữ trong `<w:t>` nhưng **giữ nguyên 100% hình vẽ hình ảnh (`w:drawing`, `v:shape`)**, bookmark (`w:bookmarkStart`), định dạng đoạn (`w:pPr`), định dạng run (`w:rPr`).
   * Không bao giờ gặp lỗi "Corrupted File" khi mở lại tài liệu đã xuất bản bằng Microsoft Word Desktop hoặc ONLYOFFICE.

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
pip install fastapi uvicorn python-multipart httpx python-docx lxml google-genai
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
   * Endpoint `POST /api/upload` nhận file và lưu vào `storage/uploads/`.
   * Backend gọi hàm giải nén zip, lấy thư mục `word/media/` chứa hình ảnh lưu vào `storage/media/{filename}/`.
2. **Khi hiển thị văn bản**:
   * Frontend gọi `GET /api/extract/{filename}`.
   * `docx_xml_processor` phân tích file quan hệ `word/_rels/document.xml.rels` để ánh xạ quan hệ mã hình ảnh (ví dụ: `rId5` -> `image1.png`).
   * Duyệt qua các phần tử `<w:p>`, trích xuất văn bản, và convert cấu trúc định dạng Bold/Italic/Underline/Alignment/Indentation và hình vẽ thành chuỗi HTML tương thích.
3. **Khi chạy AI Edit**:
   * Frontend gửi yêu cầu tới `POST /api/ai-edit`.
   * Backend chỉ lấy phần văn bản thuần của các đoạn văn gửi lên Gemini Model (`gemini-3.5-flash`) kèm System Prompt yêu cầu sửa đổi nội dung và giữ nguyên mã ID đoạn văn dưới dạng JSON.
   * Gợi ý từ AI được trả về Frontend. Frontend chạy giải thuật LCS tính toán Diff chữ và hiển thị nút Accept/Reject cho từng đoạn.
4. **Khi lưu file**:
   * Người dùng bấm **Hoàn thiện & Tải về**, gửi danh sách các đoạn văn đã chấp nhận (Accept) lên `POST /api/finalize`.
   * Backend mở file gốc, duyệt qua XML và thay thế văn bản, giữ nguyên các node vẽ `w:drawing` để ảnh không bị mất, lưu tài liệu và trả về file `.docx` mới cho client tải về.
