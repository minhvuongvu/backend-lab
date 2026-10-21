---
paths:
  - "hub/**"
  - "index.html"
  - "README.md"
  - "scripts/**"
  - "topics/**/README.html"
---

## Trang tổng và trạng thái topic
- **Bố cục trang HTML:** `index.html` (trang chủ) ở gốc; mọi trang tổng nằm trong `hub/` (`lab`, `roadmap`, `problems`, `insights`, `benchmarks`, `glossary`, `rules`); tài liệu topic trong `topics/<slug>/`. Trang tự sinh (`index.html` ← README.md, `hub/rules.html` ← CLAUDE.md + `.claude/rules/*.md`, các `hub/*.html` trừ `roadmap.html`) không sửa tay: sửa nguồn rồi `make hubs`. `make check` báo lỗi nếu trang sinh ra cũ hơn nguồn.
- `hub/roadmap.html`: danh sách topic có quan hệ tiền đề (`tr[data-slug][data-prereq][data-status][data-order]`), xếp theo 8 giai đoạn học (giai đoạn 8 là case study tổng hợp); số `#n` (`data-order`) là thứ tự gợi ý tính bằng sắp xếp topo. Thêm/sửa topic xong chạy `python3 scripts/roadmap_order.py` để đánh số và xếp nhóm lại. Thứ tự không bắt buộc: học topic bất kỳ được, tiền đề chưa học được tóm tắt trong 01 §6.1. `/research` cảnh báo khi tiền đề chưa xong (khuyến nghị, không chặn), thêm topic mới vào roadmap, cập nhật trạng thái; `/lab-status` gợi ý topic học tiếp. Tiền đề phải có lý do cơ chế (topic sau dựa vào cơ chế của topic trước), đồ thị không có chu trình.
- Trang tổng ở gốc repo (thanh điều hướng chung): `hub/lab.html` tổng quan tiến độ, chờ duyệt, topic sẵn sàng học; `hub/problems.html` tra theo triệu chứng → nguyên nhân, lựa chọn, runbook (`data-problem`); `hub/glossary.html` thuật ngữ chung (`data-term`); `hub/benchmarks.html` số liệu tham chiếu đã đo, dùng lại cho mô hình định lượng của topic sau (`data-bench`, chỉ số [đo được]). README mỗi topic có mục "Topic liên quan" tự sinh. Dựng lại tất cả bằng `make hubs`, kiểm tra markup bằng `make hubs-check`.
- `hub/insights.html`: kho insight và chuyên đề của mọi topic, gom theo tag để thấy nguyên lý lặp lại giữa các topic; dựng lại bằng `python3 scripts/build_insights.py` (hoặc `make insights`) sau mỗi phase, `--check` trước gate. Mỗi insight có `id` duy nhất và `data-tags` (2–5 tag kebab-case, ưu tiên dùng lại tag đã có).
- README của topic là HTML (khung `templates/topic-README.html`). Trạng thái máy đọc nằm ở thuộc tính `data-*`: `data-field="current-phase|updated|scope|mode|type"` (mode: full/lite/spike; type: standard/compare/capstone), phase `<li data-phase="N" data-status="todo|in-progress|done|skipped">` (class trùng với status), chờ duyệt `ul.approvals li[data-status=open|approved|rejected]`, câu hỏi `ul.questions li[data-status=open|answered]`. Khi cập nhật, sửa cả `data-*` lẫn chữ hiển thị. `README.md` gốc của repo vẫn là Markdown.
