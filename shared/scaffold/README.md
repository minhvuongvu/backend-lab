# Bộ khung dùng lại (scaffold)

`make new-topic` copy thư mục này vào `topics/<slug>/system/` và `topics/<slug>/experiments/`. Nhờ vậy mỗi topic bắt đầu phase 3 và phase 5 từ một hệ thống đã chạy được: build pass, test pass, có observability, có k6, tiêm lỗi, kiểm tra toàn vẹn và báo cáo thống kê. Công sức dồn vào phần **khác nhau giữa các implementation**, không phải dựng lại hạ tầng.

Placeholder `{{SLUG}}`, `{{PKG}}`, `{{TOPIC}}` và thư mục `__PKG__` được thay khi tạo topic.

## system/ — Spring Boot (Java 21, Spring Boot 3.5.16, Maven wrapper)

| Phần | Vai trò | Topic phải đổi gì |
|---|---|---|
| `contract/ItemService` | Contract chung mà before và mọi implementation tuân theo | Thay bằng contract ở 02 §5 |
| `impl/before/` (profile `before`) | Hệ thống as-is, phải tái hiện được vấn đề ở 01 §4 | Viết lại theo as-is của topic |
| `impl/a/` (profile `a`) | Mẫu cách một implementation cắm vào bằng `@Profile`. Hiện hành vi y hệt before | Viết implementation A; thêm `impl/b` (profile `b`)… |
| `web/ItemController` | HTTP mỏng, giống nhau cho mọi implementation để k6 gọi cùng API | Đổi endpoint theo contract |
| `config/ObservabilityConfig` + `application.yml` | Tag `topic`, `impl` cho mọi metric; histogram cho p95/p99; tracing OTLP (sampling mặc định 0) | Thường giữ nguyên |
| `application-<impl>.yml` | Chỉ chứa cấu hình khác biệt của implementation đó | Giải thích từng thuộc tính trong 03 |
| `db/migration/V1__init.sql` | Bảng mẫu `item` | Thay bằng schema ở 02 §7 |
| `test/.../AbstractIntegrationTest` | Testcontainers dạng singleton (PostgreSQL; Kafka/Redis để sẵn dạng comment) | Bật container cần dùng |
| `test/.../contract/*ContractTest` | Cùng một bộ test chạy cho mọi profile (lớp con theo implementation) | Thêm test invariant và test lỗi của topic |
| `test/.../support/Invariants` | Helper kiểm tra "mỗi id được ack được lưu đúng một lần" | Thêm invariant của topic |
| `Dockerfile` | Multi-stage, layered jar; `MaxRAMPercentage=75` để heap theo giới hạn RAM của container | Thường giữ nguyên |

Vì sao dùng `JdbcClient` thay vì JPA: mọi câu SQL hiện rõ trong code, nên transaction boundary, số round-trip và lock là thứ nhìn thấy và đo được. JPA thêm dirty checking, flush tự động, lazy loading — những cơ chế làm nhiễu phép so sánh, trừ khi chính chúng là chủ đề.

Vì sao test container dạng singleton: `@Testcontainers` + `@Container static` dừng container sau mỗi lớp test, trong khi Spring cache application context giữa các lớp (BeforeContractTest, AContractTest…), làm context đã cache trỏ vào cổng chết.

Lệnh:

```bash
cd system
./mvnw verify                                  # build + test mọi profile với PostgreSQL thật (cần Docker)
SPRING_PROFILES_ACTIVE=a ./mvnw spring-boot:run
```

## experiments/ — chạy thí nghiệm

| Phần | Vai trò |
|---|---|
| `docker-compose.yml` | App (build từ `../system`, cùng `cpus`/`mem_limit` cho mọi IMPL, label `lab.*` để Prometheus scrape), PostgreSQL, Toxiproxy chắn giữa app và DB để tiêm lỗi, `include` exporter của observability. Join network `backend-lab` |
| `.env` | Giới hạn tài nguyên, pool size, sampling tracing — giống nhau cho mọi implementation |
| `Makefile` | `up`, `down`, `plan-order`, `pilot`, `run`, `run-matrix`, `integrity`, `report`, `env`, `chaos-*` |
| `k6/` | `constant-rate`, `load-sweep`, `spike`, `soak` — đều là mô hình mở (arrival-rate), có warmup tách riêng, không threshold |
| `chaos/` | `toxiproxy.py` (latency, stall, partition, bandwidth, reset), `container.sh` (kill, stop, pause) — mỗi lần tiêm ghi một dòng JSON có timestamp |
| `checker/integrity_check.py` | Kiểm tra invariant sau mỗi lần chạy, ghi JSON vào raw |
| `charts/` | Gộp CSV k6, vẽ CDF latency, cột có CI, đường throughput–latency |

Luồng chạy chuẩn (từ `topics/<slug>/experiments`):

```bash
make -C ../../.. obs-up OBS=metrics   # observability; cùng chế độ cho mọi ô của ma trận
make up                               # dựng stack
make env                              # ghi results/env.md từ lệnh thật
make pilot                            # ước lượng độ biến thiên -> chốt RUNS
make plan-order RUNS=5 SCENARIOS=S1,F1
make run-matrix                       # chạy theo đúng thứ tự ngẫu nhiên
make report                           # stats.py summarize/compare + biểu đồ
make down
```

Mỗi `make run` ghi vào `results/raw/`:

- `<impl>-<scenario>-<run>-<ts>.k6.csv`: mẫu thô từng request (nguồn tính percentile).
- `.summary.json`: tóm tắt của k6.
- `.run.json`: thời điểm bắt đầu/kết thúc, exit code.
- `-prom.csv` + `.meta.json`: tài nguyên, JVM, HTTP trong đúng cửa sổ chạy.
- `-k6prom.csv`: metric k6 phía Prometheus.

Dữ liệu dẫn xuất (gộp, tóm tắt, so sánh) nằm ở `results/analysis/`, không bao giờ ghi vào `raw/`.

`charts/plot.py` cần pandas + matplotlib. Máy nào pip bị chặn chứng chỉ TLS (như máy lab hiện tại) thì vẽ trong container, vì lưu lượng từ container không bị chặn:

```bash
docker run --rm -v "$(cd .. && pwd -W):/t" -w /t/experiments python:3.13.7-slim \
  sh -c "pip install -q pandas matplotlib && python charts/plot.py cdf --k6 ../results/analysis/k6-all.csv --scenario S1 --out ../results/charts/S1-latency-cdf.png"
```

Toxiproxy dùng cổng API 8474. Nếu cổng bị chiếm, đặt `TOXIPROXY_API_PORT` (cả compose lẫn `chaos/toxiproxy.py` đều đọc biến này).

## Những gì topic phải làm, không được để nguyên

- Thay domain, contract, schema, request trong `k6/lib.js` (`createItem`), SQL trong `reset` và `integrity_check.py`.
- Viết implementation thật thay cho `impl/a` (hiện chỉ là bản sao before).
- Định nghĩa kịch bản S*/F* trong 04 và ánh xạ sang `SCRIPT`, `RATE`, các lệnh `chaos-*`.
- Ghi mọi thay đổi so với khung vào 03 (bước nào, vì sao).
