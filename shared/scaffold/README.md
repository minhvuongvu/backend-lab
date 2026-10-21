# Bộ khung dùng lại (scaffold)

`make new-topic` copy thư mục này vào `topics/<slug>/system/` và `topics/<slug>/experiments/`. Nhờ vậy mỗi topic bắt đầu phase 3 và phase 5 từ một hệ thống đã chạy được: build pass, test pass, có observability, có k6, tiêm lỗi, kiểm tra toàn vẹn và báo cáo thống kê. Công sức dồn vào phần **khác nhau giữa các implementation**, không phải dựng lại hạ tầng.

Placeholder `{{SLUG}}`, `{{PKG}}`, `{{TOPIC}}` và thư mục `__PKG__` được thay khi tạo topic.

## system/ — Spring Boot (Java 21, Spring Boot 4.1.1, Maven wrapper)

| Phần | Vai trò | Topic phải đổi gì |
|---|---|---|
| `contract/ItemService` | Contract chung mà before và mọi implementation tuân theo | Thay bằng contract ở 02 §5 |
| `impl/before/` (profile `before`) | Hệ thống as-is, phải tái hiện được vấn đề ở 01 §4 | Viết lại theo as-is của topic |
| `impl/a/` (profile `a`) | Mẫu cách một implementation cắm vào bằng `@Profile`. Hiện hành vi y hệt before | Viết implementation A; thêm `impl/b` (profile `b`)… |
| `web/ItemController` | HTTP mỏng, giống nhau cho mọi implementation để k6 gọi cùng API | Đổi endpoint theo contract |
| `config/ObservabilityConfig` + `application.yml` | Tag `topic`, `impl` cho mọi metric; histogram cho p95/p99; tracing OTLP (sampling mặc định 0); tắt đẩy metric qua OTLP (Prometheus là nguồn số liệu duy nhất) | Thường giữ nguyên |
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

### Ghi chú version: Spring Boot 4.1 (chuyển từ 3.5)

