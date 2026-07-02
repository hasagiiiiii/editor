# BẢNG TỔNG HỢP EFFORT FRONTEND THEO COMPONENT / FILE
**Dự án:** GenHub – Layout Builder & Layout Displays  
**Trạng thái nhánh hiện tại:** feature/layout-builder-repeater-improvement  
**Tổng Effort ghi nhận:** 38.0 giờ (Tương đương 4.75 ngày làm việc hiệu quả)

---

## I. BẢNG CHI TIẾT NỘI DUNG THAY ĐỔI & MÃ CHỨC NĂNG (MÃ CN)

Dưới đây là bảng tổng hợp chi tiết phân loại độ phức tạp (**Mã CN**) dựa trên số trường thông tin mới thêm vào và độ phức tạp xử lý tương tác của từng Component:

| Component / Thành phần | Phân loại | Nội dung thay đổi chi tiết | Số trường mới | Mã CN | Effort (Giờ) |
| :--- | :--- | :--- | :---: | :---: | :---: |
| **button-config** | Cấu hình | Dựng layout chọn khóa động từ repeater hoặc nhập tĩnh riêng biệt cho cả Link URL và Anchor ID. | 5 trường | **CN_WEB1** | 4.5h |
| **display-button** | Hiển thị | Render thẻ `<a>` thay thế `<button>` cho action Link/Anchor; xử lý smooth scroll lập trình. | 0 trường | **CN_WEB1** | 4.5h |
| **repeater-config** | Cấu hình | Tích hợp Toggle Switch bật/tắt chế độ Slideshow trượt ngang. | 1 trường | **CN_WEB1** | 1.5h |
| **display-repeater** | Hiển thị | Thuật toán drag-scroll kéo rê chuột, glide & snap về slide gần nhất, nút chevron ẩn hiện, dynamic card width. | 0 trường | **CN_WEB2** | 14.5h |
| **container-config** | Cấu hình | Bổ sung Switch điều khiển trạng thái ẩn/hiện (`hidden`) của container. | 1 trường | **CN_WEB1** | 1.0h |
| **display-container** | Hiển thị | Áp dụng `display: none` khi `hidden = true`; fix lỗi co cụm width card khi nằm trong repeater. | 0 trường | **CN_WEB1** | 1.5h |
| **input-config** | Cấu hình | Thêm loại Input "Number", tích hợp các validator đặc thù (Min, Max, Step), check lỗi Default Value. | 4 trường | **CN_WEB1** | 3.0h |
| **display-input** | Hiển thị | Render component `<nz-input-number>`; viết bộ lọc sự kiện gõ phím tránh trôi/reset con trỏ chuột. | 0 trường | **CN_WEB1** | 2.5h |
| **layout-block** (Preview)| Preview | Dựng UI trượt và chevron thử nghiệm trên Canvas Preview; khử nhân đôi width. | 0 trường | **CN_WEB1** | 3.0h |
| **layout-display** | Router | Gán `[id]="node?.id"` cho 30+ case blocks hiển thị để hỗ trợ làm mốc neo cuộn cho Anchor Link. | 0 trường | **CN_WEB1** | 1.0h |
| **Model Base** (Shared) | Dữ liệu | Khai báo các thuộc tính mới cho interface Button, Repeater, Input, Container ở 2 bên. | 0 trường | — | 2.0h |

---

## II. ĐỊNH NGHĨA PHÂN LOẠI ĐỘ PHỨC TẠP (THEO CHUẨN DỰ ÁN)
> [!NOTE]
> * **CN_WEB1:** Chức năng đơn giản (Dưới 10 trường thông tin / Component hiển thị đơn giản).
> * **CN_WEB2:** Chức năng trung bình (Có từ 10 - 20 trường thông tin cấu hình / Dựng layout & logic tương tác trung bình).
> * **CN_WEB3:** Chức năng phức tạp (Có trên 20 trường thông tin cấu hình / Logic nghiệp vụ phức tạp).

---

## III. CHI TIẾT CÁC TRƯỜNG THÔNG TIN MỚI THÊM VÀO (DESIGN-TIME)

#### A. Component: `button-config` (Có **5 trường thông tin mới**)
1. *Trường liên kết từ Repeater (`urlKey`)* (Dropdown chọn cột dữ liệu chứa link)
2. *Liên kết tĩnh (`url`)* (Input nhập URL/Deeplink)
3. *Target chuyển trang (`urlTarget`)* (Dropdown chọn mở tab mới hoặc chuyển hướng tại chỗ)
4. *Trường Anchor ID từ Repeater (`anchorKey`)* (Dropdown chọn cột dữ liệu chứa ID phần tử neo)
5. *Anchor ID tĩnh (`anchorId`)* (Input nhập ID phần tử neo nhảy tới)

