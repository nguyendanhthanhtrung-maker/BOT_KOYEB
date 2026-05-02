import os, json, logging, threading, asyncio, sqlite3, uuid, html, io
import pandas as pd
from datetime import datetime, timedelta, timezone
from github import Github
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    BotCommand
)
from telegram.constants import ParseMode
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    TypeHandler,
    filters
)
from flask import Flask, request, jsonify, render_template
# --- CONFIGURATION ---
ROOT_ADMIN_ID = 7346983056 
TOKEN = os.getenv("BOT_TOKEN") or os.getenv("TOKEN")
GH_TOKEN = os.getenv("GH_TOKEN")
REPO_NAME = "NgDanhThanhTrung/locket_"
PORT = int(os.getenv("PORT", "8000"))
CONTACT_URL = "https://t.me/NgDanhThanhTrung"
DONATE_URL = "https://ngdanhthanhtrung.github.io/Bank/"
KOYEB_URL = "https://colourful-carilyn-ngdanhthanhtrung-1cfbab15.koyeb.app/"
VN_TZ = timezone(timedelta(hours=7))
logging.basicConfig(level=logging.INFO)
DB_PATH = "data_system.db"
# --- DATABASE SETUP ---
STRINGS = {
    'vi': {
        # --- Khởi đầu & Ngôn ngữ ---
        'lang_select': "👋 Chào mừng bạn! Vui lòng chọn ngôn ngữ để bắt đầu.\n\nWelcome! Please select a language to start.",
        'mod_not_found': "🔍 <b>Không tìm thấy Module:</b> <code>/{cmd}</code>\n\nNhấn nút dưới để xem danh sách.",
        'mod_guide': (
            "📦 <b>MODULE: {title}</b>\n"
            "━━━━━━━━━━━━━━━━━━\n\n"
            "🔗 <b>ĐƯỜNG DẪN CÀI ĐẶT:</b>\n"
            "<code>{url}</code>\n\n"
            "🛠 <b>HƯỚNG DẪN CHI TIẾT:</b>\n"
            "1️⃣ <b>Sao chép:</b> Chạm vào link phía trên để copy.\n"
            "2️⃣ <b>Thêm Module:</b> Mở Shadowrocket/Surge ➔ Chọn <b>Module</b> ➔ <b>Add Module</b>.\n"
            "3️⃣ <b>Dán & Lưu:</b> Dán link đã copy và nhấn lưu.\n"
            "4️⃣ <b>HTTPS Decryption:</b> Đảm bảo <b>MITM</b> đã bật chứng chỉ (ON) để script có hiệu lực.\n\n"
            "💡 <i>Lưu ý: Nếu chưa cài chứng chỉ, hãy gõ /hdsd.</i>"
        ),
        
        # --- Menu Chính (hàm start) ---
        'welcome': (
            "👋 Chào mừng <b>{name}</b> đến với <b>@NgDanhThanhTrung_BOT</b>!\n\n"
            "🚀 <b>Tính năng chính:</b>\n"
            "🔹 Hỗ trợ tạo Module Shadowrocket cá nhân hóa.\n"
            "🔹 Tự động kích hoạt script Locket Gold vĩnh viễn.\n"
            "🔹 Dashboard Web mượt mà, dễ sử dụng.\n\n"
            "🌐 <b>Web Dashboard:</b>\n"
            "<code>{url}</code>\n\n"
            "📝 <b>Hướng dẫn:</b>\n"
            "• Nhấn nút <b>Danh sách Module</b> bên dưới để xem script.\n"
            "• Gõ <code>/get Tên | Ngày</code> để tạo script riêng.\n"
            "• Gõ /hdsd để xem cách cài đặt <b>HTTPS Decryption</b>.\n\n"
            "👨‍💻 <b>Admin:</b> @NgDanhThanhTrung"
        ),
        
        # --- Nút bấm ---
        'btn_list': "📂 Danh sách Module",
        'btn_profile': "👤 Hồ sơ",
        'btn_donate': "💰 Donate",
        'btn_guide': "📖 HDSD",
        'btn_contact': "💬 Liên hệ Admin",
        'btn_back': "🔙 Quay lại",
        'btn_bank': "💳 Ngân hàng",
        'btn_donate_up': "☕ Donate nâng cấp Premium",

        # --- Hồ sơ (hàm profile) ---
        'profile_info': (
            "👤 <b>HỒ SƠ CỦA BẠN</b>\n\n"
            "🆔 ID: <code>{id}</code>\n"
            "📅 Tham gia: <code>{join}</code>\n"
            "⚡ Tương tác: <code>{count} lần</code>\n"
            "🕒 Hoạt động: <code>{last}</code>\n"
            "🌟 Trạng thái: <b>{status}</b>"
        ),
        'status_premium': "💎 Premium",
        'status_free': "🆓 Thành viên",
        'error_no_data': "❌ Không tìm thấy dữ liệu người dùng.",
        'guide_text': (
            "📖 <b>HƯỚNG DẪN SỬ DỤNG:</b>\n\n"
            "🔹 <b>MODULE CÓ SẴN:</b>\n"
            "Nhấn nút <b>'Danh sách Module'</b> hoặc gõ /list.\n"
            "Sau đó gõ <code>/[tên_module]</code> để lấy link.\n\n"
            "🔹 <b>TẠO MODULE LOCKET RIÊNG:</b>\n"
            "Cú pháp: <code>/get tên_user | yyyy-mm-dd</code>\n"
            "<i>Ví dụ: /get ndtt | 2026-01-16</i>\n\n"
            "🛠 <b>YÊU CẦU CƠ BẢN:</b>\n"
            "Bạn cần cài đặt app <b>Shadowrocket</b> hoặc <b>Surge/Stash</b> và bật tính năng <b>HTTPS Decryption</b> (Mitm) để script hoạt động."
        ),

        # --- Quyền hạn & Donate ---
        'premium_alert': (
            "⚠️ <b>YÊU CẦU BẢN PREMIUM</b>\n\n"
            "Tính năng này chỉ dành cho người dùng Premium.\n"
            "Vui lòng ủng hộ (Donate) để mở khóa toàn bộ tính năng và hỗ trợ duy trì Server!"
        ),
        'donate_text': (
            "💰 <b>ỦNG HỘ PHÁT TRIỂN (DONATE)</b>\n\n"
            "Nếu bạn thấy hệ thống hữu ích, hãy mời Admin một ly cà phê nhé!\n"
            "Mọi sự ủng hộ đều giúp hệ thống duy trì ổn định và phát triển thêm tính năng mới. ❤️"
        ),

        # --- Tạo Module (hàm get_bundle) ---
        'get_syntax': (
            "⚠️ <b>Cú pháp:</b> <code>/get username | yyyy-mm-dd</code>\n"
            "Ví dụ: <code>/get trung | 2026-01-01</code>"
        ),
        'error_invalid_user': "❌ Username không hợp lệ (chỉ dùng chữ cái và số).",
        'error_invalid_date': "❌ Ngày không hợp lệ! Định dạng: <code>Năm-Tháng-Ngày</code> (VD: 2026-04-17)",
        'status_init_module': "⏳ <b>Đang khởi tạo Module cá nhân...</b>",
        'get_success': (
            "✅ <b>TẠO MODULE THÀNH CÔNG!</b>\n"
            "━━━━━━━━━━━━━━━━━━\n"
            "👤 <b>Username:</b> <code>{user}</code>\n"
            "📅 <b>Ngày tham gia:</b> <code>{date}</code>\n\n"
            "🔗 <b>Link Module của bạn:</b>\n"
            "<code>https://raw.githubusercontent.com/{repo}/main/{path}</code>\n\n"
            "💖 Nếu thấy hữu ích, hãy ủng hộ Admin tại /donate nhé!"
        ),
        'error_github': "❌ Lỗi kết nối GitHub: <code>{error}</code>",
        'nextdns_guide': (
            "🌐 <b>HƯỚNG DẪN CẤU HÌNH NEXTDNS</b>\n"
            "━━━━━━━━━━━━━━━━━━\n\n"
            "1️⃣ Truy cập <a href='https://my.nextdns.io'>my.nextdns.io</a> để tạo tài khoản.\n"
            "2️⃣ Đặt mật khẩu là <code>12345678</code> nếu cần Admin hỗ trợ.\n"
            "3️⃣ Gõ <code>/sendmail [Email]</code> để báo Admin chỉnh cấu hình.\n"
            "4️⃣ Lấy <b>ID</b> (6 ký tự) tại tab Setup.\n\n"
            "👉 <b>Cú pháp lấy mã:</b> <code>/nextdns [ID_CỦA_BẠN]</code>"
        ),
        'status_init_config': "⏳ <b>Đang khởi tạo cấu hình...</b>",
        'btn_nextdns_shourtcut': "⚡ Cài qua Shortcuts (iOS)",
        'nextdns_success': (
            "✅ <b>NEXTDNS CỦA BẠN ĐÃ SẴN SÀNG!</b>\n"
            "━━━━━━━━━━━━━━━━━━\n"
            "🆔 ID DNS: <code>{dns_id}</code>\n\n"
            "🛠 <b>CÁCH CÀI ĐẶT NHANH:</b>\n"
            "1. Nhấn nút <b>⚡ Cài qua Shortcuts</b> để tải phím tắt.\n"
            "2. Chạm vào mã bên dưới để <b>Copy</b>.\n"
            "3. Dán mã vào <b>Ghi chú (Notes)</b>.\n"
            "4. Nhấn <b>Chia sẻ</b> ➔ Chọn phím tắt <b>Get Mobileconfig</b>.\n\n"
            "📋 <b>MÃ XML (CHẠM ĐỂ SAO CHÉP):</b>\n"
            "<pre>{xml}</pre>"
        ),

        # --- Hỗ trợ & Feedback ---
        'sendmail_syntax': "⚠️ <b>Cú pháp:</b> <code>/sendmail [Nội dung yêu cầu]</code>",
        'sendmail_done': "✅ <b>Đã gửi thông tin tới Admin!</b>\nVui lòng chờ Admin xử lý DNS. Khi hoàn tất, bạn sẽ nhận được thông báo kèm mã ID.",
        'feedback_syntax': "⚠️ <b>Cú pháp:</b> <code>/send [nội dung góp ý/báo lỗi]</code>",
        'feedback_done': "✅ <b>Đã gửi báo cáo!</b>\nCảm ơn bạn, chúng tôi sẽ kiểm tra và phản hồi sớm nhất.",
    },

    'en': {
        # --- Startup & Language ---
        'lang_select': "👋 Welcome! Please select a language to start.\n\nChào mừng bạn! Vui lòng chọn ngôn ngữ để bắt đầu.",
        'mod_not_found': "🔍 <b>Module not found:</b> <code>/{cmd}</code>\n\nClick below to see the list.",
        'mod_guide': (
            "📦 <b>MODULE: {title}</b>\n"
            "━━━━━━━━━━━━━━━━━━\n\n"
            "🔗 <b>INSTALLATION LINK:</b>\n"
            "<code>{url}</code>\n\n"
            "🛠 <b>DETAILED GUIDE:</b>\n"
            "1️⃣ <b>Copy:</b> Tap the link above to copy.\n"
            "2️⃣ <b>Add Module:</b> Open Shadowrocket/Surge ➔ <b>Module</b> ➔ <b>Add Module</b>.\n"
            "3️⃣ <b>Paste & Save:</b> Paste the copied link and save.\n"
            "4️⃣ <b>HTTPS Decryption:</b> Ensure <b>MITM</b> certificate is ON for the script to work.\n\n"
            "💡 <i>Note: If certificates are not installed, type /hdsd.</i>"
        ),
        
        # --- Main Menu ---
        'welcome': (
            "👋 Welcome <b>{name}</b> to <b>@NgDanhThanhTrung_BOT</b>!\n\n"
            "🚀 <b>Main Features:</b>\n"
            "🔹 Personalized Shadowrocket Module creation.\n"
            "🔹 Automatic permanent Locket Gold activation.\n"
            "🔹 Smooth & easy-to-use Web Dashboard.\n\n"
            "🌐 <b>Web Dashboard:</b>\n"
            "<code>{url}</code>\n\n"
            "📝 <b>Instructions:</b>\n"
            "• Click <b>Module List</b> below to view scripts.\n"
            "• Type <code>/get Name | Date</code> to create your script.\n"
            "• Type /hdsd to see how to setup <b>HTTPS Decryption</b>.\n\n"
            "👨‍💻 <b>Admin:</b> @NgDanhThanhTrung"
        ),
        
        # --- Buttons ---
        'btn_list': "📂 Module List",
        'btn_profile': "👤 Profile",
        'btn_donate': "💰 Donate",
        'btn_guide': "📖 Guide",
        'btn_contact': "💬 Contact Admin",
        'btn_back': "🔙 Back",
        'btn_bank': "💳 Bank / Cards",
        'btn_donate_up': "☕ Donate to Upgrade Premium",

        # --- Profile ---
        'profile_info': (
            "👤 <b>YOUR PROFILE</b>\n\n"
            "🆔 ID: <code>{id}</code>\n"
            "📅 Joined: <code>{join}</code>\n"
            "⚡ Interacts: <code>{count} times</code>\n"
            "🕒 Last Active: <code>{last}</code>\n"
            "🌟 Status: <b>{status}</b>"
        ),
        'status_premium': "💎 Premium",
        'status_free': "🆓 Member",
        'error_no_data': "❌ User data not found.",
        'guide_text': (
            "📖 <b>USER GUIDE:</b>\n\n"
            "🔹 <b>AVAILABLE MODULES:</b>\n"
            "Click <b>'Module List'</b> button or type /list.\n"
            "Then type <code>/[module_name]</code> to get the link.\n\n"
            "🔹 <b>CREATE CUSTOM LOCKET MODULE:</b>\n"
            "Syntax: <code>/get username | yyyy-mm-dd</code>\n"
            "<i>Example: /get ndtt | 2026-01-16</i>\n\n"
            "🛠 <b>BASIC REQUIREMENTS:</b>\n"
            "You need <b>Shadowrocket</b>, <b>Surge</b>, or <b>Stash</b> app installed with <b>HTTPS Decryption</b> (Mitm) enabled for the script to work."
        ),

        # --- Permissions & Donate ---
        'premium_alert': (
            "⚠️ <b>PREMIUM REQUIRED</b>\n\n"
            "This feature is for Premium users only.\n"
            "Please Donate to unlock all features and support our server!"
        ),
        'donate_text': (
            "💰 <b>SUPPORT DEVELOPMENT (DONATE)</b>\n\n"
            "If you find this system useful, please buy Admin a coffee!\n"
            "Every support helps us maintain stability and develop new features. ❤️"
        ),

        # --- Get Module ---
        'get_syntax': (
            "⚠️ <b>Syntax:</b> <code>/get username | yyyy-mm-dd</code>\n"
            "Example: <code>/get trung | 2026-01-01</code>"
        ),
        'error_invalid_user': "❌ Invalid username (Letters and numbers only).",
        'error_invalid_date': "❌ Invalid date! Correct format: <code>YYYY-MM-DD</code> (Ex: 2026-04-17)",
        'status_init_module': "⏳ <b>Initializing Personal Module...</b>",
        'get_success': (
            "✅ <b>MODULE CREATED SUCCESSFULLY!</b>\n"
            "━━━━━━━━━━━━━━━━━━\n"
            "👤 <b>Username:</b> <code>{user}</code>\n"
            "📅 <b>Expiry Date:</b> <code>{date}</code>\n\n"
            "🔗 <b>Your Module Link:</b>\n"
            "<code>https://raw.githubusercontent.com/{repo}/main/{path}</code>\n\n"
            "💖 If this is helpful, please support Admin at /donate!"
        ),
        'error_github': "❌ GitHub Connection Error: <code>{error}</code>",
        'nextdns_guide': (
            "🌐 <b>NEXTDNS CONFIGURATION GUIDE</b>\n"
            "━━━━━━━━━━━━━━━━━━\n\n"
            "1️⃣ Visit <a href='https://my.nextdns.io'>my.nextdns.io</a> to create an account.\n"
            "2️⃣ Set password to <code>12345678</code> if you need Admin support.\n"
            "3️⃣ Type <code>/sendmail [Email]</code> to request Admin config.\n"
            "4️⃣ Get your <b>ID</b> (6 chars) from the Setup tab.\n\n"
            "👉 <b>Usage:</b> <code>/nextdns [YOUR_ID]</code>"
        ),
        'status_init_config': "⏳ <b>Initializing configuration...</b>",
        'btn_nextdns_shourtcut': "⚡ Install via Shortcuts (iOS)",
        'nextdns_success': (
            "✅ <b>YOUR NEXTDNS IS READY!</b>\n"
            "━━━━━━━━━━━━━━━━━━\n"
            "🆔 DNS ID: <code>{dns_id}</code>\n\n"
            "🛠 <b>QUICK INSTALLATION:</b>\n"
            "1. Click <b>⚡ Install via Shortcuts</b> to download.\n"
            "2. Tap the code below to <b>Copy</b>.\n"
            "3. Paste the code into <b>Notes</b> app.\n"
            "4. Press <b>Share</b> ➔ Select <b>Get Mobileconfig</b> shortcut.\n\n"
            "📋 <b>XML CODE (TAP TO COPY):</b>\n"
            "<pre>{xml}</pre>"
        ),

        # --- Support & Feedback ---
        'sendmail_syntax': "⚠️ <b>Syntax:</b> <code>/sendmail [Request content]</code>",
        'sendmail_done': "✅ <b>Information sent to Admin!</b>\nPlease wait for Admin to configure your DNS. You will receive a notification with an ID when finished.",
        'feedback_syntax': "⚠️ <b>Syntax:</b> <code>/send [feedback/bug report]</code>",
        'feedback_done': "✅ <b>Report sent!</b>\nThank you, we will check and respond as soon as possible.",
    }
}
def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("PRAGMA journal_mode=WAL;")
        cursor = conn.cursor()
        cursor.execute('''CREATE TABLE IF NOT EXISTS users (
            user_id TEXT PRIMARY KEY,
            full_name TEXT,
            username TEXT,
            join_date TEXT,
            last_active TEXT,
            interact_count INTEGER DEFAULT 0,
            is_premium INTEGER DEFAULT 0,
            language TEXT DEFAULT 'none'
        )''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS modules (
            key TEXT PRIMARY KEY,
            title TEXT,
            url TEXT
        )''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS admins (
            user_id TEXT PRIMARY KEY,
            added_at TEXT
        )''')
        cursor.execute("PRAGMA table_info(users)")
        columns = [column[1] for column in cursor.fetchall()]
        if 'language' not in columns:
            cursor.execute("ALTER TABLE users ADD COLUMN language TEXT DEFAULT 'none'")    
        conn.commit()
