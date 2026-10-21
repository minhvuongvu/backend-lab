---
description: Nghiên cứu một topic backend theo quy trình 7 phase (research → design → implement → plan → execute → conclusion → production)
argument-hint: <topic | X vs Y> [1-7 | next | all] [full | lite | spike]
---

Đối số: `$ARGUMENTS`

Tách đối số từ cuối lên: nếu từ cuối thuộc {`full`, `lite`, `spike`} thì đó là **chế độ** (bỏ nó đi); sau đó nếu từ cuối thuộc {`1`..`7`, `next`, `all`} thì đó là **phase**; phần còn lại là **tên topic**. Nếu tên topic có dạng `X vs Y` (hoặc `X vs Y vs Z`) thì đây là **topic so sánh** (xem § Topic so sánh), slug `x-vs-y`. Thiếu phase thì phase = `next`. Thiếu chế độ thì dùng `data-field="mode"` trong README của topic (topic mới: `full`).

Tuân thủ mọi quy tắc trong `CLAUDE.md`: 14 mục tiêu học, before, tài liệu HTML, trung thực, tối giản, so sánh công bằng, thí nghiệm, git.

## Phase 0 — Định vị topic

1. Chuyển tên topic thành slug kebab-case (chữ thường, a-z0-9, nối bằng `-`).
2. Liệt kê thư mục trong `topics/` và so khớp gần đúng, không phân biệt hoa thường (ví dụ "Outbox", "transactional outbox pattern" ↔ `transactional-outbox`).
   - Khớp được thư mục có sẵn → dùng thư mục đó. Nếu có nhiều ứng viên, hỏi tôi chọn.
   - Không khớp:
     - topic quá rộng (ví dụ "caching", "microservices", "kafka"): đề xuất 2–4 cách thu hẹp cụ thể (mỗi cách một dòng + slug gợi ý) và hỏi tôi. DỪNG.
     - ngược lại: chạy `make new-topic SLUG=<slug>`. Đây là cách DUY NHẤT để tạo topic; không tự tạo file/thư mục bằng cách khác. Nếu `make` không có, chạy `bash scripts/new-topic.sh <slug>` (chính là thứ Makefile gọi) và báo tôi.
3. Đối chiếu `ROADMAP.html` (hàng `tr[data-slug]`):
   - topic có trong roadmap: nếu `data-prereq` có topic chưa `done` (theo README của topic đó, hoặc chưa tạo), báo các tiền đề còn thiếu, vì sao chúng là tiền đề, và rằng có thể học ngay — phase 1 sẽ viết "Tóm tắt tiền đề" cho phần thiếu. Thứ tự #n chỉ là gợi ý, không chặn; chỉ hỏi lại nếu thiếu từ 3 tiền đề trở lên;
   - topic chưa có trong roadmap: sau khi tạo topic, thêm một hàng vào roadmap (track, tiền đề có lý do, vì sao nên học, chế độ gợi ý), chạy `python3 scripts/roadmap_order.py` để đánh số và xếp nhóm lại, rồi báo tôi.
4. Nếu hội thoại hiện tại đã làm một topic KHÁC: nhắc tôi chạy `/clear` rồi gọi lại lệnh. DỪNG.
5. Đọc `topics/<slug>/README.html` và mọi tài liệu phase đã có nội dung. Trạng thái lấy từ file, không lấy từ trí nhớ hội thoại.
6. Xác định chế độ và phase:
   - chế độ: nếu đối số đổi chế độ so với README (ví dụ topic đang `lite` mà gọi `full`), báo những gì phải bổ sung cho các phase đã xong (xem § Chế độ lite) và hỏi trước khi đổi; ghi `data-field="mode"`.
   - `next` → phase đầu tiên có `data-status` khác `done`/`skipped` trong `ol.phase-list`.
   - chế độ `spike` mới: đánh dấu phase 2 và 7 `skipped` ngay khi tạo topic. Nếu cả 7 đã xong, báo và dừng.
   - `N` → nếu có phase < N chưa `done`, cảnh báo phase nào còn thiếu và hỏi tôi trước khi làm.
   - `all` → chạy lần lượt từ phase `next` tới 7.
7. Nếu `ul.approvals` trong README còn mục `data-status="open"` thuộc phase trước, liệt kê chúng và hỏi tôi có muốn tiếp tục không (trừ chế độ `all`).

