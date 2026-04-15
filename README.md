# 🚀 LOCKET GOLD & NEXTDNS MANAGER SYSTEM

Tài liệu hướng dẫn triển khai hệ thống quản lý Locket Gold Premium và NextDNS trên nền tảng Koyeb dưới dạng Web Service.

---

## 📌 NGUYÊN LÝ HOẠT ĐỘNG

### 1. Cơ chế Locket Gold (Premium Crack)
- **Giả lập RevenueCat:** Hệ thống sử dụng script JavaScript can thiệp vào phản hồi từ `api.revenuecat.com`. Script ghi đè dữ liệu gói cước thành trạng thái "Gold" vĩnh viễn (năm 2999).
- **GitHub Automation:** Khi có yêu cầu từ Web, hệ thống sử dụng GitHub API để tự động tạo và đẩy file `.sgmodule` (Shadowrocket) và `.js` lên kho lưu trữ cá nhân.
- **Cài đặt:** Người dùng sử dụng link Raw từ GitHub để thêm vào ứng dụng Shadowrocket.

### 2. Quản lý NextDNS
- **MobileConfig Generator:** Tự động tạo mã XML theo chuẩn Apple (.mobileconfig) để cài đặt DNS mã hóa (DoH) trực tiếp vào thiết bị iOS.
- **Duyệt Premium:** Admin quản lý trạng thái phê duyệt thông qua Telegram Bot, dữ liệu được đồng bộ trực tiếp với Google Sheets.

---

## 🛠 HƯỚNG DẪN TRIỂN KHAI LÊN KOYEB (WEB SERVICE)

### Bước 1: Yêu cầu mã nguồn
Đảm bảo repository GitHub của bạn có đầy đủ các file:
- `bot.py`: File thực thi chính (chứa Flask Web Server và Telegram Bot).
- `requirements.txt`: Chứa danh sách thư viện (Flask, python-telegram-bot, gspread, PyGithub, v.v.).
- `Procfile`: Nội dung `web: python bot.py`.
- `templates/index.html`: Giao diện Dashboard Web.

### Bước 2: Tạo Service trên Koyeb
1. Truy cập [Koyeb App](https://app.koyeb.com/) -> **Create Service**.
2. Chọn **GitHub** và trỏ tới repository của bạn.
3. Cấu hình **Build & Deployment**:
   - **Builder:** Python.
   - **Run command:** `python bot.py`
   - **Port:** `8000` (Phải khớp với cấu hình trong code).

### Bước 3: Cấu hình Biến môi trường (Environment Variables)
Tại mục **Environment Variables** trên Koyeb, thêm các biến sau:

| Biến | Mô tả |
| :--- | :--- |
| `BOT_TOKEN` | Token lấy từ @BotFather |
| `ADMIN_ID` | ID Telegram của Admin (dùng để thực hiện lệnh điều khiển) |
| `SHEET_ID` | ID của file Google Sheet (từ URL của file) |
| `GOOGLE_CREDS` | Toàn bộ nội dung file JSON của Google Service Account |
| `GH_TOKEN` | GitHub Personal Access Token (quyền ghi repo) |
| `REPO_NAME` | Định dạng: `tên_user/tên_repo` |
| `PORT` | `8000` |

### Bước 4: Cấu hình Google Sheets
1. Tạo một bảng tính Google Sheet mới.
2. Tạo 4 Worksheet (tab) với tên: `modules`, `users`, `admin`, `data`.
3. Nhấn **Share** và cấp quyền **Editor** cho email của Service Account (tìm thấy trong file JSON của bạn).

---

## 📱 DANH SÁCH LỆNH TELEGRAM BOT
- `/start`: Khởi động và đăng ký thành viên.
- `/get [username]|[date]`: Tạo nhanh module Locket Gold.
- `/nextdns [ID]`: Tạo cấu hình DNS Apple.
- `/approve [UID]`: (Admin) Phê duyệt người dùng Premium.
- `/broadcast [text]`: (Admin) Gửi thông báo toàn hệ thống.
- `/stats`: (Admin) Kiểm tra lưu lượng và người dùng.

---

## ⚠️ LƯU Ý QUAN TRỌNG
- **Web Service:** Vì chạy đồng thời Flask và Bot, Koyeb sẽ yêu cầu Health Check thành công tại Port 8000 để duy trì dịch vụ.
- **GitHub Token:** Đảm bảo Token có quyền `repo` để tránh lỗi khi bot thực hiện đẩy mã nguồn lên GitHub.
- **Tính năng /ping:** Dashboard có cơ chế giữ cho server luôn hoạt động (Keep-alive).

**Phát triển bởi:** [NgDanhThanhTrung](https://github.com/NgDanhThanhTrung)
