# {{TOPIC}}

- **Slug:** `{{SLUG}}`
- **Tạo ngày:** {{DATE}}
- **Cập nhật lần cuối:** {{DATE}}
- **Phase hiện tại:** 0 — chưa bắt đầu

<!-- File này là NGUỒN SỰ THẬT về trạng thái topic. /research và /lab-status đọc nó.
     Sau mỗi phase: tick checklist, cập nhật "Phase hiện tại" + "Cập nhật lần cuối", thêm dòng vào nhật ký quyết định. -->

## Phạm vi

<!-- 2–4 câu: topic này nghiên cứu chính xác điều gì, và KHÔNG nghiên cứu điều gì.
     Ví dụ: "Transactional outbox với PostgreSQL + Kafka: so sánh polling publisher và CDC (Debezium).
     Không bàn về saga hay exactly-once của Kafka Streams." -->

## Checklist

- [ ] Phase 1 — Research → [01-research.html](01-research.html)
- [ ] Phase 2 — System design → [02-system-design.html](02-system-design.html)
- [ ] Phase 3 — Implement → [system/](system/) + [03-implementation.html](03-implementation.html)
- [ ] Phase 4 — Experiment plan → [04-experiment-plan.html](04-experiment-plan.html)
- [ ] Phase 5 — Execute → [experiments/](experiments/) + [results/](results/) + [05-results.html](05-results.html)
- [ ] Phase 6 — Conclusion → [06-conclusion.html](06-conclusion.html)
- [ ] Phase 7 — Production rollout → [07-production.html](07-production.html) + [deploy/](deploy/)

## Implementations

<!-- Điền ở phase 1 (01 §11). ID dùng nhất quán trong mọi tài liệu; slug dùng cho Spring profile và `make run IMPL=<slug>`.
     `before` = hệ thống as-is, luôn là mốc so sánh. -->

| ID | Slug (profile / IMPL) | Mô tả |
|---|---|---|
| before | `before` | Hệ thống as-is, chưa có solution |

## Stack

<!-- Mặc định theo CLAUDE.md: Java 21, Spring Boot 3.x, PostgreSQL, Redis, Kafka, Testcontainers, k6.
     Ghi version đã pin ở đây. Nếu đổi stack, ghi lý do. -->

| Thành phần | Version | Ghi chú |
|---|---|---|
| | | |

## Chờ duyệt

<!-- Các quyết định cần tôi xác nhận. Ở chế độ `all`, gate sau phase 1/2/4 ghi vào đây thay vì dừng.
     Định dạng: - [ ] (phase N) <quyết định> — <phương án đề xuất> / <phương án khác>
     Khi đã duyệt: tick [x] và ghi kết quả vào nhật ký quyết định. -->

## Nhật ký quyết định

<!-- Mỗi quyết định quan trọng một dòng: chọn gì, bỏ gì, vì sao. Không xoá dòng cũ; quyết định bị đảo thì thêm dòng mới. -->

| Ngày | Phase | Quyết định | Lý do / phương án bị loại |
|---|---|---|---|
| {{DATE}} | 0 | Tạo topic | |

## Câu hỏi mở

<!-- Những điều chưa rõ, phát sinh trong quá trình làm. Đánh dấu [x] khi đã trả lời và ghi chỗ trả lời. -->
