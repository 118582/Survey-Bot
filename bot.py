# -*- coding: utf-8 -*-
"""
بوت تليجرام لتوزيع المواد الدراسية (PDF وفيديوهات) + لوحة تحكم أدمن
=====================================================================
طريقة العمل (للطلاب):
- /start : يعرض قائمة المواد -> أقسام -> ملفات -> إرسال الملف

طريقة العمل (للأدمن):
- /admin : يفتح لوحة تحكم بأزرار لإضافة/حذف مواد وأقسام وملفات مباشرة
  من داخل تليجرام، بدون الحاجة لتعديل materials.json يدوياً.
- فقط الشخص اللي الـ ID بتاعه مطابق لـ ADMIN_ID يقدر يستخدم /admin.

المتطلبات:
    pip install python-telegram-bot --upgrade
"""

import os
import json
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ConversationHandler,
    ContextTypes,
    filters,
)

# =========================================================
#  1) الإعدادات العامة -- عدّل هنا فقط ما تحتاجه
# =========================================================

# التوكن يُقرأ من متغير بيئة اسمه BOT_TOKEN
BOT_TOKEN = ("8753500776:AAFf3i35j7ReiHae0eFlPH9Fx97-4LQL2Tg")
if not BOT_TOKEN:
    raise ValueError("لم يتم ضبط BOT_TOKEN! أضفه كمتغير بيئة قبل تشغيل البوت.")

# آيدي الأدمن المسموح له فقط باستخدام /admin -- غيّره لو حبيت تضيف أدمن تاني
ADMIN_IDS = [7724699440]

MATERIALS_FILE = "materials.json"
WELCOME_MESSAGE = "أهلاً بك 👋\nاختر المادة التي تريد الوصول لملفاتها:"

# =========================================================
#  2) تحميل وحفظ بيانات المواد
# =========================================================

