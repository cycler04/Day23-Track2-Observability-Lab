# Báo cáo phản ánh Lab Ngày 23

**Sinh viên:** *Nguyễn Ngọc Dũng*
**Ngày nộp:** 2026-06-29
**URL GitHub của Lab:** *[https://github.com/cycler04/Day23-Track2-Observability-Lab.git]*

---

# 1. Phần cứng và kết quả kiểm tra môi trường

Kết quả chạy lệnh `python3 00-setup/verify-docker.py`:

```text
Docker:        OK  (28.3.0)
Compose v2:    OK  (2.38.1-desktop.1)
RAM available: 7.63 GB (OK)
Ports free:    OK
Report written: D:\ForCoding\CodeProject\VinAIEnv\Day23-Track2-Observability-Lab\00-setup\setup-report.json
```

---

# 2. Track 02 — Dashboard và Alert

## Dashboard gồm 6 panel

Đính kèm ảnh:

`submission/screenshots/dashboard-overview.png`

## Panel Burn-rate

Đính kèm ảnh:

`submission/screenshots/slo-burn-rate.png`

## Quá trình Alert kích hoạt và khôi phục

| Thời điểm    | Hành động                                               | Minh chứng                    |
| ------------ | ------------------------------------------------------- | ----------------------------- |
| T0           | Dừng container `day23-app` bằng `docker stop day23-app` | Alertmanager bắt đầu kiểm tra |
| T0 + 80 giây | Alert `ServiceDown` được kích hoạt                      | Slack nhận thông báo lỗi      |
| T1           | Khởi động lại ứng dụng bằng `docker start day23-app`    | —                             |
| T1 + 45 giây | Alert được khôi phục (Resolved)                         | Slack nhận thông báo phục hồi |

## Điều khiến tôi bất ngờ về Prometheus và Grafana

Điều khiến tôi ấn tượng nhất là tham số `for:` trong luật cảnh báo của Prometheus. Ban đầu tôi nghĩ rằng khi điều kiện xảy ra thì alert sẽ được kích hoạt ngay, nhưng thực tế `for: 1m` yêu cầu trạng thái lỗi phải duy trì liên tục trong một phút trước khi Prometheus gửi cảnh báo. Đây là cơ chế rất phù hợp trong môi trường thực tế vì giúp loại bỏ các lỗi thoáng qua (transient failures), tuy nhiên khi thực hiện demo cần chờ khoảng 80 giây mới thấy alert xuất hiện.

Ngoài ra, Alertmanager sử dụng `group_wait: 10s` để gom nhiều cảnh báo xảy ra gần nhau thành một thông báo duy nhất gửi đến Slack. Cơ chế này giúp tránh hiện tượng "alert storm" và giảm số lượng thông báo không cần thiết, nhưng cũng đòi hỏi phải hiểu rõ cách Alertmanager thực hiện routing và grouping.

---

# 3. Track 03 — Tracing và Logging

## Ảnh Trace từ Jaeger

Đính kèm:

`submission/screenshots/jaeger-trace.png`

Hiển thị chuỗi span:

```
predict
 ├── embed-text
 ├── vector-search
 └── generate-tokens
```

## Log tương ứng với Trace

```json
{
  "event": "prediction served",
  "log_level": "info",
  "timestamp": "2026-06-29T04:22:13Z",
  "model": "llama3-mock",
  "input_tokens": 4,
  "output_tokens": 54,
  "quality": 0.82,
  "duration_seconds": 0.0186,
  "trace_id": "d175c1724c352ea96e6ed35209f27be4"
}
```

**Trace ID:**

```
d175c1724c352ea96e6ed35209f27be4
```

## Phân tích Tail Sampling

Dịch vụ xử lý khoảng **16 request/giây** khi kiểm thử tải (969 request trong 60 giây).

Với cấu hình giả lập của bài lab:

* 5% request lỗi
* 1% request chậm
* 94% request bình thường

Số trace được lưu lại:

```text
sampled = N × (P(error)×1.0 + P(slow)×1.0 + P(healthy)×0.01)

        = 16 × (0.05 + 0.01 + 0.94 × 0.01)

        = 16 × 0.0694

        ≈ 1.11 trace/giây
```

So với việc lưu toàn bộ trace, phương pháp này giúp giảm khoảng **93% chi phí lưu trữ**.

Bộ nhớ đệm (buffer) sử dụng cửa sổ quyết định 30 giây với khả năng lưu tối đa khoảng **50.000 trace**, tương đương có thể xử lý khoảng **1.666 trace/giây** trước khi xảy ra hiện tượng tràn bộ nhớ đệm.

---

# 4. Track 04 — Drift Detection

## Kết quả PSI

```json
{
  "prompt_length": {
    "psi": 3.461,
    "kl": 1.7982,
    "ks_stat": 0.702,
    "ks_pvalue": 0.0,
    "drift": "yes"
  },
  "embedding_norm": {
    "psi": 0.0187,
    "kl": 0.0324,
    "ks_stat": 0.052,
    "ks_pvalue": 0.133853,
    "drift": "no"
  },
  "response_length": {
    "psi": 0.0162,
    "kl": 0.0178,
    "ks_stat": 0.056,
    "ks_pvalue": 0.086899,
    "drift": "no"
  },
  "response_quality": {
    "psi": 8.8486,
    "kl": 13.5011,
    "ks_stat": 0.941,
    "ks_pvalue": 0.0,
    "drift": "yes"
  }
}
```

## Kiểm định phù hợp với từng đặc trưng

### `prompt_length`

Phù hợp nhất với **KS Test**.

Đây là biến liên tục và không bị giới hạn miền giá trị. Phân phối đã thay đổi đáng kể khi giá trị trung bình tăng từ khoảng 50 lên 85. KS Test là kiểm định phi tham số, nhạy với mọi thay đổi trong phân phối nên rất phù hợp để phát hiện sự dịch chuyển. Mặc dù PSI cũng phát hiện drift rất mạnh (3.46 lớn hơn nhiều so với ngưỡng 0.2), KS còn cung cấp giá trị p-value giúp đánh giá ý nghĩa thống kê của sự thay đổi.

### `embedding_norm`

Phù hợp với **KL Divergence**.

Giá trị này gần tuân theo phân phối chuẩn và hầu như không thay đổi giữa hai tập dữ liệu. KL Divergence đo khoảng cách thông tin giữa hai phân phối nên thích hợp để phát hiện các thay đổi nhỏ đối với những đặc trưng có phân phối đã biết.

### `response_length`

Phù hợp với **PSI**.

Đây là chỉ số nghiệp vụ dễ diễn giải. PSI hoạt động trên dữ liệu đã chia thành các khoảng (bucket), giúp trả lời trực quan câu hỏi liệu độ dài phản hồi có thay đổi đáng kể hay không. Kết quả PSI = 0.016 cho thấy không có dấu hiệu drift.

### `response_quality`

Nên sử dụng kết hợp **KS Test** và **PSI**.

Điểm chất lượng nằm trong khoảng [0,1] và thay đổi rất mạnh từ phân phối Beta(8,2) sang Beta(2,6). Cả PSI (8.85) và KS (0.94) đều phát hiện drift rõ rệt. Trong thực tế, KS thích hợp để phát hiện sớm bằng kiểm định thống kê, còn PSI giúp đánh giá mức độ ảnh hưởng của drift dưới góc nhìn nghiệp vụ.

---

# 5. Track 05 — Tích hợp với các bài Lab trước

## Metric nào khó tích hợp nhất?

Theo tôi, các metric từ **Day 17 (Airflow)** và **Day 18 (Spark)** là khó tích hợp nhất vì chúng yêu cầu triển khai thêm nhiều thành phần hạ tầng như Airflow Scheduler, StatsD Exporter hoặc Spark Metrics Sink. Việc cấu hình và vận hành các thành phần này phức tạp hơn nhiều so với các dịch vụ còn lại.

Trong bài lab này, các exporter mô phỏng của Day 19 (Qdrant) và Day 20 (llama.cpp) chạy trên máy host tại các cổng 9101 và 9102, sau đó Prometheus thu thập dữ liệu thông qua `host.docker.internal`.

Một điểm đáng chú ý là dashboard được thiết kế theo hướng **fail-soft**: khi một dịch vụ không khả dụng, dashboard chỉ hiển thị "No Data" thay vì bị lỗi hoàn toàn. Đây là một nguyên tắc rất quan trọng trong hệ thống quan sát thực tế, bởi chính hệ thống giám sát cũng cần hoạt động ổn định ngay cả khi các dịch vụ được giám sát gặp sự cố.

---

# 6. Thay đổi quan trọng nhất

Thay đổi có tác động lớn nhất là **sửa lại cách tạo Span để các span con được gắn đúng vào span cha `predict`**.

Ban đầu, chương trình sử dụng:

```python
tracer.start_span("predict")
```

để tạo span cha, trong khi các span con lại sử dụng:

```python
tracer.start_as_current_span(...)
```

Vấn đề là `start_span()` chỉ tạo span mới nhưng **không đưa span đó vào context hiện tại**, vì vậy các span con không nhận được span cha và xuất hiện như những root span độc lập trong Jaeger.

Giải pháp là thay bằng:

```python
with tracer.start_as_current_span("predict") as span:
```

Cách này vừa tạo span mới vừa đặt span đó làm span hiện hành, nhờ đó toàn bộ các span con (`embed-text`, `vector-search`, `generate-tokens`) đều được liên kết chính xác với `predict`.

Sau khi sửa, Jaeger hiển thị đúng cây trace:

```
FastAPI handler
└── predict
    ├── embed-text
    ├── vector-search
    └── generate-tokens
```

Điều này giúp việc phân tích nguyên nhân của từng request trở nên trực quan hơn.

Đồng thời, việc liên kết log và trace cũng hoạt động chính xác hơn vì `trace_id` được lấy từ đúng span hiện hành. Nhờ vậy có thể chuyển trực tiếp từ log trong Loki sang trace tương ứng trong Jaeger, hoàn thiện mô hình ba trụ cột của Observability gồm **Metrics – Traces – Logs**.

---

# 7. Bonus — AgentOps (B3)

## agentops-report.json

```json
{
  "generated_at": "04:02:15Z",
  "span_export": true,
  "agent_slis": {
    "tasks": 3,
    "success_rate": 0.667,
    "avg_steps_per_task": 3.33,
    "tool_error_rate": 0.1,
    "cost_per_task_usd": 4.7e-05,
    "loops_detected": 1
  }
}
```

## So sánh pass^k và pass@k

**pass@k** trả lời câu hỏi: *Trong k lần thử, có ít nhất một lần tác vụ thành công hay không?* Đây là chỉ số phản ánh năng lực tối đa của agent.

Tuy nhiên, chỉ số này chưa đủ để đánh giá khả năng triển khai trong thực tế. Một agent có thể đạt **pass@10 = 100%** nhưng nếu chỉ thành công 1 lần trong 10 lần chạy thì vẫn không đủ độ tin cậy cho các quy trình nghiệp vụ.

Ngược lại, **pass^k** yêu cầu agent phải thành công trong **mọi lần thử**, vì vậy phản ánh mức độ ổn định và khả năng triển khai thực tế tốt hơn.

Trong bài lab:

* **Task 1** (mua sản phẩm có giá thấp nhất): `pass^k ≈ 1.0` do thuật toán hoạt động hoàn toàn xác định.
* **Task 2** (kiểm tra tồn kho rồi mua): `pass^k < 1.0` vì dịch vụ kiểm tra tồn kho đôi khi trả về lỗi 503.
* **Task 3** (so sánh giá, có vòng lặp): `pass^k = 0` vì luôn bị cơ chế phát hiện vòng lặp dừng lại.

Theo tôi, chỉ số nên được giám sát đầu tiên là:

```
loops_detected / total_tasks > 0.1
```

Nếu tỷ lệ vòng lặp vượt quá 10%, hệ thống cần phát cảnh báo ngay vì đây là dạng lỗi gây tiêu tốn nhiều token và chi phí nhất trong các workflow của AI Agent.
