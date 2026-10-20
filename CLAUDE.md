# backend-lab — quy tắc cho mọi phiên

Repo là "phòng thí nghiệm" để nghiên cứu sâu từng công nghệ/kỹ thuật backend theo quy trình 6 phase, kiểm chứng bằng thí nghiệm thật. Lệnh chính: `/research <topic> [phase]`, `/lab-status`.

## Mục tiêu
- Giúp tôi hiểu sâu, không phải làm demo.
- Luôn giải thích "tại sao" và cơ chế bên trong (internals), không chỉ "làm thế nào".

## Ngôn ngữ
- Tài liệu `.md`/`.html` viết tiếng Việt, giữ nguyên thuật ngữ tiếng Anh.
- Code, comment, tên biến, commit message viết tiếng Anh.

## Tài liệu HTML (phase 1)
- `01-research.html` theo khung `templates/01-research.html`, dùng chung `shared/docs/lab.css` + `lab.js` (mục lục, mermaid, highlight, dark mode). Không nhúng CSS/JS riêng vào từng trang.
- Thay mọi `<div class="guide">` bằng nội dung thật rồi xoá; khi xong, bỏ class `draft` khỏi `<body>`.
- Nhãn: `<span class="tag measured">`, `<a class="tag doc" href="#src-N">`, `<span class="tag inferred">`.
- Mỗi phần lớn có ít nhất một `callout insight`: điều không hiển nhiên (giả định ngầm, cái giá ẩn, bậc độ lớn, chỗ docs và hiểu biết phổ biến khác nhau).
- Mermaid đặt trong `<pre class="mermaid">`; escape `<` thành `&lt;` trong nội dung sơ đồ/code.

## Ánh xạ phase → nơi ghi kết quả

| Phase | Nội dung | Nơi ghi |
|---|---|---|
| 1 | Research | `01-research.html` |
| 2 | System design | `02-system-design.md` |
| 3 | Implement | `system/` |
| 4 | Experiment plan | `03-experiment-plan.md` |
| 5 | Execute | `experiments/` + `results/` |
| 6 | Conclusion | `04-conclusion.md` |

Topic mới chỉ được tạo bằng `make new-topic SLUG=<slug>` (copy `templates/`, thêm dòng vào bảng ở `README.md` gốc).

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
- Ghi rõ những gì cố ý bỏ qua.

## So sánh công bằng
- Mọi cách implement dùng chung một contract (interface/API) và cùng workload.
- Chọn implementation bằng Spring profile hoặc biến môi trường.

## Trung thực
- Không bịa số liệu.
- Mọi con số trong `04-conclusion.md` phải trỏ tới file trong `results/raw/`.
- Thí nghiệm lỗi hoặc không chạy được (ví dụ thiếu Docker) thì báo rõ và dừng, không ước lượng thay.
- Đánh dấu rõ 3 loại thông tin: **[đo được]** / **[theo tài liệu + link]** / **[suy luận]**.

## Nguồn
- Ưu tiên tài liệu chính thức, paper gốc, source code, engineering blog của công ty vận hành thật.
- Ghi link ở cuối mỗi tài liệu.

## Thí nghiệm
- Viết giả thuyết trước khi chạy.
- Mỗi lần chỉ thay đổi 1 biến.
- Có warmup; mỗi kịch bản chạy ít nhất 3 lần.
- Báo throughput, p50/p95/p99, error rate, và tài nguyên (CPU/RAM/connection) khi liên quan.
- Kỹ thuật về reliability/consistency phải có kịch bản lỗi (kill container, network delay/partition, crash giữa transaction...) và kiểm tra tính đúng đắn của dữ liệu, không chỉ đo hiệu năng.
- Dữ liệu thô trong `results/raw/` đặt tên `<impl>-<scenario>-<run>-<timestamp>`, không sửa tay.

## Tái lập
- Mọi thứ chạy được bằng `make` trong `experiments/` (`make up`, `make run IMPL=x`, `make report`).
- Ghi môi trường chạy vào `results/env.md`.
- Observability dùng chung: `make obs-up` (Prometheus :9090 với remote-write receiver, Grafana :3000).

## Git
- Commit sau mỗi phase: `topic(<slug>): phase N - <tóm tắt>`.