def load_materials():
    with open(MATERIALS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_materials(materials: dict):
    with open(MATERIALS_FILE, "w", encoding="utf-8") as f:
        json.dump(materials, f, ensure_ascii=False, indent=2)


def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


# =========================================================
#  3) دوال بناء الأزرار (للطلاب)
# =========================================================

def build_subjects_keyboard(materials: dict) -> InlineKeyboardMarkup:
    buttons = []
    for subject_key, subject_data in materials.items():
        buttons.append([InlineKeyboardButton(subject_data["title"], callback_data=f"subj:{subject_key}")])
    return InlineKeyboardMarkup(buttons)


def build_categories_keyboard(materials: dict, subject_key: str) -> InlineKeyboardMarkup:
    subject = materials[subject_key]
    buttons = []
    for cat_key, cat_data in subject["categories"].items():
        buttons.append([InlineKeyboardButton(cat_data["title"], callback_data=f"cat:{subject_key}:{cat_key}")])
    buttons.append([InlineKeyboardButton("⬅️ رجوع للمواد", callback_data="back:main")])
    return InlineKeyboardMarkup(buttons)


def build_files_keyboard(materials: dict, subject_key: str, cat_key: str) -> InlineKeyboardMarkup:
    files = materials[subject_key]["categories"][cat_key]["files"]
    buttons = []
    for idx, file_item in enumerate(files):
        buttons.append([InlineKeyboardButton(file_item["title"], callback_data=f"file:{subject_key}:{cat_key}:{idx}")])
    if not files:
        buttons.append([InlineKeyboardButton("لا توجد ملفات بعد", callback_data="noop")])
    buttons.append([InlineKeyboardButton("⬅️ رجوع", callback_data=f"subj:{subject_key}")])
    return InlineKeyboardMarkup(buttons)


# =========================================================
#  4) معالجات الطلاب (start + الأزرار العادية)
# =========================================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    materials = load_materials()
    await update.message.reply_text(WELCOME_MESSAGE, reply_markup=build_subjects_keyboard(materials))


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    materials = load_materials()
    data = query.data

    if data == "back:main":
        await query.edit_message_text(WELCOME_MESSAGE, reply_markup=build_subjects_keyboard(materials))
        return

    if data == "noop":
        return

    parts = data.split(":")
    action = parts[0]

    if action == "subj":
        subject_key = parts[1]
        subject_title = materials[subject_key]["title"]
        await query.edit_message_text(f"{subject_title}\nاختر القسم:", reply_markup=build_categories_keyboard(materials, subject_key))

    elif action == "cat":
        subject_key, cat_key = parts[1], parts[2]
        cat_title = materials[subject_key]["categories"][cat_key]["title"]
        await query.edit_message_text(f"{cat_title}\nاختر الملف:", reply_markup=build_files_keyboard(materials, subject_key, cat_key))

    elif action == "file":
        subject_key, cat_key, idx = parts[1], parts[2], int(parts[3])
        file_item = materials[subject_key]["categories"][cat_key]["files"][idx]
        file_id = file_item["file_id"]
        file_type = file_item.get("type", "document")
        if file_type == "video":
            await context.bot.send_video(chat_id=query.message.chat_id, video=file_id, caption=file_item["title"])
        else:
            await context.bot.send_document(chat_id=query.message.chat_id, document=file_id, caption=file_item["title"])


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("استخدم /start لعرض قائمة المواد والملفات المتاحة.")


# =========================================================
#  5) لوحة تحكم الأدمن
# =========================================================
# حالات المحادثة (Conversation States)
(
    MENU,
    ADD_SUBJECT_TITLE,
    ADD_SUBJECT_KEY,
    ADD_CAT_PICK_SUBJECT,
    ADD_CAT_TITLE,
    ADD_CAT_KEY,
    ADD_FILE_PICK_SUBJECT,
    ADD_FILE_PICK_CATEGORY,
    ADD_FILE_UPLOAD,
    ADD_FILE_TITLE,
    DEL_FILE_PICK_SUBJECT,
    DEL_FILE_PICK_CATEGORY,
    DEL_FILE_PICK_FILE,
    DEL_SUBJECT_PICK,
) = range(14)


def admin_menu_keyboard() -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton("➕ إضافة مادة", callback_data="admin:add_subject")],
        [InlineKeyboardButton("➕ إضافة قسم لمادة", callback_data="admin:add_cat")],
        [InlineKeyboardButton("➕ إضافة ملف", callback_data="admin:add_file")],
        [InlineKeyboardButton("🗑 حذف ملف", callback_data="admin:del_file")],
        [InlineKeyboardButton("🗑 حذف مادة كاملة", callback_data="admin:del_subject")],
        [InlineKeyboardButton("📋 عرض كل المواد", callback_data="admin:list")],
        [InlineKeyboardButton("❌ إغلاق", callback_data="admin:close")],
    ]
    return InlineKeyboardMarkup(buttons)


def pick_subject_keyboard(materials: dict, prefix: str) -> InlineKeyboardMarkup:
    """لوحة اختيار مادة أثناء عمليات الأدمن. prefix يحدد المرحلة القادمة."""
    buttons = []
    for key, data in materials.items():
        buttons.append([InlineKeyboardButton(data["title"], callback_data=f"{prefix}:{key}")])
    buttons.append([InlineKeyboardButton("❌ إلغاء", callback_data="admin:cancel")])
    return InlineKeyboardMarkup(buttons)


def pick_category_keyboard(materials: dict, subject_key: str, prefix: str) -> InlineKeyboardMarkup:
    buttons = []
    for cat_key, cat_data in materials[subject_key]["categories"].items():
        buttons.append([InlineKeyboardButton(cat_data["title"], callback_data=f"{prefix}:{subject_key}:{cat_key}")])
    buttons.append([InlineKeyboardButton("❌ إلغاء", callback_data="admin:cancel")])
    return InlineKeyboardMarkup(buttons)


