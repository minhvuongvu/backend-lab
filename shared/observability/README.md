# Shared observability stack

Stack dùng chung cho mọi topic: metrics, logs, traces, profiles, kèm số liệu tài nguyên theo từng container. Mục tiêu:
- **Nhìn để hiểu:** dùng Grafana khi điều tra.
- **Lưu để chứng minh:** export ra `results/raw/`.

Trong lab này, dashboard chỉ để khám phá. Mọi con số đưa vào 05/06 phải lấy từ file export hoặc k6 summary (xem §7).

## 1. Tổng quan

| Tín hiệu | Thành phần | Cổng trên host (mặc định → biến override) |
|---|---|---|
| Metrics (lưu, query) | Prometheus `v3.13.4` (LTS) | `9090` → `PROM_PORT` |
| UI, correlation | Grafana `13.2.4` | `3000` → `GRAFANA_PORT` (admin/admin) |
| Tài nguyên từng container | `docker-stats` exporter (Python stdlib, Docker Engine API) | không publish (Prometheus scrape nội bộ `:9417`) |
| OTLP ingest (traces/logs/metrics) | Grafana Alloy `v1.21.0` | `4317` → `OTLP_GRPC_PORT`, `4318` → `OTLP_HTTP_PORT`, UI `12345` → `ALLOY_PORT` |
| Logs | Loki `3.7.8` | không publish (Grafana query nội bộ) |
| Traces | Tempo `3.1.0` (monolithic) | không publish |
| Profiles | Pyroscope `1.21.1` | `4040` → `PYROSCOPE_PORT` |
| Datastore metrics | postgres-exporter `v0.20.1`, redis_exporter `v1.94.0`, kafka-exporter `v1.10.0` | chạy trong stack của topic (§3) |

Mọi cổng bind `127.0.0.1`.

```
 topic stack (network backend-lab)                       shared stack (backend-lab-obs)
 ┌───────────────────────────────┐
 │ app container  (labels lab.*) │──scrape /actuator/prometheus──┐
 │ *-exporter     (labels lab.*) │──scrape /metrics──────────────┤ docker_sd_configs
 │ stdout/stderr ────────────────┼──docker socket──► Alloy ──────┼──► Loki
 │ OTLP :4318 ───────────────────┼──────────────────► Alloy ──┬──┼──► Tempo ──metrics-generator──► Prometheus
 └───────────────────────────────┘                            ├──┼──► Loki            (service graph, span metrics)
                                                              └──┼──► Prometheus (OTLP metrics, remote write)
 Docker Engine API ──► docker-stats exporter ──scrape──────────────► Prometheus   (lab_container_*)
 app on host :8080-8082 ──scrape host.docker.internal──────────────► Prometheus   (job spring-host)
 k6 ──remote write /api/v1/write─────────────────────────────────────► Prometheus   (k6_*)
 Pyroscope Java agent ──push :4040────────────────────────────────────► Pyroscope
                                         Grafana ◄── Prometheus · Loki · Tempo · Pyroscope
```

**Vì sao không dùng cAdvisor?** Trên Docker Desktop/WSL2, cAdvisor không phát hiện được container nào (API chỉ trả về `/`). Lỗi này đã tái hiện với v0.49.1, v0.52.1 và v0.53.0, kể cả khi bật `privileged` và `cgroup: host`. `docker-stats` lấy số liệu từ chính API mà `docker stats` dùng nên chạy được mọi nơi có Docker. Nó xuất `lab_container_*`: CPU seconds, CPU limit, throttling, memory (trừ inactive page cache, giống `docker stats`), network, block IO, pids, restart, OOM-killed.

**Phạm vi thu thập:** chỉ các container nằm trên network `backend-lab`, gồm stack của topic và chính stack observability (để thấy overhead của nó). Các stack khác trên máy không bị thu.