init_db()
# --- HELPERS ---
def is_admin(user_id: int) -> bool:
    uid_str = str(user_id)
    if uid_str == str(ROOT_ADMIN_ID): 
        return True
    with sqlite3.connect(DB_PATH) as conn:
        res = conn.execute("SELECT 1 FROM admins WHERE user_id = ?", (uid_str,)).fetchone()
        return res is not None        
async def is_premium(user_id: int) -> bool:
    """Kiểm tra xem người dùng có phải Premium không (Logic ngầm)"""
    uid_str = str(user_id)
    with sqlite3.connect(DB_PATH) as conn:
        res = conn.execute("SELECT is_premium FROM users WHERE user_id = ?", (uid_str,)).fetchone()
        return res is not None and res[0] == 1
def get_lang(user_id: str) -> str:
    """
    Lấy ngôn ngữ của người dùng từ DB.
    Trả về 'en' hoặc 'vi'. Mặc định là 'vi' nếu chưa chọn hoặc không tìm thấy user.
    """
    try:
        with sqlite3.connect(DB_PATH) as conn:
            res = conn.execute("SELECT language FROM users WHERE user_id = ?", (str(user_id),)).fetchone()
            if res and res[0] and res[0] != 'none':
                return res[0]
    except Exception as e:
        print(f"Error getting language: {e}")
    return 'vi'
