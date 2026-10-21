---
paths:
  - "topics/**/*.html"
  - "templates/**"
---

## Tài liệu HTML
- Mỗi tài liệu phase theo khung trong `templates/`, dùng chung `shared/docs/lab.css` + `lab.js` (mục lục, điều hướng giữa tài liệu, mermaid, highlight, dark mode). Không nhúng CSS/JS riêng vào từng trang.
- Thay mọi `<div class="guide">` bằng nội dung thật rồi xoá; khi xong, bỏ class `draft` khỏi `<body>`. Không để ô bảng hay comment placeholder rỗng: không áp dụng thì ghi "—" kèm lý do.
- Nhãn: `<span class="tag measured">`, `<a class="tag doc" href="#src-N">`, `<span class="tag inferred">`.
- Mỗi phần lớn có ít nhất một `callout insight`: điều không hiển nhiên (giả định ngầm, cái giá ẩn, bậc độ lớn, chỗ docs và hiểu biết phổ biến khác nhau).
- Mỗi insight PHẢI giải thích vì sao: `p.claim` (khẳng định) + `div.why` chứa `dl.why-steps` gồm **Cơ chế** (các bước nhân quả, mỗi bước nêu thành phần/cấu trúc dữ liệu/giao thức cụ thể), **Điều kiện**, **Định lượng**, **Khi nào không đúng**, **Liên hệ** (mục chứa cơ chế) + `div.evidence` (nhãn nguồn + cách kiểm chứng). Insight thiếu phần nào, hoặc "Vì sao" chỉ nhắc lại khẳng định, là không đạt. Chuẩn độ sâu: insight mẫu trong `templates/01-research.html`.
- Mọi chỗ "vì sao / lý do" khác (ô bảng, ưu/nhược, chọn/bỏ, NFR, nhánh cây quyết định...) cũng phải là giải thích nhân quả, không phải nhãn kiểu "vì nhanh hơn", "do overhead". Mỗi "vì sao" trả lời được: cái gì xảy ra, theo thứ tự nào, ở thành phần nào, trong điều kiện nào, lớn cỡ nào, khi nào không còn đúng. Ô bảng hẹp: lý do ngắn + `[Rn]`, chi tiết ở `ol.reasons` dưới bảng.
- Tài liệu 03: mỗi bước thực thi là `li.step` với `dl.step-meta` (**Mục đích**, **Cơ chế**, **Thay đổi hành vi**, **Nếu bỏ qua / làm sai**, **Kiểm tra bước đã đúng**), rồi mới tới code trích nguyên văn và `div.code-notes` giải thích từng khối code. Bước chỉ có code là không đạt; cấu hình giải thích từng thuộc tính (giá trị, mặc định, cơ chế, vì sao chọn, sai thì sao).
- **Chuyên đề đặc thù (CĐ):** hiện tượng/cơ chế chỉ solution hoặc một cách implement mới có (không tồn tại ở before hay cách khác, không hiển nhiên, ảnh hưởng đáng kể) được viết thành chuyên đề riêng trong 01: `CĐn` cho solution, `CĐ-An` trong khối của cách A. Mỗi chuyên đề có hiện tượng, cơ chế bên trong, điều kiện kích hoạt + định lượng, phát hiện & xử lý, kiểm chứng, insight. Mã CĐ được dùng tiếp ở §25, 04, 03, 06, 07; không đánh số lại §1–27.
- "Bài toán" không chỉ là hệ thống hỏng: có thể là đúng đắn, hiệu năng, khả năng mở rộng, chi phí hay vận hành. Xác định loại vấn đề trước rồi chọn chỉ số đo tương ứng.
- Mermaid đặt trong `<pre class="mermaid">`; escape `<`, `>`, `&` trong code (`&lt;`...).
- Code trong 03 và 07 trích NGUYÊN VĂN từ file thật (`<figure class="code">` với caption là đường dẫn + dòng). Không có code chỉ tồn tại trong tài liệu.
- Kiểm tra render bằng headless Chrome/Edge (`--dump-dom`, không còn "Syntax error" của mermaid) trước khi kết thúc phase.