**Correlation trong Grafana** (datasource đã cấu hình sẵn):
- **Metric → trace:** exemplar `trace_id` (Micrometer) và `traceID` (Tempo metrics-generator).
- **Log → trace:** derived field bắt traceId trong pattern `[app,traceId,spanId]` của Spring Boot, JSON `trace_id`/`traceId`, hoặc label OTLP `trace_id`.
- **Trace → logs / metrics / profile / service map:** `tracesToLogsV2`, `tracesToMetrics`, `tracesToProfiles`, `serviceMap`.

## 2. Chạy

```bash
make obs-up                    # full: Prometheus, Grafana, docker-stats, Alloy, Loki, Tempo, Pyroscope
make obs-up OBS=metrics        # chỉ Prometheus + Grafana + docker-stats (overhead thấp nhất)
make obs-down
```

- **Network:** `backend-lab` là **external**, được `make obs-up` (hoặc `make up` của topic) tạo nếu chưa có. Nhờ vậy bên nào khởi động trước cũng được.
- **Trùng cổng:** máy hiện đã có stack khác chiếm `9090/3000/4317/4318/4040`. Khi đó dùng override, ví dụ:

  ```bash
  make obs-up PROM_PORT=19090 GRAFANA_PORT=13000 OTLP_GRPC_PORT=14317 OTLP_HTTP_PORT=14318 PYROSCOPE_PORT=14040 ALLOY_PORT=22345
  ```

  Nhớ dùng cùng cổng đó cho k6 và cho app chạy trên host.

## 3. Nối một topic vào

Trong `topics/<slug>/experiments/docker-compose.yml`:

```yaml
include:                                    # chỉ include exporter mà topic cần
  - path: ../../../shared/observability/exporters/postgres.yml
  - path: ../../../shared/observability/exporters/redis.yml
  - path: ../../../shared/observability/exporters/kafka.yml

services:
  app:
    image: ...
    environment:
      SPRING_PROFILES_ACTIVE: ${IMPL:-before}
      MANAGEMENT_OTLP_TRACING_ENDPOINT: http://alloy:4318/v1/traces
    labels:
      lab.scrape: "true"                    # Prometheus docker_sd chỉ giữ container có label này
      lab.port: "8080"                      # cổng metrics TRONG container
      lab.path: /actuator/prometheus        # mặc định /metrics
    networks: [default, lab]
  postgres:                                 # tên service khớp mặc định của exporter
    image: postgres:...
    networks: [default, lab]

networks:
  lab:
    name: backend-lab
    external: true
```

**Exporter có sẵn trong `exporters/`.** Mặc định giả định tên service `postgres` / `redis` / `kafka`; override bằng biến môi trường hoặc `env_file` trong `include`:

| File | Biến override | Metric chính |
|---|---|---|
| `postgres.yml` | `PG_EXPORTER_URI` (`postgres:5432/postgres?sslmode=disable`), `PG_EXPORTER_USER`, `PG_EXPORTER_PASSWORD`, `PG_EXPORTER_EXTRA_FLAGS` | `pg_stat_database_*` (connections, commit/rollback, blks_hit/read, deadlocks), `pg_locks_count`, long-running tx |
| `redis.yml` | `REDIS_EXPORTER_ADDR` (`redis://redis:6379`), `REDIS_EXPORTER_PASSWORD` | `redis_commands_*`, `redis_keyspace_hits/misses_total`, `redis_memory_used_bytes`, `redis_evicted_keys_total`, `redis_connected_clients` |
| `kafka.yml` | `KAFKA_EXPORTER_BOOTSTRAP` (`kafka:9092`) | `kafka_consumergroup_lag`, `kafka_topic_partition_current_offset` |

- **Per-query stats của Postgres:** bật extension `pg_stat_statements` trên server, rồi đặt `PG_EXPORTER_EXTRA_FLAGS=--collector.stat_statements`.
- **Metric nội bộ của Kafka broker** (request latency, ISR, purgatory, log flush): kafka-exporter không có. Chỉ khi topic thật sự cần thì gắn `jmx_exporter` javaagent vào broker, rồi thêm label `lab.*` cho cổng của agent.

