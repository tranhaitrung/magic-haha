# Facebook Social Affiliate Channel Scanner

Công cụ tự động quét danh sách kênh Facebook từ file Excel, tìm URL trong bình luận bài viết, resolve chuỗi redirect, và phân loại:

- Có link Shopee Affiliate hay không (`has_shopee_affiliate`)
- Có Eco link trong redirect chain hay không (`has_eco_link`)

Mục tiêu là giảm thao tác kiểm tra thủ công của team Ops và xuất kết quả ra CSV để xử lý tiếp.

## 1. Hướng Triển Khai Phase 1: Local Folder Mode

Phase này chốt dùng thư mục local làm đầu vào/đầu ra, chưa tích hợp Google Drive.

### 1.1 Luồng file vận hành

Tạo cây thư mục local chuẩn:

```text
workspace/
├── data/
│   ├── inbox/        # Ops thả file input vào đây
│   ├── processing/   # file đang được xử lý
│   ├── output/       # output csv sau khi scan
│   ├── archive/      # input đã chạy thành công
│   └── error/        # input lỗi schema hoặc xử lý thất bại
└── logs/
  └── scanner.log
```

Luồng chuẩn:

1. Ops đặt file `.xlsx` vào `data/inbox/`.
2. Scanner pick file cũ nhất, move sang `data/processing/`.
3. Chạy scan và ghi output vào `data/output/`.
4. Nếu thành công: move input sang `data/archive/`.
5. Nếu lỗi không recover: move input sang `data/error/`.

### 1.2 Quy tắc đặt tên file

- Input: giữ nguyên tên do Ops upload.
- Output: `scan_output_<input_basename>_YYYYMMDD_HHMMSS.csv`.
- Error report (nếu có): `error_<input_basename>_YYYYMMDD_HHMMSS.txt`.

## 2. Phạm Vi Phase 1

Được hỗ trợ:

- Đọc input `.xlsx` có cột `channel_url` từ local folder
- Mở kênh Facebook bằng Playwright (headful)
- Scroll tìm bài viết và extract URL trong comment
- Resolve redirect chain cho URL trong comment
- Phân loại Shopee / Eco domain theo `config.json`
- Xuất output CSV theo schema yêu cầu vào local output folder
- Ghi log chi tiết ra `scanner.log` và stdout
- Xử lý các exception quan trọng: login, captcha, blocked, timeout, input invalid

Không thuộc phạm vi:

- Dashboard UI
- Job queue / retry queue / resume jobs
- CRM integration
- Đồng bộ file qua cloud storage
- Bypass CAPTCHA

## 3. Kiến Trúc Cơ Bản (Implement-Ready)

Kiến trúc dự án theo hướng pipeline, tách module rõ ràng để dễ test và dễ thay đổi:

1. `cli`
- Parse tham số dòng lệnh (`--input`, `--profile`)
- Validate input cơ bản
- Khởi tạo runtime và trigger scan
- Hỗ trợ 2 chế độ chạy:
  - `single-file`: chạy 1 file chỉ định
  - `folder-watch`: quét lần lượt file trong `data/inbox`

2. `orchestrator`
- Điều phối state file: `inbox -> processing -> archive/error`
- Đảm bảo không xử lý trùng file trong cùng phiên
- Checkpoint kết quả tạm để tránh mất dữ liệu

3. `config`
- Load và validate `config.json`
- Cung cấp domain lists, scan limits và local folder paths

4. `input_reader`
- Đọc file Excel active sheet
- Tìm cột `channel_url` theo header
- Normalize URL (trim, validate, dedupe)

5. `browser_runtime`
- Khởi tạo Playwright browser context
- Áp dụng anti-bot behavioral settings (delay random, viewport, locale, timezone)
- Quản lý page lifecycle

6. `channel_scanner`
- Điều hướng vào kênh
- Detect status (`login_required`, `captcha`, `blocked`, `no_post`, ...)
- Thu thập danh sách bài viết

7. `post_scanner`
- Mở bài viết
- Expand comment theo giới hạn
- Extract text comment và URL bằng regex

