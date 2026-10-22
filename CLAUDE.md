# backend-lab — quy tắc cho mọi phiên

Repo là "phòng thí nghiệm" để nghiên cứu sâu từng công nghệ, pattern, kỹ thuật, solution trong hệ thống phân tán theo quy trình 7 phase, kiểm chứng bằng thí nghiệm thật. Lệnh chính: `/research <topic> [phase]`, `/lab-status`.

File này chỉ giữ nguyên tắc cốt lõi. Quy tắc chi tiết nằm trong `.claude/rules/` (tự nạp khi làm việc với file khớp `paths`; `/research` đọc rõ ở phase cần):
- `.claude/rules/html-docs.md`: viết tài liệu HTML, insight, "vì sao", bước 03, chuyên đề CĐ.
- `.claude/rules/experiments.md`: phương pháp luận thí nghiệm, đo, thống kê, dữ liệu thô, tái lập, observability.
- `.claude/rules/hub-and-topics.md`: trang tổng (`hub/`), roadmap, kho insight, trạng thái `data-*` trong README topic.
- Quy trình từng phase, chế độ lite/spike, topic so sánh, case study: `.claude/commands/research.md`.

## Mục tiêu
- Giúp tôi hiểu sâu để nâng cao năng lực, không phải làm demo.
- Luôn giải thích "tại sao" và cơ chế bên trong (internals), không chỉ "làm thế nào".

## Mục tiêu học → nơi trả lời

Mỗi topic phải trả lời đủ 14 mục tiêu sau. `lab-reviewer` dùng bảng này để kiểm tra độ phủ.

| # | Mục tiêu | Nơi trả lời |
|---|---|---|
| 1 | Bối cảnh nghiệp vụ, hệ thống đang có, mục tiêu, bài toán | 01 §1–6 |
| 2 | Lý thuyết solution: cách hoạt động, mạnh/yếu, đảm bảo/không đảm bảo, failure mode, tiêu chí chọn/bỏ | 01 §7–15 + chuyên đề CĐn |
| 3 | Các cách implement | 01 §16 |
| 4 | Cách hoạt động của từng cách | 01 §17 |
| 5 | Mạnh/yếu, đảm bảo/không đảm bảo, failure mode của từng cách | 01 §17 + chuyên đề CĐ-An |
| 6 | Thay đổi mọi tiêu chí phi chức năng của từng cách so với before | 01 §18 (dự đoán, dựa trên mô hình định lượng §11) → 06 (thực đo) |
| 7 | Giới hạn lý thuyết & đánh đổi nền tảng của từng cách | 01 §11, §17 |
| 8 | Tiêu chí chọn/bỏ của từng cách | 01 §17, §20 → 06 (decision guide hiệu chỉnh) |
| 9 | Từng bước thực thi (code, cấu hình) | 03 |
| 10 | Lưu ý khi implement | 01 §17 (lý thuyết) + 03 (gặp thực tế) |
| 11 | Xem code của từng cách | `system/` + trích dẫn trong 03 |
| 12 | Thiết kế thí nghiệm trước/sau cho từng cách (phương pháp luận, phương pháp đo, độ phủ kịch bản) | 01 §24 + 04 |
| 13 | Thực thi, so sánh trước/sau, kết luận | `experiments/`, `results/`, 05, 06 |
| 14 | Triển khai lên môi trường người dùng thật | 07 + `deploy/` |

## Ngôn ngữ
- Tài liệu `.md`/`.html` viết tiếng Việt, giữ nguyên thuật ngữ tiếng Anh.
- Code, comment, tên biến, commit message viết tiếng Anh.

## Ánh xạ phase → nơi ghi kết quả

File `0N-*.html` thuộc phase N.

| Phase | Nội dung | Nơi ghi |
|---|---|---|
| 1 | Research | `01-research.html` |
| 2 | System design | `02-system-design.html` |
| 3 | Implement | `system/` + `03-implementation.html` |
| 4 | Experiment plan | `04-experiment-plan.html` |
| 5 | Execute | `experiments/` + `results/` + `05-results.html` |
| 6 | Conclusion | `06-conclusion.html` |
| 7 | Production rollout | `07-production.html` + `deploy/` |

Topic mới chỉ được tạo bằng `make new-topic SLUG=<slug>` (copy `templates/` + `shared/scaffold/`, thêm dòng vào bảng ở `README.md` gốc).

## before và các implementation
- `before` là hệ thống as-is chưa có solution. Nó luôn được implement, test và đo như mọi implementation khác, làm mốc so sánh trước/sau.
- ID (`before`, A, B, C...) và slug khai báo một lần trong bảng "Implementations" của README topic (`topics/<slug>/README.html`), dùng nhất quán ở mọi tài liệu, Spring profile và `make run IMPL=<slug>`.

## Tài liệu (tóm tắt, chi tiết ở `.claude/rules/html-docs.md`)
- Tài liệu phase là HTML theo khung `templates/`, dùng chung `shared/docs/lab.css` + `lab.js`; không nhúng CSS/JS riêng.
- Mỗi phần lớn có ít nhất một insight; mọi insight và mọi "vì sao" phải là giải thích nhân quả (cơ chế, điều kiện, định lượng, khi nào không đúng), không phải nhãn.
- Code trong 03 và 07 trích nguyên văn từ file thật.

