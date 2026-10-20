---
description: Nghiên cứu một topic backend theo quy trình 6 phase (research → design → implement → plan → execute → conclusion)
argument-hint: <topic> [1-6 | next | all]
---

Đối số: `$ARGUMENTS`

Tách đối số: nếu TỪ CUỐI CÙNG thuộc {`1`,`2`,`3`,`4`,`5`,`6`,`next`,`all`} thì đó là **phase**, phần còn lại là **tên topic**. Nếu không, toàn bộ là tên topic và phase = `next`.

Tuân thủ mọi quy tắc trong `CLAUDE.md` (ngôn ngữ, trung thực, tối giản, so sánh công bằng, thí nghiệm, git).

## Phase 0 — Định vị topic

1. Chuyển tên topic thành slug kebab-case (chữ thường, a-z0-9, nối bằng `-`).
2. Liệt kê thư mục trong `topics/` và so khớp gần đúng, không phân biệt hoa thường (ví dụ "Outbox", "transactional outbox pattern" ↔ `transactional-outbox`).
   - Khớp được thư mục có sẵn → dùng thư mục đó. Nếu có nhiều ứng viên, hỏi tôi chọn.
   - Không khớp:
     - topic quá rộng (ví dụ "caching", "microservices", "kafka"): đề xuất 2–4 cách thu hẹp cụ thể (mỗi cách một dòng + slug gợi ý) và hỏi tôi. DỪNG.
     - ngược lại: chạy `make new-topic SLUG=<slug>`. Đây là cách DUY NHẤT để tạo topic; không tự tạo file/thư mục bằng cách khác. Nếu `make` không có, chạy `bash scripts/new-topic.sh <slug>` (chính là thứ Makefile gọi) và báo tôi.
3. Nếu hội thoại hiện tại đã làm một topic KHÁC: nhắc tôi chạy `/clear` rồi gọi lại lệnh. DỪNG.
4. Đọc `topics/<slug>/README.md` và mọi file phase đã có nội dung. Trạng thái lấy từ file, không lấy từ trí nhớ hội thoại.
5. Xác định phase:
   - `next` → phase đầu tiên chưa tick trong checklist. Nếu cả 6 đã xong, báo và dừng.
   - `N` → nếu có phase < N chưa tick, cảnh báo phase nào còn thiếu và hỏi tôi trước khi làm.
   - `all` → chạy lần lượt từ phase `next` tới 6.
6. Nếu mục "Chờ duyệt" trong README còn mục chưa tick thuộc phase trước, liệt kê chúng và hỏi tôi có muốn tiếp tục không (trừ chế độ `all`).

Báo ngắn: topic, slug, phase sẽ chạy, rồi bắt đầu.

## Phase 1 — Research → `01-research.html`

- Dùng subagent song song để tìm nguồn, mỗi agent một góc:
  1. tài liệu chính thức / spec / paper gốc;
  2. source code & internals (link tới file/dòng);
  3. engineering blog, postmortem, talk của công ty vận hành thật (cho §10 case study);
  4. failure mode, anti-pattern, issue/bug tracker (cho §8, §11).
  Mỗi agent trả về tóm tắt kèm link; tự tổng hợp và kiểm tra chéo, chỗ nguồn mâu thuẫn thì ghi rõ.
- Viết vào `01-research.html` theo đúng khung template (quy tắc HTML trong `CLAUDE.md`). Nội dung bắt buộc:
  - **TL;DR** (viết cuối cùng);
  - **Phần A — Bối cảnh:** kiến thức nền & thuật ngữ; vấn đề (tình huống cụ thể, sequence diagram có điểm hỏng, hệ thống hỏng thế nào nếu không có nó, vì sao vấn đề khó);
  - **Phần B — Cơ chế:** internals kèm sơ đồ mermaid, đảm bảo/bất biến/giả định ngầm, vòng đời trạng thái, chi phí ở tầng thấp (bậc độ lớn); tham số quan trọng & giá trị mặc định theo version;
  - **Phần C — Các cách implement:** 2–4 cách, gồm cả cách "ngây thơ" làm baseline; mỗi cách: nguyên lý, sơ đồ, các bước implement chi tiết, snippet cốt lõi, ưu/nhược, lỗi thường gặp và cách tránh; ma trận trade-off;
  - **Phần D — Thực tế production:** danh mục failure mode (cả khi đã làm đúng), vận hành (metric, alert, tuning), case study có nguồn, hiểu lầm & anti-pattern, khi nào KHÔNG nên dùng, cây quyết định;
  - **Phần E — Hướng tới thí nghiệm:** câu hỏi cần kiểm chứng (kèm dự đoán hiện tại), câu hỏi tự kiểm tra kiểu phỏng vấn senior, nguồn tham khảo.
