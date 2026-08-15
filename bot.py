# -*- coding: utf-8 -*-
"""
بوت تليجرام لتوزيع المواد الدراسية (PDF وفيديوهات)
====================================================
طريقة العمل:
- كل المواد والملفات معرّفة في ملف materials.json
- البوت يعرض قائمة المواد -> يعرض فئات المادة (محاضرات / فيديوهات) -> يعرض الملفات -> يرسل الملف

للتعديل والإضافة:
- لإضافة مادة جديدة أو ملف جديد: عدّل ملف materials.json فقط، لا تحتاج تلمس هذا الكود إطلاقاً.
- لمعرفة file_id لأي ملف: استخدم سكربت get_file_id.py المرفق.

المتطلبات:
    pip install python-telegram-bot --upgrade
"""

import os
import json
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# =========================================================
#  1) الإعدادات العامة -- عدّل هنا فقط ما تحتاجه
# =========================================================

# التوكن يُقرأ من متغير بيئة اسمه BOT_TOKEN (يُضبط من إعدادات الاستضافة / Variables)
# للتجربة على جهازك فقط، يمكنك مؤقتاً استبدال السطر بـ: BOT_TOKEN = "التوكن هنا"
BOT_TOKEN = os.environ.get("BOT_TOKEN")

if not BOT_TOKEN:
    raise ValueError("لم يتم ضبط BOT_TOKEN! أضفه كمتغير بيئة قبل تشغيل البوت.")

# اسم ملف الإعدادات الذي يحتوي على المواد والملفات
MATERIALS_FILE = "materials.json"

# رسالة الترحيب التي تظهر عند /start
WELCOME_MESSAGE = "أهلاً بك 👋\nاختر المادة التي تريد الوصول لملفاتها:"

# =========================================================
#  2) تحميل بيانات المواد من ملف JSON
# =========================================================

def load_materials():
    """تحميل بيانات المواد من ملف materials.json في كل مرة (حتى تنعكس أي تعديلات فوراً بدون إعادة تشغيل)."""
    with open(MATERIALS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


# =========================================================
#  3) دوال بناء الأزرار (Keyboards)
# =========================================================

def build_subjects_keyboard(materials: dict) -> InlineKeyboardMarkup:
    """بناء قائمة أزرار المواد الرئيسية."""
    buttons = []
    for subject_key, subject_data in materials.items():
        buttons.append(
            [InlineKeyboardButton(subject_data["title"], callback_data=f"subj:{subject_key}")]
        )
    return InlineKeyboardMarkup(buttons)


def build_categories_keyboard(materials: dict, subject_key: str) -> InlineKeyboardMarkup:
    """بناء قائمة أزرار فئات مادة معينة (محاضرات / فيديوهات ...)."""
    subject = materials[subject_key]
    buttons = []
    for cat_key, cat_data in subject["categories"].items():
        buttons.append(
            [InlineKeyboardButton(cat_data["title"], callback_data=f"cat:{subject_key}:{cat_key}")]
        )
    # زر رجوع للقائمة الرئيسية
    buttons.append([InlineKeyboardButton("⬅️ رجوع للمواد", callback_data="back:main")])
    return InlineKeyboardMarkup(buttons)


def build_files_keyboard(materials: dict, subject_key: str, cat_key: str) -> InlineKeyboardMarkup:
    """بناء قائمة أزرار الملفات داخل فئة معينة."""
    files = materials[subject_key]["categories"][cat_key]["files"]
    buttons = []
    for idx, file_item in enumerate(files):
        buttons.append(
            [InlineKeyboardButton(file_item["title"], callback_data=f"file:{subject_key}:{cat_key}:{idx}")]
        )
    if not files:
        buttons.append([InlineKeyboardButton("لا توجد ملفات بعد", callback_data="noop")])
    # زر رجوع لفئات نفس المادة
    buttons.append([InlineKeyboardButton("⬅️ رجوع", callback_data=f"subj:{subject_key}")])
    return InlineKeyboardMarkup(buttons)


# =========================================================
#  4) معالجات الأوامر والأزرار (Handlers)
# =========================================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """أمر /start : يعرض قائمة المواد."""
    materials = load_materials()
    await update.message.reply_text(
        WELCOME_MESSAGE,
        reply_markup=build_subjects_keyboard(materials),
    )


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالج ضغطات الأزرار، يفسر callback_data ويقرر ماذا يعرض."""
    query = update.callback_query
    await query.answer()  # مهم لإخفاء علامة التحميل في تليجرام

    materials = load_materials()
    data = query.data

    # الرجوع للقائمة الرئيسية للمواد
    if data == "back:main":
        await query.edit_message_text(
            WELCOME_MESSAGE,
            reply_markup=build_subjects_keyboard(materials),
        )
        return

    # زر بدون فعل (عند عدم وجود ملفات)
    if data == "noop":
        return

    parts = data.split(":")
    action = parts[0]

    # ---- عرض فئات مادة معينة ----
    if action == "subj":
        subject_key = parts[1]
        subject_title = materials[subject_key]["title"]
        await query.edit_message_text(
            f"{subject_title}\nاختر القسم:",
            reply_markup=build_categories_keyboard(materials, subject_key),
        )

    # ---- عرض ملفات فئة معينة ----
    elif action == "cat":
        subject_key, cat_key = parts[1], parts[2]
        cat_title = materials[subject_key]["categories"][cat_key]["title"]
        await query.edit_message_text(
            f"{cat_title}\nاختر الملف:",
            reply_markup=build_files_keyboard(materials, subject_key, cat_key),
        )

    # ---- إرسال الملف المطلوب ----
    elif action == "file":
        subject_key, cat_key, idx = parts[1], parts[2], int(parts[3])
        file_item = materials[subject_key]["categories"][cat_key]["files"][idx]
        file_id = file_item["file_id"]
        file_type = file_item.get("type", "document")

        # إرسال حسب نوع الملف
        if file_type == "video":
            await context.bot.send_video(chat_id=query.message.chat_id, video=file_id, caption=file_item["title"])
        else:
            await context.bot.send_document(chat_id=query.message.chat_id, document=file_id, caption=file_item["title"])


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """أمر /help : شرح مختصر."""
    await update.message.reply_text(
        "استخدم /start لعرض قائمة المواد والملفات المتاحة."
    )


# =========================================================
#  5) تشغيل البوت
# =========================================================

def main():
    logging.basicConfig(level=logging.INFO)

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CallbackQueryHandler(button_handler))

    print("✅ البوت يعمل الآن...")
    app.run_polling()


if __name__ == "__main__":
    main()
