---
description: Báo cáo tiến độ mọi topic, gợi ý lệnh /research tiếp theo và topic nên học tiếp theo lộ trình
---

Chỉ đọc, không sửa file.

1. Liệt kê mọi thư mục `topics/*/` có `README.html`. Nếu không có topic nào, báo "Chưa có topic" và gợi ý `/research <topic>`.
2. Với mỗi topic, đọc `README.html` và lấy từ thuộc tính `data-*` (không dựa vào chữ hiển thị):
   - **Phase đã xong:** các `ol.phase-list li[data-status="done"]` (lấy `data-phase`).
   - **Phase kế tiếp:** `li` đầu tiên có `data-status` khác `done`/`skipped` (hoặc "xong"); ghi chú nếu đang `in-progress`.
   - **Chế độ:** `data-field="mode"` (full / lite).
   - **Số điểm chờ duyệt:** số `ul.approvals li[data-status="open"]`.
   - **Lần cập nhật cuối:** `data-field="updated"`; nếu thiếu, dùng `git log -1 --format=%cs -- topics/<slug>`.
3. Đối chiếu với bảng Topics ở `README.md` gốc; nếu lệch (topic thiếu dòng, phase khác nhau) thì ghi chú cảnh báo bên dưới bảng.
4. In bảng:

| Topic | Chế độ | Phase đã xong | Phase kế tiếp | Chờ duyệt | Cập nhật cuối |
|---|---|---|---|---|---|

5. Dưới bảng, với mỗi topic chưa xong, gợi ý một lệnh, ví dụ:
   - còn điểm chờ duyệt → "duyệt các mục trong `topics/<slug>/README.html` § Chờ duyệt, rồi `/research <slug>`";
   - bình thường → `/research <slug>` (phase kế tiếp);
   - phase 5 → nhắc cần Docker đang chạy và có thể `make obs-up` trước.
6. **Học gì tiếp theo** (từ `hub/roadmap.html`, các hàng `tr[data-slug]`):
   - topic "sẵn sàng" = chưa tạo hoặc `planned`, và mọi slug trong `data-prereq` đã `done`;
   - gợi ý tối đa 3 topic sẵn sàng, ưu tiên `data-priority` thấp (1 = cao nhất) rồi theo thứ tự đường học đang đi; mỗi gợi ý một dòng: vì sao bây giờ (tiền đề nào vừa xong mở khoá nó) + lệnh `/research <slug>` (chế độ mặc định: full nếu `data-priority="1"` hoặc case study, còn lại lite; ghi rõ chế độ sẽ dùng);
   - cảnh báo nếu roadmap và README của topic lệch trạng thái.
7. Dòng cuối: số insight và chuyên đề trong `hub/insights.html` (nếu có), nhắc chạy `python3 scripts/build_insights.py` nếu file cũ hơn tài liệu topic mới nhất.
8. Nhắc: mỗi phiên một topic, `/clear` trước khi chuyển topic.