## Làm việc song song (multi-agent)
- Việc gì tách được thành các phần độc lập thì chạy song song bằng nhiều subagent, không làm tuần tự. Đây là sở thích cố định của tôi, áp dụng cho mọi phiên.
- Mỗi agent được giao rõ file/thư mục mình phụ trách, không sửa file của agent khác, không commit. Agent chính giữ phần tích hợp, kiểm chứng và commit.
- Gợi ý theo phase: phase 1 mỗi agent một góc nguồn; phase 3 mỗi agent một implementation; phase 5 tách chạy thí nghiệm, vẽ biểu đồ, kiểm tra toàn vẹn, viết nháp 05; tài liệu HTML dài có thể chia theo phần.
- Không chia nhỏ việc ngắn hoặc phụ thuộc chặt vào nhau chỉ để có nhiều agent.

## Chế độ và loại topic
- Chế độ mặc định khi tạo topic: `full` cho topic ưu tiên 1 trong roadmap và case study; `lite` cho mọi topic khác. Đối số `full`/`lite`/`spike` ghi đè; chế độ lưu trong README topic được giữ ở các phiên sau.
- `lite` ghi kết luận là "khám phá (lite)", `spike` ghi "spike". Không chế độ nào nới quy tắc trung thực và test tính đúng đắn.
- Loại topic: `standard`, `compare` (`/research X vs Y`), `capstone` (`/research case-…`). Chi tiết từng chế độ/loại trong `.claude/commands/research.md`.

## Một chủ đề, một phiên
- Mỗi phiên chỉ làm một topic.
- Nếu hội thoại hiện tại đã làm topic khác, nhắc tôi chạy `/clear` trước khi tiếp tục.
- Trạng thái nằm trong file, không nằm trong hội thoại. Khi bắt đầu, luôn đọc `topics/<slug>/README.html` và các file phase trước.
- Trong cùng một topic, `/clear` giữa các phase vẫn an toàn.

## Hỏi đáp và câu hỏi nên hỏi
- Mỗi câu hỏi tôi đặt ra trong phiên của một topic (kể cả ngoài `/research`) được ghi vào `topics/<slug>/questions.html`: câu hỏi gần nguyên văn + câu trả lời đúng chuẩn "vì sao" + link tới mục liên quan. Không ghi câu hỏi thao tác thuần ("chạy lệnh nào", "sửa giúp file X"). Đáp án đổi sau khi đo thì thêm `div.a-update`, không xoá đáp án cũ.
- `topics/<slug>/suggested-questions.html`: câu hỏi Claude đề xuất tôi nên hỏi (không kèm đáp án, để tôi tự nghĩ trước). Khi tôi hỏi một câu trong đó, đánh dấu `asked` và link tới đáp án ở `questions.html`.
- Markup và quy tắc chi tiết: `.claude/rules/hub-and-topics.md` § Hỏi đáp; trang tổng `hub/questions.html`.

## Stack mặc định
- Java 21, Spring Boot 4.x (bản ổn định còn hỗ trợ OSS; 3.5 hết hỗ trợ OSS từ 2026-06-30 — chỉ dùng 3.x khi topic cần giống môi trường cũ và ghi lý do), Maven wrapper (`./mvnw`), PostgreSQL, Redis, Kafka, Docker Compose.
- Testcontainers cho integration test.
- k6 cho load test; Python (pandas + matplotlib, chạy trong image `make analysis`) để xử lý số liệu và vẽ biểu đồ.
- Chỉ đổi stack khi topic đòi hỏi, và ghi lý do vào README của topic.
- Tra cứu phiên bản ổn định hiện tại trước khi chọn; pin version rõ ràng (không dùng `latest`).

## Tối giản
- Hệ thống chỉ đủ để phơi bày vấn đề mà kỹ thuật giải quyết.
- Không auth, không UI, không lớp trừu tượng thừa, trừ khi đó chính là chủ đề.
- Ghi rõ những gì cố ý bỏ qua (02 §9) và cách xử lý chúng ở production (07).

## So sánh công bằng
- before và mọi implementation dùng chung một contract (interface/API), cùng workload, cùng giới hạn tài nguyên, cùng cấu hình observability.
- Chọn implementation bằng Spring profile hoặc biến môi trường.

## Trung thực
- Không bịa số liệu.
- Mọi con số trong 05 và 06 phải trỏ tới file đã commit trong `results/raw/` (hoặc `results/analysis/`); mẫu từng request lớn nằm ngoài git ở `results/raw-samples/`, được ghim bằng sha256 trong `MANIFEST.json` (chi tiết: `.claude/rules/experiments.md`).
- Thí nghiệm lỗi hoặc không chạy được (ví dụ thiếu Docker) thì báo rõ và dừng, không ước lượng thay.
- Đánh dấu rõ 3 loại thông tin: **[đo được]** / **[theo tài liệu + link]** / **[suy luận]**.
- Phần production (07) chưa kiểm chứng trong lab phải đánh dấu là tài liệu hoặc suy luận.

## Nguồn
- Ưu tiên tài liệu chính thức, paper gốc, source code, engineering blog của công ty vận hành thật.
- Ghi link ở cuối mỗi tài liệu.

## Thí nghiệm và tái lập (tóm tắt, chi tiết ở `.claude/rules/experiments.md`)
- Thiết kế trước, chạy sau: giả thuyết, ngưỡng, tiêu chí bác bỏ và số lần lặp chốt trong 04 trước khi chạy; before là nhóm đối chứng.
- Mọi thứ chạy được bằng `make` trong `experiments/`; môi trường chạy ghi vào `results/env.md`.
- Cổng riêng của máy (observability, toxiproxy) đặt trong `lab.env` (copy từ `lab.env.example`, không commit); mọi Makefile tự nạp.
- `make doctor` kiểm tra máy trước khi chạy; `make check` trước khi commit thay đổi tooling.

## Git
- Commit sau mỗi phase: `topic(<slug>): phase N - <tóm tắt>`.
