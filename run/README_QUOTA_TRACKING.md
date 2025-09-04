# Quota Tracking System

## Tổng quan

Hệ thống Quota Tracking được tích hợp vào `all_in_one_backup.py` để theo dõi và quản lý việc sử dụng API, đảm bảo không vượt quá giới hạn quota hàng ngày.

## Tính năng chính

### 1. Token Usage Tracking
- **Gemini API**: Theo dõi số token input/output và chi phí
- **Deepgram API**: Theo dõi thời lượng audio và chi phí
- **Tự động phát hiện ngôn ngữ** để tính token chính xác

### 2. Quota Management
- **Daily Limits**: Tự động reset mỗi ngày
- **Warning System**: Cảnh báo khi sử dụng >80% quota
- **Real-time Monitoring**: Theo dõi trạng thái quota trong thời gian thực

### 3. Cost Calculation
- **Gemini**: $0.075/1M input tokens, $0.30/1M output tokens
- **Deepgram**: $0.0043/phút audio
- **Tự động tính toán** chi phí cho mỗi operation

## Cách sử dụng

### Trong `all_in_one_backup.py`

```python
# Token Calculator được tự động khởi tạo
self.token_calculator = TokenCalculator()

# Theo dõi API calls
self.token_calculator.track_api_call(
    operation="translate",
    input_text="Chinese text",
    output_text="Vietnamese text", 
    api_type="gemini"
)

# Theo dõi Deepgram
self.token_calculator.track_api_call(
    operation="speech_to_text",
    audio_duration=120.5,
    api_type="deepgram"
)

# Hiển thị summary cuối cùng
self.token_calculator.log_summary()
```

### Kiểm tra Quota Status

```python
# Kiểm tra trạng thái hiện tại
status = self.token_calculator.check_quota_status()

# Lấy warnings
warnings = self.token_calculator.get_quota_warnings()

# Export data
self.token_calculator.export_to_file("usage_report.json")
```

## Quota Limits

### Gemini API
- **Daily Tokens**: 15,000,000 tokens
- **Daily Cost**: $10.00
- **Status**: OK (<80%) hoặc WARNING (≥80%)

### Deepgram API  
- **Daily Minutes**: 1,000 minutes
- **Daily Cost**: $4.30
- **Status**: OK (<80%) hoặc WARNING (≥80%)

## Output Format

### Token Usage Summary
```
======================================================================
📊 TOKEN USAGE & QUOTA SUMMARY
======================================================================
📅 Date: 2025-09-04 11:22:04
🔄 Total Operations: 2
🔤 Gemini Operations: 1
🎤 Deepgram Operations: 1

🔤 GEMINI API:
  Total Tokens: 6
  Cost: $0.000002
  Daily Tokens: 6 / 15,000,000 (0.0%)
  Daily Cost: $0.000002 / $10.00 (0.0%)

🎤 DEEPGRAM API:
  Total Cost: $0.008600
  Daily Minutes: 2.0 / 1000.0 (0.2%)
  Daily Cost: $0.008600 / $4.30 (0.2%)

💰 OVERALL SUMMARY:
  Total Cost: $0.008602
  Daily Total Cost: $0.008602
======================================================================
```

### Quota Warnings
```
🚨 QUOTA WARNINGS:
  ⚠️ Gemini API approaching daily limits
  ⚠️ Deepgram API approaching daily limits
```

## Files liên quan

- `token_calculator.py`: Module chính cho quota tracking
- `all_in_one_backup.py`: Script chính đã tích hợp quota tracking
- `test_quota_simple.py`: Test đơn giản
- `demo_quota_tracking.py`: Demo đầy đủ tính năng

## Test và Demo

### Chạy test đơn giản
```bash
cd run
python test_quota_simple.py
```

### Chạy demo đầy đủ
```bash
cd run
python demo_quota_tracking.py
```

### Test tích hợp
```bash
cd run
python test_quota_integration.py
```

## Lưu ý quan trọng

1. **Tự động reset**: Daily tracking tự động reset mỗi ngày
2. **Exception handling**: Có fallback display nếu Token Calculator gặp lỗi
3. **Real-time monitoring**: Theo dõi quota trong thời gian thực
4. **Export capability**: Có thể export data ra JSON để phân tích
5. **Warning system**: Tự động cảnh báo khi gần đạt giới hạn

## Troubleshooting

### Token Calculator không hiển thị
- Kiểm tra logging level (phải là INFO)
- Kiểm tra exception handling trong main script
- Chạy test riêng để verify

### Quota không reset
- Kiểm tra system date
- Restart application nếu cần
- Verify daily tracking logic

### Cost calculation sai
- Kiểm tra pricing constants
- Verify input/output text length
- Check language detection logic


