import os, json, logging, threading, asyncio, re
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
from flask import Flask

# ================= CONFIG =================
TOKEN = os.getenv("BOT_TOKEN") or os.getenv("TOKEN")
SHEET_ID = os.getenv("SHEET_ID")
GH_TOKEN = os.getenv("GH_TOKEN")
REPO_NAME = "NgDanhThanhTrung/locket_"
PORT = int(os.getenv("PORT", "8000"))
CONTACT_URL = "https://t.me/NgDanhThanhTrung"
DONATE_URL = "https://ngdanhthanhtrung.github.io/Bank/"
WEB_URL = "https://ngdanhthanhtrung.github.io/Modules-NDTT-Premium/"

logging.basicConfig(level=logging.INFO)

# ================= TEMPLATE =================
JS_TEMPLATE = """// ========= ID ========= //
const mapping = {{
  '%E8%BD%A6%E7%A5%A8%E7%A5%A8': ['vip+watch_vip'],
  'Locket': ['Gold']
}};
var ua=$request.headers["User-Agent"]||$request.headers["user-agent"],
obj=JSON.parse($response.body);
obj.Attention="Chúc mừng bạn! Vui lòng không bán hoặc chia sẻ cho người khác!";
var {user}={{
  is_sandbox:!1,
  ownership_type:"PURCHASED",
  billing_issues_detected_at:null,
  period_type:"normal",
  expires_date:"2999-12-18T01:04:17Z",
  grace_period_expires_date:null,
  unsubscribe_detected_at:null,
  original_purchase_date:\"{date}T01:04:18Z\",
  purchase_date:\"{date}T01:04:17Z\",
  store:\"app_store\"
}};
var {user}_sub={{
  grace_period_expires_date:null,
  purchase_date:\"{date}T01:04:17Z\",
  product_identifier:\"com.{user}.premium.yearly\",
  expires_date:\"2999-12-18T01:04:17Z\"
}};
const match=Object.keys(mapping).find(e=>ua.includes(e));
if(match){{
  let[e,s]=mapping[match];
  s?({user}_sub.product_identifier=s,obj.subscriber.subscriptions[s]={user}):obj.subscriber.subscriptions[\"com.{user}.premium.yearly\"]={user},obj.subscriber.entitlements[e]={user}_sub
}}else{{
  obj.subscriber.subscriptions[\"com.{user}.premium.yearly\"]={user};
  obj.subscriber.entitlements.pro={user}_sub
}}
$done({{body:JSON.stringify(obj)}});"""

MODULE_TEMPLATE = """#!name=Locket-Gold ({user})
#!desc=Crack By NgDanhThanhTrung
[Script]
revenuecat = type=http-response, pattern=^https:\\/\\/api\\.revenuecat\\.com\\/.+\\/(receipts$|subscribers\\/[^/]+$), script-path={js_url}, requires-body=true, max-size=-1, timeout=60
deleteHeader = type=http-request, pattern=^https:\\/\\/api\\.revenuecat\\.com\\/.+\\/(receipts|subscribers), script-path=https://raw.githubusercontent.com/NgDanhThanhTrung/locket_/main/Locket_NDTT/deleteHeader.js, timeout=60
[MITM]
hostname = %APPEND% api.revenuecat.com"""

# --- 3. HÀM HỖ TRỢ ---
def is_admin(user_id: int) -> bool:
    """
    Check admin theo Telegram user_id
    Sheet 'admin':
      - Cột A: user_id (dùng để check)
      - Cột B: username (chỉ để nhìn, KHÔNG dùng)
    """
    try:
        if user_id is None:
            return False

        _, _, s_a = get_sheets()
        if s_a is None:
            return False
        admin_ids = s_a.col_values(1)[1:]
        return str(user_id) in admin_ids

    except Exception as e:
        logging.error(f"is_admin failed | user_id={user_id} | {e}")
        return False
def get_sheets():
    creds_raw = os.getenv("GOOGLE_CREDS")
    if not creds_raw:
        raise RuntimeError("Missing GOOGLE_CREDS")

    creds = ServiceAccountCredentials.from_json_keyfile_dict(
        json.loads(creds_raw),
        [
            "https://spreadsheets.google.com/feeds",
            "https://www.googleapis.com/auth/drive"
        ]
    )
    ss = gspread.authorize(creds).open_by_key(SHEET_ID)
    return ss.worksheet("modules"), ss.worksheet("users"), ss.worksheet("admin")

def is_admin(user_id: int) -> bool:
    try:
        _, _, s_a = get_sheets()
        return str(user_id) in s_a.col_values(1)[1:]
    except:
        return False

# ================= UI =================
def get_kb(include_list=False):
    kb = []
    if include_list:
        kb.append([InlineKeyboardButton("📂 Danh sách Module", callback_data="show_list")])
    kb.append([
        InlineKeyboardButton("💬 Liên hệ", url=CONTACT_URL),
        InlineKeyboardButton("☕ Donate", url=DONATE_URL)
    ])
    kb.append([InlineKeyboardButton("✨ Web Hướng Dẫn", url=WEB_URL)])
    return InlineKeyboardMarkup(kb)