Báo ngắn: topic, slug, chế độ, phase sẽ chạy, rồi bắt đầu.

## Phase 1 — Research → `01-research.html` (mục tiêu 1–8, 10)

- Dùng subagent song song để tìm nguồn, mỗi agent một góc:
  1. bối cảnh nghiệp vụ & case study: engineering blog, postmortem, talk của công ty vận hành thật (quy mô, lý do chọn, sự cố);
  2. tài liệu chính thức / spec / paper gốc / định lý nền tảng (đảm bảo, giới hạn lý thuyết);
  3. source code & internals của các thư viện/hạ tầng dùng cho từng cách implement (link tới file/dòng, giá trị mặc định theo version);
  4. failure mode, anti-pattern, issue/bug tracker.
  Mỗi agent trả về tóm tắt kèm link; tự tổng hợp và kiểm tra chéo, chỗ nguồn mâu thuẫn thì ghi rõ.
- Viết theo đúng khung template (27 mục, 5 phần):
  - **A. Bối cảnh:** nghiệp vụ (có số liệu quy mô), hệ thống as-is (= before), mục tiêu đo được, bài toán — xác định loại vấn đề (đúng đắn / hiệu năng / mở rộng / chi phí / vận hành), biểu hiện và chỉ số đo, vì sao khó; lịch sử & bối cảnh ra đời; thuật ngữ;
  - **B. Solution:** mô hình tư duy, cách hoạt động (internals), đảm bảo / KHÔNG đảm bảo, lập luận tính đúng đắn từng bước, mô hình định lượng (công thức + ước lượng bậc độ lớn), mạnh/yếu, failure mode, tiêu chí chọn/bỏ + thay thế, quan hệ với pattern khác;
  - **C. Các cách implement:** tổng quan (before + 2–4 cách); mỗi cách: cách hoạt động, đảm bảo/không đảm bảo, mạnh/yếu, failure mode, giới hạn lý thuyết & đánh đổi nền tảng, mô hình định lượng riêng, tiêu chí chọn/bỏ, các bước thực thi (thiết kế), lưu ý; bảng phi chức năng so với before; hệ sinh thái & công cụ; cây quyết định;
  - **D. Thực tế:** case study có nguồn, hiểu lầm & anti-pattern, tranh luận & câu hỏi mở;
  - **E. Hướng tới thí nghiệm:** chiến lược kiểm chứng, câu hỏi cần kiểm chứng (kèm dự đoán định lượng), tự kiểm tra kiểu phỏng vấn senior, nguồn.
- Mỗi insight có `claim` + `why` (chuỗi nhân quả, không nhắc lại khẳng định) + `evidence`.
- Chủ động tìm chuyên đề đặc thù (CĐn cho solution, CĐ-An cho từng cách): đọc source/issue tracker/postmortem để tìm hiện tượng chỉ cách đó mới có; agent tìm nguồn "failure mode & issue tracker" báo cáo ứng viên chuyên đề. Liệt kê ở danh mục chuyên đề, mỗi chuyên đề có câu hỏi kiểm chứng ở §25.
- Nếu thấy topic cần thêm mục lý thuyết ngoài template (ví dụ mô hình nhất quán hình thức, thuật toán đồng thuận, cấu trúc dữ liệu đặc thù), thêm mục đó và ghi lý do vào nhật ký quyết định.
- Tài liệu dài: có thể chia viết song song theo phần (mỗi agent một phần A–E), agent chính hợp nhất và kiểm tra tính nhất quán.
- **Tóm tắt tiền đề (§6.1):** với mỗi topic tiền đề trong roadmap chưa `done`, viết phần cốt lõi đủ để hiểu topic này (cơ chế liên quan, 1–3 đoạn + sơ đồ nếu cần, insight quan trọng nhất của tiền đề đó) kèm link tới hàng roadmap / topic đó. Mục tiêu: học được topic này mà không phải học trọn tiền đề trước. Tiền đề đã `done` thì chỉ link.
- Điền mục "Phạm vi" và bảng "Implementations" trong README của topic.
- Kiểm tra chất lượng (xem "Kiểm tra tài liệu" bên dưới) → **Gate**.

## Phase 2 — System design → `02-system-design.html`

