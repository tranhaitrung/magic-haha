## Hướng Dẫn Sử Dụng Facebook Social Affiliate Channel Scanner

### 1. Chuẩn Bị Môi Trường

#### 1.1 Python 3.11+

Kiểm tra version:
```bash
python3 --version
```

#### 1.2 Cài Đặt Dependencies

```bash
# Tạo môi trường ảo (khuyến nghị)
python3 -m venv .venv

# Kích hoạt (macOS/Linux)
source .venv/bin/activate

# Cài đặt packages
pip install -U pip
pip install -r requirements.txt

# Cài Playwright browsers (Chromium)
playwright install chromium
```

### 2. Cấu Hình Ban Đầu

#### 2.1 File config.json

File `config.json` đã được chuẩn bị sẵn với cấu hình mặc định:

```json
{
  "paths": {
    "inbox_dir": "./data/inbox",
    "processing_dir": "./data/processing",
    "output_dir": "./data/output",
    "archive_dir": "./data/archive",
    "error_dir": "./data/error",
    "log_dir": "./logs"
  },
  "eco_domains": [...]  // Danh sách domain Eco
  "shopee_domains": [...], // Danh sách domain Shopee
  "scan": {
    "max_posts_per_channel": 20,
    "max_scroll_times": 10,
    "max_comment_expand": 5,
    // ... các tham số timing khác
  }
}
```

**Khi cần thêm domain mới**: Mở `config.json`, thêm domain vào array `eco_domains` hoặc `shopee_domains`, lưu file, rồi chạy lại tool. Không cần sửa code.

#### 2.2 Chuẩn Bị Browser Profile (Tùy Chọn)

Nếu muốn tránh màn hình đăng nhập Facebook:

**Lần đầu tiên**: Mở Chrome → Đăng nhập Facebook → Tìm thư mục profile:
- **macOS**: `~/Library/Application Support/Google/Chrome/Default`
- **Windows**: `%USERPROFILE%\AppData\Local\Google\Chrome\User Data\Default`

Truyền path này khi chạy tool (xem mục 3.2).

### 3. Chạy Scanner

#### 3.1 Chế Độ Watch-Dir (Khuyến Nghị)

App sẽ pick file cũ nhất từ `data/inbox`, xử lý, rồi chuyển sang `data/output`:

```bash
python3 fb_aff_scanner.py
```

Hoặc chỉ định folder inbox:

```bash
python3 fb_aff_scanner.py --watch-dir ./data/inbox
```

**Quy trình**:
1. Đặt file Excel vào `data/inbox/`.
2. Chạy command trên.
3. Tool tự động move file vào `data/processing`, xử lý, rồi move input sang `data/archive`.
4. Output CSV được lưu trong `data/output/`.

#### 3.2 Chế Độ Single-File

Chạy scan 1 file cụ thể:

```bash
python3 fb_aff_scanner.py --input /path/to/input.xlsx
```

#### 3.3 Với Chrome Profile (Để Tránh Login)

Truyền profile path:

```bash
# macOS
python3 fb_aff_scanner.py --profile ~/Library/Application\ Support/Google/Chrome/Default

# Linux
python3 fb_aff_scanner.py --profile ~/.config/google-chrome/Default

# Windows
python3 fb_aff_scanner.py --profile "%USERPROFILE%\AppData\Local\Google\Chrome\User Data\Default"
```

### 4. Chuẩn Bị File Input

File input phải là Excel (.xlsx) với cột `channel_url` bắt buộc:

| channel_url | note |
| --- | --- |
| https://www.facebook.com/example.page | Kênh review mỹ phẩm |
| https://www.facebook.com/groups/12345 | Group deal săn sale |
| https://www.facebook.com/user.name | Profile cá nhân |

**Lưu ý**:
- Cột `channel_url` phải ở hàng 1 (header).
- URL phải bắt đầu bằng `http://` hoặc `https://`.
- Cột `note` là tùy chọn, chỉ để ghi chú nội bộ.

Đặt file vào `data/inbox/` rồi chạy tool.

### 5. Theo Dõi Quá Trình

Tool sẽ in log trực tiếp ra terminal:

```
2026-05-12 10:30:45 [INFO] Loaded 10 valid channel URLs
2026-05-12 10:30:50 [INFO] [1/10] Scanning: https://www.facebook.com/test.page
2026-05-12 10:31:02 [INFO] Found 15 posts — scanning comments...
2026-05-12 10:31:45 [INFO] ✓ HIT — post: https://www.facebook.com/...
2026-05-12 10:32:10 [INFO] [2/10] Scanning: https://www.facebook.com/...
...
2026-05-12 11:05:30 [INFO] Done. total=10 success=8 failed=2 output=./data/output/scan_output_...xlsx
```