**Container phải nằm trên network `backend-lab`**, nếu không Prometheus và Alloy không thấy nó. Thiếu label `lab.scrape: "true"` thì Prometheus bỏ qua container, nhưng log vẫn được thu.

## 4. Cấu hình Spring Boot (3.x)

Dependencies:

```xml
<dependency><groupId>org.springframework.boot</groupId><artifactId>spring-boot-starter-actuator</artifactId></dependency>
<dependency><groupId>io.micrometer</groupId><artifactId>micrometer-registry-prometheus</artifactId></dependency>
<dependency><groupId>io.micrometer</groupId><artifactId>micrometer-tracing-bridge-otel</artifactId></dependency>
<dependency><groupId>io.opentelemetry</groupId><artifactId>opentelemetry-exporter-otlp</artifactId></dependency>
<!-- tuỳ chọn: span cho JDBC query -->
<dependency><groupId>net.ttddyy.observation</groupId><artifactId>datasource-micrometer-spring-boot</artifactId></dependency>
```

`application.yml`:

```yaml
management:
  endpoints.web.exposure.include: health,prometheus
  metrics.distribution.percentiles-histogram.http.server.requests: true   # cần cho histogram_quantile p95/p99
  tracing.sampling.probability: 1.0        # mặc định 0.1 (10%) — xem §8 về overhead
  otlp.tracing.endpoint: http://localhost:4318/v1/traces   # trong container: http://alloy:4318/v1/traces
spring:
  kafka:
    template.observation-enabled: true     # span producer + propagate trace context qua header
    listener.observation-enabled: true     # span consumer nối tiếp trace của producer
```

- **Correlation ID trong log:** khi có Micrometer Tracing, Spring Boot tự thêm correlation ID (`traceId`, `spanId` từ MDC) vào log. Muốn đổi format thì dùng `logging.pattern.correlation`.
- **Exemplar:** Micrometer tự gắn exemplar `trace_id` vào histogram khi tracing bật, không cần cấu hình thêm. Trên Grafana bật "Exemplars" trong panel để nhảy sang trace.
- **Logs:**
  - App chạy trong container: stdout được Alloy tự thu, không cần làm gì.
  - App chạy trên host: log không tới Loki. Khi chạy thí nghiệm nên đưa app vào container, vừa có log vừa có `lab_container_*` và giới hạn tài nguyên giống nhau giữa các implementation.
  - Gửi log qua OTLP (Alloy → Loki `/otlp`) là tuỳ chọn: đặt `management.otlp.logging.endpoint: http://localhost:4318/v1/logs` (có trong Spring Boot 3.4+, đã đối chiếu với appendix properties của 3.5) và thêm OpenTelemetry Logback appender để log đi vào OpenTelemetry SDK. Đường OTLP log → Alloy → Loki đã được kiểm tra bằng log mẫu, log vào Loki kèm label `trace_id`.

## 5. Profiling (Pyroscope Java agent)

```bash
# Agent jar: https://github.com/grafana/pyroscope-java/releases  (pin version, tải vào experiments/)
PYROSCOPE_APPLICATION_NAME=<slug>.<impl> \
PYROSCOPE_SERVER_ADDRESS=http://pyroscope:4040 \
PYROSCOPE_PROFILER_EVENT=itimer \
PYROSCOPE_PROFILER_ALLOC=512k \
PYROSCOPE_PROFILER_LOCK=10ms \
PYROSCOPE_FORMAT=jfr \
java -javaagent:pyroscope.jar -jar app.jar
```