def pick_file_keyboard(materials: dict, subject_key: str, cat_key: str) -> InlineKeyboardMarkup:
    buttons = []
    files = materials[subject_key]["categories"][cat_key]["files"]
    for idx, f in enumerate(files):
        buttons.append([InlineKeyboardButton(f["title"], callback_data=f"delf:{subject_key}:{cat_key}:{idx}")])
    buttons.append([InlineKeyboardButton("❌ إلغاء", callback_data="admin:cancel")])
    return InlineKeyboardMarkup(buttons)


# ---- بداية المحادثة: /admin ----
async def admin_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("هذا الأمر مخصص للأدمن فقط.")
        return ConversationHandler.END
    await update.message.reply_text("🔧 لوحة تحكم الأدمن:", reply_markup=admin_menu_keyboard())
    return MENU


# ---- توجيه اختيار القائمة الرئيسية ----
async def admin_menu_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    materials = load_materials()

    if data == "admin:close":
        await query.edit_message_text("تم إغلاق لوحة التحكم.")
        return ConversationHandler.END

    if data == "admin:cancel":
        await query.edit_message_text("🔧 لوحة تحكم الأدمن:", reply_markup=admin_menu_keyboard())
        return MENU

    if data == "admin:list":
        if not materials:
            text = "لا توجد أي مواد بعد."
        else:
            lines = []
            for skey, sdata in materials.items():
                lines.append(f"📚 {sdata['title']}  (key: {skey})")
                for ckey, cdata in sdata["categories"].items():
                    count = len(cdata["files"])
                    lines.append(f"   └ {cdata['title']} (key: {ckey}) — {count} ملف")
            text = "\n".join(lines)
        await query.edit_message_text(text, reply_markup=admin_menu_keyboard())
        return MENU

    if data == "admin:add_subject":
        await query.edit_message_text("اكتب اسم المادة (سيظهر للطلاب)، مثال: المساحة التصويرية")
        return ADD_SUBJECT_TITLE

    if data == "admin:add_cat":
        if not materials:
            await query.edit_message_text("لا توجد مواد بعد، أضف مادة أولاً.", reply_markup=admin_menu_keyboard())
            return MENU
        await query.edit_message_text("اختر المادة التي تريد إضافة قسم لها:", reply_markup=pick_subject_keyboard(materials, "acsub"))
        return ADD_CAT_PICK_SUBJECT

    if data == "admin:add_file":
        if not materials:
            await query.edit_message_text("لا توجد مواد بعد، أضف مادة أولاً.", reply_markup=admin_menu_keyboard())
            return MENU
        await query.edit_message_text("اختر المادة:", reply_markup=pick_subject_keyboard(materials, "afsub"))
        return ADD_FILE_PICK_SUBJECT

    if data == "admin:del_file":
        if not materials:
            await query.edit_message_text("لا توجد مواد بعد.", reply_markup=admin_menu_keyboard())
            return MENU
        await query.edit_message_text("اختر المادة:", reply_markup=pick_subject_keyboard(materials, "dfsub"))
        return DEL_FILE_PICK_SUBJECT

    if data == "admin:del_subject":
        if not materials:
            await query.edit_message_text("لا توجد مواد بعد.", reply_markup=admin_menu_keyboard())
            return MENU
        await query.edit_message_text("اختر المادة التي تريد حذفها بالكامل:", reply_markup=pick_subject_keyboard(materials, "delsub"))
        return DEL_SUBJECT_PICK

    return MENU


