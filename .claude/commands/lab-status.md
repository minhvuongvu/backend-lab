---
description: Báo cáo tiến độ mọi topic trong topics/ và gợi ý lệnh /research tiếp theo
---

Chỉ đọc, không sửa file.

1. Liệt kê mọi thư mục `topics/*/` có `README.html`. Nếu không có topic nào, báo "Chưa có topic" và gợi ý `/research <topic>`.
2. Với mỗi topic, đọc `README.html` và lấy từ thuộc tính `data-*` (không dựa vào chữ hiển thị):
   - **Phase đã xong:** các `ol.phase-list li[data-status="done"]` (lấy `data-phase`).
   - **Phase kế tiếp:** `li` đầu tiên có `data-status` khác `done` (hoặc "xong" nếu đủ 7); ghi chú nếu đang `in-progress`.
   - **Số điểm chờ duyệt:** số `ul.approvals li[data-status="open"]`.
   - **Lần cập nhật cuối:** `data-field="updated"`; nếu thiếu, dùng `git log -1 --format=%cs -- topics/<slug>`.
3. Đối chiếu với bảng Topics ở `README.md` gốc; nếu lệch (topic thiếu dòng, phase khác nhau) thì ghi chú cảnh báo bên dưới bảng.
4. In bảng:

| Topic | Phase đã xong | Phase kế tiếp | Chờ duyệt | Cập nhật cuối |
|---|---|---|---|---|

5. Dưới bảng, với mỗi topic chưa xong, gợi ý một lệnh, ví dụ:
   - còn điểm chờ duyệt → "duyệt các mục trong `topics/<slug>/README.html` § Chờ duyệt, rồi `/research <slug>`";
   - bình thường → `/research <slug>` (phase kế tiếp);
   - phase 5 → nhắc cần Docker đang chạy và có thể `make obs-up` trước.
6. Nhắc: mỗi phiên một topic, `/clear` trước khi chuyển topic.
