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
- `/research 1`: bắt đầu topic số #1 trong [hub/roadmap.html](hub/roadmap.html) (số đứng trước tên mỗi topic); `/research 1 3` chạy riêng phase 3 của topic đó.
- `/research transactional outbox`: gõ tên/slug thay cho số; chạy phase kế tiếp, dừng ở các điểm duyệt.
- `/research transactional outbox 5`: chạy riêng một phase.
- `/research idempotency key all`: chạy một mạch, các điểm cần duyệt ghi vào README của topic.
- Mọi topic mới mặc định chạy chế độ **lite** (học nhanh: ít kịch bản, bỏ phase 7); nâng lên đầy đủ sau bằng `/research cache stampede full` (hoặc `/research 12 full`).
- `/lab-status`: xem tiến độ mọi topic và gợi ý topic nên học tiếp theo lộ trình.
- `/research cdc debezium spike`: khám phá nhanh một hiện tượng; `/research redis lock vs postgres advisory lock`: topic so sánh hai công nghệ.
- `/research case-payment-system`: case study tổng hợp — ghép nhiều topic đã học thành một hệ thống và kiểm chứng end-to-end (giai đoạn 8 trong lộ trình).
- Trang tổng (mở bằng trình duyệt): [hub/lab.html](hub/lab.html) tổng quan · [hub/roadmap.html](hub/roadmap.html) lộ trình · [hub/problems.html](hub/problems.html) tra theo vấn đề · [hub/insights.html](hub/insights.html) kho insight · [hub/benchmarks.html](hub/benchmarks.html) số liệu tham chiếu · [hub/glossary.html](hub/glossary.html) thuật ngữ · [hub/questions.html](hub/questions.html) hỏi đáp + câu hỏi nên hỏi (tự ôn: ẩn đáp án).
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
| `make insights` | Dựng lại `hub/insights.html` từ mọi topic và kiểm tra cấu trúc insight |
| `make hubs` | Dựng lại mọi trang tổng (LAB, INSIGHTS, PROBLEMS, GLOSSARY, BENCHMARKS) và mục Topic liên quan |
| `make roadmap` | Đánh số thứ tự học, xếp nhóm theo giai đoạn và kiểm tra tiền đề / lộ trình trong `hub/roadmap.html` |
| `make hubs-check` | Kiểm tra markup insight / vấn đề / thuật ngữ / số liệu của mọi topic |
| `make doctor` | Kiểm tra máy: công cụ, JDK 21, Docker, cổng (theo `lab.env`), TLS, git remote |
| `make analysis-image` | Build image phân tích pin version (pandas + matplotlib) ở `shared/analysis/` |
| `make analysis CMD="python scripts/stats.py ..."` | Chạy lệnh Python trong image phân tích, repo mount tại `/lab` (không cần pip trên máy) |
| `make check` | Mọi kiểm tra: unit test, linter roadmap/trang tổng, trang sinh ra còn mới, cú pháp, render |

Cổng riêng của máy (khi 9090/3000/4317… bị chiếm): `cp lab.env.example lab.env` rồi sửa. File `lab.env` không commit; Makefile gốc và `experiments/Makefile` của mọi topic tự nạp, nên `make obs-up`, thí nghiệm và k6 dùng cùng cổng. Ghi đè tạm một lần vẫn được: `make obs-up GRAFANA_PORT=13001`.
Cách nối app, exporter, k6 và xuất số liệu vào `results/raw`: [shared/observability/README.md](shared/observability/README.md).

## Cấu trúc

```
backend-lab/
├── index.html                # trang chủ (sinh từ README.md) — mở file này trong trình duyệt
├── README.md                 # nguồn của index.html; GitHub hiển thị file này
├── CLAUDE.md                 # nguyên tắc cốt lõi cho mọi phiên (cùng .claude/rules/ là nguồn của hub/rules.html)
├── lab.env.example           # mẫu cổng riêng của máy → copy thành lab.env (không commit)
├── Makefile                  # make help: doctor, obs-*, new-topic, roadmap, hubs, check, hooks…
├── hub/                      # các trang tổng, dùng chung thanh điều hướng
│   ├── lab.html              #   tổng quan tiến độ, chờ duyệt, topic sẵn sàng học
│   ├── roadmap.html          #   lộ trình 8 giai đoạn (bảng là nguồn dữ liệu, sơ đồ tự sinh)
│   ├── problems.html         #   tra theo triệu chứng → nguyên nhân, lựa chọn, runbook
│   ├── insights.html         #   kho insight + chuyên đề của mọi topic
│   ├── benchmarks.html       #   số liệu tham chiếu đã đo
│   ├── glossary.html         #   thuật ngữ chung
│   ├── questions.html        #   hỏi đáp + câu hỏi nên hỏi của mọi topic
│   └── rules.html            #   bản HTML của CLAUDE.md + .claude/rules/
├── topics/<slug>/            # mỗi topic: README.html + 01…07 + questions.html + suggested-questions.html + system/ + experiments/ + results/ + deploy/
├── templates/                # khung tài liệu cho mỗi topic
├── shared/docs/              # CSS/JS dùng chung cho mọi trang HTML
├── shared/scaffold/          # bộ khung Spring Boot + experiment kit, copy vào mỗi topic khi tạo
├── shared/observability/     # Prometheus, Loki, Tempo, Pyroscope, Alloy, Grafana dùng chung
├── shared/analysis/          # image Python pin version để xử lý số liệu, vẽ biểu đồ
├── scripts/                  # new-topic, doctor, stats, prom_export, roadmap_order, build_* (trang tổng), check_render
├── tests/                    # unit test cho các script (make test)
└── .claude/                  # /research, /lab-status, subagent lab-reviewer, rules/ (quy tắc chi tiết theo loại file)
```

Trang HTML tự sinh (`index.html`, `hub/*.html` trừ `roadmap.html`) không sửa tay: sửa nguồn rồi chạy `make hubs`.

## Topics

<!-- topics:start -->
| Topic | Phase hiện tại | Link |
|---|---|---|
<!-- topics:end -->