async def check_premium_permission(u: Update):
    """
    Kiểm tra quyền Premium và thông báo bằng ngôn ngữ phù hợp nếu người dùng bị từ chối truy cập.
    """
    uid = u.effective_user.id
    lang = get_lang(uid) 
    s = STRINGS[lang] 
    if await is_premium(uid) or is_admin(uid):
        return True
    kb = [
        [InlineKeyboardButton(s['btn_donate_up'], callback_data="donate_info")],
        [InlineKeyboardButton(s['btn_contact'], url=CONTACT_URL)]
    ]
    await send_ui(u, s['premium_alert'], kb)
    return False  
async def add_admin_db(user_id: str):
    """
    Thêm admin mới vào database (Dữ liệu nội bộ)
    """
    now = datetime.now(VN_TZ).strftime("%Y-%m-%d %H:%M:%S")
    uid_str = str(user_id)
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            "INSERT OR REPLACE INTO admins (user_id, added_at) VALUES (?, ?)", 
            (uid_str, now)
        )
        conn.commit()
async def db_auto_reg(u: Update, c: ContextTypes.DEFAULT_TYPE = None):
    user = u.effective_user
    if not user or user.is_bot: return
    uid = str(user.id)
    uname = (f"@{user.username}" if user.username else "N/A")
    fname = user.full_name
    now = datetime.now(VN_TZ).strftime("%Y-%m-%d %H:%M:%S")
    is_command = bool(u.message and u.message.text and u.message.text.startswith('/'))
    interact_inc = 1 if is_command else 0
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute('''
            INSERT INTO users (user_id, full_name, username, join_date, last_active, interact_count, language) 
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET 
                full_name = excluded.full_name, 
                username = excluded.username,
                last_active = excluded.last_active, 
                interact_count = interact_count + ?
        ''', (uid, fname, uname, now, now, interact_inc, 'none', interact_inc))
        conn.commit()
async def send_ui(u: Update, text: str, kb: list):
    """
    Hiển thị giao diện người dùng. 
    Tự động chỉnh sửa tin nhắn cũ nếu là Callback hoặc gửi tin mới nếu cần.
    """
    reply_markup = InlineKeyboardMarkup(kb)
    if u.callback_query:
        try:
            await u.callback_query.edit_message_text(
                text=text, 
                parse_mode=ParseMode.HTML, 
                reply_markup=reply_markup, 
                disable_web_page_preview=False
            )
        except Exception as e:
            logging.warning(f"send_ui edit error (fallback to reply): {e}")
            await u.effective_message.reply_text(
                text=text, 
                parse_mode=ParseMode.HTML, 
                reply_markup=reply_markup, 
                disable_web_page_preview=False
            )
    else:
        await u.effective_message.reply_text(
            text=text, 
            parse_mode=ParseMode.HTML, 
            reply_markup=reply_markup, 
            disable_web_page_preview=False
        )
# --- TEMPLATES ---
JS_TEMPLATE = """const mapping = {{
  '%E8%BD%A6%E7%A5%A8%E7%A5%A8': ['vip', 'watch_vip'],
  'Locket': ['Gold', 'com.{user}.premium.yearly']
}};

const ua = $request.headers["User-Agent"] || $request.headers["user-agent"];
let obj = JSON.parse($response.body);

obj.subscriber = obj.subscriber || {{}};
obj.subscriber.entitlements = obj.subscriber.entitlements || {{}};
obj.subscriber.subscriptions = obj.subscriber.subscriptions || {{}};

const premiumInfo = {{
  is_sandbox: false,
  ownership_type: "PURCHASED",
  billing_issues_detected_at: null,
  period_type: "normal",
  expires_date: "2999-12-18T01:04:17Z",
  original_purchase_date: "{date}T01:04:17Z",
  purchase_date: "{date}T01:04:17Z",
  store: "app_store"
}};

const entitlementInfo = {{
  grace_period_expires_date: null,
  purchase_date: "{date}T01:04:17Z",
  product_identifier: "com.{user}.premium.yearly",
  expires_date: "2999-12-18T01:04:17Z"
}};

const match = Object.keys(mapping).find(e => ua.includes(e));

if (match) {{
  let [entKey, subKey] = mapping[match];
  let finalSubKey = subKey || "com.{user}.premium.yearly";
  
  entitlementInfo.product_identifier = finalSubKey;
  obj.subscriber.subscriptions[finalSubKey] = premiumInfo;
  obj.subscriber.entitlements[entKey] = entitlementInfo;
}} else {{
  obj.subscriber.subscriptions["com.{user}.premium.yearly"] = premiumInfo;
  obj.subscriber.entitlements["Gold"] = entitlementInfo;
  obj.subscriber.entitlements["pro"] = entitlementInfo;
}}

obj.Attention = "Chúc mừng bạn! Vui lòng không bán hoặc chia sẻ cho người khác!";

$done({{ body: JSON.stringify(obj) }});"""

MODULE_TEMPLATE = """#!name=Locket-Gold ({user})
#!desc=Crack By NgDanhThanhTrung
[Script]
revenuecat = type=http-response, pattern=^https:\\/\\/api\\.revenuecat\\.com\\/.+\\/(receipts$|subscribers\\/[^/]+$), script-path={js_url}, requires-body=true, max-size=-1, timeout=60
deleteHeader = type=http-request, pattern=^https:\\/\\/api\\.revenuecat\\.com\\/.+\\/(receipts|subscribers), script-path=https://raw.githubusercontent.com/NgDanhThanhTrung/locket_/main/Locket_NDTT/deleteHeader.js, timeout=60
[MITM]
hostname = %APPEND% api.revenuecat.com"""