8. `redirect_resolver`
- Resolve redirect chain với timeout
- Ghi nhận `redirect_chain` và `final_url`
- Support timeout/network errors ở cấp URL

9. `classifier`
- Match Shopee domain từ `final_url`
- Match Eco domain trên toàn bộ `redirect_chain`
- Trả về kết quả classify và `detected_domain`

10. `result_writer`
- Ghi output CSV theo schema
- Lưu file vào `data/output/`

11. `logger`
- Log ra stdout + `scanner.log`
- Có format thống nhất để trace và debug

## 4. Luồng Xử Lý Tổng Quan

1. Người dùng chạy tool ở chế độ `single-file` hoặc `folder-watch`.
2. Tool load config và validate input.
3. Tool lấy file từ local path (hoặc đọc file chỉ định).
4. Tool đọc danh sách channel URL hợp lệ.
5. Với mỗi channel:
- Navigate channel page
- Scroll thu thập post links
- Duyệt từng post, extract comment URLs
- Resolve redirect cho từng URL
- Classify Shopee/Eco
- Chốt kết quả cho channel
6. Ghi output CSV, cập nhật trạng thái file input, và log tổng kết.

Ghi chú:

- Nếu gặp CAPTCHA: dừng toàn bộ và xuất partial output.
- Nếu `login_required`: skip kênh hiện tại, tiếp tục kênh sau; dừng toàn bộ nếu vượt ngưỡng liên tiếp.

## 5. Cấu Trúc Output Dữ Liệu

Mỗi channel 1 dòng, bao gồm các cột:

- `channel_url`
- `channel_name`
- `scan_status`
- `has_shopee_affiliate`
- `has_eco_link`
- `matched_post_url`
- `matched_comment_text`
- `original_comment_link`
- `redirect_chain`
- `final_url`
- `detected_domain`
- `scanned_at`
- `error_message`

## 6. Config Vận Hành

Tất cả tham số nằm trong `config.json`, không hardcode:

- Local paths (`inbox_dir`, `processing_dir`, `output_dir`, `archive_dir`, `error_dir`, `log_dir`)
- Domain lists (`eco_domains`, `shopee_domains`)
- Giới hạn scan (`max_posts_per_channel`, `max_scroll_times`, ...)
- Delay ranges và timeout
- Control login-fail threshold

Ví dụ cấu hình local paths:

```json
{
  "paths": {
    "inbox_dir": "./data/inbox",
    "processing_dir": "./data/processing",
    "output_dir": "./data/output",
    "archive_dir": "./data/archive",
    "error_dir": "./data/error",
    "log_dir": "./logs"
  }
}
```

Nguyên tắc:

- Thêm domain mới chỉ cần sửa `config.json`
- Không sửa code cho thay đổi rules domain

## 7. Chiến Lược Trích Xuất Dữ Liệu Hiệu Quả

- Dedupe ở nhiều cấp: channel, post, comment URL
- Cache kết quả redirect resolve trong cùng phiên scan
- Dùng URL pattern để nhận diện post thay vì phụ thuộc class CSS
- Worker pool nhỏ cho redirect resolving để tăng throughput
- Ghi kết quả định kỳ (checkpoint) để giảm mất dữ liệu khi dừng sớm
- Logging có cấu trúc để phân tích bottleneck

## 8. Setup Môi Trường Để Bắt Đầu Implement

1. Cài Python 3.11 hoặc 3.12.
2. Tạo môi trường ảo và cài dependencies.
3. Cài Playwright browser runtime.
4. Tạo cấu trúc thư mục local theo mục 1.1.
5. Tạo `config.json` và cấu hình đầy đủ paths + domains.