- **Vì sao 4.1.1:** Spring Boot 3.5 hết hỗ trợ OSS ngày 30/06/2026 (3.5.16 là bản OSS cuối). 4.1 là dòng ổn định mới nhất, hỗ trợ OSS tới 31/07/2027 theo [endoflife.date](https://endoflife.date/spring-boot); 4.0 chỉ tới 31/12/2026; 4.2 mới ở milestone. Nguồn: [Spring Boot 4.1.1 available now](https://spring.io/blog/2026/08/20/spring-boot-4-1-1-available-now/), [Spring Boot 4.0 Migration Guide](https://github.com/spring-projects/spring-boot/wiki/Spring-Boot-4.0-Migration-Guide).
- **Những gì đã đổi so với 3.5 và vì sao:**

| Thay đổi | Vì sao |
|---|---|
| `spring-boot-starter-web` → `spring-boot-starter-webmvc` | Boot 4 modular: starter cũ bị deprecate, tên mới nói rõ là Spring MVC |
| `flyway-core` → `spring-boot-starter-flyway` (giữ `flyway-database-postgresql`) | Auto-config của Flyway tách thành module riêng; chỉ thêm thư viện Flyway thì không còn được tự cấu hình |
| `micrometer-tracing-bridge-otel` + `opentelemetry-exporter-otlp` → `spring-boot-starter-opentelemetry` | Starter gồm bridge, exporter OTLP và auto-config (module `spring-boot-opentelemetry`) |
| `spring-boot-starter-test` → `spring-boot-starter-webmvc-test` + `spring-boot-starter-jdbc-test` | Mỗi module có starter test riêng, kéo theo `spring-boot-starter-test` |
| Testcontainers `junit-jupiter`, `postgresql` → `testcontainers-junit-jupiter`, `testcontainers-postgresql` (2.0.5); `org.testcontainers.containers.PostgreSQLContainer<?>` → `org.testcontainers.postgresql.PostgreSQLContainer` | Testcontainers 2 thêm tiền tố artifact, chuyển lớp module sang package `org.testcontainers.<module>` và bỏ generic |
| `MeterRegistryCustomizer`: `org.springframework.boot.actuate.autoconfigure.metrics` → `org.springframework.boot.micrometer.metrics.autoconfigure` | Lớp chuyển sang module `spring-boot-micrometer-metrics` |
| `management.otlp.tracing.endpoint` → `management.opentelemetry.tracing.export.otlp.endpoint` | Tên cũ bị loại ở mức `error` từ 4.0.0: Boot bỏ qua nó, trace sẽ không được gửi mà không báo lỗi |
| Thêm `management.otlp.metrics.export.enabled: false`, `management.logging.export.otlp.enabled: false` | Starter OpenTelemetry bật đẩy metric và log qua OTLP mặc định; lab dùng Prometheus scrape và Alloy thu stdout, nên tắt để không tốn tài nguyên của app đang đo và không trùng dữ liệu |
| Kafka (khi bật): `spring-kafka` → `spring-boot-starter-kafka`; `testcontainers-kafka` | Starter modular; `spring.kafka.template/listener.observation-enabled` giữ nguyên tên (mặc định `false`) |

- **Không đổi:** Java 21, Maven wrapper (Maven 3.9.9), cấu trúc contract / `impl/<id>` / profile, Dockerfile (`-Djarmode=tools extract --layers --launcher` vẫn chạy với Boot 4).
- **Đã kiểm chứng thật (21/10/2026):** `./mvnw verify` → BUILD SUCCESS, 6/6 test (before + a, Testcontainers PostgreSQL); image build và app `healthy` trong compose với `IMPL=before` và `IMPL=a`; POST 201 / GET 200; `/actuator/prometheus` có tag `impl`, `topic` và bucket `http_server_requests_seconds_bucket`; trace gửi tới `alloy:4318`; không còn `OtlpMeterRegistry`; không có cảnh báo thuộc tính lỗi thời khi khởi động.
- **Jackson 3:** Boot 4 dùng Jackson 3 (package `tools.jackson`, trừ annotation vẫn ở `com.fasterxml.jackson.annotation`). Bộ khung không import Jackson trực tiếp nên không phải sửa; topic nào cấu hình Jackson thì dùng `JsonMapper`/`JsonMapperBuilderCustomizer` và thuộc tính `spring.jackson.json.*`.

## experiments/ — chạy thí nghiệm

| Phần | Vai trò |
|---|---|
| `docker-compose.yml` | App (build từ `../system`, cùng `cpus`/`mem_limit` cho mọi IMPL, label `lab.*` để Prometheus scrape), PostgreSQL, Toxiproxy chắn giữa app và DB để tiêm lỗi, `include` exporter của observability. Join network `backend-lab` |
| `.env` | Giới hạn tài nguyên, pool size, sampling tracing — giống nhau cho mọi implementation |
| `Makefile` | `up`, `down`, `plan-order`, `pilot`, `run`, `run-matrix`, `integrity`, `report`, `samples-verify`, `env`, `chaos-*` |
| `k6/` | `constant-rate`, `load-sweep`, `spike`, `soak` — đều là mô hình mở (arrival-rate), có warmup tách riêng, không threshold |
| `chaos/` | `toxiproxy.py` (latency, stall, partition, bandwidth, reset), `container.sh` (kill, stop, pause) — mỗi lần tiêm ghi một dòng JSON có timestamp |
| `checker/integrity_check.py` | Kiểm tra invariant sau mỗi lần chạy (đọc mẫu k6 `.csv.gz`), ghi JSON vào `results/raw/` |
| `charts/` | Vẽ CDF latency, cột có CI, đường throughput–latency (chạy trong analysis image); gộp CSV k6 khi cần phân tích tay |

Luồng chạy chuẩn (từ `topics/<slug>/experiments`):

```bash
make -C ../../.. obs-up OBS=metrics   # observability; cùng chế độ cho mọi ô của ma trận
make -C ../../.. analysis-image      # một lần: pandas + matplotlib cho biểu đồ
make up                               # dựng stack
make env                              # ghi results/env.md từ lệnh thật
make pilot                            # ước lượng độ biến thiên -> chốt RUNS
make plan-order RUNS=5 SCENARIOS=S1,F1
make run-matrix                       # chạy theo đúng thứ tự ngẫu nhiên
make report                           # stats.py summarize/compare + biểu đồ
make down
```

### Dữ liệu thô: hai tầng

Mẫu từng request của k6 (`--out csv`) tốn khoảng 100 byte/request: một lần chạy 2 phút ở 2000 req/s đã ~95 MB. GitHub cảnh báo file trên 50 MB và từ chối file trên 100 MB, còn lịch sử git giữ mọi phiên bản mãi mãi. Vì vậy dữ liệu thô chia hai tầng:

| Thư mục | Nội dung | Commit? |
|---|---|---|
| `results/raw/` | File nhỏ, dùng trực tiếp để phân tích: `<id>.summary.json` (tóm tắt k6), `<id>.run.json` (start/end/exit code), `<id>-prom.csv` + `.meta.json` (tài nguyên, JVM, HTTP đúng cửa sổ chạy), `<id>-k6prom.csv`, `<id>-integrity.json`, `run-order.csv`, `chaos.jsonl` | Có. Không file nào quá 10 MB |
| `results/raw-samples/` | Mẫu từng request `<impl>-<scenario>-<run>-<ts>.k6.csv.gz` (k6 nén gzip ngay khi ghi, vì tên file kết thúc bằng `.gz`) — nguồn tính percentile | Không (gitignore) |
| `results/raw-samples/MANIFEST.json` | Mỗi file một dòng: `name`, `bytes`, `sha256`, `rows`, `created`, `command`, `testid` | Có |

`<id>` = `<impl>-<scenario>-<run>-<ts>`. Mỗi `make run` tự ghi cả hai tầng rồi chạy `scripts/raw_manifest.py update` để cập nhật manifest. `make report` kiểm tra mẫu khớp manifest (`raw_manifest.py verify`: sai hash → dừng; thiếu file trên máy này → chỉ báo), đọc thẳng các `.csv.gz` (không cần bước gộp) rồi ghi `runs.csv`, `runs.groups.csv`, `compare-*.csv` vào `results/analysis/` (dẫn xuất, commit được, không bao giờ ghi vào `raw/`).

Hệ quả: số liệu trong 05/06 trỏ tới file trong `results/raw/` hoặc `results/analysis/` (có trong git); mẫu gốc của chúng được ghim bằng sha256 trong manifest, nên máy khác chạy lại `make report` sẽ biết ngay mẫu có đúng là mẫu đã dùng không (`make samples-verify STRICT=1`). Pre-commit hook chặn mọi file staged quá 10 MB (`LAB_MAX_FILE_MB` để đổi) và mọi file trong `raw-samples/` trừ manifest.

Sao lưu mẫu ngoài git (tuỳ chọn, mặc định không cấu hình): Git LFS (`git lfs track "topics/*/results/raw-samples/*.gz"` rồi bỏ dòng ignore tương ứng; tốn quota LFS của GitHub) hoặc một kho ngoài (S3/MinIO, ổ mạng: `rclone copy results/raw-samples remote:backend-lab/<slug>/`). Manifest là thứ để đối chiếu sau khi tải về.

### Biểu đồ

`charts/plot.py` cần pandas + matplotlib; `make report` chạy nó trong image dùng chung `backend-lab/analysis:1` (build một lần: `make -C ../../.. analysis-image`), vì pip trên máy lab bị chặn chứng chỉ TLS còn trong container thì không. Repo được mount vào `/lab`:

```bash
docker run --rm -v "$(cd ../../.. && pwd -W):/lab" -w /lab/topics/<slug>/experiments backend-lab/analysis:1 \
  python charts/plot.py cdf --k6 ../results/raw-samples/*.k6.csv.gz --scenario S1 --out ../results/charts/S1-latency-cdf.png
```

### Cổng

Toxiproxy dùng cổng API 8474, Prometheus 9090. Nếu cổng bị chiếm, ghi đè trong `lab.env` ở gốc repo (copy từ `lab.env.example`, không commit): Makefile của experiments `include` file này và `export` các biến, nên compose, `chaos/toxiproxy.py` và bước xuất Prometheus của `make run` (`PROM_PORT`) dùng cùng cổng với `make obs-up`. Không có `lab.env` thì dùng mặc định.

## Những gì topic phải làm, không được để nguyên

- Thay domain, contract, schema, request trong `k6/lib.js` (`createItem`), SQL trong `reset` và `integrity_check.py`.
- Viết implementation thật thay cho `impl/a` (hiện chỉ là bản sao before).
- Định nghĩa kịch bản S*/F* trong 04 và ánh xạ sang `SCRIPT`, `RATE`, các lệnh `chaos-*`.
- Ghi mọi thay đổi so với khung vào 03 (bước nào, vì sao).