- Tiêu chí chất lượng trước khi gọi gate:
  - không còn `<div class="guide">`, comment placeholder rỗng, hay class `draft`;
  - mỗi phần A–D có ít nhất một `callout insight`; khẳng định quan trọng đều có nhãn;
  - mọi `href="#src-N"` trỏ tới nguồn tồn tại;
  - render kiểm tra bằng headless Chrome/Edge (`--headless --screenshot`, hoặc `--dump-dom` để chắc mermaid không lỗi) nếu có trình duyệt.
- Điền mục "Phạm vi" trong README của topic.
- → **Gate**.

## Phase 2 — System design → `02-system-design.md`

- Domain tối giản, các thành phần (version pin, đã tra phiên bản ổn định hiện tại), sơ đồ mermaid.
- Contract chung, cách mỗi implementation cắm vào (Spring profile / biến môi trường).
- Schema dữ liệu, metric cần expose, cách kiểm tra đúng đắn dữ liệu, những gì cố ý bỏ qua.
- Điền bảng "Stack" trong README của topic.
- → **Gate**.

## Phase 3 — Implement → `system/`

- Code mọi cách implement có trong 01, theo contract ở 02. Maven wrapper, Java 21, Spring Boot 3.x.
- Mỗi cách có integration test (Testcontainers) chứng minh tính đúng đắn trước khi đo hiệu năng — bao gồm test cho chính vấn đề mà baseline mắc phải (baseline được phép fail theo cách đã dự đoán; ghi rõ).
- Expose `/actuator/prometheus` để dùng với `shared/observability`.
- `./mvnw verify` phải pass. Nếu không chạy được (thiếu Docker/JDK), báo rõ và DỪNG, không đánh dấu phase xong.

## Phase 4 — Experiment plan → `03-experiment-plan.md`

- Giả thuyết (lấy từ câu hỏi ở 01), biến độc lập, biến phụ thuộc, biến kiểm soát.
- Workload, kịch bản bình thường và kịch bản lỗi (bắt buộc với reliability/consistency).
- Ma trận impl × scenario, tiêu chí đánh giá.
- Yếu tố có thể làm sai lệch kết quả trên máy local, và cách giảm thiểu.
- → **Gate**.

## Phase 5 — Execute → `experiments/` + `results/`

- Viết `experiments/`: `docker-compose.yml`, script k6 / chaos, `Makefile` với `make up`, `make run IMPL=x`, `make report`, `make down`.
- Ghi `results/env.md` bằng output của lệnh thật trước khi chạy.
- Chạy toàn bộ ma trận (warmup, ≥ 3 lần mỗi ô), lưu raw vào `results/raw/<impl>-<scenario>-<run>-<timestamp>.*`, không sửa tay.
- Kiểm tra toàn vẹn dữ liệu sau các kịch bản lỗi; lưu kết quả kiểm tra vào raw.
- Vẽ biểu đồ bằng Python (pandas + matplotlib) vào `results/charts/`.
- Kết quả bất thường (độ biến thiên lớn, trái giả thuyết, lỗi lạ) → điều tra và ghi lại trong README (câu hỏi mở / nhật ký).
- Lệnh nào thất bại thì báo rõ kèm output và DỪNG; không ước lượng thay số liệu.

## Phase 6 — Conclusion → `04-conclusion.md`

- Tóm tắt.
- Bảng so sánh có link tới raw data (mọi con số phải truy được về `results/raw/`).
- Từng giả thuyết: đúng, sai hay chưa kết luận được, và vì sao.
- Những điều bất ngờ.
- Decision guide theo ngữ cảnh.
- Giới hạn của thí nghiệm so với production.
- Bài học rút ra, câu hỏi nghiên cứu tiếp.
- Gọi subagent `lab-reviewer` kiểm tra khả năng truy vết số liệu; sửa vấn đề nghiêm trọng.

## Gate (sau phase 1, 2 và 4)

1. Gọi subagent `lab-reviewer` với đường dẫn topic và phase vừa xong.
2. Sửa mọi vấn đề **nghiêm trọng**; vấn đề **nên sửa** thì sửa hoặc ghi lý do không sửa vào nhật ký quyết định.
3. Chế độ thường: tóm tắt cho tôi trong 5–10 dòng (đã làm gì, reviewer nêu gì, đã sửa gì) kèm danh sách quyết định cần duyệt, rồi **DỪNG chờ xác nhận**.
4. Chế độ `all`: vẫn chạy reviewer nhưng không dừng; ghi các điểm cần duyệt vào mục "Chờ duyệt" trong README của topic (`- [ ] (phase N) ...`) rồi chạy tiếp.

## Kết thúc mỗi phase

1. Cập nhật README của topic: tick checklist, "Phase hiện tại", "Cập nhật lần cuối", thêm dòng nhật ký quyết định, câu hỏi mở.
2. Cập nhật cột "Phase hiện tại" của topic trong bảng Topics ở `README.md` gốc (ví dụ `2/6 — System design`).
3. Commit: `topic(<slug>): phase N - <tóm tắt tiếng Anh>`. Chỉ add file trong `topics/<slug>/` và `README.md` gốc.
