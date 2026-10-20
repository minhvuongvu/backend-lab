---
description: Báo cáo tiến độ mọi topic trong topics/ và gợi ý lệnh /research tiếp theo
---

Chỉ đọc, không sửa file.

1. Liệt kê mọi thư mục `topics/*/` có `README.md`. Nếu không có topic nào, báo "Chưa có topic" và gợi ý `/research <topic>`.
2. Với mỗi topic, đọc `README.md` và lấy:
   - **Phase đã xong:** các mục đã tick `[x]` trong "Checklist".
   - **Phase kế tiếp:** mục đầu tiên chưa tick (hoặc "xong" nếu đủ 7).
   - **Số điểm chờ duyệt:** số dòng `- [ ]` trong mục "Chờ duyệt".
   - **Lần cập nhật cuối:** dòng "Cập nhật lần cuối"; nếu thiếu, dùng `git log -1 --format=%cs -- topics/<slug>`.
3. Đối chiếu với bảng Topics ở `README.md` gốc; nếu lệch (topic thiếu dòng, phase khác nhau) thì ghi chú cảnh báo bên dưới bảng.
4. In bảng:

| Topic | Phase đã xong | Phase kế tiếp | Chờ duyệt | Cập nhật cuối |
|---|---|---|---|---|

5. Dưới bảng, với mỗi topic chưa xong, gợi ý một lệnh, ví dụ:
   - còn điểm chờ duyệt → "duyệt các mục trong `topics/<slug>/README.md` § Chờ duyệt, rồi `/research <slug>`";
   - bình thường → `/research <slug>` (phase kế tiếp);
   - phase 5 → nhắc cần Docker đang chạy và có thể `make obs-up` trước.
6. Nhắc: mỗi phiên một topic, `/clear` trước khi chuyển topic.
