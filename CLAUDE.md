# backend-lab — quy tắc cho mọi phiên

Repo là "phòng thí nghiệm" để nghiên cứu sâu từng công nghệ, pattern, kỹ thuật, solution trong hệ thống phân tán theo quy trình 7 phase, kiểm chứng bằng thí nghiệm thật. Lệnh chính: `/research <topic> [phase]`, `/lab-status`.

## Mục tiêu
- Giúp tôi hiểu sâu để nâng cao năng lực, không phải làm demo.
- Luôn giải thích "tại sao" và cơ chế bên trong (internals), không chỉ "làm thế nào".

## Mục tiêu học → nơi trả lời

Mỗi topic phải trả lời đủ 14 mục tiêu sau. `lab-reviewer` dùng bảng này để kiểm tra độ phủ.

| # | Mục tiêu | Nơi trả lời |
|---|---|---|
| 1 | Bối cảnh nghiệp vụ, hệ thống đang có, mục tiêu, bài toán | 01 §1–4 |
| 2 | Lý thuyết solution: cách hoạt động, mạnh/yếu, đảm bảo/không đảm bảo, failure mode, tiêu chí chọn/bỏ | 01 §6–10 |
| 3 | Các cách implement | 01 §11 |
| 4 | Cách hoạt động của từng cách | 01 §12 |
| 5 | Mạnh/yếu, đảm bảo/không đảm bảo, failure mode của từng cách | 01 §12 |
| 6 | Thay đổi mọi tiêu chí phi chức năng của từng cách so với before | 01 §13 (dự đoán) → 06 §3 (thực đo) |
| 7 | Giới hạn lý thuyết & đánh đổi nền tảng của từng cách | 01 §12 |
| 8 | Tiêu chí chọn/bỏ của từng cách | 01 §12, §14 → 06 §5 |
| 9 | Từng bước thực thi (code, cấu hình) | 03 |
| 10 | Lưu ý khi implement | 01 §12 (lý thuyết) + 03 (gặp thực tế) |
| 11 | Xem code của từng cách | `system/` + trích dẫn trong 03 |
| 12 | Thiết kế thí nghiệm trước/sau cho từng cách | 04 |
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

Topic mới chỉ được tạo bằng `make new-topic SLUG=<slug>` (copy `templates/`, thêm dòng vào bảng ở `README.md` gốc).

## before và các implementation
- `before` là hệ thống as-is chưa có solution. Nó luôn được implement, test và đo như mọi implementation khác, làm mốc so sánh trước/sau.
- ID (`before`, A, B, C...) và slug khai báo một lần trong bảng "Implementations" của README topic, dùng nhất quán ở mọi tài liệu, Spring profile và `make run IMPL=<slug>`.

## Tài liệu HTML
- Mỗi tài liệu phase theo khung trong `templates/`, dùng chung `shared/docs/lab.css` + `lab.js` (mục lục, điều hướng giữa tài liệu, mermaid, highlight, dark mode). Không nhúng CSS/JS riêng vào từng trang.
- Thay mọi `<div class="guide">` bằng nội dung thật rồi xoá; khi xong, bỏ class `draft` khỏi `<body>`. Không để ô bảng hay comment placeholder rỗng: không áp dụng thì ghi "—" kèm lý do.
- Nhãn: `<span class="tag measured">`, `<a class="tag doc" href="#src-N">`, `<span class="tag inferred">`.
- Mỗi phần lớn có ít nhất một `callout insight`: điều không hiển nhiên (giả định ngầm, cái giá ẩn, bậc độ lớn, chỗ docs và hiểu biết phổ biến khác nhau).
- Mermaid đặt trong `<pre class="mermaid">`; escape `<`, `>`, `&` trong code (`&lt;`...).
- Code trong 03 và 07 trích NGUYÊN VĂN từ file thật (`<figure class="code">` với caption là đường dẫn + dòng). Không có code chỉ tồn tại trong tài liệu.
- Kiểm tra render bằng headless Chrome/Edge (`--dump-dom`, không còn "Syntax error" của mermaid) trước khi kết thúc phase.

