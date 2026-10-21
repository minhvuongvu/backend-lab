# backend-lab — quy tắc cho mọi phiên

Repo là "phòng thí nghiệm" để nghiên cứu sâu từng công nghệ, pattern, kỹ thuật, solution trong hệ thống phân tán theo quy trình 7 phase, kiểm chứng bằng thí nghiệm thật. Lệnh chính: `/research <topic> [phase]`, `/lab-status`.

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

Topic mới chỉ được tạo bằng `make new-topic SLUG=<slug>` (copy `templates/`, thêm dòng vào bảng ở `README.md` gốc).

## before và các implementation
- `before` là hệ thống as-is chưa có solution. Nó luôn được implement, test và đo như mọi implementation khác, làm mốc so sánh trước/sau.
- ID (`before`, A, B, C...) và slug khai báo một lần trong bảng "Implementations" của README topic (`topics/<slug>/README.html`), dùng nhất quán ở mọi tài liệu, Spring profile và `make run IMPL=<slug>`.

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

## Làm việc song song (multi-agent)
- Việc gì tách được thành các phần độc lập thì chạy song song bằng nhiều subagent, không làm tuần tự. Đây là sở thích cố định của tôi, áp dụng cho mọi phiên.
- Mỗi agent được giao rõ file/thư mục mình phụ trách, không sửa file của agent khác, không commit. Agent chính giữ phần tích hợp, kiểm chứng và commit.
- Gợi ý theo phase: phase 1 mỗi agent một góc nguồn; phase 3 mỗi agent một implementation; phase 5 tách chạy thí nghiệm, vẽ biểu đồ, kiểm tra toàn vẹn, viết nháp 05; tài liệu HTML dài có thể chia theo phần.
- Không chia nhỏ việc ngắn hoặc phụ thuộc chặt vào nhau chỉ để có nhiều agent.

## Trang tổng, chế độ, loại topic
- `ROADMAP.html`: danh sách topic có quan hệ tiền đề (`tr[data-slug][data-prereq][data-status]`). `/research` cảnh báo khi tiền đề chưa xong (khuyến nghị, không chặn), thêm topic mới vào roadmap, cập nhật trạng thái; `/lab-status` gợi ý topic học tiếp. Tiền đề phải có lý do cơ chế (topic sau dựa vào cơ chế của topic trước), đồ thị không có chu trình.
- Trang tổng ở gốc repo (thanh điều hướng chung): `LAB.html` tổng quan tiến độ, chờ duyệt, topic sẵn sàng học; `PROBLEMS.html` tra theo triệu chứng → nguyên nhân, lựa chọn, runbook (`data-problem`); `GLOSSARY.html` thuật ngữ chung (`data-term`); `BENCHMARKS.html` số liệu tham chiếu đã đo, dùng lại cho mô hình định lượng của topic sau (`data-bench`, chỉ số [đo được]). README mỗi topic có mục "Topic liên quan" tự sinh. Dựng lại tất cả bằng `make hubs`, kiểm tra markup bằng `make hubs-check`.
- `INSIGHTS.html`: kho insight và chuyên đề của mọi topic, gom theo tag để thấy nguyên lý lặp lại giữa các topic; dựng lại bằng `python3 scripts/build_insights.py` (hoặc `make insights`) sau mỗi phase, `--check` trước gate. Mỗi insight có `id` duy nhất và `data-tags` (2–5 tag kebab-case, ưu tiên dùng lại tag đã có).
- Chế độ `lite` (`/research <topic> lite`): cho topic học nhanh; bảng nới lỏng trong `.claude/commands/research.md` § Chế độ lite. Kết luận ở lite ghi rõ "khám phá (lite)". Không nới quy tắc trung thực và test tính đúng đắn.
- Chế độ `spike` (`/research <topic> spike`): khám phá nhanh một hiện tượng/câu hỏi (thường một chuyên đề), § Chế độ spike. Kết luận ghi rõ "spike".
- Topic so sánh (`/research X vs Y`): `data-field="type"` = `compare`, mỗi công nghệ là một implementation, bắt buộc mục "So sánh trực diện" trong 01, dùng lại topic đã có thay vì viết lại; § Topic so sánh.

## Một chủ đề, một phiên
- Mỗi phiên chỉ làm một topic.
- Nếu hội thoại hiện tại đã làm topic khác, nhắc tôi chạy `/clear` trước khi tiếp tục.
- Trạng thái nằm trong file, không nằm trong hội thoại. Khi bắt đầu, luôn đọc `topics/<slug>/README.html` và các file phase trước.
- README của topic là HTML (khung `templates/topic-README.html`). Trạng thái máy đọc nằm ở thuộc tính `data-*`: `data-field="current-phase|updated|scope|mode|type"` (mode: full/lite/spike; type: standard/compare), phase `<li data-phase="N" data-status="todo|in-progress|done|skipped">` (class trùng với status), chờ duyệt `ul.approvals li[data-status=open|approved|rejected]`, câu hỏi `ul.questions li[data-status=open|answered]`. Khi cập nhật, sửa cả `data-*` lẫn chữ hiển thị. `README.md` gốc của repo vẫn là Markdown.
- Trong cùng một topic, `/clear` giữa các phase vẫn an toàn.

## Stack mặc định
- Java 21, Spring Boot 4.x (bản ổn định còn hỗ trợ OSS; 3.5 hết hỗ trợ OSS từ 2026-06-30 — chỉ dùng 3.x khi topic cần giống môi trường cũ và ghi lý do), Maven wrapper (`./mvnw`), PostgreSQL, Redis, Kafka, Docker Compose.
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