# ---- إضافة مادة: استقبال الاسم ثم المفتاح ----
async def add_subject_title(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["new_subject_title"] = update.message.text.strip()
    await update.message.reply_text(
        "اكتب معرّف قصير بالإنجليزي بدون مسافات لهذه المادة (يُستخدم داخلياً فقط)\n"
        "مثال: surveying2"
    )
    return ADD_SUBJECT_KEY


async def add_subject_key(update: Update, context: ContextTypes.DEFAULT_TYPE):
    key = update.message.text.strip().replace(" ", "_")
    materials = load_materials()

    if key in materials:
        await update.message.reply_text("هذا المعرف مستخدم بالفعل، اكتب معرف آخر:")
        return ADD_SUBJECT_KEY

    materials[key] = {
        "title": context.user_data["new_subject_title"],
        "categories": {
            "lectures": {"title": "📄 المحاضرات (PDF)", "files": []},
            "videos": {"title": "🎥 الفيديوهات", "files": []},
        },
    }
    save_materials(materials)

    await update.message.reply_text(
        f"✅ تمت إضافة المادة: {context.user_data['new_subject_title']}\n"
        f"(تم إنشاء قسمين تلقائياً: محاضرات وفيديوهات)",
        reply_markup=admin_menu_keyboard(),
    )
    return MENU


# ---- إضافة قسم لمادة موجودة ----
async def add_cat_pick_subject(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    subject_key = query.data.split(":")[1]
    context.user_data["target_subject"] = subject_key
    await query.edit_message_text("اكتب اسم القسم الجديد (سيظهر للطلاب)، مثال: 🧪 تمارين محلولة")
    return ADD_CAT_TITLE


async def add_cat_title(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["new_cat_title"] = update.message.text.strip()
    await update.message.reply_text("اكتب معرّف قصير بالإنجليزي لهذا القسم، مثال: exercises")
    return ADD_CAT_KEY


async def add_cat_key(update: Update, context: ContextTypes.DEFAULT_TYPE):
    key = update.message.text.strip().replace(" ", "_")
    subject_key = context.user_data["target_subject"]
    materials = load_materials()

    if key in materials[subject_key]["categories"]:
        await update.message.reply_text("هذا المعرف مستخدم بالفعل داخل هذه المادة، اكتب معرف آخر:")
        return ADD_CAT_KEY

    materials[subject_key]["categories"][key] = {"title": context.user_data["new_cat_title"], "files": []}
    save_materials(materials)

    await update.message.reply_text("✅ تمت إضافة القسم بنجاح.", reply_markup=admin_menu_keyboard())
    return MENU


# ---- إضافة ملف: اختيار مادة -> قسم -> رفع الملف -> اسم الملف ----
async def add_file_pick_subject(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    subject_key = query.data.split(":")[1]
    materials = load_materials()
    context.user_data["target_subject"] = subject_key
    await query.edit_message_text("اختر القسم:", reply_markup=pick_category_keyboard(materials, subject_key, "afcat"))
    return ADD_FILE_PICK_CATEGORY


async def add_file_pick_category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    _, subject_key, cat_key = query.data.split(":")
    context.user_data["target_subject"] = subject_key
    context.user_data["target_category"] = cat_key
    await query.edit_message_text("📎 دلوقتي ابعت ملف الـ PDF أو الفيديو اللي عايز تضيفه.")
    return ADD_FILE_UPLOAD


async def add_file_upload(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    if message.document:
        context.user_data["new_file_id"] = message.document.file_id
        context.user_data["new_file_type"] = "document"
    elif message.video:
        context.user_data["new_file_id"] = message.video.file_id
        context.user_data["new_file_type"] = "video"
    else:
        await message.reply_text("من فضلك ابعت ملف PDF أو فيديو فقط.")
        return ADD_FILE_UPLOAD

    await message.reply_text("اكتب اسم/عنوان الملف اللي هيظهر للطلاب، مثال: المحاضرة 3 - الأخطاء المساحية")
    return ADD_FILE_TITLE


async def add_file_title(update: Update, context: ContextTypes.DEFAULT_TYPE):
    title = update.message.text.strip()
    subject_key = context.user_data["target_subject"]
    cat_key = context.user_data["target_category"]

    materials = load_materials()
    materials[subject_key]["categories"][cat_key]["files"].append(
        {
            "title": title,
            "file_id": context.user_data["new_file_id"],
            "type": context.user_data["new_file_type"],
        }
    )
    save_materials(materials)

    await update.message.reply_text(f"✅ تمت إضافة الملف: {title}", reply_markup=admin_menu_keyboard())
    return MENU


# ---- حذف ملف: اختيار مادة -> قسم -> ملف ----
async def del_file_pick_subject(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    subject_key = query.data.split(":")[1]
    materials = load_materials()
    await query.edit_message_text("اختر القسم:", reply_markup=pick_category_keyboard(materials, subject_key, "dfcat"))
    return DEL_FILE_PICK_CATEGORY


async def del_file_pick_category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    _, subject_key, cat_key = query.data.split(":")
    materials = load_materials()
    await query.edit_message_text("اختر الملف اللي عايز تحذفه:", reply_markup=pick_file_keyboard(materials, subject_key, cat_key))
    return DEL_FILE_PICK_FILE


async def del_file_pick_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    _, subject_key, cat_key, idx = query.data.split(":")
    idx = int(idx)

    materials = load_materials()
    removed = materials[subject_key]["categories"][cat_key]["files"].pop(idx)
    save_materials(materials)

    await query.edit_message_text(f"🗑 تم حذف الملف: {removed['title']}", reply_markup=admin_menu_keyboard())
    return MENU


# ---- حذف مادة كاملة ----
async def del_subject_pick(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    subject_key = query.data.split(":")[1]

    materials = load_materials()
    removed = materials.pop(subject_key)
    save_materials(materials)

    await query.edit_message_text(f"🗑 تم حذف المادة بالكامل: {removed['title']}", reply_markup=admin_menu_keyboard())
    return MENU


async def admin_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("تم الإلغاء.", reply_markup=admin_menu_keyboard())
    return MENU


# =========================================================
#  6) تشغيل البوت
# =========================================================

def main():
    logging.basicConfig(level=logging.INFO)
    app = Application.builder().token(BOT_TOKEN).build()

    # أوامر الطلاب
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))

    # محادثة الأدمن
    admin_conv = ConversationHandler(
        entry_points=[CommandHandler("admin", admin_start)],
        states={
            MENU: [CallbackQueryHandler(admin_menu_router, pattern="^admin:")],
            ADD_SUBJECT_TITLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_subject_title)],
            ADD_SUBJECT_KEY: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_subject_key)],
            ADD_CAT_PICK_SUBJECT: [CallbackQueryHandler(add_cat_pick_subject, pattern="^acsub:")],
            ADD_CAT_TITLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_cat_title)],
            ADD_CAT_KEY: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_cat_key)],
            ADD_FILE_PICK_SUBJECT: [CallbackQueryHandler(add_file_pick_subject, pattern="^afsub:")],
            ADD_FILE_PICK_CATEGORY: [CallbackQueryHandler(add_file_pick_category, pattern="^afcat:")],
            ADD_FILE_UPLOAD: [MessageHandler(filters.Document.ALL | filters.VIDEO, add_file_upload)],
            ADD_FILE_TITLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_file_title)],
            DEL_FILE_PICK_SUBJECT: [CallbackQueryHandler(del_file_pick_subject, pattern="^dfsub:")],
            DEL_FILE_PICK_CATEGORY: [CallbackQueryHandler(del_file_pick_category, pattern="^dfcat:")],
            DEL_FILE_PICK_FILE: [CallbackQueryHandler(del_file_pick_file, pattern="^delf:")],
            DEL_SUBJECT_PICK: [CallbackQueryHandler(del_subject_pick, pattern="^delsub:")],
        },
        fallbacks=[CommandHandler("cancel", admin_cancel), CallbackQueryHandler(admin_menu_router, pattern="^admin:")],
    )
    app.add_handler(admin_conv)

    # أزرار الطلاب العادية (لازم تكون بعد محادثة الأدمن)
    app.add_handler(CallbackQueryHandler(button_handler))

    print("✅ البوت يعمل الآن...")
    app.run_polling()


if __name__ == "__main__":
    main()