NEXTDNS_CONFIG = """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>PayloadContent</key>
    <array>
        <dict>
            <key>DNSSettings</key>
            <dict>
                <key>DNSProtocol</key>
                <string>HTTPS</string>
                <key>ServerURL</key>
                <string>https://apple.nextdns.io/{dns_id}</string>
            </dict>
            <key>PayloadIdentifier</key>
            <string>com.nextdns.dns.{dns_id}</string>
            <key>PayloadType</key>
            <string>com.apple.dnsSettings.managed</string>
            <key>PayloadUUID</key>
            <string>{uuid1}</string>
            <key>PayloadVersion</key>
            <integer>1</integer>
        </dict>
    </array>
    <key>PayloadDisplayName</key>
    <string>NextDNS ({dns_id})</string>
    <key>PayloadIdentifier</key>
    <string>com.nextdns.config.{dns_id}</string>
    <key>PayloadType</key>
    <string>Configuration</string>
    <key>PayloadUUID</key>
    <string>{uuid2}</string>
    <key>PayloadVersion</key>
    <integer>1</integer>
</dict>
</plist>"""

# --- HANDLERS ---
async def start(u: Update, c: ContextTypes.DEFAULT_TYPE):
    uid = str(u.effective_user.id)
    await db_auto_reg(u, c)
    lang = get_lang(uid)
    with sqlite3.connect(DB_PATH) as conn:
        res = conn.execute("SELECT language FROM users WHERE user_id = ?", (uid,)).fetchone()
    if not res or res[0] == 'none':
        kb = [
            [
                InlineKeyboardButton("Tiếng Việt 🇻🇳", callback_data="set_lang_vi"),
                InlineKeyboardButton("English 🇺🇸", callback_data="set_lang_en")
            ]
        ]
        return await send_ui(u, STRINGS['vi']['lang_select'], kb)
    s = STRINGS[lang]
    txt = s['welcome'].format(
        name=u.effective_user.first_name, 
        url=KOYEB_URL
    )
    kb = [
        [InlineKeyboardButton(s['btn_list'], callback_data="show_list")],
        [
            InlineKeyboardButton(s['btn_profile'], callback_data="profile"), 
            InlineKeyboardButton(s['btn_donate'], callback_data="donate_info")
        ],
        [
            InlineKeyboardButton(s['btn_guide'], callback_data="hdsd"), 
            InlineKeyboardButton(s['btn_contact'], url=CONTACT_URL)
        ]
    ]
    await send_ui(u, txt, kb)
async def send_mail_to_admin(u: Update, c: ContextTypes.DEFAULT_TYPE):
    user = u.effective_user
    uid = user.id
    lang = get_lang(uid)
    s = STRINGS[lang]
    if not c.args:
        return await u.message.reply_text(s['sendmail_syntax'], parse_mode=ParseMode.HTML)
    user_msg = " ".join(c.args)
    kb_admin = [[InlineKeyboardButton("✅ XÁC NHẬN XỬ LÝ", callback_data=f"done_req_{uid}")]]
    report_to_admin = (
        "📨 <b>YÊU CẦU HỖ TRỢ DNS</b>\n"
        "━━━━━━━━━━━━━━━━━━\n"
        f"👤 <b>Người gửi:</b> {user.full_name}\n"
        f"🆔 <b>ID:</b> <code>{uid}</code>\n"
        f"📝 <b>Nội dung:</b> {user_msg}"
    )
    try:
        await c.bot.send_message(
            ROOT_ADMIN_ID, 
            report_to_admin, 
            parse_mode=ParseMode.HTML, 
            reply_markup=InlineKeyboardMarkup(kb_admin)
        )
        await u.message.reply_text(s['sendmail_done'], parse_mode=ParseMode.HTML)
    except Exception as e:
        err_msg = f"❌ Error: {str(e)}" if lang == 'en' else f"❌ Lỗi gửi tin nhắn: {str(e)}"
        await u.message.reply_text(err_msg)        
async def done_dns_cmd(u: Update, c: ContextTypes.DEFAULT_TYPE):
    if not is_admin(u.effective_user.id): return
    if not c.args or "|" not in " ".join(c.args):
        return await u.message.reply_text("⚠️ <b>Cú pháp:</b> <code>/donedns [ID User] | [ID DNS]</code>", parse_mode=ParseMode.HTML)
    try:
        parts = [p.strip() for p in " ".join(c.args).split("|")]
        target_id = parts[0]
        dns_id = parts[1]
        target_lang = get_lang(target_id)
        if target_lang == 'en':
            msg_to_user = (
                "🎉 <b>NOTIFICATION: DNS IS READY!</b>\n\n"
                "Admin has completed the DNS configuration for you.\n"
                f"🆔 Your DNS ID: <code>{dns_id}</code>\n\n"
                f"👉 You can now use: <code>/nextdns {dns_id}</code> to get your profile."
            )
        else: 
            msg_to_user = (
                "🎉 <b>THÔNG BÁO: DNS ĐÃ SẴN SÀNG!</b>\n\n"
                "Admin đã hoàn tất việc chỉnh sửa DNS cho bạn.\n"
                f"🆔 ID DNS của bạn là: <code>{dns_id}</code>\n\n"
                f"👉 Bây giờ bạn có thể dùng lệnh: <code>/nextdns {dns_id}</code> để cấu hình."
            )
        await c.bot.send_message(target_id, msg_to_user, parse_mode=ParseMode.HTML)
        await u.message.reply_text(f"✅ Đã gửi ID DNS <code>{dns_id}</code> tới người dùng <code>{target_id}</code> thành công!")
    except Exception as e:
        await u.message.reply_text(f"❌ Lỗi: {str(e)}")
async def callback_handler(u: Update, c: ContextTypes.DEFAULT_TYPE):
    query = u.callback_query
    await query.answer()
    data = query.data
    uid = str(query.from_user.id)
    if data.startswith("set_lang_"):
        new_lang = data.split("_")[-1]
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute("UPDATE users SET language = ? WHERE user_id = ?", (new_lang, uid))
            conn.commit()
        return await start(u, c)
    if data == "show_list":
        await send_module_list(u, c)
    elif data.startswith("list_page_"):
        page_num = int(data.split("_")[-1])
        await send_module_list(u, c, page=page_num)
    elif data == "profile":
        await profile(u, c)
    elif data == "donate_info":
        await donate_info(u, c)
    elif data == "back_start":
        await start(u, c)
    elif data == "hdsd":
        await hdsd_ui(u, c)
    elif data.startswith("done_req_"):
        target_uid = data.split("_")[-1]
        admin_txt = (
            f"📩 <b>TIẾN HÀNH TRẢ KẾT QUẢ</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"👤 Người dùng: <code>{target_uid}</code>\n\n"
            f"Hãy dùng lệnh dưới đây để gửi mã DNS cho họ:\n"
            f"<code>/donedns {target_uid} | [MÃ_DNS_TẠI_ĐÂY]</code>"
        )
        await c.bot.send_message(
            chat_id=ROOT_ADMIN_ID,
            text=admin_txt,
            parse_mode=ParseMode.HTML
        )
async def send_feedback(u: Update, c: ContextTypes.DEFAULT_TYPE):
    uid = u.effective_user.id
    lang = get_lang(uid) 
    s = STRINGS[lang]    
    if not c.args:
        return await u.message.reply_text(s['feedback_syntax'], parse_mode=ParseMode.HTML)
    user = u.effective_user
    text = " ".join(c.args)
    report = (f"🆘 <b>YÊU CẦU HỖ TRỢ</b>\n"
              f"━━━━━━━━━━━━━━━━━━\n"
              f"👤 Người gửi: {user.full_name} (<code>{user.id}</code>)\n"
              f"📝 Nội dung: {text}")
    try:
        await c.bot.send_message(ROOT_ADMIN_ID, report, parse_mode=ParseMode.HTML)
        await u.message.reply_text(s['feedback_done'], parse_mode=ParseMode.HTML)
    except Exception as e:
        err_msg = f"❌ Error: {str(e)}" if lang == 'en' else f"❌ Lỗi: {str(e)}"
        await u.message.reply_text(err_msg)
async def profile(u: Update, c: ContextTypes.DEFAULT_TYPE):
    uid = str(u.effective_user.id)
    lang = get_lang(uid)
    s = STRINGS[lang]
    with sqlite3.connect(DB_PATH) as conn:
        user = conn.execute(
            "SELECT join_date, interact_count, is_premium, last_active FROM users WHERE user_id = ?", 
            (uid,)
        ).fetchone()
    if not user: 
        return await u.effective_message.reply_text(s.get('error_no_data', "❌ No data found."))
    status = s['status_premium'] if user[2] == 1 else s['status_free']
    txt = s['profile_info'].format(
        id=uid,
        join=user[0],
        count=user[1],
        last=user[3],
        status=status
    )
    kb = [[InlineKeyboardButton(s['btn_back'], callback_data="back_start")]]
    await send_ui(u, txt, kb)