## Thí nghiệm (phương pháp luận)
Chi tiết trong `templates/04-experiment-plan.html`; công cụ thống kê `scripts/stats.py`.
- **Thiết kế trước, chạy sau:** giả thuyết có hướng + độ lớn dự đoán (từ mô hình định lượng 01 §11), ngưỡng hiệu ứng có ý nghĩa thực tế, tiêu chí bác bỏ, quy tắc loại bỏ outlier và số lần lặp — chốt trước khi chạy. Sau khi chạy không sửa giả thuyết.
- **Đối chứng:** before là nhóm đối chứng; mọi implementation so với before (và với nhau khi cần) trên cùng contract, workload, giới hạn tài nguyên.
- **Biến:** so sánh chính đổi một yếu tố mỗi lần (OFAT); chỉ dùng thiết kế giai thừa nhỏ khi giả thuyết có tương tác giữa các tham số. Liệt kê biến gây nhiễu đã biết và cách kiểm soát.
- **Tuning công bằng:** mỗi implementation được chỉnh tới cấu hình hợp lý tốt nhất trong cùng ngân sách tài nguyên, ghi lại quá trình tuning; không so default với đã tune.
- **Thứ tự chạy ngẫu nhiên, xen kẽ theo block** (`stats.py plan-order`) để trải đều drift, nhiệt độ, tác vụ nền; không chạy hết A rồi mới tới B.
- **Số lần lặp:** chạy pilot để ước lượng độ biến thiên rồi chốt số lần; mặc định ≥ 5 lần cho latency đuôi (3 lần quá ít để ước lượng p99 và khoảng tin cậy).
- **Workload:** mô hình mở (constant-arrival-rate) để tránh coordinated omission; ghi rõ phân phối arrival, phân phối key (uniform/Zipf/hot key), payload, kích thước dữ liệu so với bộ nhớ (working set vừa/vượt cache), seed.
- **Đo:** warmup đến khi đạt steady state theo tiêu chí định trước (`stats.py steady-state`); percentile tính từ mẫu thô (k6 `--out csv`), không lấy trung bình percentile giữa các lần chạy; ghi điểm đo (client/server/DB); hiệu chuẩn công cụ đo bằng độ trễ biết trước; theo dõi sức khoẻ load generator (CPU, dropped iterations); USE cho tài nguyên, RED cho service.
- **Độ phủ kịch bản:** xét đủ danh mục trong 04 (bình thường, quét tải tới bão hoà, spike, soak, quá tải/backpressure, tiêm lỗi gồm cả gray failure, phục hồi, nhiều instance/đồng thời, hot key, cold start, dữ liệu tăng trưởng); kịch bản nào không áp dụng phải ghi lý do. Kỹ thuật reliability/consistency bắt buộc có tiêm lỗi + kiểm tra toàn vẹn dữ liệu (id duy nhất, invariant checker, lưu lịch sử thao tác).
- **Thống kê:** báo median + IQR và khoảng tin cậy 95% bằng bootstrap theo lần chạy; Δ so với before kèm CI, Mann–Whitney U và effect size (Cliff's delta); phân biệt "có ý nghĩa thống kê" với "có ý nghĩa thực tế".
- **Tính hợp lệ:** ghi các đe doạ internal/external/construct/statistical-conclusion và cách giảm thiểu; lần chạy không hợp lệ được ghi lại kèm lý do, không xoá im lặng.
- **Báo cáo:** throughput, p50/p95/p99/p99.9, error rate, tài nguyên (CPU/RAM/connection), kèm Δ so với before; biểu đồ phân phối (CDF/HDR), đường throughput–latency khi quét tải, chuỗi thời gian để thấy độ ổn định.
- Dữ liệu thô trong `results/raw/` đặt tên `<impl>-<scenario>-<run>-<timestamp>`, không sửa tay; thứ tự chạy lưu ở `results/raw/run-order.csv`.

## Tái lập
- Bộ khung dùng lại `shared/scaffold/` (Spring Boot system + experiment kit) được `make new-topic` copy vào `system/` và `experiments/` của mỗi topic; topic chỉ viết phần khác biệt. Cải tiến chung thì sửa ở `shared/scaffold/`, không sửa riêng lẻ trong từng topic.
- Mọi thứ chạy được bằng `make` trong `experiments/` (`make up`, `make run IMPL=x SCENARIO=y`, `make report`, `make down`).
- Ghi môi trường chạy vào `results/env.md`.
- Observability dùng chung (`shared/observability/README.md`): `make obs-up` = metrics + logs + traces + profiles (Prometheus, Loki, Tempo, Pyroscope, Alloy, Grafana); `make obs-up OBS=metrics` = chỉ metrics. Cổng đổi được qua `PROM_PORT`, `GRAFANA_PORT`, `OTLP_*_PORT`, `PYROSCOPE_PORT`.
- Topic nối vào bằng network `backend-lab`, label `lab.scrape/lab.port/lab.path` cho container cần scrape, và `include` exporter trong `shared/observability/exporters/` (postgres, redis, kafka).
- Trong phase 5, app chạy trong container có giới hạn CPU/RAM (giống before và mọi implementation) để đo được tài nguyên bằng `lab_container_*`.
- Cấu hình observability (sampling tracing, profiling, `OBS`) phải GIỐNG NHAU cho before và mọi implementation, ghi vào `results/env.md`. Đo hiệu năng thuần thì dùng `OBS=metrics` + sampling 0; chạy chẩn đoán thì bật full.
- Số liệu từ Prometheus đưa vào `results/raw/` bằng `scripts/prom_export.py`; dashboard chỉ để khám phá, không phải nguồn số liệu.
- Artifact triển khai trong `deploy/` phải được validate bằng công cụ tương ứng (`kubectl --dry-run=client`, `helm template`, `terraform validate`...), ghi lệnh vào 07.

## Git
- Commit sau mỗi phase: `topic(<slug>): phase N - <tóm tắt>`.
