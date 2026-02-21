import os, json, logging, threading, asyncio, re, uuid
import gspread
from functools import lru_cache
from datetime import datetime
from oauth2client.service_account import ServiceAccountCredentials
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
    filters
)
from flask import Flask, render_template, request, jsonify

app = None 
ADMIN_ID = int(os.getenv("ADMIN_ID", "7346983056"))  
TOKEN = os.getenv("BOT_TOKEN") or os.getenv("TOKEN")
SHEET_ID = os.getenv("SHEET_ID")
GH_TOKEN = os.getenv("GH_TOKEN")
REPO_NAME = "NgDanhThanhTrung/locket_"
PORT = int(os.getenv("PORT", "8000"))
CONTACT_URL = "https://t.me/NgDanhThanhTrung"
DONATE_URL = "https://ngdanhthanhtrung.github.io/Bank/"
KOYEB_URL = "https://judicial-hali-ngdthanhtrung-c1fe28c3.koyeb.app/"
WEB_URL = "https://ngdanhthanhtrung.github.io/Modules-NDTT-Premium/"

logging.basicConfig(level=logging.INFO)

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

NEXTDNS_MOBILECONFIG = """<?xml version="1.0" encoding="UTF-8"?>
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


async def run_sync(func, *args):
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, func, *args)

def get_sheets():
    creds_raw = os.getenv("GOOGLE_CREDS")
    if not creds_raw: raise RuntimeError("Missing GOOGLE_CREDS")
    creds = ServiceAccountCredentials.from_json_keyfile_dict(
        json.loads(creds_raw),
        ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    )
    ss = gspread.authorize(creds).open_by_key(SHEET_ID)
    return (
        ss.worksheet("modules"), 
        ss.worksheet("users"), 
        ss.worksheet("admin"), 
        ss.worksheet("data")
    )

@lru_cache(maxsize=128)
def is_admin(user_id: int) -> bool:
    try:
        s_m, s_u, s_a, s_d = get_sheets() 
        return str(user_id) in s_a.col_values(1)[1:]
    except: return False

def ensure_data_header(sheet):
    try:
        if sheet.row_values(1) != ["user_id", "username", "messages"]:
            sheet.update([["user_id", "username", "messages"]], "A1:C1")
    except: pass
async def auto_reg(u: Update, s_u, s_d):
    user = u.effective_user
    if not user: return
    try:
        uid, uname = str(user.id), (f"@{user.username}" if user.username else "N/A")
        if uid not in s_u.col_values(1):
            s_u.append_row([uid, user.full_name, uname])
        ensure_data_header(s_d)
        ids = s_d.col_values(1)
        if uid not in ids:
            s_d.append_row([uid, uname, 1])
        else:
            row = ids.index(uid) + 1
            curr = s_d.cell(row, 3).value
            s_d.update_cell(row, 3, (int(curr) if curr and str(curr).isdigit() else 0) + 1)
    except Exception as e: logging.error(f"Auto reg error: {e}")

def get_kb(include_list=False):
    kb = []
    kb.append([InlineKeyboardButton("🌐 Mở Web Dashboard (Koyeb)", url=KOYEB_URL)])
    if include_list: 
        kb.append([InlineKeyboardButton("📂 Danh sách Module", callback_data="show_list")])
    kb.append([
        InlineKeyboardButton("💬 Liên hệ", url=CONTACT_URL), 
        InlineKeyboardButton("☕ Donate", url=DONATE_URL)
    ])
    kb.append([InlineKeyboardButton("✨ Web Hướng Dẫn (GitHub)", url=WEB_URL)])
    return InlineKeyboardMarkup(kb)

async def start(u: Update, c: ContextTypes.DEFAULT_TYPE):
    s_m, s_u, s_a, s_d = get_sheets()
    await auto_reg(u, s_u, s_d)
    txt = (
        f"👋 Chào mừng <b>{u.effective_user.first_name}</b> đến với <b>@NgDanhThanhTrung_BOT</b>!\n\n"
        f"🚀 <b>Tính năng chính:</b>\n"
        f"🔹 Hỗ trợ tạo Module Shadowrocket cá nhân hóa.\n"
        f"🔹 Tự động kích hoạt script Locket Gold vĩnh viễn.\n"
        f"🔹 Dashboard Web mượt mà, dễ sử dụng.\n\n"
        f"🌐 <b>Web Dashboard:</b>\n"
        f"<code>{KOYEB_URL}</code>\n\n"
        f"📝 <b>Hướng dẫn:</b>\n"
        f"• Nhấn nút <b>Danh sách Module</b> bên dưới để xem script.\n"
        f"• Gõ <code>/get Tên | Ngày</code> để tạo script riêng.\n"
        f"• Gõ /hdsd để xem cách cài đặt <b>HTTPS Decryption</b>.\n\n"
        f"👨‍💻 <b>Admin:</b> @NgDanhThanhTrung"
    )
    await u.message.reply_text(
        txt, 
        parse_mode=ParseMode.HTML, 
        reply_markup=get_kb(True),
        disable_web_page_preview=False
    )

async def hdsd(u: Update, c: ContextTypes.DEFAULT_TYPE):
    s_m, s_u, s_a, s_d = get_sheets()
    await auto_reg(u, s_u, s_d)
    txt = (
        "📖 <b>HƯỚNG DẪN SỬ DỤNG:</b>\n\n"
        "🔹 <b>MODULE CÓ SẴN:</b>\n"
        "Nhấn nút 'Danh sách Module' hoặc gõ /list.\n"
        "Sau đó gõ <code>/[tên_module]</code> để lấy link.\n\n"
        "🔹 <b>TẠO MODULE LOCKET RIÊNG:</b>\n"
        "Cú pháp: <code>/get tên_user | yyyy-mm-dd</code>\n"
        "<i>Ví dụ: /get ndtt | 2025-01-16</i>"
    )
    if is_admin(u.effective_user.id):
        txt += (
            "\n\n⚡ <b>QUYỀN ADMIN:</b>\n"
            "• /stats - Thống kê\n"
            "• /broadcast - Thông báo\n"
            "• /setlink - Thêm/Sửa\n"
            "• /delmodule - Xóa"
        )
    await u.message.reply_text(txt, parse_mode=ParseMode.HTML, reply_markup=get_kb())

async def profile(u: Update, c: ContextTypes.DEFAULT_TYPE):
    s_m, s_u, s_a, s_d = get_sheets()
    uid = str(u.effective_user.id)
    ids = s_d.col_values(1)
    
    if uid not in ids: 
        return await u.message.reply_text("❌ <b>Dữ liệu chưa đồng bộ.</b> Hãy gõ /start để khởi tạo.")
    
    row = ids.index(uid) + 1
    msg_count = s_d.cell(row, 3).value or "0"
    
    text = (
        f"👤 <b>HỒ SƠ NGƯỜI DÙNG</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🆔 <b>ID:</b> <code>{uid}</code>\n"
        f"🏷 <b>Username:</b> @{u.effective_user.username if u.effective_user.username else 'N/A'}\n"
        f"📛 <b>Tên:</b> {u.effective_user.full_name}\n"
        f"💬 <b>Tương tác:</b> <code>{msg_count}</code> tin nhắn\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"✨ <i>Cảm ơn bạn đã sử dụng dịch vụ!</i>"
    )
    await u.message.reply_text(text, parse_mode=ParseMode.HTML)
    
async def sync_github_files(user, date):
    repo = Github(GH_TOKEN).get_repo(REPO_NAME)
    js_p, mod_p = f"{user}/Locket_Gold.js", f"{user}/Locket_{user}.sgmodule"
    js_url = f"https://raw.githubusercontent.com/{REPO_NAME}/main/{js_p}"
    
    js_content = JS_TEMPLATE.format(user=user, date=date)
    mod_content = MODULE_TEMPLATE.format(user=user, js_url=js_url)
    
    for path, content in [(js_p, js_content), (mod_p, mod_content)]:
        try:
            f = repo.get_contents(path, ref="main")
            repo.update_file(path, f"Sync {user}", content, f.sha, branch="main")
        except:
            repo.create_file(path, f"Sync {user}", content, branch="main")
    return f"https://raw.githubusercontent.com/{REPO_NAME}/main/{mod_p}"

async def get_bundle(u: Update, c: ContextTypes.DEFAULT_TYPE):
    await auto_reg(u, *get_sheets()[1:4])
    raw = " ".join(c.args)
    if "|" not in raw:
        return await u.message.reply_text("⚠️ Cú pháp: /get user | yyyy-mm-dd")
    
    user, date = [p.strip() for p in raw.split("|")]
    status = await u.message.reply_text("⏳ Đang xử lý...")
    try:
        mod_url = await sync_github_files(user, date)
        await status.edit_text(f"✅ Thành công!\n<code>{mod_url}</code>", parse_mode=ParseMode.HTML)
    except Exception as e:
        await status.edit_text(f"❌ Lỗi: {e}")

async def get_nextdns(u: Update, c: ContextTypes.DEFAULT_TYPE):
    try:
        try:
            await auto_reg(u, *get_sheets()[1:4])
        except:
            pass

        if not c.args:
            guide = (
                "🛠 <b>HƯỚNG DẪN TẠO NEXTDNS:</b>\n\n"
                "1️⃣ Truy cập <a href='https://my.nextdns.io'>my.nextdns.io</a> đăng ký tài khoản.\n"
                "2️⃣ Đặt mật khẩu là <code>12345678</code> để Admin hỗ trợ.\n"
                "3️⃣ Gõ lệnh <code>/send [Email_của_bạn]</code> để báo Admin.\n"
                "4️⃣ Lấy <b>ID</b> tại tab Setup (ví dụ: <code>abc123</code>).\n\n"
                "👉 <b>Để lấy mã cấu hình, gõ:</b> <code>/nextdns [ID_của_bạn]</code>"
            )
            return await u.message.reply_text(guide, parse_mode=ParseMode.HTML, disable_web_page_preview=True)

        dns_id = c.args[0].strip()
        status = await u.message.reply_text("⏳ Đang tạo mã cấu hình...")

        content = NEXTDNS_MOBILECONFIG.format(
            dns_id=dns_id,
            uuid1=str(uuid.uuid4()),
            uuid2=str(uuid.uuid4())
        )

        shortcut_url = "https://www.icloud.com/shortcuts/ef6f685318484784940648ad520b5c4f"
        keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton("⚡ Cài qua Shortcuts", url=shortcut_url)
        ]])

        import html
        safe_content = html.escape(content)

        msg_text = (
            f"✅ <b>Mã cấu hình cho ID:</b> <code>{dns_id}</code>\n\n"
            f"👇 <b>BƯỚC TIẾP THEO:</b>\n"
            f"1. Chạm vào đoạn code dưới để <b>Copy</b>.\n"
            f"2. Dán vào ứng dụng <b>Ghi chú (Notes)</b>.\n"
            f"3. Nhấn <b>Chia sẻ</b> -> Chọn <b>Shortcuts NextDNS</b>.\n\n"
            f"<pre>{safe_content}</pre>"
        )

        await u.message.reply_text(msg_text, parse_mode=ParseMode.HTML, reply_markup=keyboard)
        await status.delete()

    except Exception as e:
        logging.error(f"Error: {e}")
        if 'status' in locals():
            await status.edit_text(f"❌ Lỗi: {str(e)}")
        else:
            await u.message.reply_text(f"❌ Lỗi: {str(e)}")

async def send_email_to_admin(u: Update, c: ContextTypes.DEFAULT_TYPE):
    if not c.args:
        return await u.message.reply_text("⚠️ Cú pháp: <code>/send your_email@gmail.com</code>", parse_mode=ParseMode.HTML)
    
    email = c.args[0]
    admin_id = ADMIN_ID 
    user = u.effective_user
    
    await c.bot.send_message(
        chat_id=admin_id,
        text=(
            f"📩 <b>YÊU CẦU NEXTDNS</b>\n"
            f"👤: {user.full_name} (@{user.username})\n"
            f"🆔: <code>{user.id}</code>\n"
            f"📧: <code>{email}</code>\n\n"
            f"Dùng: <code>/approve {user.id}</code> để duyệt."
        ),
        parse_mode=ParseMode.HTML
    )
    await u.message.reply_text("✅ Đã gửi Email cho Admin. Vui lòng đợi Admin phê duyệt.")

async def approve_user(u: Update, c: ContextTypes.DEFAULT_TYPE):
    if u.effective_user.id != ADMIN_ID: 
        return
        
    if not c.args: 
        return await u.message.reply_text("⚠️ Cú pháp: /approve [user_id]")
    
    target_id = c.args[0].strip()
    shortcut_url = "https://www.icloud.com/shortcuts/ef6f685318484784940648ad520b5c4f"
    
    try:
        msg = (
            "✅ <b>YÊU CẦU ĐÃ ĐƯỢC DUYỆT</b>\n\n"
            "Admin đã phê duyệt Email của bạn. Bây giờ bạn có thể gõ lệnh để lấy mã:\n"
            "👉 <code>/nextdns [ID_của_bạn]</code>\n\n"
            f"💡 Đừng quên cài sẵn <a href='{shortcut_url}'>Phím tắt này</a> để cài đặt nhanh!"
        )
        await c.bot.send_message(chat_id=target_id, text=msg, parse_mode=ParseMode.HTML, disable_web_page_preview=True)
        await u.message.reply_text(f"✅ Đã duyệt User: <code>{target_id}</code>", parse_mode=ParseMode.HTML)
    except Exception as e:
        await u.message.reply_text(f"❌ Lỗi gửi tin: {e}")

async def send_module_list(u: Update, c: ContextTypes.DEFAULT_TYPE):
    s_m, s_u, s_a, s_d = get_sheets()
    target = u.message if u.message else u.callback_query.message
    
    modules = s_m.get_all_records()
    if not modules:
        return await target.reply_text("📭 <b>Danh sách Module hiện đang trống.</b>", parse_mode=ParseMode.HTML)

    m_list = "📂 <b>DANH SÁCH MODULE HỆ THỐNG</b>\n"
    m_list += "<i>Nhấn vào lệnh để lấy hướng dẫn cài đặt</i>\n"
    m_list += "━━━━━━━━━━━━━━━━━━━━\n"
    for r in modules:
        m_list += f"🔹 /{r['key']} ➔ <b>{r['title']}</b>\n"
    m_list += "━━━━━━━━━━━━━━━━━━━━\n"
    m_list += "👉 <i>Sử dụng các lệnh trên để lấy link chi tiết.</i>"

    await target.reply_text(m_list, parse_mode=ParseMode.HTML, reply_markup=get_kb())
    
    if is_admin(u.effective_user.id) and u.message:
        users = s_u.get_all_records()
        u_list = "👥 <b>QUẢN LÝ NGƯỜI DÙNG (ADMIN ONLY)</b>\n"
        u_list += "━━━━━━━━━━━━━━━━━━━━\n"
        for r in users[:20]: # Hiển thị 20 người gần nhất
            u_list += f"👤 <code>{r['id']}</code> - {r['name']}\n"
        u_list += "━━━━━━━━━━━━━━━━━━━━\n"
        u_list += f"<i>Tổng cộng: {len(users)} thành viên.</i>"
        await u.message.reply_text(u_list, parse_mode=ParseMode.HTML)
        
async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    user_id = update.effective_user.id
    
    # Phản hồi ngay lập tức để icon đồng hồ cát trên nút bấm biến mất
    await query.answer()

    # SỬA TẠI ĐÂY: Kiểm tra quyền bằng biến ADMIN_ID (số) thay vì gọi hàm is_admin (Sheets)
    if user_id != ADMIN_ID:
        return await query.message.reply_text("❌ Bạn không có quyền thực hiện thao tác này!")

    admin_name = update.effective_user.full_name

    if data.startswith("approve_locket:"):
        username = data.split(":")[1]
        await query.edit_message_text(
            text=f"✅ <b>HOÀN TẤT DUYỆT LOCKET</b>\n━━━━━━━━━━━━━━━━━━━━\n👤 User: <code>{username}</code>\n👨‍💻 Admin: <b>{admin_name}</b>\n✨ <i>Hệ thống đã kích hoạt thành công!</i>",
            parse_mode=ParseMode.HTML
        )

    elif data.startswith("approve_dns:"):
        parts = data.split(":")
        dns_id, email = parts[1], parts[2] if len(parts) > 2 else "N/A"
        await query.edit_message_text(
            text=f"✅ <b>HOÀN TẤT DUYỆT NEXTDNS</b>\n━━━━━━━━━━━━━━━━━━━━\n📧 Email: <code>{email}</code>\n🆔 ID: <code>{dns_id}</code>\n👨‍💻 Admin: <b>{admin_name}</b>",
            parse_mode=ParseMode.HTML
        )

    elif data.startswith("deny_"):
        await query.edit_message_text(
            text=f"❌ <b>YÊU CẦU ĐÃ BỊ TỪ CHỐI</b>\n━━━━━━━━━━━━━━━━━━━━\n👨‍💻 Admin thực hiện: {admin_name}\n⚠️ <i>Yêu cầu này sẽ không được xử lý.</i>",
            parse_mode=ParseMode.HTML
        )

    elif data == "show_list":
        await send_module_list(update, context)
        
async def handle_msg(u: Update, c: ContextTypes.DEFAULT_TYPE):
    if not u.message or not u.message.text or not u.message.text.startswith('/'): return
    cmd = u.message.text.replace("/", "").lower().split('@')[0].strip()
    system_cmds = ["start", "hdsd", "list", "get", "setlink", "delmodule", "broadcast", "stats", "myid", "profile", "nextdns", "send", "approve"]
    if cmd in system_cmds: return
    try:
        s_m, s_u, s_a, s_d = get_sheets()
        await auto_reg(u, s_u, s_d)
        db = {r['key'].lower().strip(): r for r in s_m.get_all_records()}
        if cmd in db:
            item = db[cmd]
            guide = (
                f"✨ <b>HƯỚNG DẪN: {item['title'].upper()}</b> ✨\n\n"
                f"1️⃣ <b>Copy URL:</b> Chạm giữ link bên dưới:\n<code>{item['url']}</code>\n\n"
                f"2️⃣ <b>Shadowrocket:</b> Tab <b>Module</b> ➔ <b>Add Module</b> ➔ Dán URL ➔ OK.\n\n"
                f"3️⃣ <b>HTTPS Decryption:</b>\n"
                f"• Bật <b>HTTPS Decryption</b> trong Settings.\n"
                f"• Chọn <b>Generate New CA</b> ➔ Install.\n"
                f"• Vào Cài đặt máy ➔ Tin cậy chứng chỉ.\n\n"
                f"4️⃣ <b>Kết nối:</b> Bật VPN và tận hưởng!\n\n"
                f"⚠️ <i>Lưu ý: Luôn bật VPN khi sử dụng.</i>"
            )
            kb = [[InlineKeyboardButton(f"🔗 Mở Link {item['title']}", url=item['url'])]]
            kb.extend(get_kb(True).inline_keyboard)
            await u.message.reply_text(guide, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(kb))
    except Exception as e: logging.error(f"Handle msg error: {e}")

async def stats(u: Update, c: ContextTypes.DEFAULT_TYPE):
    if not is_admin(u.effective_user.id): return
    
    s_m, s_u, s_a, s_d = get_sheets()
    count_m = len(s_m.get_all_records())
    count_u = len(s_u.col_values(1)) - 1
    count_a = len(s_a.col_values(1)) - 1
    
    msg = (
        f"📊 <b>THỐNG KÊ HỆ THỐNG</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🌐 <b>Người dùng:</b> <code>{count_u}</code>\n"
        f"📦 <b>Số lượng Module:</b> <code>{count_m}</code>\n"
        f"🛡 <b>Quản trị viên:</b> <code>{count_a}</code>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"⏱ <i>Cập nhật: {datetime.now().strftime('%H:%M:%S %d/%m/%Y')}</i>"
    )
    await u.message.reply_text(msg, parse_mode=ParseMode.HTML)
async def set_link(u: Update, c: ContextTypes.DEFAULT_TYPE):
    if not is_admin(u.effective_user.id): return
    try:
        k, t, l = [a.strip() for a in " ".join(c.args).split("|")]
        s_m, _, _, _ = get_sheets()
        cell = s_m.find(k.lower(), in_column=1)
        if cell: s_m.update(f'B{cell.row}:C{cell.row}', [[t, l]])
        else: s_m.append_row([k.lower(), t, l])
        await u.message.reply_text(f"✅ Đã lưu module: {t}")
    except: await u.message.reply_text("❌ Cú pháp: /setlink key | Tên | URL")

async def del_mod(u: Update, c: ContextTypes.DEFAULT_TYPE):
    if not is_admin(u.effective_user.id) or not c.args: return
    s_m, _, _, _ = get_sheets()
    cell = s_m.find(c.args[0].lower().strip(), in_column=1)
    if cell: 
        s_m.delete_rows(cell.row)
        await u.message.reply_text(f"🗑 Đã xóa module: {c.args[0]}")
    else: await u.message.reply_text("🔍 Không tìm thấy mã module.")

async def broadcast(u: Update, c: ContextTypes.DEFAULT_TYPE):
    if not is_admin(u.effective_user.id): return
    msg_parts = u.message.text_html.split(maxsplit=1)
    if len(msg_parts) < 2: return await u.message.reply_text("⚠️ Nhập nội dung sau /broadcast")
    msg = msg_parts[1]
    _, s_u, _, _ = get_sheets()
    users, count = s_u.col_values(1)[1:], 0
    for uid in users:
        try:
            await c.bot.send_message(uid, msg, parse_mode=ParseMode.HTML)
            count += 1
            await asyncio.sleep(0.05)
        except: pass
    await u.message.reply_text(f"✅ Đã gửi tới {count} người.")

server = Flask(__name__)

@server.route('/')
def index():
    return render_template('index.html')

@server.route('/api/generate', methods=['POST'])
def api_generate():
    data = request.json
    user_web = data.get('user', '').strip()
    date_web = data.get('join_date')

    if not user_web or not date_web:
        return jsonify({"error": "Vui lòng nhập đủ thông tin!"}), 400
    
    try:
        # SỬA: Chạy hàm sync_github_files thông qua loop đang chạy của bot app
        future = asyncio.run_coroutine_threadsafe(sync_github_files(user_web, date_web), app.loop)
        url = future.result() # Đợi lấy kết quả URL từ GitHub
        
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("✅ Duyệt Gold", callback_data=f"approve_locket:{user_web}"),
                InlineKeyboardButton("❌ Từ chối", callback_data=f"deny_locket:{user_web}")
            ]
        ])

        if app:
            msg = (
                f"👑 <b>YÊU CẦU KÍCH HOẠT LOCKET GOLD</b>\n"
                f"<i>Hệ thống ghi nhận yêu cầu mới</i>\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"👤 <b>Khách hàng:</b> <code>{user_web}</code>\n"
                f"📅 <b>Ngày tạo:</b> <code>{date_web}</code>\n"
                f"⚙️ <b>Trạng thái:</b> <code>Đang chờ...</code>\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"📂 <b>Cấu hình GitHub:</b>\n"
                f"<a href='{url}'>🌐 Xem mã nguồn tại đây</a>\n\n"
                f"👉 <i>Nhấn nút dưới để xử lý nhanh.</i>"
            )
            # SỬA: Gửi tin nhắn thông qua loop của bot để không gây treo hệ thống
            asyncio.run_coroutine_threadsafe(
                app.bot.send_message(
                    chat_id=ADMIN_ID, 
                    text=msg, 
                    parse_mode='HTML', 
                    reply_markup=keyboard,
                    disable_web_page_preview=True
                ),
                app.loop
            )

        return jsonify({"success": True, "url": url})
    except Exception as e:
        logging.error(f"API Generate Error: {e}")
        return jsonify({"error": str(e)}), 500
        
@server.route('/api/send_request', methods=['POST'])
def api_send_request():
    data = request.json
    username = data.get('username', '').strip()
    req_type = data.get('type', 'locket_gold_activation')
    
    if not username:
        return jsonify({"error": "Vui lòng nhập Username!"}), 400
    
    try:
        # Sử dụng ADMIN_ID và gửi qua loop của bot
        msg = (
            f"👑 <b>YÊU CẦU KÍCH HOẠT LOCKET GOLD</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"👤 Username: <code>{username}</code>\n"
            f"🛠 Loại: <code>{req_type}</code>\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"<i>Gửi từ Web Dashboard</i>"
        )
        
        # Chạy lệnh gửi message trên luồng của Telegram App
        asyncio.run_coroutine_threadsafe(
            app.bot.send_message(chat_id=ADMIN_ID, text=msg, parse_mode='HTML'),
            app.loop
        )

        return jsonify({"success": True})
    except Exception as e:
        logging.error(f"API Send Request Error: {e}")
        return jsonify({"error": str(e)}), 500
        
@server.route('/api/nextdns_unified', methods=['POST'])
def api_nextdns_unified():
    data = request.json
    dns_id = data.get('dns_id', '').strip()
    email = data.get('email', '').strip()
    
    if not dns_id: return jsonify({"error": "Thiếu DNS ID"}), 400
    
    try:
        xml_content = NEXTDNS_MOBILECONFIG.format(
            dns_id=dns_id, 
            uuid1=str(uuid.uuid4()).upper(), 
            uuid2=str(uuid.uuid4()).upper()
        )

        # Nếu có email, gửi thông báo duyệt cho Admin thông qua Loop của Bot
        if email and app:
            keyboard = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("✅ Duyệt Premium", callback_data=f"approve_dns:{dns_id}:{email}"),
                    InlineKeyboardButton("❌ Từ chối", callback_data=f"deny_dns:{dns_id}")
                ]
            ])
            
            msg = (
                f"💎 <b>YÊU CẦU NEXTDNS PREMIUM</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"📧 <b>Email:</b> <code>{email}</code>\n"
                f"🆔 <b>DNS ID:</b> <code>{dns_id}</code>\n"
                f"🎯 <b>Phân loại:</b> <code>Premium Account</code>\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"<i>Vui lòng nâng cấp tài khoản trước khi duyệt!</i>"
            )
            
            # Chạy lệnh gửi message trên luồng của Telegram App
            asyncio.run_coroutine_threadsafe(
                app.bot.send_message(
                    chat_id=ADMIN_ID, 
                    text=msg, 
                    parse_mode='HTML', 
                    reply_markup=keyboard
                ),
                app.loop
            )

        return jsonify({"success": True, "config": xml_content})
    except Exception as e:
        logging.error(f"API NextDNS Error: {e}")
        return jsonify({"error": str(e)}), 500
        
async def post_init(app):
    await app.bot.set_my_commands([
        BotCommand("start","Bắt đầu"), 
        BotCommand("nextdns", "Tạo cấu hình NextDNS"),
        BotCommand("send", "Gửi email cho Admin"),
        BotCommand("list","Danh sách"), 
        BotCommand("profile","Hồ sơ"), 
        BotCommand("hdsd","Hướng dẫn"),
        BotCommand("get", "Tạo Locket riêng")
    ])

if __name__ == "__main__":
    threading.Thread(
        target=lambda: server.run(host="0.0.0.0", port=PORT, use_reloader=False), 
        daemon=True
    ).start()
    
    app = ApplicationBuilder().token(TOKEN).post_init(post_init).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("profile", profile))
    app.add_handler(CommandHandler("hdsd", hdsd))
    app.add_handler(CommandHandler("send", send_email_to_admin))
    app.add_handler(CommandHandler("approve", approve_user))
    app.add_handler(CommandHandler("nextdns", get_nextdns))
    app.add_handler(CommandHandler("list", send_module_list))
    app.add_handler(CommandHandler("stats", stats))
    app.add_handler(CommandHandler("setlink", set_link))
    app.add_handler(CommandHandler("delmodule", del_mod))
    app.add_handler(CommandHandler("broadcast", broadcast))
    app.add_handler(CommandHandler("get", get_bundle))
    app.add_handler(CommandHandler("myid", lambda u, c: u.message.reply_text(f"🆔 ID: `{u.effective_user.id}`", parse_mode=ParseMode.MARKDOWN)))  

    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(MessageHandler(filters.COMMAND, handle_msg))

    print("--- SERVER STARTED ---")
    app.run_polling(drop_pending_updates=True)
