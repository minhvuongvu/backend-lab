---
paths:
  - "hub/**"
  - "index.html"
  - "README.md"
  - "scripts/**"
  - "topics/**/README.html"
  - "topics/**/questions.html"
  - "topics/**/suggested-questions.html"
---

## Trang tổng và trạng thái topic
- **Bố cục trang HTML:** `index.html` (trang chủ) ở gốc; mọi trang tổng nằm trong `hub/` (`lab`, `roadmap`, `problems`, `insights`, `benchmarks`, `glossary`, `questions`, `rules`); tài liệu topic trong `topics/<slug>/`. Trang tự sinh (`index.html` ← README.md, `hub/rules.html` ← CLAUDE.md + `.claude/rules/*.md`, các `hub/*.html` trừ `roadmap.html`) không sửa tay: sửa nguồn rồi `make hubs`. `make check` báo lỗi nếu trang sinh ra cũ hơn nguồn.
- `hub/roadmap.html`: danh sách topic có quan hệ tiền đề (`tr[data-slug][data-prereq][data-status][data-order]`), xếp theo 8 giai đoạn học (giai đoạn 8 là case study tổng hợp); số `#n` (`data-order`) là thứ tự gợi ý tính bằng sắp xếp topo. Thêm/sửa topic xong chạy `python3 scripts/roadmap_order.py` để đánh số và xếp nhóm lại. Thứ tự không bắt buộc: học topic bất kỳ được, tiền đề chưa học được tóm tắt trong 01 §6.1. `/research` cảnh báo khi tiền đề chưa xong (khuyến nghị, không chặn), thêm topic mới vào roadmap, cập nhật trạng thái; `/lab-status` gợi ý topic học tiếp. Tiền đề phải có lý do cơ chế (topic sau dựa vào cơ chế của topic trước), đồ thị không có chu trình.
- Trang tổng ở gốc repo (thanh điều hướng chung): `hub/lab.html` tổng quan tiến độ, chờ duyệt, topic sẵn sàng học; `hub/problems.html` tra theo triệu chứng → nguyên nhân, lựa chọn, runbook (`data-problem`); `hub/glossary.html` thuật ngữ chung (`data-term`); `hub/benchmarks.html` số liệu tham chiếu đã đo, dùng lại cho mô hình định lượng của topic sau (`data-bench`, chỉ số [đo được]). README mỗi topic có mục "Topic liên quan" tự sinh. Dựng lại tất cả bằng `make hubs`, kiểm tra markup bằng `make hubs-check`.
- `hub/insights.html`: kho insight và chuyên đề của mọi topic, gom theo tag để thấy nguyên lý lặp lại giữa các topic; dựng lại bằng `python3 scripts/build_insights.py` (hoặc `make insights`) sau mỗi phase, `--check` trước gate. Mỗi insight có `id` duy nhất và `data-tags` (2–5 tag kebab-case, ưu tiên dùng lại tag đã có).
- **Hỏi đáp (`questions.html`) và câu hỏi nên hỏi (`suggested-questions.html`)** trong mỗi topic, gom ở `hub/questions.html` (`make hubs`, kiểm tra `make hubs-check`):
  - Hỏi đáp: `section#qa-log > article.qa[id=q-NNN][data-status=open|answered|revisit][data-phase][data-date][data-kind][data-tags]` gồm `h3.q` (câu hỏi gần nguyên văn), `div.a` (bắt buộc trừ khi `open`), tuỳ chọn `p.refs`, `p.followup`, `div.a-update[data-date]`. `data-kind` ∈ concept, why, how, compare, tradeoff, debug, production; 1–5 tag kebab-case, ưu tiên tag insight đã có.
  - Hai trang này không có class `draft` (luôn đang ghi); mỗi mục là con trực tiếp của `section#qa-log` / `section#ask-list`; ví dụ trong `div.guide` (`q-000`, `s-000`) xoá khi có mục thật đầu tiên.
  - Ghi ngay sau khi trả lời, trong cùng lượt; đáp án theo chuẩn "vì sao" của `html-docs.md` (kết luận trước, rồi cơ chế, điều kiện, định lượng, khi nào không đúng) và có nhãn nguồn. Câu chưa trả lời chắc được (cần đo) để `open` và ghi ở phase nào sẽ trả lời; khi có số đo thì cập nhật bằng `div.a-update` và đổi `answered`/`revisit`.
  - Câu hỏi nên hỏi: `section#ask-list > article.ask[id=s-NNN][data-status=suggested|asked|skipped][data-phase][data-level=foundation|senior|expert][data-kind][data-tags]` gồm `h3.q`, `p.why-ask` (câu hỏi lộ ra lỗ hổng hay hiểu lầm nào, dựa vào cơ chế nào), tuỳ chọn `p.hint` (nơi tìm đáp án); khi đã hỏi: `asked` + `p.answered-by` link `questions.html#q-NNN`. Không ghi đáp án trong file này.
  - Câu hỏi gợi ý tốt là câu bắt phải suy luận về cơ chế, đánh đổi, failure mode, bậc độ lớn hay quyết định production (kiểu câu hỏi phỏng vấn senior/staff, design review), không phải câu tra định nghĩa. Mỗi phase thêm 3–7 câu trải đều các mức; `expert` là câu mà người đã vận hành hệ thống thật mới nghĩ tới.
- README của topic là HTML (khung `templates/topic-README.html`). Trạng thái máy đọc nằm ở thuộc tính `data-*`: `data-field="current-phase|updated|scope|mode|type"` (mode: full/lite/spike; type: standard/compare/capstone), phase `<li data-phase="N" data-status="todo|in-progress|done|skipped">` (class trùng với status), chờ duyệt `ul.approvals li[data-status=open|approved|rejected]`, câu hỏi `ul.questions li[data-status=open|answered]`. Khi cập nhật, sửa cả `data-*` lẫn chữ hiển thị. `README.md` gốc của repo vẫn là Markdown.