- Domain tối giản (ánh xạ từ nghiệp vụ thật), kiến trúc before và after của từng cách (mermaid), thành phần + version pin (đã tra bản ổn định hiện tại) + giới hạn tài nguyên giống nhau.
- Contract chung, cách mỗi implementation cắm vào (Spring profile / env).
- Schema dữ liệu, metric cần expose cho mọi tiêu chí "có đo" ở 01 §18 (chọn tín hiệu: metric / log / trace / profile theo `shared/observability/README.md`), cách kiểm tra đúng đắn dữ liệu, những gì cố ý bỏ qua.
- Điền bảng "Stack" trong README của topic.
- Kiểm tra tài liệu → **Gate**.

## Phase 3 — Implement → `system/` + `03-implementation.html` (mục tiêu 9–11)

- Bắt đầu từ bộ khung đã được `new-topic` copy vào `system/` (xem `shared/scaffold/README.md`): thay domain mẫu `Item` bằng domain của topic, định nghĩa contract ở `contract/`, mỗi implementation một package `impl/<id>/` + `@Profile` + `application-<id>.yml`, contract test chạy chung cho mọi implementation.
- Code before và mọi cách implement ở 01, theo contract ở 02. Maven wrapper, Java 21, Spring Boot 4.x (version theo bộ khung). Expose `/actuator/prometheus`, bật tracing OTLP và log correlation theo `shared/observability/README.md`.
- Nếu có từ 2 implementation trở lên, dùng subagent song song: mỗi agent một implementation (module/package riêng), agent chính giữ contract chung, tích hợp và chạy `./mvnw verify`.
- Integration test (Testcontainers):
  - before: test tái hiện bài toán (được kỳ vọng thể hiện lỗi; ghi rõ);
  - mỗi cách: test chứng minh các invariant ở 01 §7 và failure mode chính được xử lý.
- `./mvnw verify` phải pass. Nếu không chạy được (thiếu Docker/JDK), báo rõ và DỪNG, không đánh dấu phase xong.
- Sau khi pass, viết `03-implementation.html`: từng bước thực thi (dependency → migration → config → code → test) của mỗi cách, trích code NGUYÊN VĂN kèm đường dẫn + dòng, giải thích từng thuộc tính cấu hình, lưu ý gặp phải thực tế khi code, bảng so sánh code giữa các cách.

## Phase 4 — Experiment plan → `04-experiment-plan.html` (mục tiêu 12)

- Theo phương pháp luận trong `CLAUDE.md` § Thí nghiệm và khung 04: giả thuyết có hướng + độ lớn dự đoán (01 §11, §25) + ngưỡng thực tế + tiêu chí bác bỏ; thiết kế đối chứng với before; biến và biến gây nhiễu; tuning công bằng; thứ tự chạy ngẫu nhiên theo block; số lần lặp từ pilot.
- Mô hình workload (open model, phân phối arrival/key, dữ liệu so với bộ nhớ), phương pháp đo (điểm đo, percentile từ mẫu thô, steady state, hiệu chuẩn, sức khoẻ load generator, USE/RED, đo tính đúng đắn).
- Đi hết danh mục kịch bản (bình thường, quét tải, spike, soak, quá tải, tiêm lỗi gồm gray failure, phục hồi, nhiều instance, hot key, cold start, tăng trưởng dữ liệu); không áp dụng phải ghi lý do. before cũng chạy mọi kịch bản liên quan.
- Tiêu chí hợp lệ của một lần chạy, quy tắc loại bỏ, kế hoạch phân tích thống kê, đe doạ tính hợp lệ (internal/external/construct/statistical) và cách giảm thiểu.
- Kiểm tra tài liệu → **Gate**.

## Phase 5 — Execute → `experiments/` + `results/` + `05-results.html` (mục tiêu 13)