File log đầy đủ được lưu tại `logs/scanner.log`.

### 6. Xem Kết Quả Output

Sau khi scan xong, file output sẽ nằm trong `data/output/`:

**Tên file**: `scan_output_<input_basename>_YYYYMMDD_HHMMSS.csv`

**Ví dụ**: `scan_output_channels_20260512_103530.csv`

**Cấu trúc output**:
- **channel_url**: URL kênh từ input
- **channel_name**: Tên kênh lấy từ `<title>` trang
- **scan_status**: success, login_required, captcha, blocked, no_post, error
- **has_shopee_affiliate**: yes/no
- **has_eco_link**: yes/no
- **matched_post_url**: URL bài viết tìm thấy link
- **matched_comment_text**: Nội dung comment (max 300 ký tự)
- **original_comment_link**: URL gốc từ comment
- **redirect_chain**: Chuỗi redirect, nối bằng `→`
- **final_url**: URL sau cùng sau redirect
- **detected_domain**: Domain khớp (shopee.vn, goeco.link, v.v.)
- **scanned_at**: Timestamp scan
- **error_message**: Lý do lỗi nếu có

**Màu sắc**:
- **Xanh**: `has_shopee_affiliate = yes` hoặc `has_eco_link = yes` hoặc `scan_status = success`
- **Đỏ**: `no` hoặc `error`
- **Vàng**: Warning states (login_required, blocked, no_post)

### 7. Xử Lý Lỗi Thường Gặp

#### 7.1 "Login Required" Nhiều Lần Liên Tiếp

Nếu gặp 3 kênh liên tiếp `login_required`, tool tự dừng. Giải pháp:
- Truyền `--profile` với folder Chrome đã login.
- Hoặc mở browser bằng tay, đăng nhập vào Facebook, rồi chạy lại.

#### 7.2 "CAPTCHA Detected"

Tool sẽ dừng ngay và lưu partial output (những channel đã scan được). Giải pháp:
- Giải CAPTCHA bằng tay trên màn hình.
- Chạy lại tool sau khi CAPTCHA được xác nhận.

#### 7.3 "No Posts Found"

Kênh có thể là:
- Không công khai (private).
- Chỉ có reels, không có bài viết thông thường.
- Layout khác thường (events-only, v.v.).

Kiểm tra thủ công trên Facebook.

#### 7.4 Config Error

Nếu gặp lỗi khi load config:
```
ERROR: Failed to load config: ...
```

Kiểm tra `config.json`:
- Syntax JSON hợp lệ (dùng [jsonlint.com](https://jsonlint.com) để check).
- Các field bắt buộc có đủ: `paths`, `eco_domains`, `shopee_domains`, `scan`.

### 8. Tệp Trạng Thái (Advanced)

Các file được di chuyển tự động theo trạng thái:

- **data/inbox/**: File chưa xử lý
- **data/processing/**: File đang chạy (nếu app crash, file vẫn ở đây)
- **data/archive/**: File đã scan thành công
- **data/error/**: File lỗi schema hoặc exception không recover
- **data/output/**: File CSV output
- **logs/**: File scanner.log

Nếu app bị ngắt giữa chừng, file ở `processing/` sẽ được xử lý lại khi chạy tiếp.

### 9. Command Reference

```bash
# Watch-dir mặc định (sử dụng ./data/inbox)
python3 fb_aff_scanner.py

# Watch-dir custom
python3 fb_aff_scanner.py --watch-dir /custom/path

# Single-file
python3 fb_aff_scanner.py --input /path/to/file.xlsx

# Với config custom (mặc định là ./config.json)
python3 fb_aff_scanner.py --config /custom/config.json

# Với Chrome profile
python3 fb_aff_scanner.py --profile /path/to/chrome/profile

# Kết hợp
python3 fb_aff_scanner.py --input /data/input.xlsx --profile ~/.config/google-chrome/Default
```

### 10. Logs & Debugging

Xem log realtime:
```bash
tail -f logs/scanner.log
```

Xem log của lần chạy cuối cùng:
```bash
cat logs/scanner.log
```

Để enable debug chi tiết hơn, kiểm tra file log text trước khi report vấn đề.

---

**Ghi chú**: Tool chạy ở **headful mode** (mở browser có giao diện) để tránh bị coi là bot. Không close/alt-tab browser khi tool đang chạy.