- **Địa chỉ server:** `http://pyroscope:4040` khi app chạy trong network `backend-lab`; trên host là `http://localhost:${PYROSCOPE_PORT}`.
- **Event và format:** `PYROSCOPE_PROFILER_EVENT` nhận `itimer` (mặc định), `cpu` hoặc `wall`. Muốn bật thêm alloc/lock thì phải dùng `PYROSCOPE_FORMAT=jfr`.
- **Alloc và lock:** `PYROSCOPE_PROFILER_ALLOC` là ngưỡng byte, để rỗng là tắt. `PYROSCOPE_PROFILER_LOCK` là ngưỡng thời gian chờ lock; tên biến này **chưa xác minh được trên docs chính thức** (chỉ thấy trong ví dụ của bên thứ ba), cần kiểm tra trang Java SDK của Pyroscope trước khi dùng.
- Trên Grafana: Explore → Pyroscope, hoặc Drilldown → Profiles.

## 6. k6

```bash
K6_PROMETHEUS_RW_SERVER_URL=http://localhost:9090/api/v1/write \
K6_PROMETHEUS_RW_TREND_STATS="p(50),p(95),p(99),avg,max" \
k6 run -o experimental-prometheus-rw --tag testid=<impl>-<scenario>-<run> --summary-export ../results/raw/<impl>-<scenario>-<run>-<ts>-k6-summary.json script.js
```

- **`--tag testid=...`:** để dashboard và script export lọc được theo từng lần chạy (`k6_*{testid="..."}`).
- **Chạy k6 bằng Docker (máy chưa có k6):** `docker run --rm -i --network backend-lab -e K6_PROMETHEUS_RW_SERVER_URL=http://prometheus:9090/api/v1/write ... grafana/k6:<version> run - <script.js`. Gọi app bằng tên service nếu app ở trong network, hoặc `host.docker.internal:<port>` nếu app chạy trên host.
- **Trend stats bị tính lại mỗi khoảng flush:** `k6_http_req_duration_p99` trên Prometheus không phải p99 của cả lần chạy. Số liệu cuối cùng lấy từ `--summary-export`.

## 7. Lưu số liệu vào `results/raw`

Dùng `scripts/prom_export.py` (stdlib, gọi Prometheus `query_range`) ngay sau mỗi lần chạy:

```bash
python3 scripts/prom_export.py --prom http://localhost:9090 \
  --start <ISO8601|epoch> --end <ISO8601|epoch> --step 5s \
  --preset resources --label compose_project=<project> \
  --out topics/<slug>/results/raw/<impl>-<scenario>-<run>-<ts>-resources.csv --meta
```

- **Preset:** `resources` | `jvm` | `http` | `k6` | `postgres` | `redis` | `kafka`.
- **`--meta`:** ghi kèm file mô tả query, khoảng thời gian và Prometheus URL, để số liệu tái lập được.
- **Bảng số liệu ở 05/06** phải trỏ tới các CSV này hoặc k6 summary, không trỏ tới screenshot dashboard.

## 8. Overhead & công bằng

Stack này chạy **trên cùng máy** với hệ thống đang đo, nên chính nó là một biến gây nhiễu.

- **Tài nguyên lúc rảnh:** khoảng 600 MiB RAM, đo ngày 2026-10-20: Grafana ~334 MiB, Alloy ~66, Loki ~62, Prometheus ~61, Pyroscope ~43, Tempo ~28, docker-stats ~14. Khi có tải, Alloy, Loki và Tempo tốn CPU tỷ lệ với lượng log/span.
- **Tracing 100% và profiling** thêm CPU, allocation và latency vào chính app đang đo. Mức tăng phụ thuộc throughput và số span mỗi request, chưa đo trong lab này.
- **Quy tắc:**
  - Cấu hình observability phải **giống hệt** nhau giữa `before` và mọi implementation (cùng `OBS`, cùng sampling, cùng profiler).
  - Nên tách hai loại lần chạy:
    - **Performance run:** `OBS=metrics`, `management.tracing.sampling.probability=0`, không gắn profiler.
    - **Diagnosis run:** full stack, sampling 1.0, có profiler. Dùng để giải thích *vì sao*, không lấy số latency từ đây.
  - Ghi lại loại lần chạy và cấu hình observability vào `results/env.md`.
