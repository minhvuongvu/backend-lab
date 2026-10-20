# {{TOPIC}} — Experiment plan

> Phase 4 · Cập nhật: {{DATE}}
> Viết TRƯỚC khi chạy. Sau khi chạy, không sửa giả thuyết; sai thì ghi là sai ở 04-conclusion.md.

## 1. Giả thuyết

<!-- Lấy từ 01-research.html §14 (cột "Dự đoán hiện tại"); kịch bản lỗi lấy từ §8. Mỗi giả thuyết phải bác bỏ được (falsifiable) và có ngưỡng định lượng nếu có thể.
     Ví dụ: "H1: Ở 1k req/s, impl B có p99 cao hơn A không quá 20% (vì thêm 1 INSERT trong cùng transaction)." -->

| ID | Từ câu hỏi | Giả thuyết | Lý do kỳ vọng | Bác bỏ nếu |
|---|---|---|---|---|
| H1 | Q1 | | | |

## 2. Biến

- **Biến độc lập** (thứ thay đổi, mỗi lần chỉ 1): <!-- implementation, tải (req/s), kích thước payload, số partition... và các mức giá trị -->
- **Biến phụ thuộc** (thứ đo): <!-- throughput, p50/p95/p99, error rate, CPU/RAM, số connection, số bản ghi mất/trùng... -->
- **Biến kiểm soát** (giữ cố định): <!-- version, heap, pool size, tài nguyên Docker, dữ liệu khởi tạo -->

## 3. Workload

<!-- Mô tả k6 scenario: executor (constant-arrival-rate được ưu tiên để tránh coordinated omission), rate, duration,
     phân phối key, kích thước dữ liệu, dữ liệu seed. Warmup bao lâu và có bị loại khỏi số liệu không. -->

- Warmup:
- Thời lượng đo:
- Số lần lặp mỗi kịch bản: ≥ 3

## 4. Kịch bản

### 4.1. Bình thường

| ID | Mô tả | Tham số |
|---|---|---|
| S1 | | |

### 4.2. Lỗi

<!-- Bắt buộc với kỹ thuật reliability/consistency: kill container, network delay/partition (tc netem, toxiproxy),
     crash giữa transaction, disk đầy... Mỗi kịch bản: lỗi được tiêm lúc nào, kéo dài bao lâu, và KIỂM TRA ĐÚNG ĐẮN gì sau đó. -->

| ID | Lỗi tiêm vào | Thời điểm / thời lượng | Kiểm tra toàn vẹn dữ liệu |
|---|---|---|---|
| F1 | | | |

## 5. Ma trận impl × scenario

<!-- ✓ = chạy, — = không áp dụng (ghi lý do). Mỗi ô ✓ chạy ≥ 3 lần. -->

| Impl \ Scenario | S1 | F1 |
|---|---|---|
| A (baseline) | ✓ | ✓ |

## 6. Tiêu chí đánh giá

<!-- Thế nào là "tốt hơn"? Thứ tự ưu tiên giữa đúng đắn, latency, throughput, tài nguyên, độ phức tạp vận hành.
     Ngưỡng nào thì chênh lệch được coi là có ý nghĩa (so với độ biến thiên giữa các lần chạy)? -->

## 7. Yếu tố gây sai lệch trên máy local và cách giảm thiểu

<!-- Ví dụ: load generator và hệ thống tranh CPU trên cùng máy; Docker Desktop VM giới hạn tài nguyên;
     JIT/cache chưa warm; thermal throttling; tác vụ nền; page cache của DB; clock skew khi đo latency end-to-end. -->

| Yếu tố | Ảnh hưởng | Giảm thiểu |
|---|---|---|
| | | |

## 8. Cách thu thập & lưu kết quả

- Lệnh: `cd experiments && make up && make run IMPL=<impl> && make report`
- Raw: `results/raw/<impl>-<scenario>-<run>-<timestamp>.*` (không sửa tay)
- Môi trường: `results/env.md`
- Biểu đồ: `results/charts/`