async def donate_info(u: Update, c: ContextTypes.DEFAULT_TYPE):
    uid = u.effective_user.id
    lang = get_lang(uid)
    s = STRINGS[lang]
    txt = s['donate_text']
    kb = [
        [InlineKeyboardButton(s['btn_bank'], url=DONATE_URL)],
        [InlineKeyboardButton(s['btn_back'], callback_data="back_start")]
    ]
    await send_ui(u, txt, kb)   
async def get_bundle(u: Update, c: ContextTypes.DEFAULT_TYPE):
    uid = u.effective_user.id
    lang = get_lang(uid)
    s = STRINGS[lang]
    if not c.args or "|" not in " ".join(c.args): 
        return await u.message.reply_text(
            s['get_syntax'], 
            parse_mode=ParseMode.HTML
        )
    full_text = " ".join(c.args)
    parts = [p.strip() for p in full_text.split("|")]
    raw_username = parts[0]
    safe_user = "".join(x for x in raw_username if x.isalnum())
    if not safe_user:
        return await u.message.reply_text(s['error_invalid_user'])
    try:
        raw_date = parts[1].replace("/", "-").replace(".", "-")
        date_obj = datetime.strptime(raw_date, "%Y-%m-%d")
        date_str = date_obj.strftime("%Y-%m-%d")
    except (ValueError, IndexError):
        return await u.message.reply_text(
            s['error_invalid_date'], 
            parse_mode=ParseMode.HTML
        )
    status = await u.message.reply_text(s['status_init_module'], parse_mode=ParseMode.HTML)
    try:
        repo = Github(GH_TOKEN).get_repo(REPO_NAME)
        js_p, mod_p = f"{safe_user}/LocketGold.js", f"{safe_user}/LocketGold.sgmodule"
        js_url = f"https://raw.githubusercontent.com/{REPO_NAME}/main/{js_p}"
        js_c = JS_TEMPLATE.format(user=safe_user, date=date_str)
        mod_c = MODULE_TEMPLATE.format(user=raw_username, js_url=js_url)
        for p, cnt in [(js_p, js_c), (mod_p, mod_c)]:
            try:
                f = repo.get_contents(p)
                repo.update_file(p, f"Update module: {safe_user}", cnt, f.sha)
            except:
                repo.create_file(p, f"Create module: {safe_user}", cnt)
        await status.edit_text(
            s['get_success'].format(
                user=raw_username,
                date=date_str,
                repo=REPO_NAME,
                path=mod_p
            ), 
            parse_mode=ParseMode.HTML
        )
    except Exception as e:
        logging.error(f"GitHub Error: {str(e)}")
        err_msg = s['error_github'].format(error=str(e))
        await status.edit_text(err_msg, parse_mode=ParseMode.HTML)
async def get_nextdns(u: Update, c: ContextTypes.DEFAULT_TYPE):
    try:
        await db_auto_reg(u, c)
        uid = u.effective_user.id
        lang = get_lang(uid)
        s = STRINGS[lang]
        if not c.args:
            return await u.message.reply_text(
                s['nextdns_guide'], 
                parse_mode=ParseMode.HTML, 
                disable_web_page_preview=True
            )
        dns_id = c.args[0].strip()
        status = await u.message.reply_text(s['status_init_config'], parse_mode=ParseMode.HTML)
        xml_content = NEXTDNS_CONFIG.format(
            dns_id=dns_id,
            uuid1=str(uuid.uuid4()),
            uuid2=str(uuid.uuid4())
        )
        shortcut_url = "https://www.icloud.com/shortcuts/ef6f685318484784940648ad520b5c4f"
        kb = [
            [InlineKeyboardButton(s['btn_nextdns_shourtcut'], url=shortcut_url)],
            [
                InlineKeyboardButton(s['btn_back'], callback_data="back_start"), 
                InlineKeyboardButton(s['btn_contact'], url=CONTACT_URL)
            ]
        ]
        safe_xml = html.escape(xml_content)
        msg_text = s['nextdns_success'].format(
            dns_id=dns_id,
            xml=safe_xml
        )
        await u.message.reply_text(
            msg_text, 
            parse_mode=ParseMode.HTML, 
            reply_markup=InlineKeyboardMarkup(kb)
        )
        await status.delete()
    except Exception as e:
        logging.error(f"Lỗi NextDNS: {e}")
        error_prefix = "❌ <b>System Error:</b>" if lang == 'en' else "❌ <b>Lỗi hệ thống:</b>"
        error_txt = f"{error_prefix} <code>{str(e)}</code>"
        if 'status' in locals():
            await status.edit_text(error_txt, parse_mode=ParseMode.HTML)
        else:
            await u.message.reply_text(error_txt, parse_mode=ParseMode.HTML)
            
# --- ADMIN FUNCTIONS ---
async def admin_panel(u: Update, c: ContextTypes.DEFAULT_TYPE):
    if not is_admin(u.effective_user.id): 
        return
    uid = u.effective_user.id
    lang = get_lang(uid)
    s = STRINGS[lang]
    txt = (
        "🛠 <b>BẢNG ĐIỀU KHIỂN QUẢN TRỊ VIÊN</b>\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        "📊 <b>Thống kê & Hệ thống:</b>\n"
        "• <code>/stats</code>: Xem tổng User, Premium và Modules.\n"
        "• <code>/saoluu</code>: Xuất file Excel backup toàn bộ dữ liệu.\n"
        "• <code>/broadcast [nội dung]</code>: Gửi thông báo tới toàn bộ người dùng.\n\n"
        "👤 <b>Quản lý Người dùng:</b>\n"
        "• <code>/approve [ID]</code>: Cấp quyền <b>Premium</b> cho người dùng.\n"
        "• <code>/revoke [ID]</code>: Thu hồi quyền Premium.\n"
        "• <code>/addadmin [ID]</code>: Cấp quyền <b>Admin</b> (Chỉ Root Admin).\n\n"
        "📦 <b>Quản lý Modules:</b>\n"
        "• <code>/setlink key | title | url</code>: Thêm/Sửa module.\n"
        "• <code>/delmodule [key]</code>: Xóa module khỏi hệ thống.\n\n"   
        "💡 <i>Mẹo: Nhấn vào ID người dùng để copy nhanh khi xử lý lệnh.</i>"
    )
    kb = [
        [InlineKeyboardButton("📂 Danh sách & Quản lý User", callback_data="show_list")],
        [InlineKeyboardButton(s['btn_back'], callback_data="back_start")] 
    ]
    await send_ui(u, txt, kb)
async def revoke_user(u: Update, c: ContextTypes.DEFAULT_TYPE):
    if not is_admin(u.effective_user.id) or not c.args: 
        return
    target_uid = c.args[0]
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("UPDATE users SET is_premium = 0 WHERE user_id = ?", (target_uid,))
        conn.commit()
    target_lang = get_lang(target_uid)
    if target_lang == 'en':
        notice = "🚫 <b>NOTICE:</b> Your Premium access has been revoked by the Administrator."
    else:
        notice = "🚫 <b>THÔNG BÁO:</b> Quyền Premium của bạn đã bị thu hồi bởi Quản trị viên."
    try:
        await c.bot.send_message(target_uid, notice, parse_mode=ParseMode.HTML)
        await u.message.reply_text(f"🚫 Đã thu hồi và gửi thông báo tới ID: <code>{target_uid}</code>")
    except Exception:
        await u.message.reply_text(f"🚫 Đã thu hồi ID: <code>{target_uid}</code> (Không thể gửi thông báo cho user).")    