- `experiments/` đã có sẵn bộ khung (compose, Makefile, k6 constant-rate/load-sweep/spike/soak, chaos toxiproxy/container, integrity checker, charts): chỉ sửa phần khác biệt của topic (service phụ thuộc, exporter cần include, kịch bản k6, invariant cần kiểm, lệnh tiêm lỗi).
- Yêu cầu với `experiments/`: `docker-compose.yml` (join network `backend-lab`, `include` exporter cần thiết, app chạy trong container có giới hạn tài nguyên), script k6 (remote write + `--tag testid=<impl>-<scenario>-<run>`) / chaos, `Makefile` với `make up`, `make run IMPL=x SCENARIO=y`, `make report`, `make down`.
- `make obs-up` trước khi chạy; ghi chế độ observability (`OBS`, sampling, profiling) vào `results/env.md` và giữ nguyên cho mọi ô của ma trận.
- Ghi `results/env.md` bằng output của lệnh thật trước khi chạy.
- Chạy pilot → chốt số lần lặp và thời gian warmup (`scripts/stats.py steady-state`); hiệu chuẩn công cụ đo bằng độ trễ biết trước.
- Sinh thứ tự chạy `scripts/stats.py plan-order` → `results/raw/run-order.csv`; chạy toàn bộ ma trận theo đúng thứ tự đó; lưu raw (k6 summary + mẫu thô `--out csv`) vào `results/raw/<impl>-<scenario>-<run>-<timestamp>.*`, không sửa tay; ghi lần chạy không hợp lệ kèm lý do.
- Phân tích bằng `scripts/stats.py summarize` và `compare --baseline before` (CI bootstrap theo lần chạy, Mann–Whitney, Cliff's delta, ngưỡng thực tế).
- Sau mỗi lần chạy, xuất số liệu Prometheus của khoảng thời gian chạy vào raw bằng `scripts/prom_export.py` (preset `resources`, `jvm`, `http`, `k6` và datastore liên quan) kèm `--meta`.
- Kiểm tra toàn vẹn dữ liệu sau các kịch bản lỗi; lưu kết quả kiểm tra vào raw.
- Bất thường: dùng trace (Tempo), log (Loki) và profile (Pyroscope) để tìm nguyên nhân; ghi lại truy vấn đã dùng.
- Vẽ biểu đồ bằng Python (pandas + matplotlib) vào `results/charts/`, ưu tiên biểu đồ before vs từng cách. Có thể chạy song song bằng subagent: một agent vẽ biểu đồ, một agent kiểm tra toàn vẹn dữ liệu, một agent viết nháp 05.
- Viết `05-results.html`: nhật ký chạy, bảng before vs after kèm Δ, toàn vẹn dữ liệu, độ biến thiên, bất thường & điều tra. Mọi số link tới raw.
- Lệnh nào thất bại thì báo rõ kèm output và DỪNG; không ước lượng thay số liệu.

## Phase 6 — Conclusion → `06-conclusion.html` (mục tiêu 13)

- Kết luận từng cách so với before (được gì, mất gì, vì sao theo cơ chế).
- Kết quả từng giả thuyết: đúng, sai hay chưa kết luận được, kèm effect size, CI và ngưỡng thực tế, và vì sao (cơ chế).
- Mô hình định lượng ở 01 §11 dự đoán đúng/sai bao nhiêu; hiệu chỉnh mô hình bằng số đo.
- Đe doạ tính hợp lệ nào đã thực sự xảy ra và ảnh hưởng tới kết luận ra sao.
- Tiêu chí phi chức năng: dự đoán (01 §13) vs thực đo, giải thích chỗ lệch.
- Điều bất ngờ, decision guide đã hiệu chỉnh, giới hạn so với production, bài học, câu hỏi nghiên cứu tiếp.
- Gọi subagent `lab-reviewer` kiểm tra truy vết số liệu; sửa vấn đề nghiêm trọng.

## Phase 7 — Production rollout → `07-production.html` + `deploy/` (mục tiêu 14)

- Với mỗi cách đáng triển khai (theo 06): khác biệt lab → production, topology, cấu hình lab vs production, capacity planning từ số đo, migration zero-downtime từ before, rollout/rollback, SLO/metric/alert, security, chi phí.
- Viết artifact mẫu trong `deploy/` (Kubernetes manifest / Helm values / config) và validate bằng công cụ có sẵn; công cụ không có thì ghi rõ là chưa validate.
- Runbook theo failure mode và checklist go-live.
- Gọi subagent `lab-reviewer`; sửa vấn đề nghiêm trọng.

## Chế độ lite

Cho topic cần học nhanh. Mục tiêu: vẫn hiểu đúng cơ chế và thấy được khác biệt chính, nhưng bỏ phần tốn thời gian ít giá trị học. Chế độ ghi ở `data-field="mode"` của README topic; mọi quy tắc trong `CLAUDE.md` vẫn áp dụng trừ những điểm nới lỏng dưới đây.

| Phase | Lite làm gì | Được bỏ / rút gọn |
|---|---|---|
| 1 | Bắt buộc §1–4, §8–9, §11 (ngắn), §13–14, §16–18, §25, §27 và chuyên đề đặc thù quan trọng nhất; before + tối đa 2 cách implement | Mục khác ghi "— (lite)"; insight vẫn đủ `why-steps` |
| 2 | Domain, contract, schema, cách cắm implementation | Bảng observability rút gọn |
| 3 | Code + test đúng đắn như full (không nới) | 03 chỉ viết đủ cho bước cốt lõi và cấu hình; bước khác tóm tắt |
| 4 | 1 kịch bản bình thường ở một mức tải + 1 kịch bản lỗi (bắt buộc nếu là reliability/consistency) + kịch bản tái hiện chuyên đề | Không quét tải, soak, spike; bỏ pilot; N = 3 được phép |
| 5 | Thứ tự ngẫu nhiên, steady state, raw, `stats.py` như full | Biểu đồ tối thiểu (CDF + cột có CI) |
| 6 | Kết luận ghi rõ **"khám phá (lite)"**: tạm thời, CI với N = 3 không đáng tin; liệt kê những gì chế độ full sẽ bổ sung | — |
| 7 | Bỏ qua: `data-status="skipped"` | Toàn bộ |

- Gate ở lite: chỉ sau phase 1 và 4.
- Nâng lite → full (`/research <topic> full`): bổ sung các mục đã ghi "— (lite)", thêm implementation và kịch bản còn thiếu, chạy lại phase 5 với N từ pilot, cập nhật 06, rồi làm phase 7.

## Chế độ spike

Khám phá nhanh MỘT hiện tượng hoặc MỘT câu hỏi (thường là một chuyên đề đặc thù, ví dụ "replication slot làm WAL phình khi connector dừng"), không đi cả quy trình. Ghi `data-field="mode"` = `spike`.

- Phase 0: hỏi tôi (hoặc lấy từ đối số) **đích của spike**: hiện tượng/câu hỏi cụ thể, kết quả nào thì coi là trả lời được. Ghi vào `data-field="scope"`.
- Phase 1: chỉ §4 (vấn đề), §8 (cơ chế liên quan), §11 (định lượng cho hiện tượng), chuyên đề đích (đầy đủ), §24–25 (một câu hỏi chính), §27; mục khác ghi "— (spike)". Insight vẫn đủ `why-steps`.
- Phase 2: gộp vào phase 3 (`data-status="skipped"`, lý do "gộp vào 3 — spike").
- Phase 3: hệ thống tối thiểu chỉ đủ tái hiện hiện tượng (dùng bộ khung `shared/scaffold/`); có test chứng minh hiện tượng xảy ra (hoặc không). 03 chỉ các bước cốt lõi.
- Phase 4: một giả thuyết, một kịch bản tái hiện (+ kịch bản đối chứng nếu cần), N = 3; vẫn có steady state và thứ tự ngẫu nhiên nếu có nhiều cấu hình.
- Phase 5–6: như lite; 06 ghi rõ **"spike"**: trả lời câu hỏi đích được tới đâu, độ tin cậy, cần gì để chắc chắn hơn.
- Phase 7: `skipped`.
- Gate: chỉ sau phase 1. Nâng spike → lite/full: bổ sung mục đã ghi "— (spike)", làm phase 2 đầy đủ, mở rộng implementation và kịch bản.

## Topic so sánh (`X vs Y`)

So sánh hai (hoặc nhiều) công nghệ/cách giải cùng một bài toán, ví dụ `Redis distributed lock vs PostgreSQL advisory lock`, `Kafka vs RabbitMQ cho work queue`. Ghi `data-field="type"` = `compare` trong README topic; chế độ (full/lite/spike) vẫn áp dụng như bình thường.

- **Implementations:** mỗi công nghệ được so là một implementation (A = X, B = Y…); `before` vẫn là hệ thống as-is (có thể trùng với một bên nếu hệ thống đang dùng X — ghi rõ).
- **Dùng lại topic đã có:** trước khi viết, tra `ROADMAP.html`, `INSIGHTS.html`, `GLOSSARY.html`, `PROBLEMS.html` và các topic liên quan; phần lý thuyết đã có ở topic khác thì tóm tắt 2–3 câu + link, không viết lại. Ghi nguồn dùng lại vào nhật ký quyết định.
- **Phase 1:** bắt buộc mục "So sánh trực diện" trong 01 (bảng theo chiều: mô hình & đảm bảo, kiến trúc bên trong, đặc tính hiệu năng, mô hình lỗi, vận hành, hệ sinh thái, chi phí, độ khó di chuyển X ↔ Y), mỗi ô có lý do nhân quả `[Rn]`; tập trung vào chỗ hai bên KHÁC nhau về cơ chế và vì sao khác.
- **Phase 4:** cùng contract, cùng workload, tuning công bằng là điều kiện sống còn (so sánh công nghệ dễ thiên vị nhất ở đây); ghi quá trình tuning của từng bên.
- **Phase 6:** decision guide "chọn X khi…, chọn Y khi…" có điều kiện định lượng; ghi rõ phạm vi kết luận (version, cấu hình, quy mô đã thử).
- **Roadmap:** topic so sánh nhận các topic về X và Y (nếu có) làm tiền đề.

## Kiểm tra tài liệu (trước gate / trước khi kết thúc phase có tài liệu HTML)

- Không còn `<div class="guide">`, ô/placeholder rỗng, hay class `draft`.
- Mỗi phần lớn có ít nhất một `callout insight`; khẳng định quan trọng đều có nhãn; mọi `href="#src-N"` trỏ tới nguồn tồn tại.
- Mục tiêu học của phase (bảng trong `CLAUDE.md`) đều đã được trả lời cho before và MỌI cách implement (ở lite: các mục bắt buộc của lite).
- Insight có `data-tags` và `id`; hàng vấn đề/failure mode/decision/runbook có `data-problem` (+ `data-kind`/`data-choice`), thuật ngữ có `data-term`, số liệu tham chiếu ở 05 có `data-bench`. Chạy `make hubs-check` (hoặc ba lệnh `--check` của `build_insights.py`, `build_knowledge.py`, `build_dashboard.py`); lỗi thì sửa trước khi gate.
- Render bằng headless Chrome/Edge (`--headless=new --dump-dom`) nếu có: không có "Syntax error" của mermaid.

## Gate (sau phase 1, 2 và 4; lite: sau phase 1 và 4; spike: sau phase 1)

1. Gọi subagent `lab-reviewer` với đường dẫn topic và phase vừa xong.
2. Sửa mọi vấn đề **nghiêm trọng**; vấn đề **nên sửa** thì sửa hoặc ghi lý do không sửa vào nhật ký quyết định.
3. Chế độ thường: tóm tắt cho tôi trong 5–10 dòng (đã làm gì, reviewer nêu gì, đã sửa gì) kèm danh sách quyết định cần duyệt, rồi **DỪNG chờ xác nhận**.
4. Chế độ `all`: vẫn chạy reviewer nhưng không dừng; ghi các điểm cần duyệt vào `ul.approvals` trong README của topic (`<li data-status="open" data-phase="N">...`) rồi chạy tiếp.

## Kết thúc mỗi phase

1. Cập nhật `topics/<slug>/README.html`: phase vừa xong `data-status="done"` + `class="done"` (phase đang làm dở: `in-progress`), `data-field="current-phase"`, `data-field="updated"`, thêm dòng vào bảng nhật ký quyết định, cập nhật câu hỏi mở; phase 1 điền `data-field="scope"` và bảng Implementations, phase 2 điền bảng Stack.
2. Cập nhật cột "Phase hiện tại" của topic trong bảng Topics ở `README.md` gốc (ví dụ `2/7 — System design`, thêm ` (lite)` nếu chế độ lite).
3. Cập nhật hàng của topic trong `ROADMAP.html`: `data-status` (`in-progress` khi đang làm, `done` khi xong phase 6 ở lite hoặc phase 7 ở full) và chip hiển thị.
4. Dựng lại các trang tổng: `make hubs` (hoặc lần lượt `build_insights.py`, `build_knowledge.py`, `build_dashboard.py`): cập nhật `INSIGHTS.html`, `PROBLEMS.html`, `GLOSSARY.html`, `BENCHMARKS.html`, `LAB.html` và mục "Topic liên quan" trong README của mọi topic.
5. Commit: `topic(<slug>): phase N - <tóm tắt tiếng Anh>`. Lần commit đầu có `system/`: `git update-index --chmod=+x topics/<slug>/system/mvnw topics/<slug>/experiments/chaos/*.sh` (Windows không giữ bit thực thi). Chỉ add file trong `topics/` (README của topic khác có thể đổi ở mục Topic liên quan), `README.md` gốc, `ROADMAP.html` và các trang tổng `*.html` ở gốc.
