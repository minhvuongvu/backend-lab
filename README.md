# backend-lab

"Phòng thí nghiệm" để nghiên cứu sâu từng công nghệ/kỹ thuật backend (Java/Spring Boot, PostgreSQL, Redis, Kafka...) theo quy trình 6 phase, kiểm chứng bằng thí nghiệm thật thay vì chỉ đọc tài liệu.

| Phase | Nội dung | Nơi ghi |
|---|---|---|
| 1 | Research | `01-research.md` |
| 2 | System design | `02-system-design.md` |
| 3 | Implement | `system/` |
| 4 | Experiment plan | `03-experiment-plan.md` |
| 5 | Execute | `experiments/` + `results/` |
| 6 | Conclusion | `04-conclusion.md` |

Quy tắc chung cho mọi phiên Claude Code nằm trong [CLAUDE.md](CLAUDE.md).

## Cách dùng

- Mở Claude Code trong `backend-lab/`.
- `/research transactional outbox`: chạy phase kế tiếp, dừng ở các điểm duyệt.
- `/research transactional outbox 5`: chạy riêng một phase.
- `/research idempotency key all`: chạy một mạch, các điểm cần duyệt ghi vào README của topic.
- `/lab-status`: xem tiến độ mọi topic.
- Một chủ đề, một phiên. Dùng `/clear` khi chuyển chủ đề để context không bị lẫn.
- `make obs-up` trước phase 5 nếu muốn xem metric trên Grafana.
- Yêu cầu: Docker, JDK 21, k6, Python 3 (và GNU make + bash; trên Windows dùng Git Bash/WSL).

### Lệnh make

| Lệnh | Tác dụng |
|---|---|
| `make new-topic SLUG=<kebab-case>` | Tạo topic mới từ `templates/` (cách duy nhất để tạo topic) |
| `make obs-up` | Bật Prometheus (http://localhost:9090) + Grafana (http://localhost:3000, admin/admin) |
| `make obs-down` | Tắt observability stack |

k6 đẩy metric vào Prometheus qua remote write:

```bash
K6_PROMETHEUS_RW_SERVER_URL=http://localhost:9090/api/v1/write \
K6_PROMETHEUS_RW_TREND_STATS="p(50),p(95),p(99),avg,max" \
k6 run -o experimental-prometheus-rw script.js
```

App Spring Boot chạy trên host (cổng 8080, expose `/actuator/prometheus`) được Prometheus scrape qua `host.docker.internal:8080`.

## Cấu trúc

```
backend-lab/
├── CLAUDE.md                 # quy tắc chung
├── Makefile                  # obs-up, obs-down, new-topic
├── scripts/new-topic.sh      # logic của make new-topic
├── .claude/                  # /research, /lab-status, subagent lab-reviewer
├── templates/                # khung tài liệu cho mỗi topic
├── shared/observability/     # Prometheus + Grafana dùng chung
└── topics/<slug>/            # mỗi topic một thư mục
```

## Topics

<!-- topics:start -->
| Topic | Phase hiện tại | Link |
|---|---|---|
<!-- topics:end -->
