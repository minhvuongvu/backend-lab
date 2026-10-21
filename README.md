# backend-lab

"Phòng thí nghiệm" để nghiên cứu sâu từng công nghệ/kỹ thuật backend (Java/Spring Boot, PostgreSQL, Redis, Kafka...) theo quy trình 7 phase, kiểm chứng bằng thí nghiệm thật thay vì chỉ đọc tài liệu.

| Phase | Nội dung | Nơi ghi |
|---|---|---|
| 1 | Research: bối cảnh, lý thuyết, các cách implement, đánh đổi | `01-research.html` |
| 2 | System design: hệ thống tối giản, before/after | `02-system-design.html` |
| 3 | Implement: code + hướng dẫn từng bước | `system/` + `03-implementation.html` |
| 4 | Experiment plan: thí nghiệm trước/sau | `04-experiment-plan.html` |
| 5 | Execute: chạy, đo, báo cáo số liệu | `experiments/` + `results/` + `05-results.html` |
| 6 | Conclusion | `06-conclusion.html` |
| 7 | Production rollout | `07-production.html` + `deploy/` |

Mỗi topic so sánh **before** (hệ thống as-is) với từng cách implement. 14 mục tiêu học và nơi trả lời: xem [CLAUDE.md](CLAUDE.md#mục-tiêu-học--nơi-trả-lời). Tài liệu là HTML: mở trực tiếp bằng trình duyệt (cần internet để tải mermaid/highlight.js).

Quy tắc chung cho mọi phiên Claude Code nằm trong [CLAUDE.md](CLAUDE.md).

## Cách dùng

- Mở Claude Code trong `backend-lab/`.
- `/research transactional outbox`: chạy phase kế tiếp, dừng ở các điểm duyệt.
- `/research transactional outbox 5`: chạy riêng một phase.
- `/research idempotency key all`: chạy một mạch, các điểm cần duyệt ghi vào README của topic.
- `/research cache stampede lite`: chế độ học nhanh (ít kịch bản, bỏ phase 7); nâng lên đầy đủ sau bằng `/research cache stampede full`.
- `/lab-status`: xem tiến độ mọi topic và gợi ý topic nên học tiếp theo lộ trình.
- `/research cdc debezium spike`: khám phá nhanh một hiện tượng; `/research redis lock vs postgres advisory lock`: topic so sánh hai công nghệ.
- `/research case-payment-system`: case study tổng hợp — ghép nhiều topic đã học thành một hệ thống và kiểm chứng end-to-end (giai đoạn 8 trong lộ trình).
- Trang tổng (mở bằng trình duyệt): [LAB.html](LAB.html) tổng quan · [ROADMAP.html](ROADMAP.html) lộ trình · [PROBLEMS.html](PROBLEMS.html) tra theo vấn đề · [INSIGHTS.html](INSIGHTS.html) kho insight · [BENCHMARKS.html](BENCHMARKS.html) số liệu tham chiếu · [GLOSSARY.html](GLOSSARY.html) thuật ngữ.
- Một chủ đề, một phiên. Dùng `/clear` khi chuyển chủ đề để context không bị lẫn.
- `make obs-up` trước phase 5 nếu muốn xem metric trên Grafana.
- Yêu cầu: Docker, JDK 21, k6, Python 3 (và GNU make + bash; trên Windows dùng Git Bash/WSL).

### Lệnh make

| Lệnh | Tác dụng |
|---|---|
| `make new-topic SLUG=<kebab-case>` | Tạo topic mới từ `templates/` (cách duy nhất để tạo topic) |
| `make obs-up` | Bật observability đầy đủ: metrics, logs, traces, profiles (Grafana http://localhost:3000, admin/admin) |
| `make obs-up OBS=metrics` | Chỉ Prometheus + Grafana + docker-stats (overhead thấp nhất, dùng khi đo hiệu năng thuần) |
| `make obs-status` | Trạng thái container và health của các target Prometheus |
| `make obs-down` | Tắt observability stack |
| `make insights` | Dựng lại `INSIGHTS.html` từ mọi topic và kiểm tra cấu trúc insight |
| `make hubs` | Dựng lại mọi trang tổng (LAB, INSIGHTS, PROBLEMS, GLOSSARY, BENCHMARKS) và mục Topic liên quan |
| `make roadmap` | Đánh số thứ tự học, xếp nhóm theo giai đoạn và kiểm tra tiền đề / lộ trình trong `ROADMAP.html` |
| `make hubs-check` | Kiểm tra markup insight / vấn đề / thuật ngữ / số liệu của mọi topic |

Cổng đổi được khi bị trùng: `make obs-up PROM_PORT=19090 GRAFANA_PORT=13000 OTLP_GRPC_PORT=14317 OTLP_HTTP_PORT=14318 PYROSCOPE_PORT=14040`.
Cách nối app, exporter, k6 và xuất số liệu vào `results/raw`: [shared/observability/README.md](shared/observability/README.md).

## Cấu trúc

```
backend-lab/
├── CLAUDE.md                 # quy tắc chung
├── ROADMAP.html              # lộ trình topic theo tiền đề (bảng là nguồn dữ liệu, sơ đồ tự sinh)
├── LAB.html, INSIGHTS.html, PROBLEMS.html, GLOSSARY.html, BENCHMARKS.html  # trang tổng, sinh bằng make hubs
├── Makefile                  # obs-up, obs-down, new-topic
├── scripts/new-topic.sh      # logic của make new-topic
├── scripts/prom_export.py    # xuất số liệu Prometheus ra CSV cho results/raw
├── scripts/stats.py          # thứ tự chạy, steady state, CI bootstrap, so sánh với before
├── scripts/roadmap_order.py  # thứ tự học #n, nhóm theo giai đoạn, kiểm tra tiền đề và lộ trình
├── scripts/build_*.py        # build_insights / build_knowledge / build_dashboard: dựng trang tổng, --check markup
├── .claude/                  # /research, /lab-status, subagent lab-reviewer
├── templates/                # khung tài liệu cho mỗi topic
├── shared/observability/     # Prometheus, Loki, Tempo, Pyroscope, Alloy, Grafana dùng chung
├── shared/docs/              # CSS/JS dùng chung cho tài liệu HTML
├── shared/scaffold/          # bộ khung Spring Boot + experiment kit, copy vào mỗi topic khi tạo
└── topics/<slug>/            # mỗi topic một thư mục
```

## Topics

<!-- topics:start -->
| Topic | Phase hiện tại | Link |
|---|---|---|
<!-- topics:end -->
