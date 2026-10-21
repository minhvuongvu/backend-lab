---
paths:
  - "topics/**/experiments/**"
  - "topics/**/results/**"
  - "topics/**/04-*.html"
  - "topics/**/05-*.html"
  - "topics/**/06-*.html"
  - "shared/scaffold/**"
  - "shared/observability/**"
  - "shared/analysis/**"
---

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
- **Dữ liệu thô hai tầng:** `results/raw/` chỉ chứa file nhỏ dùng trực tiếp để phân tích (k6 summary JSON, `prom_export` CSV, integrity JSON, `run-order.csv`), không file nào quá 10 MB; mẫu từng request của k6 nằm ở `results/raw-samples/*.k6.csv.gz` (gitignore), chỉ commit `results/raw-samples/MANIFEST.json` (bytes, sha256, rows, lệnh sinh, testid; cập nhật bằng `scripts/raw_manifest.py update`). Số liệu trong 05/06 trỏ tới file đã commit ở `results/raw/` hoặc `results/analysis/`; mẫu gốc được ghim bằng sha256 trong manifest (`make samples-verify`). Pre-commit hook chặn file staged > 10 MB (trừ Git LFS) và mọi file trong `raw-samples/` trừ manifest. Lý do: GitHub từ chối file > 100 MB, mà một lần chạy k6 `--out csv` dài vài phút đã ~95 MB.

## Tái lập
- Bộ khung dùng lại `shared/scaffold/` (Spring Boot system + experiment kit) được `make new-topic` copy vào `system/` và `experiments/` của mỗi topic; topic chỉ viết phần khác biệt. Cải tiến chung thì sửa ở `shared/scaffold/`, không sửa riêng lẻ trong từng topic.
- Mọi thứ chạy được bằng `make` trong `experiments/` (`make up`, `make run IMPL=x SCENARIO=y`, `make report`, `make down`).
- Ghi môi trường chạy vào `results/env.md`.
- Xử lý số liệu và vẽ biểu đồ chạy trong image phân tích pin version (`shared/analysis/`, `make analysis-image`; chạy bằng `make analysis CMD="python scripts/... "` ở gốc repo), không phụ thuộc pip trên máy host. Đổi version trong `shared/analysis/requirements.txt` là thay đổi phương pháp: ghi vào `results/env.md`.
- Observability dùng chung (`shared/observability/README.md`): `make obs-up` = metrics + logs + traces + profiles (Prometheus, Loki, Tempo, Pyroscope, Alloy, Grafana); `make obs-up OBS=metrics` = chỉ metrics. Cổng đổi được qua `PROM_PORT`, `GRAFANA_PORT`, `OTLP_*_PORT`, `PYROSCOPE_PORT`, đặt cố định cho máy trong `lab.env` (copy từ `lab.env.example`, không commit); Makefile gốc và `experiments/Makefile` của topic tự nạp nên mọi lệnh dùng cùng cổng.
- Topic nối vào bằng network `backend-lab`, label `lab.scrape/lab.port/lab.path` cho container cần scrape, và `include` exporter trong `shared/observability/exporters/` (postgres, redis, kafka).
- Trong phase 5, app chạy trong container có giới hạn CPU/RAM (giống before và mọi implementation) để đo được tài nguyên bằng `lab_container_*`.
- Cấu hình observability (sampling tracing, profiling, `OBS`) phải GIỐNG NHAU cho before và mọi implementation, ghi vào `results/env.md`. Đo hiệu năng thuần thì dùng `OBS=metrics` + sampling 0; chạy chẩn đoán thì bật full.
- Số liệu từ Prometheus đưa vào `results/raw/` bằng `scripts/prom_export.py`; dashboard chỉ để khám phá, không phải nguồn số liệu.
- Artifact triển khai trong `deploy/` phải được validate bằng công cụ tương ứng (`kubectl --dry-run=client`, `helm template`, `terraform validate`...), ghi lệnh vào 07.