async def auto_reg(u: Update):
    user = u.effective_user
    if not user: return
    _, s_u, _ = get_sheets()
    try:
        if str(user.id) not in s_u.col_values(1):
            s_u.append_row([str(user.id), user.full_name, f"@{user.username}" if user.username else "N/A"])
    except: pass

async def send_module_list(u: Update, c: ContextTypes.DEFAULT_TYPE):
    s_m, s_u, _ = get_sheets()
    if not s_m: return
    m_list = "<b>📂 DANH SÁCH MODULE HỆ THỐNG:</b>\n\n" + "\n".join([f"🔹 /{r['key']} - {r['title']}" for r in s_m.get_all_records()])
    target = u.message if u.message else u.callback_query.message
    await target.reply_text(m_list, parse_mode=ParseMode.HTML)
    if is_admin(u.effective_user.id) and u.message:
        users = s_u.get_all_records()
        u_list = "<b>👥 DANH SÁCH USER:</b>\n\n" + "\n".join([f"👤 {r['name']} ({r.get('username', 'N/A')})" for r in users])
        await u.message.reply_text(u_list, parse_mode=ParseMode.HTML)

# --- 4. LỆNH BOT ---
async def start(u: Update, c: ContextTypes.DEFAULT_TYPE):
    await auto_reg(u)
    user_name = u.effective_user.first_name
    txt = (
        f"👋 Chào mừng <b>{user_name}</b> đến với Bot của NgDanhThanhTrung!\n\n"
        f"🔹 Bot hỗ trợ lấy link Module Shadowrocket và tạo script Locket Gold riêng.\n"
        f"🔹 Nhấn nút <b>Danh sách Module</b> bên dưới để xem các script có sẵn.\n"
        f"🔹 Gõ /hdsd để xem cách cài đặt HTTPS Decryption."
    )
    await u.message.reply_text(
        txt, 
        parse_mode=ParseMode.HTML, 
        reply_markup=get_kb(include_list=True) 
    )
async def hdsd(u: Update, c: ContextTypes.DEFAULT_TYPE):
    await auto_reg(u)

    user_id = u.effective_user.id

    txt = (
        "📖 <b>HƯỚNG DẪN SỬ DỤNG:</b>\n\n"
        "🔹 <b>MODULE CÓ SẴN:</b>\n"
        "Nhấn nút 'Danh sách Module' hoặc gõ /list. "
        "Sau đó gõ <code>/[tên_module]</code> để lấy link.\n\n"
        "🔹 <b>TẠO MODULE LOCKET RIÊNG:</b>\n"
        "Cú pháp: <code>/get tên_user | yyyy-mm-dd</code>\n"
        "<i>Ví dụ: /get ndtt | 2025-01-16</i>\n"
        "• Tên user: viết liền không dấu.\n"
        "• Ngày: Năm-Tháng-Ngày (đăng ký)."
    )

    if is_admin(user_id):
        txt += "\n\n⚡ <b>ADMIN:</b>\n/setlink\n/delmodule\n/broadcast\n/stats"

    await u.message.reply_text(
        txt,
        parse_mode=ParseMode.HTML,
        reply_markup=get_combined_kb()
    )

async def get_bundle(u: Update, c: ContextTypes.DEFAULT_TYPE):
    await auto_reg(u)
    raw_text = " ".join(c.args)
    if "|" not in raw_text: return await u.message.reply_text("⚠️ Sai cú pháp! /get user | yyyy-mm-dd")
    try:
        user, date = [p.strip() for p in raw_text.split("|")]
        status_msg = await u.message.reply_text("⏳ Đang xử lý GitHub...")
        repo = Github(GH_TOKEN).get_repo(REPO_NAME)
        js_p, mod_p = f"{user}/Locket_Gold.js", f"{user}/Locket_{user}.sgmodule"
        js_url = f"https://raw.githubusercontent.com/{REPO_NAME}/main/{js_p}"

        for path, content in [(js_p, JS_TEMPLATE.format(user=user, date=date)), (mod_p, MODULE_TEMPLATE.format(user=user, js_url=js_url))]:
            try:
                f = repo.get_contents(path, ref="main")
                repo.update_file(path, f"Update {user}", content, f.sha, branch="main")
            except: repo.create_file(path, f"Create {user}", content, branch="main")

        await status_msg.edit_text(f"✅ <b>Thành công!</b>\nLink:\n<code>https://raw.githubusercontent.com/{REPO_NAME}/main/{mod_p}</code>", parse_mode=ParseMode.HTML)
    except Exception as e: await u.message.reply_text(f"❌ Lỗi: {e}")

# --- LỆNH ADMIN BỔ SUNG ---
async def set_link(u: Update, c: ContextTypes.DEFAULT_TYPE):
    if not is_admin(u.effective_user.id):
        await u.message.reply_text("❌ Lệnh này chỉ dành cho admin.")
        return
    try:
        k, t, l = [a.strip() for a in " ".join(c.args).split("|")]
        s_m, _, _ = get_sheets()
        cell = s_m.find(k.lower(), in_column=1)
        if cell: s_m.update(f'B{cell.row}:C{cell.row}', [[t, l]])
        else: s_m.append_row([k.lower(), t, l])
        await u.message.reply_text(f"✅ Đã lưu module: {t}")
    except: await u.message.reply_text("❌ Cú pháp: /setlink key | Tên | URL")

