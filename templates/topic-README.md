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

- [ ] Phase 1 — Research → [01-research.md](01-research.md)
- [ ] Phase 2 — System design → [02-system-design.md](02-system-design.md)
- [ ] Phase 3 — Implement → [system/](system/)
- [ ] Phase 4 — Experiment plan → [03-experiment-plan.md](03-experiment-plan.md)
- [ ] Phase 5 — Execute → [experiments/](experiments/) + [results/](results/)
- [ ] Phase 6 — Conclusion → [04-conclusion.md](04-conclusion.md)

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