- **Độ phân giải 5s:** `scrape_interval: 5s` cộng với `rate()` làm phẳng các spike ngắn. Latency percentile lấy từ k6 summary (hoặc HdrHistogram), không suy ra từ Prometheus rate.
- **CPU throttling:** nếu container có `cpus` limit, xem `lab_container_cpu_throttled_seconds_total`. p99 tăng vọt nhiều khi là do throttling chứ không do thuật toán.

## 9. Dashboards (folder `backend-lab`)

- **backend-lab — JVM / HTTP / k6:**
  - HTTP rate, error rate, p50/p95/p99.
  - Heap, GC, threads, HikariCP.
  - k6 rate, latency, VUs, dropped iterations.
- **Containers:** CPU (cores), throttling, memory/limit, network, block IO, restarts/OOM theo container, lọc theo `compose_project`.
- **Datastores:**
  - PostgreSQL: connections, TPS, cache hit, locks, deadlocks.
  - Redis: ops, hit ratio, memory, evictions.
  - Kafka: lag theo group/topic, produce rate.
- **Service graph & spans:** RED theo service/span từ Tempo metrics-generator (`traces_spanmetrics_*`, `traces_service_graph_*`).

Ngoài ra Grafana 13 có sẵn các app Drilldown (Metrics, Logs, Traces, Profiles) để khám phá mà không cần dashboard.

## 10. Troubleshooting

| Triệu chứng | Nguyên nhân / cách xử lý |
|---|---|
| Target `docker` không xuất hiện hoặc `down` | Container chưa ở network `backend-lab`, thiếu `lab.scrape: "true"`, hoặc `lab.port` sai (là cổng trong container, không phải cổng publish). Kiểm tra http://localhost:9090/targets |
| Target `spring-host` down | Bình thường khi app không chạy trên host. Nếu đang chạy: kiểm tra `/actuator/prometheus` đã expose chưa |
| Loki "timestamp too old" | Thường do ingest log cũ của container ngoài lab. Alloy đã lọc chỉ lấy network `backend-lab`; nếu còn gặp thì kiểm tra container đó có thật sự thuộc lab không |
| Tempo log `no jobs found` mức error | Backend worker lúc rảnh, không phải lỗi |
| Grafana báo lỗi datasource Loki/Tempo/Pyroscope | Đang chạy `OBS=metrics`, các service đó không được khởi động |
| Không có trace | Sai endpoint OTLP (host: `localhost:${OTLP_HTTP_PORT}`, container: `alloy:4318`), sampling = 0, hoặc thiếu `opentelemetry-exporter-otlp` |
| `docker manifest inspect` / pull lỗi ngắt quãng | Docker Hub rate limit. Chờ rồi thử lại; `docker pull` trực tiếp thường vẫn được |
| Cổng bị chiếm | Override bằng `PROM_PORT`, `GRAFANA_PORT`, `OTLP_*_PORT`, `PYROSCOPE_PORT`, `ALLOY_PORT` (§2) |

## Nguồn

- Spring Boot tracing (sampling, correlation, OTLP dependencies): https://docs.spring.io/spring-boot/3.5/reference/actuator/tracing.html
- Pyroscope Java SDK: https://grafana.com/docs/pyroscope/latest/configure-client/language-sdks/java/
- k6 Prometheus remote write: https://grafana.com/docs/k6/latest/results-output/real-time/prometheus-remote-write/
- Prometheus `docker_sd_configs`: https://prometheus.io/docs/prometheus/latest/configuration/configuration/#docker_sd_config
- Grafana Alloy components: https://grafana.com/docs/alloy/latest/reference/components/
- Tempo 3.0 migration: https://grafana.com/docs/tempo/latest/set-up-for-tracing/setup-tempo/migrate-to-3/