async def stats(u: Update, c: ContextTypes.DEFAULT_TYPE):
    if not is_admin(u.effective_user.id): return
    with sqlite3.connect(DB_PATH) as conn:
        u_c = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        p_c = conn.execute("SELECT COUNT(*) FROM users WHERE is_premium = 1").fetchone()[0]
        m_c = conn.execute("SELECT COUNT(*) FROM modules").fetchone()[0]
        vi_c = conn.execute("SELECT COUNT(*) FROM users WHERE language = 'vi'").fetchone()[0]
        en_c = conn.execute("SELECT COUNT(*) FROM users WHERE language = 'en'").fetchone()[0]
        none_c = conn.execute("SELECT COUNT(*) FROM users WHERE language = 'none'").fetchone()[0]
        today = datetime.now(VN_TZ).strftime("%Y-%m-%d")
        active_today = conn.execute("SELECT COUNT(*) FROM users WHERE last_active LIKE ?", (f"{today}%",)).fetchone()[0]
    txt = (
        "📊 <b>THỐNG KÊ HỆ THỐNG</b>\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        f"👤 <b>Người dùng:</b> <code>{u_c}</code>\n"
        f"💎 <b>Premium:</b> <code>{p_c}</code>\n"
        f"📦 <b>Modules:</b> <code>{m_c}</code>\n"
        f"⚡ <b>Hoạt động hôm nay:</b> <code>{active_today}</code>\n\n"
        "🌐 <b>Phân bố ngôn ngữ:</b>\n"
        f"• Tiếng Việt 🇻🇳: <code>{vi_c}</code>\n"
        f"• English 🇺🇸: <code>{en_c}</code>\n"
        f"• Chưa chọn: <code>{none_c}</code>"
    )
    await u.message.reply_text(txt, parse_mode=ParseMode.HTML)
async def clear_members(u: Update, c: ContextTypes.DEFAULT_TYPE):
    if u.effective_user.id != ROOT_ADMIN_ID:
        return
    status_msg = await u.message.reply_text("⏳ <b>Đang tiến hành dọn dẹp cơ sở dữ liệu...</b>", parse_mode=ParseMode.HTML)
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            count = cursor.execute("SELECT COUNT(*) FROM users").fetchone()[0]
            cursor.execute("DELETE FROM users")
            cursor.execute("DELETE FROM sqlite_sequence WHERE name='users'")
            conn.commit()
        await status_msg.edit_text(
            f"✅ <b>DỌN DẸP HOÀN TẤT!</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"🗑 Đã xóa: <code>{count}</code> thành viên.\n"
            f"📦 Dữ liệu Modules: <b>Vẫn giữ nguyên.</b>",
            parse_mode=ParseMode.HTML
        )
    except Exception as e:
        logging.error(f"Clear Members Error: {e}")
        await status_msg.edit_text(f"❌ <b>Lỗi hệ thống:</b> <code>{str(e)}</code>", parse_mode=ParseMode.HTML)
async def restore_data(u: Update, c: ContextTypes.DEFAULT_TYPE):
    if not is_admin(u.effective_user.id): return
    doc = u.message.document
    if not doc or not doc.file_name.endswith(".xlsx"):
        return await u.message.reply_text("⚠️ Vui lòng gửi file <code>.xlsx</code> để khôi phục.")
    status_msg = await u.message.reply_text("⏳ <b>Đang phân tích & khôi phục dữ liệu...</b>", parse_mode=ParseMode.HTML)
    try:
        file = await c.bot.get_file(doc.file_id)
        file_bytes = await file.download_as_bytearray()
        df_u = pd.read_excel(io.BytesIO(file_bytes), sheet_name='Thành Viên')
        df_m = pd.read_excel(io.BytesIO(file_bytes), sheet_name='Danh Sách Modules')
        with sqlite3.connect(DB_PATH) as conn:
            for _, row in df_u.iterrows():
                conn.execute('''
                    INSERT INTO users (user_id, full_name, username, join_date, last_active, interact_count, is_premium, language)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(user_id) DO UPDATE SET
                        full_name=excluded.full_name,
                        username=excluded.username,
                        last_active=excluded.last_active,
                        interact_count=max(users.interact_count, excluded.interact_count),
                        is_premium=max(users.is_premium, excluded.is_premium),
                        language=excluded.language
                ''', (str(row['user_id']), row['full_name'], row['username'], row['join_date'], 
                      row['last_active'], row['interact_count'], row['is_premium'], row.get('language', 'vi')))
            for _, row in df_m.iterrows():
                conn.execute('''
                    INSERT INTO modules (key, title, url)
                    VALUES (?, ?, ?)
                    ON CONFLICT(key) DO UPDATE SET 
                        title=excluded.title, 
                        url=excluded.url
                ''', (row['key'], row['title'], row['url']))
            conn.commit()   
        await status_msg.edit_text(
            f"✅ <b>KHÔI PHỤC THÀNH CÔNG!</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"👤 Đã xử lý: <code>{len(df_u)}</code> Users\n"
            f"📦 Đã xử lý: <code>{len(df_m)}</code> Modules",
            parse_mode=ParseMode.HTML
        )
    except Exception as e:
        logging.error(f"Restore Error: {e}")
        await status_msg.edit_text(f"❌ <b>Lỗi khôi phục:</b> <code>{str(e)}</code>", parse_mode=ParseMode.HTML)
async def backup_data(u: Update, c: ContextTypes.DEFAULT_TYPE):
    if not is_admin(u.effective_user.id): return
    status_msg = await u.message.reply_text("⏳ <b>Đang trích xuất dữ liệu ra file Excel...</b>", parse_mode=ParseMode.HTML)
    try:
        with sqlite3.connect(DB_PATH) as conn:
            df_u = pd.read_sql_query("SELECT * FROM users", conn)
            df_m = pd.read_sql_query("SELECT * FROM modules", conn)
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df_u.to_excel(writer, sheet_name='Thành Viên', index=False)
            df_m.to_excel(writer, sheet_name='Danh Sách Modules', index=False)
        output.seek(0)
        timestamp = datetime.now(VN_TZ).strftime("%d-%m-%Y_%H%M")
        caption = (
            f"📂 <b>SAO LƯU HOÀN TẤT</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"👤 Người dùng: <code>{len(df_u)}</code>\n"
            f"📦 Modules: <code>{len(df_m)}</code>\n"
            f"⏰ Thời gian: <code>{timestamp}</code>"
        )
        await u.message.reply_document(
            document=output, 
            filename=f"NDTT_Backup_{timestamp}.xlsx", 
            caption=caption,
            parse_mode=ParseMode.HTML
        )
        await status_msg.delete()
    except Exception as e: 
        await status_msg.edit_text(f"❌ <b>Lỗi sao lưu:</b> <code>{str(e)}</code>", parse_mode=ParseMode.HTML)
async def approve_user(u: Update, c: ContextTypes.DEFAULT_TYPE):
    if not is_admin(u.effective_user.id) or not c.args: 
        return
    target_uid = c.args[0]
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("UPDATE users SET is_premium = 1 WHERE user_id = ?", (target_uid,))
        conn.commit()
    target_lang = get_lang(target_uid)
    if target_lang == 'en':
        congrats_msg = (
            "🎉 <b>CONGRATULATIONS!</b>\n\n"
            "Your account has been upgraded to <b>Premium</b> status!\n"
            "You now have full access to all exclusive features. Enjoy! ✨"
        )
    else:
        congrats_msg = (
            "🎉 <b>CHÚC MỪNG!</b>\n\n"
            "Tài khoản của bạn đã được nâng cấp lên <b>Premium</b>!\n"
            "Giờ đây bạn có thể sử dụng toàn bộ tính năng đặc quyền của Bot. Trải nghiệm ngay! ✨"
        )
    try: 
        await c.bot.send_message(target_uid, congrats_msg, parse_mode=ParseMode.HTML)
        await u.message.reply_text(f"✅ Đã cấp quyền Premium và gửi thông báo tới ID: <code>{target_uid}</code>", parse_mode=ParseMode.HTML)
    except Exception as e: 
        logging.error(f"Approve Notification Error: {e}")
        await u.message.reply_text(
            f"⚠️ Đã duyệt Premium cho ID <code>{target_uid}</code> trên Database,\n"
            f"nhưng không thể gửi tin nhắn thông báo (User đã block bot hoặc ID sai).",
            parse_mode=ParseMode.HTML
        )
async def broadcast(u: Update, c: ContextTypes.DEFAULT_TYPE):
    if not is_admin(u.effective_user.id): return
    msg = " ".join(c.args)
    if not msg: 
        return await u.message.reply_text("⚠️ <b>Cú pháp:</b> <code>/broadcast [nội dung]</code>", parse_mode=ParseMode.HTML)
    parts = msg.split("|")
    msg_vi = parts[0].strip()
    msg_en = parts[1].strip() if len(parts) > 1 else msg_vi
    status_msg = await u.message.reply_text("⏳ <b>Đang bắt đầu gửi thông báo...</b>", parse_mode=ParseMode.HTML)
    with sqlite3.connect(DB_PATH) as conn: 
        users = conn.execute("SELECT user_id, language FROM users").fetchall()
    count = 0
    blocked = 0
    for user_id, lang in users:
        try:
            content = msg_en if lang == 'en' else msg_vi
            final_msg = (
                f"📢 <b>SYSTEM NOTIFICATION</b>\n" if lang == 'en' else f"📢 <b>THÔNG BÁO TỪ HỆ THỐNG</b>\n"
            )
            final_msg += f"━━━━━━━━━━━━━━━━━━\n\n{content}"
            await c.bot.send_message(user_id, final_msg, parse_mode=ParseMode.HTML)
            count += 1
            await asyncio.sleep(0.05) 
        except Exception:
            blocked += 1
            continue       
    await status_msg.edit_text(
        f"✅ <b>GỬI THÔNG BÁO HOÀN TẤT</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"🚀 Thành công: <code>{count}</code>\n"
        f"🚫 Thất bại (Block): <code>{blocked}</code>",
        parse_mode=ParseMode.HTML
    )