## Một chủ đề, một phiên
- Mỗi phiên chỉ làm một topic.
- Nếu hội thoại hiện tại đã làm topic khác, nhắc tôi chạy `/clear` trước khi tiếp tục.
- Trạng thái nằm trong file, không nằm trong hội thoại. Khi bắt đầu, luôn đọc `README.md` của topic và các file phase trước.
- Trong cùng một topic, `/clear` giữa các phase vẫn an toàn.

## Stack mặc định
- Java 21, Spring Boot 3.x, Maven wrapper (`./mvnw`), PostgreSQL, Redis, Kafka, Docker Compose.
- Testcontainers cho integration test.
- k6 cho load test; Python (pandas + matplotlib) để xử lý số liệu và vẽ biểu đồ.
- Chỉ đổi stack khi topic đòi hỏi, và ghi lý do vào README của topic.
- Tra cứu phiên bản ổn định hiện tại trước khi chọn; pin version rõ ràng (không dùng `latest`).

## Tối giản
- Hệ thống chỉ đủ để phơi bày vấn đề mà kỹ thuật giải quyết.
- Không auth, không UI, không lớp trừu tượng thừa, trừ khi đó chính là chủ đề.
- Ghi rõ những gì cố ý bỏ qua (02 §9) và cách xử lý chúng ở production (07).

## So sánh công bằng
- before và mọi implementation dùng chung một contract (interface/API), cùng workload, cùng giới hạn tài nguyên.
- Chọn implementation bằng Spring profile hoặc biến môi trường.

## Trung thực
- Không bịa số liệu.
- Mọi con số trong 05 và 06 phải trỏ tới file trong `results/raw/`.
- Thí nghiệm lỗi hoặc không chạy được (ví dụ thiếu Docker) thì báo rõ và dừng, không ước lượng thay.
- Đánh dấu rõ 3 loại thông tin: **[đo được]** / **[theo tài liệu + link]** / **[suy luận]**.
- Phần production (07) chưa kiểm chứng trong lab phải đánh dấu là tài liệu hoặc suy luận.

## Nguồn
- Ưu tiên tài liệu chính thức, paper gốc, source code, engineering blog của công ty vận hành thật.
- Ghi link ở cuối mỗi tài liệu.

## Thí nghiệm
- Viết giả thuyết trước khi chạy; mỗi giả thuyết so sánh một implementation với before (hoặc giữa các implementation).
- Mỗi lần chỉ thay đổi 1 biến.
- Có warmup; mỗi kịch bản chạy ít nhất 3 lần.
- Báo throughput, p50/p95/p99, error rate, và tài nguyên (CPU/RAM/connection) khi liên quan, kèm Δ so với before.
- Kỹ thuật về reliability/consistency phải có kịch bản lỗi (kill container, network delay/partition, crash giữa transaction...) và kiểm tra tính đúng đắn của dữ liệu, không chỉ đo hiệu năng.
- Dữ liệu thô trong `results/raw/` đặt tên `<impl>-<scenario>-<run>-<timestamp>`, không sửa tay.

## Tái lập
- Mọi thứ chạy được bằng `make` trong `experiments/` (`make up`, `make run IMPL=x SCENARIO=y`, `make report`, `make down`).
- Ghi môi trường chạy vào `results/env.md`.
- Observability dùng chung: `make obs-up` (Prometheus với remote-write receiver, Grafana). Cổng đổi được: `PROM_PORT`, `GRAFANA_PORT`.
- Artifact triển khai trong `deploy/` phải được validate bằng công cụ tương ứng (`kubectl --dry-run=client`, `helm template`, `terraform validate`...), ghi lệnh vào 07.

## Git
- Commit sau mỗi phase: `topic(<slug>): phase N - <tóm tắt>`.