Lệnh mẫu:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install playwright openpyxl pydantic
playwright install chromium
```

## 9. Đóng Gói Và Phân Phối Nội Bộ (Windows + macOS)

Mục tiêu: 1 codebase, phát hành artifact riêng cho từng OS.

Phương án khuyến nghị:

- Build binary bằng PyInstaller hoặc Nuitka
- Release 2 nhóm artifact:
  - Windows: `.exe` (zip portable hoặc installer)
  - macOS: binary/app bundle (zip hoặc pkg)
- Config đặt ngoài binary để Ops có thể cập nhật nhanh
- Mỗi release kèm checksum SHA256 và release notes

CI/CD matrix:

- `windows-latest`
- `macos-latest`

Pipeline:

1. Run tests/smoke tests
2. Build artifacts theo OS
3. Tính checksum
4. Upload lên internal release channel

## 10. Runtime Policies Và Compliance

Bắt buộc:

- Không bypass CAPTCHA
- Không fake fingerprint theo hướng stealth hoàn toàn
- Không dùng proxy để đổi IP
- Không auto-login credential
- Production run ở chế độ headful

## 11. CLI Sử Dụng

```bash
python fb_aff_scanner.py --input <path_to_excel> [--profile <chrome_user_data_dir>]
python fb_aff_scanner.py --watch-dir ./data/inbox [--profile <chrome_user_data_dir>]
```

Ý nghĩa tham số:

- `--input`: bắt buộc, đường dẫn file `.xlsx`
- `--watch-dir`: chạy theo chế độ local inbox
- `--profile`: tùy chọn, sử dụng profile đã login Facebook

## 12. Đề Xuất Cấu Trúc Thư Mục

```text
.
├── README.md
├── config.json
├── fb_aff_scanner.py
├── data/
│   ├── inbox/
│   ├── processing/
│   ├── output/
│   ├── archive/
│   └── error/
├── logs/
│   └── scanner.log
├── src/
│   ├── cli.py
│   ├── orchestrator.py
│   ├── models.py
│   ├── config_loader.py
│   ├── excel_reader.py
│   ├── browser_runtime.py
│   ├── channel_scanner.py
│   ├── post_scanner.py
│   ├── redirect_resolver.py
│   ├── classifier.py
│   ├── result_writer.py
│   └── logging_setup.py
├── tests/
│   ├── test_excel_reader.py
│   ├── test_classifier.py
│   └── test_redirect_resolver.py
└── packaging/
    ├── pyinstaller/
    ├── windows/
    └── macos/
```

  ## 13. Trạng Thái File Và Luật Vận Hành

  Mỗi file input có trạng thái xử lý rõ ràng:

  1. `NEW`: nằm trong `inbox`.
  2. `PROCESSING`: đang chạy scan.
  3. `DONE`: đã sinh output và move sang `archive`.
  4. `FAILED`: lỗi schema hoặc lỗi hệ thống không recover, move sang `error`.

  Luật vận hành:

  - Chỉ xử lý 1 file tại một thời điểm trong Phase 1.
  - Nếu app restart, file còn trong `processing` được đưa lại `inbox` để chạy lại.
  - Không ghi đè output cũ, luôn tạo file mới theo timestamp.

  ## 14. Kế Hoạch Implement Theo Thứ Tự

  1. Tạo `models.py` và schema dữ liệu scan/output.
  2. Implement `config_loader.py` + validate config.
  3. Implement `excel_reader.py` + unit test.
  4. Implement `orchestrator.py` cho local file state machine.
  5. Implement scanner core (`browser_runtime`, `channel_scanner`, `post_scanner`).
  6. Implement `redirect_resolver.py` + cache theo phiên.
  7. Implement `classifier.py` + test domain matching.
  8. Implement `result_writer.py` + style output excel.
  9. Wire CLI (`--input`, `--watch-dir`) và logging thống nhất.
  10. Chạy smoke test end-to-end với 1 file mẫu.

  ## 15. Definition Of Done (Tóm Tắt)

- Đọc đúng input Excel có cột `channel_url`
- Scan liên tục nhiều kênh không crash
- Extract + resolve URL đúng logic
- Classify Shopee/Eco đúng theo config
- Xuất Excel đúng schema và màu trạng thái
- Xử lý đầy đủ exception cases quan trọng
- Log đầy đủ để truy vết
- Không hardcode tham số vận hành

---

Nếu cần, bước tiếp theo là bổ sung:

- `config.json` mẫu
- Skeleton source code module
- Hướng dẫn build artifact cho Windows/macOS trong CI