async def set_link(u: Update, c: ContextTypes.DEFAULT_TYPE):
    if not is_admin(u.effective_user.id): 
        return
    try:
        args_text = " ".join(c.args)
        k, t, l = [p.strip() for p in args_text.split("|")]
        title_parts = t.split("/")
        title_vi = title_parts[0].strip()
        title_en = title_parts[1].strip() if len(title_parts) > 1 else title_vi
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute(
                "INSERT OR REPLACE INTO modules (key, title, url) VALUES (?, ?, ?)", 
                (k.lower(), t, l)
            )
            conn.commit()   
        await u.message.reply_text(
            f"✅ <b>LƯU MODULE THÀNH CÔNG</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"🔑 Key: <code>{k.lower()}</code>\n"
            f"📝 Tiêu đề: <code>{t}</code>\n"
            f"🔗 Link: {l}",
            parse_mode=ParseMode.HTML
        )
    except Exception:
        await u.message.reply_text(
            "⚠️ <b>Cú pháp sai!</b>\n"
            "Sử dụng: <code>/setlink key | tiêu đề | link</code>\n\n"
            "<i>Mẹo: Có thể dùng tiêu đề song ngữ dạng:</i>\n"
            "<code>/setlink locket | Locket Việt / Locket Eng | https://...</code>",
            parse_mode=ParseMode.HTML
        )
async def del_mod(u: Update, c: ContextTypes.DEFAULT_TYPE):
    if not is_admin(u.effective_user.id) or not c.args: 
        return await u.message.reply_text("⚠️ <b>Cú pháp:</b> <code>/delmodule [key]</code>", parse_mode=ParseMode.HTML)
    key = c.args[0].lower()
    try:
        with sqlite3.connect(DB_PATH) as conn:
            exist = conn.execute("SELECT key FROM modules WHERE key = ?", (key,)).fetchone()
            if not exist:
                return await u.message.reply_text(f"❌ Không tìm thấy module nào có key: <code>{key}</code>", parse_mode=ParseMode.HTML)
            conn.execute("DELETE FROM modules WHERE key = ?", (key,))
            conn.commit()   
        await u.message.reply_text(
            f"🗑 <b>XÓA MODULE THÀNH CÔNG</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"🔑 Key đã xóa: <code>{key}</code>",
            parse_mode=ParseMode.HTML
        )
    except Exception as e:
        logging.error(f"Delete Module Error: {e}")
        await u.message.reply_text(f"❌ <b>Lỗi khi xóa:</b> <code>{str(e)}</code>", parse_mode=ParseMode.HTML)
async def set_admin_cmd(u: Update, c: ContextTypes.DEFAULT_TYPE):
    """Lệnh cấp quyền Admin (Chỉ Root Admin ID mới dùng được)"""
    if u.effective_user.id != ROOT_ADMIN_ID:
        return
    if not c.args:
        return await u.message.reply_text(
            "⚠️ <b>Cú pháp:</b> <code>/addadmin [ID_NGUOI_DUNG]</code>", 
            parse_mode=ParseMode.HTML
        )
    target_id = c.args[0]
    try:
        await add_admin_db(target_id)
        await u.message.reply_text(
            f"✅ <b>NÂNG CẤP ADMIN THÀNH CÔNG</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"👤 ID: <code>{target_id}</code> đã trở thành Quản trị viên hệ thống.", 
            parse_mode=ParseMode.HTML
        )
        target_lang = get_lang(target_id)
        if target_lang == 'en':
            admin_msg = "👑 <b>SYSTEM NOTICE:</b> You have been promoted to <b>Administrator</b>. Use /admin to access the panel."
        else:
            admin_msg = "👑 <b>THÔNG BÁO:</b> Bạn đã được cấp quyền <b>Quản trị viên</b>. Sử dụng lệnh /admin để mở bảng điều khiển."
        try:
            await c.bot.send_message(target_id, admin_msg, parse_mode=ParseMode.HTML)
        except:
            pass
    except Exception as e:
        logging.error(f"Add Admin Error: {e}")
        await u.message.reply_text(f"❌ <b>Lỗi khi cấp quyền:</b> <code>{str(e)}</code>", parse_mode=ParseMode.HTML)
# --- LIST & CALLBACKS ---
async def send_module_list(u: Update, c: ContextTypes.DEFAULT_TYPE, page: int = 1):
    uid = u.effective_user.id
    lang = get_lang(uid)
    s = STRINGS[lang]
    is_user_admin = is_admin(uid)
    per_page = 5
    with sqlite3.connect(DB_PATH) as conn:
        mods = conn.execute("SELECT key, title FROM modules").fetchall()
        header_mod = "📂 <b>MODULE LIST</b>" if lang == 'en' else "📂 <b>DANH SÁCH MODULES</b>"
        txt = f"{header_mod} ({len(mods)})\n\n"
        if mods:
            mod_lines = []
            for m_key, m_title in mods:
                titles = m_title.split("/")
                display_title = titles[1].strip() if (lang == 'en' and len(titles) > 1) else titles[0].strip()
                mod_lines.append(f"🔹 /{m_key} - {display_title}")
            txt += "\n".join(mod_lines)
        else:
            txt += "📭 " + ("No modules available." if lang == 'en' else "Hiện chưa có module nào.")
        kb = [[InlineKeyboardButton(s['btn_donate'], callback_data="donate_info")]]
        if is_user_admin:
            offset = (page - 1) * per_page
            total_users = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
            total_pages = (total_users + per_page - 1) // per_page
            users = conn.execute("""
                SELECT user_id, full_name, join_date, interact_count, is_premium 
                FROM users ORDER BY last_active DESC LIMIT ? OFFSET ?
            """, (per_page, offset)).fetchall()
            txt += f"\n\n👑 <b>ADMIN: USER MGMT ({page}/{total_pages})</b>"
            for us in users:
                status = "💎" if us[4] else "🆓"
                txt += (f"\n\n👤 <b>{us[1]}</b> (<code>{us[0]}</code>)\n"
                        f"📅 Join: {us[2]} | ⚡ Cnt: {us[3]} | {status}")
            nav = []
            if page > 1:
                nav.append(InlineKeyboardButton("⬅️ Prev", callback_data=f"list_page_{page-1}"))
            if page < total_pages:
                nav.append(InlineKeyboardButton("Next ➡️", callback_data=f"list_page_{page+1}"))
            if nav: kb.append(nav)
    kb.append([InlineKeyboardButton(s['btn_profile'], callback_data="profile")])
    kb.append([InlineKeyboardButton(s['btn_back'], callback_data="back_start")])
    await send_ui(u, txt, kb)
async def hdsd_ui(u: Update, c: ContextTypes.DEFAULT_TYPE):
    uid = u.effective_user.id
    lang = get_lang(uid)
    s = STRINGS[lang]
    txt = s['guide_text']
    kb = [[InlineKeyboardButton(s['btn_back'], callback_data="back_start")]]
    await send_ui(u, txt, kb)
async def callback_handler(u: Update, c: ContextTypes.DEFAULT_TYPE):
    query = u.callback_query
    data = query.data
    await query.answer()
    uid = str(query.from_user.id)
    if data.startswith("set_lang_") or data.startswith("setlang_"):
        new_lang = data.split("_")[-1]
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute("UPDATE users SET language = ? WHERE user_id = ?", (new_lang, uid))
            conn.commit()
        try:
            await query.delete_message()
        except Exception as e:
            logging.error(f"Không thể xóa tin nhắn: {e}")
        return await start(u, c)
    if data == "show_list":
        await send_module_list(u, c)
    elif data.startswith("list_page_"):
        page_num = int(data.split("_")[-1])
        await send_module_list(u, c, page=page_num)
    elif data == "profile":
        await profile(u, c)
    elif data == "donate_info":
        await donate_info(u, c)
    elif data == "hdsd":
        await hdsd_ui(u, c)
    elif data == "back_start":
        await start(u, c)
    elif data == "admin_panel":
        await admin_panel(u, c)
    elif data.startswith("done_req_"):
        target_uid = data.split("_")[-1]
        admin_txt = (
            f"📩 <b>TIẾN HÀNH TRẢ KẾT QUẢ</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"👤 Người dùng: <code>{target_uid}</code>\n\n"
            f"Hãy dùng lệnh dưới đây để gửi mã DNS cho họ:\n"
            f"<code>/donedns {target_uid} | [MÃ_DNS_TẠI_ĐÂY]</code>"
        )
        await c.bot.send_message(chat_id=ROOT_ADMIN_ID, text=admin_txt, parse_mode=ParseMode.HTML)