async def del_mod(u: Update, c: ContextTypes.DEFAULT_TYPE):
    if not is_admin(u.effective_user.id):
        await u.message.reply_text("❌ Lệnh này chỉ dành cho admin.")
        return
    if not c.args:
        return

    s_m, _, _ = get_sheets()
    try:
        cell = s_m.find(c.args[0].lower(), in_column=1)
        if cell: s_m.delete_rows(cell.row); await u.message.reply_text(f"🗑 Đã xóa module: {c.args[0]}")
        else: await u.message.reply_text("🔍 Không tìm thấy mã module này.")
    except Exception as e: await u.message.reply_text(f"❌ Lỗi: {e}")

async def broadcast(u: Update, c: ContextTypes.DEFAULT_TYPE):
    if not is_admin(u.effective_user.id):
        await u.message.reply_text("❌ Lệnh này chỉ dành cho admin.")
        return
    if not c.args:
        return

    msg = " ".join(c.args)
    _, s_u, _ = get_sheets()
    users = s_u.col_values(1)[1:]
    count = 0
    for uid_str in users:
        try:
            await c.bot.send_message(chat_id=uid_str, text=f"📢 <b>THÔNG BÁO TỪ ADMIN:</b>\n\n{msg}", parse_mode=ParseMode.HTML)
            count += 1
            await asyncio.sleep(0.05)
        except: pass
    await u.message.reply_text(f"✅ Đã gửi tới {count} người dùng.")

async def handle_callback(u: Update, c: ContextTypes.DEFAULT_TYPE):
    await u.callback_query.answer()
    if u.callback_query.data == "show_list": await send_module_list(u, c)

async def myid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        f"🆔 ID Telegram của bạn là:\n`{update.effective_user.id}`",
        parse_mode=ParseMode.MARKDOWN
    )
async def stats(u: Update, c: ContextTypes.DEFAULT_TYPE):
    if not is_admin(u.effective_user.id):
        await u.message.reply_text("❌ Lệnh này chỉ dành cho admin.")
        return

    try:
        s_m, s_u, s_a = get_sheets()
        total_modules = len(s_m.get_all_records())
        total_users = len(s_u.col_values(1)) - 1
        total_admins = len(s_a.col_values(1)) - 1

        text = (
            "📊 <b>THỐNG KÊ HỆ THỐNG</b>\n\n"
            f"👥 User: <b>{total_users}</b>\n"
            f"📦 Module: <b>{total_modules}</b>\n"
            f"👑 Admin: <b>{total_admins}</b>"
        )
        await u.message.reply_text(text, parse_mode=ParseMode.HTML)
    except Exception as e:
        await u.message.reply_text(f"❌ Lỗi stats: {e}")


async def handle_msg(u: Update, c: ContextTypes.DEFAULT_TYPE):
    await auto_reg(u)

    if not u.message or not u.message.text or not u.message.text.startswith('/'):
        return

    cmd = u.message.text.replace("/", "").lower().split('@')[0]

    if cmd in ["start", "hdsd", "list", "get", "setlink", "delmodule", "broadcast", "stats", "myid"]:
        return
    s_m, _, _ = get_sheets()
    db = {r['key'].lower(): r for r in s_m.get_all_records()}
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
        kb.extend(get_combined_kb().inline_keyboard)
        
        await u.message.reply_text(guide, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(kb))

# --- 5. KHỞI CHẠY WEB SERVICE ---
server = Flask(__name__)
@server.route('/')
def ping(): return "Bot is Live!", 200

async def post_init(app):
    # Cập nhật menu lệnh hiển thị trong ứng dụng Telegram
    await app.bot.set_my_commands([
        BotCommand("start", "Khởi động"),
        BotCommand("list", "Danh sách Module"),
        BotCommand("hdsd", "Hướng dẫn sử dụng")
    ])

if __name__ == "__main__":
    threading.Thread(target=lambda: server.run(host="0.0.0.0", port=PORT), daemon=True).start()
    app = ApplicationBuilder().token(TOKEN).post_init(post_init).build()
    
    # Đưa các lệnh cụ thể lên trước
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("stats", stats))
    app.add_handler(CommandHandler("myid", myid))
    app.add_handler(CommandHandler("hdsd", hdsd))
    app.add_handler(CommandHandler("list", send_module_list))
    app.add_handler(CommandHandler("get", get_bundle))
    app.add_handler(CommandHandler("setlink", set_link))
    app.add_handler(CommandHandler("delmodule", del_mod))
    app.add_handler(CommandHandler("broadcast", broadcast))
    
    app.add_handler(CallbackQueryHandler(handle_callback))
    
    # MessageHandler (bộ lọc tổng quát) luôn để dưới cùng
    app.add_handler(MessageHandler(filters.COMMAND, handle_msg))
    
    app.run_polling(drop_pending_updates=True)