#### B. Component: `input-config` (Có **4 trường thông tin mới**)
1. Lựa chọn kiểu số *Number* cho *Input Type* (Dropdown)
2. *Min* (Input nhập giá trị nhỏ nhất)
3. *Max* (Input nhập giá trị lớn nhất)
4. *Step* (Input nhập bước nhảy)

#### C. Component: `repeater-config` (Có **1 trường thông tin mới**)
1. *Show as Slider (Slideshow)* (Switch bật/tắt chế độ trượt Carousel)

#### D. Component: `container-config` (Có **1 trường thông tin mới**)
1. *Hidden (Ẩn hiển thị)* (Switch bật/tắt trạng thái ẩn container)

---

## IV. CHI TIẾT PHÂN RÃ CÔNG VIỆC WBS THEO FILE 

### 1. Phần 1: Các Component Cấu hình (Layout Builder - Design Time)
| Tên Component | Tập tin ảnh hưởng | Nội dung chi tiết các thay đổi mới | Effort |
| :--- | :--- | :--- | :---: |
| **Model Base** | [models/layout-node-base.ts](file:///d:/genhub/genhub-web/apps/layout-builder/src/app/models/layout-node-base.ts) | Đồng bộ các thuộc tính cấu hình mới (`showAsSlider`, `url`, `urlKey`, `urlTarget`, `anchorKey`, `anchorId`, `hidden`, `min`, `max`, `step`). | 1.0h |
| **repeater-config** | [repeater-config.component.html](file:///d:/genhub/genhub-web/apps/layout-builder/src/app/components/layout-configs/repeater-config/repeater-config.component.html) | Thiết kế công tắc Toggle Switch kích hoạt chế độ Slideshow. | 0.5h |
| | [repeater-config.component.ts](file:///d:/genhub/genhub-web/apps/layout-builder/src/app/components/layout-configs/repeater-config/repeater-config.component.ts) | Viết hàm `onShowAsSliderChange()` cập nhật cờ slider và khởi tạo mặc định. | 1.0h |
| **button-config** | [button-config.component.html](file:///d:/genhub/genhub-web/apps/layout-builder/src/app/components/layout-configs/button-config/button-config.component.html) | Dựng layout chọn khóa động hoặc nhập tĩnh riêng biệt cho cả Link URL và Anchor ID. | 4.0h |
| | [button-config.component.ts](file:///d:/genhub/genhub-web/apps/layout-builder/src/app/components/layout-configs/button-config/button-config.component.ts) | Trực quan hóa panel, viết callbacks dọn dẹp các trường rác khi thay đổi actionType. | 0.5h |
| **container-config** | [container-config.component.html](file:///d:/genhub/genhub-web/apps/layout-builder/src/app/components/layout-configs/container-config/container-config.component.html) | Bổ sung Switch điều khiển trạng thái ẩn/hiện (`hidden`). | 0.5h |
| | [container-config.component.scss](file:///d:/genhub/genhub-web/apps/layout-builder/src/app/components/layout-configs/container-config/container-config.component.scss) | CSS định dạng lại nz-switch hiển thị hợp lý trong panel. | 0.5h |
| **input-config** | [input-config.component.html](file:///d:/genhub/genhub-web/apps/layout-builder/src/app/components/layout-configs/input-config/input-config.component.html) | Thêm loại "Number", ẩn các validator chữ, hiện validator số (Min, Max, Step). | 1.5h |
| | [input-config.component.ts](file:///d:/genhub/genhub-web/apps/layout-builder/src/app/components/layout-configs/input-config/input-config.component.ts) | Viết logic `patchOptionalNumber` giới hạn số và hàm validate Default Value. | 1.0h |
| | [input-config.component.scss](file:///d:/genhub/genhub-web/apps/layout-builder/src/app/components/layout-configs/input-config/input-config.component.scss) | Styling thông báo báo lỗi màu đỏ khi gõ sai định dạng mặc định kiểu số. | 0.5h |
| **layout-block** *(Preview)* | [layout-block.component.html](file:///d:/genhub/genhub-web/apps/layout-builder/src/app/components/layout-block/layout-block.component.html) | Thêm cấu trúc Slider Preview và các chevron trượt thử trên Canvas. | 0.5h |
| | [layout-block.component.ts](file:///d:/genhub/genhub-web/apps/layout-builder/src/app/components/layout-block/layout-block.component.ts) | Xử lý click trượt preview và hàm khử nhân đôi width container con trên Canvas. | 2.0h |
| | [layout-block.component.scss](file:///d:/genhub/genhub-web/apps/layout-builder/src/app/components/layout-block/layout-block.component.scss) | Tạo CSS ẩn thanh cuộn ngang và chevron overlay cho Canvas Preview. | 0.5h |

### 2. Phần 2: Các Component Hiển thị (Layout Displays - Runtime)
| Tên Component | Loại Hiển Thị | Tập tin ảnh hưởng | Nội dung chi tiết các thay đổi mới | Effort |
| :--- | :--- | :--- | :--- | :---: |
| **Model Base** | — | [models/layout-node-base.ts](file:///d:/genhub/genhub-web/libs/layout-displays/src/models/layout-node-base.ts) | Bổ sung các cấu trúc trường động cho Displays. | 1.0h |
| **layout-display** | Router tổng | [layout-display.component.html](file:///d:/genhub/genhub-web/libs/layout-displays/src/lib/layout-display/layout-display.component.html) | Khai báo truyền thuộc tính `[id]="node?.id"` cho tất cả case block con để làm mốc nhảy Anchor. | 1.0h |
| **display-repeater** | Slide/Grid | [display-repeater.component.html](file:///d:/genhub/genhub-web/libs/layout-displays/src/lib/layout-display/blocks/display-repeater/display-repeater.component.html) | Cấu trúc slider track, gắn chặn rê kéo ảnh mặc định. | 2.0h |
| | | [display-repeater.component.ts](file:///d:/genhub/genhub-web/libs/layout-displays/src/lib/layout-display/blocks/display-repeater/display-repeater.component.ts) | **Xử lý thuật toán kéo rê chuột**, snap slide khi nhả chuột, nút điều hướng chevron, dynamic width. | 10.5h |
| | | [display-repeater.component.scss](file:///d:/genhub/genhub-web/libs/layout-displays/src/lib/layout-display/blocks/display-repeater/display-repeater.component.scss) | CSS class active-dragging, style co giãn card con khít 100%. | 2.0h |
| **display-button** | Nút / Thẻ `<a>` | [display-button.component.html](file:///d:/genhub/genhub-web/libs/layout-displays/src/lib/layout-display/blocks/display-button/display-button.component.html) | Đổi cấu trúc thẻ `<button>` sang thẻ liên kết `<a>` khi actionType là Link/Anchor. | 2.5h |
| | | [display-button.component.ts](file:///d:/genhub/genhub-web/libs/layout-displays/src/lib/layout-display/blocks/display-button/display-button.component.ts) | Viết giải quyết URL/Anchor động từ context, viết sự kiện chặn click để nhảy cuộn mượt. | 2.0h |
| **display-container** | Ô chứa | [display-container.component.html](file:///d:/genhub/genhub-web/libs/layout-displays/src/lib/layout-display/blocks/display-container/display-container.component.html) | Ẩn/hiện container bằng display none: `[style.display]="cfg.hidden ? 'none' : 'block'"`. | 0.5h |
| | | [display-container.component.ts](file:///d:/genhub/genhub-web/libs/layout-displays/src/lib/layout-display/blocks/display-container/display-container.component.ts) | Sửa logic giãn rộng 100% khi Container nằm trong Repeater thường/slide. | 1.0h |
| **display-input** | Input / Số | [display-input.component.html](file:///d:/genhub/genhub-web/libs/layout-displays/src/lib/layout-display/blocks/display-input/display-input.component.html) | Nhúng `<nz-input-number>` hiển thị nhập số thực tế. | 0.5h |
| | | [display-input.component.ts](file:///d:/genhub/genhub-web/libs/layout-displays/src/lib/layout-display/blocks/display-input/display-input.component.ts) | Viết hàm `onNumberInput` giải quyết vấn đề trôi con trỏ chuột khi người dùng nhập số thập phân. | 1.5h |
| | | [display-input.component.scss](file:///d:/genhub/genhub-web/libs/layout-displays/src/lib/layout-display/blocks/display-input/display-input.component.scss) | Đồng bộ chiều rộng 100% và bo góc cho phần tử nz-input-number. | 0.5h |