async def dynamic_module_handler(u: Update, c: ContextTypes.DEFAULT_TYPE):
    if not u.message or not u.message.text or not u.message.text.startswith('/'):
        return
    cmd = u.message.text.split()[0][1:].split('@')[0].lower()
    sys_cmds = [
        'start', 'profile', 'list', 'get', 'nextdns', 'donate', 'admin', 
        'stats', 'sendmail', 'donedns', 'saoluu', 'approve', 'send', 
        'revoke', 'broadcast', 'setlink', 'delmodule', 'addadmin', 'hdsd', 'clear'
    ]
    if cmd in sys_cmds:
        return
    uid = u.effective_user.id
    lang = get_lang(uid)
    s = STRINGS[lang]
    try:
        with sqlite3.connect(DB_PATH) as conn:
            res = conn.execute("SELECT title, url FROM modules WHERE key = ?", (cmd,)).fetchone()
        if res:
            title_raw, url = res
            titles = title_raw.split("/")
            display_title = titles[1].strip().upper() if (lang == 'en' and len(titles) > 1) else titles[0].strip().upper()
            txt = s['mod_guide'].format(title=display_title, url=url)
            kb = [
                [InlineKeyboardButton(f"📋 Copy {display_title}", callback_data=f"copyurl_{cmd}")],
                [InlineKeyboardButton(s['btn_show_list'], callback_data="show_list")]
            ]
            await u.message.reply_text(
                text=txt, 
                parse_mode=ParseMode.HTML, 
                reply_markup=InlineKeyboardMarkup(kb), 
                disable_web_page_preview=True
            )
        elif u.effective_chat.type == "private":
            # Nếu không tìm thấy module trong chat riêng tư
            not_found_txt = s['mod_not_found'].format(cmd=cmd)
            kb = [[InlineKeyboardButton(s['btn_show_list'], callback_data="show_list")]]
            await u.message.reply_text(text=not_found_txt, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(kb))
    except Exception as e:
        logging.error(f"Error in dynamic_handler: {e}")
        
# --- WEB SERVER & API ---
server = Flask(__name__)
@server.route('/')
def index():
    return render_template('index.html')
@server.route('/api/generate', methods=['POST'])
def api_generate():
    data = request.json
    raw_username = data.get('user', '').strip()
    raw_date = data.get('date', '').strip()
    if not raw_username or not raw_date:
        return jsonify({"success": False, "error": "Thiếu thông tin!"})
    safe_user = "".join(x for x in raw_username if x.isalnum())
    try:
        date_obj = datetime.strptime(raw_date.replace("/", "-").replace(".", "-"), "%Y-%m-%d")
        date_str = date_obj.strftime("%Y-%m-%d")
        repo = Github(GH_TOKEN).get_repo(REPO_NAME)
        js_p, mod_p = f"{safe_user}/LocketGold.js", f"{safe_user}/LocketGold.sgmodule"
        js_url = f"https://raw.githubusercontent.com/{REPO_NAME}/main/{js_p}"
        js_c = JS_TEMPLATE.format(user=safe_user, date=date_str)
        mod_c = MODULE_TEMPLATE.format(user=raw_username, js_url=js_url)
        for p, cnt in [(js_p, js_c), (mod_p, mod_c)]:
            try:
                f = repo.get_contents(p)
                repo.update_file(p, f"Web Update: {safe_user}", cnt, f.sha)
            except:
                repo.create_file(p, f"Web Create: {safe_user}", cnt)
        return jsonify({
            "success": True, 
            "url": f"https://raw.githubusercontent.com/{REPO_NAME}/main/{mod_p}"
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})
@server.route('/api/sendmail', methods=['POST'])
def api_sendmail():
    data = request.json
    email = data.get('email', '').strip()
    if not email:
        return jsonify({"success": False, "error": "Vui lòng nhập Email!"})
    report_to_admin = (
        "🌐 <b>YÊU CẦU TỪ WEB DASHBOARD</b>\n"
        "━━━━━━━━━━━━━━━━━━\n"
        f"📧 <b>Email:</b> {email}\n"
        f"📝 <b>Nội dung:</b> Yêu cầu duyệt Gold / DNS"
    )
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(app.bot.send_message(ROOT_ADMIN_ID, report_to_admin, parse_mode=ParseMode.HTML))
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})
@server.route('/api/nextdns', methods=['POST'])
def api_nextdns():
    data = request.json
    dns_id = data.get('dns_id', '').strip()
    if not dns_id:
        return jsonify({"success": False, "error": "Thiếu ID NextDNS!"})
    try:
        xml_content = NEXTDNS_CONFIG.format(
            dns_id=dns_id,
            uuid1=str(uuid.uuid4()),
            uuid2=str(uuid.uuid4())
        )
        return jsonify({"success": True, "config": xml_content})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})
async def post_init(application):
    commands_vi = [
        BotCommand("start", "🏠 Bắt đầu"), 
        BotCommand("profile", "👤 Hồ sơ cá nhân"),
        BotCommand("list", "📂 Danh sách Modules"), 
        BotCommand("get", "✨ Tạo Locket Gold"),
        BotCommand("nextdns", "🌐 Tạo Config NextDNS"), 
        BotCommand("send", "🆘 Báo lỗi/Góp ý"),
        BotCommand("donate", "💰 Donate ủng hộ"),
        BotCommand("admin", "🛠 Bảng điều khiển Admin")
    ]
    commands_en = [
        BotCommand("start", "🏠 Start/Restart"), 
        BotCommand("profile", "👤 My Profile"),
        BotCommand("list", "📂 Module List"), 
        BotCommand("get", "✨ Create Locket Gold"),
        BotCommand("nextdns", "🌐 NextDNS Config"), 
        BotCommand("send", "🆘 Report Bug/Feedback"),
        BotCommand("donate", "💰 Support Admin"),
        BotCommand("admin", "🛠 Admin Panel")
    ]
    await application.bot.set_my_commands(commands_vi)
    try:
        await application.bot.set_my_commands(commands_en, language_code='en')
    except Exception as e:
        logging.error(f"Error setting English commands: {e}")
        
# --- MAIN ---
if __name__ == "__main__":
    app = ApplicationBuilder().token(TOKEN).post_init(post_init).build()

    # 2. Đăng ký tất cả các Handlers cho Bot
    app.add_handler(TypeHandler(Update, db_auto_reg), group=-1)
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("profile", profile))
    app.add_handler(CommandHandler("list", send_module_list))
    app.add_handler(CommandHandler("get", get_bundle))
    app.add_handler(CommandHandler("nextdns", get_nextdns))
    app.add_handler(CommandHandler("donate", donate_info))
    app.add_handler(CommandHandler("admin", admin_panel))
    app.add_handler(CommandHandler("stats", stats))
    app.add_handler(CommandHandler("sendmail", send_mail_to_admin))
    app.add_handler(CommandHandler("donedns", done_dns_cmd))
    app.add_handler(CommandHandler("saoluu", backup_data))
    app.add_handler(MessageHandler(filters.Document.FileExtension("xlsx"), restore_data))
    app.add_handler(CommandHandler("clear", clear_members)) 
    app.add_handler(CommandHandler("approve", approve_user))
    app.add_handler(CommandHandler("send", send_feedback))
    app.add_handler(CommandHandler("revoke", revoke_user))
    app.add_handler(CommandHandler("broadcast", broadcast))
    app.add_handler(CommandHandler("setlink", set_link))
    app.add_handler(CommandHandler("delmodule", del_mod))
    app.add_handler(CommandHandler("addadmin", set_admin_cmd))
    app.add_handler(CommandHandler("hdsd", hdsd_ui))
    app.add_handler(CallbackQueryHandler(callback_handler))

    app.add_handler(MessageHandler(filters.COMMAND, dynamic_module_handler))

    threading.Thread(
        target=lambda: server.run(host="0.0.0.0", port=PORT, use_reloader=False), 
        daemon=True
    ).start()

    print(f"🚀 Hệ thống đang chạy tại Port: {PORT}")
    app.run_polling(drop_pending_updates=True)
