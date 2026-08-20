# -*- coding: utf-8 -*-
"""
=====================================================================================
   🏆 بوت المساحة الأسطوري - النسخة الذهبية 🏆
=====================================================================================
المميزات الجديدة:
- زخرفة موحدة بأسلوب احترافي (• ⟬ ⟭ •، ⌯، ✬︙)
- قسم الكتب الدراسية (Study Books)
- قسم المساح العام (10+ أقسام)
- دعم الروابط بدلاً من رفع الملفات
- كويز يدعم الصور عبر الروابط
- نظام صلاحيات متقدم للأدمنية
- لوحة أدمن مقسمة لأقسام فرعية
- زر الأدمن يظهر للكل مع صلاحيات
- زر رجوع بدلاً من إغلاق المحادثة
- تمارين محلولة بدلاً من الشرح
=====================================================================================
"""

import os
import sys
import json
import random
import shutil
import py_compile
import logging
import zipfile
import io
from datetime import datetime
from typing import Dict, List, Optional, Any

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

# =====================================================================================
#  1) الإعدادات العامة
# =====================================================================================

BOT_TOKEN = "8753500776:AAFf3i35j7ReiHae0eFlPH9Fx97-4LQL2Tg"

# الأدمنية الافتراضية (سيتم تخزين الصلاحيات في admins.json)
DEFAULT_ADMINS = {
    "7724699440": "full_access",
    "6004659847": "full_access",
}

# قنوات الاشتراك الإجباري
REQUIRED_CHANNELS = [
    {"name": "اكسيز للمساحة", "username": "@axissurveying"},
    {"name": "تحديثات بوت اكسيز", "username": "@axis_updates"},
    {"name": "سنة تانية مساحة", "username": "@part2_survey"},
    {"name": "سنة تانية ري", "username": "@part2_leveling"},
    {"name": "اكسيز شات", "chat_id": -1003257254001, "invite_link": "https://t.me/+xnCCq2g-kxtmZWI8"},
]

# الملفات
MATERIALS_FILE = "materials.json"
USERS_FILE = "users.json"
CUSTOM_BUTTONS_FILE = "custom_buttons.json"
TIPS_FILE = "tips.json"
QUIZ_FILE = "quiz.json"
MENU_LABELS_FILE = "menu_labels.json"
INSTRUMENTS_FILE = "instruments.json"
TOOLS_FILE = "tools.json"
STUDY_BOOKS_FILE = "study_books.json"
ADMINS_FILE = "admins.json"
GENERAL_SURVEY_FILE = "general_survey.json"
LINKS_FILE = "links.json"

ALLOWED_UPLOAD_FILES = [
    "bot.py", "requirements.txt", "Procfile",
    "materials.json", "custom_buttons.json", "tips.json", "quiz.json", "users.json",
    "instruments.json", "tools.json", "menu_labels.json",
    "study_books.json", "admins.json", "general_survey.json", "links.json",
]

ALLOWED_RESET_FILES = [
    "materials.json", "custom_buttons.json", "tips.json", "quiz.json", "users.json",
    "instruments.json", "tools.json", "menu_labels.json",
    "study_books.json", "admins.json", "general_survey.json", "links.json",
]

# توزيع الأزرار
MAIN_MENU_LAYOUT = [1, 2, 1, 2, 1, 2, 1, 1]
SUBJECTS_MENU_LAYOUT = [2, 1, 2, 1, 2, 1, 2, 1]

# =====================================================================================
#  2) النصوص مع الزخرفة الجديدة
# =====================================================================================

def format_arabic_separator(text: str = "") -> str:
    """إنشاء فاصل عربي بطول مناسب للنص"""
    base = "ـ• ┉ • ┉ • ┉ • ┉ • ┉ •"
    if len(text) > 20:
        return base + " ┉ • ┉ • ┉ •"
    return base

def format_english_separator(text: str = "") -> str:
    """إنشاء فاصل إنجليزي بطول مناسب للنص"""
    base = "• ┉ • ┉ • ┉ • ┉ • ┉ •"
    if len(text) > 20:
        return base + " ┉ • ┉ • ┉ •"
    return base

TEXTS = {
    "ar": {
        "header": "",
        "footer": "",
        "separator": "ـ• ┉ • ┉ • ┉ • ┉ • ┉ •",
        "separator_long": "ـ• ┉ • ┉ • ┉ • ┉ • ┉ • ┉ • ┉ • ┉ • ┉ •",
        "welcome": "✬︙ مرحباً بك في بوت المساحة الأسطوري ✬︙\nـ• ┉ • ┉ • ┉ • ┉ • ┉ •\n⌯ اختر أحد الأقسام التالية:",
        "materials_section": "• ⟬ 📘 المواد الدراسية ⟭ •",
        "study_books_section": "• ⟬ 📚 الكتب الدراسية ⟭ •",
        "general_survey_section": "• ⟬ 🧭 المساح العام ⟭ •",
        "instruments_section": "• ⟬ 🔭 الأجهزة المساحية ⟭ •",
        "tools_section": "• ⟬ 🧰 الأدوات المساحية ⟭ •",
        "tip_section": "• ⟬ 💡 معلومات مساحية ⟭ •",
        "quiz_section": "• ⟬ 🎯 اختبـر نفسك ⟭ •",
        "language_section": "• ⟬ 🌐 تغيير اللغة ⟭ •",
        "admin_section": "• ⟬ ⚙️ لوحة الأدمن ⟭ •",
        "choose_subject": "⌯ اختر المادة 📖",
        "choose_category": "⌯ اختر القسم 📂",
        "choose_file": "⌯ اختر الملف 📄",
        "choose_book": "⌯ اختر الكتاب 📚",
        "choose_general_section": "⌯ اختر القسم 🧭",
        "back": "• ⟬ 🔙 رجوع ⟭ •",
        "back_main_menu": "• ⟬ 🏠 القائمة الرئيسية ⟭ •",
        "no_files": "⌯ لا توجد ملفات بعد ❌",
        "no_books": "⌯ لا توجد كتب بعد ❌",
        "no_general_sections": "⌯ لا توجد أقسام بعد ❌",
        "still_not_subscribed": "⌯ لسه مش مشترك في كل القنوات! اشترك أولاً ثم اضغط تحقق ❌",
        "not_admin": "⌯ عذراً، هذا القسم خاص بالأدمنية فقط ⛔",
        "exercises_section": "• ⟬ 📝 تمارين محلولة ⟭ •",
        "choose_quiz_subject": "🎯 اختر المادة اللي عايز تختبر نفسك فيها:",
        "no_quiz_for_subject": "⌯ لا توجد أسئلة على المادة دي لسه ❌",
        "quiz_correct": "✅ إجابة صحيحة! 🎉",
        "quiz_wrong": "❌ إجابة خاطئة. حاول مرة أخرى!",
        "general_survey_welcome": "🧭 مرحباً بك في قسم المساح العام\nهنا ستجد كل ما يفيد المساحين:",
        "admin_panel_header": "✬︙ لوحة تحكم الأدمن ✬︙\nـ• ┉ • ┉ • ┉ • ┉ • ┉ •",
        "admin_menu_materials": "• ⟬ 📘 إدارة المواد الدراسية ⟭ •",
        "admin_menu_books": "• ⟬ 📚 إدارة الكتب الدراسية ⟭ •",
        "admin_menu_general": "• ⟬ 🧭 إدارة المساح العام ⟭ •",
        "admin_menu_admins": "• ⟬ 👥 إدارة الأدمنية ⟭ •",
        "admin_menu_broadcast": "• ⟬ 📢 الإذاعة ⟭ •",
        "admin_menu_settings": "• ⟬ ⚙️ إعدادات البوت ⟭ •",
        "admin_menu_backup": "• ⟬ 📦 نسخ احتياطي وتصفير ⟭ •",
        "admin_menu_close": "• ⟬ 🔙 رجوع للقائمة الرئيسية ⟭ •",
        "no_tips": "⌯ لا توجد معلومات مضافة بعد.",
        "no_quiz": "⌯ لا توجد أسئلة مضافة بعد.",
        "no_instruments": "⌯ لا توجد أجهزة مضافة بعد.",
        "no_tools": "⌯ لا توجد أدوات مضافة بعد.",
        "choose_instrument": "⌯ اختر الجهاز:",
        "choose_tool": "⌯ اختر الأداة:",
    },
    "en": {
        "header": "",
        "footer": "",
        "separator": "• ┉ • ┉ • ┉ • ┉ • ┉ •",
        "separator_long": "• ┉ • ┉ • ┉ • ┉ • ┉ • ┉ • ┉ • ┉ • ┉ •",
        "welcome": "✬︙ Welcome to the Legendary Surveying Bot ✬︙\n• ┉ • ┉ • ┉ • ┉ • ┉ •\n⌯ Choose a section:",
        "materials_section": "• ⟬ 📘 Study Materials ⟭ •",
        "study_books_section": "• ⟬ 📚 Study Books ⟭ •",
        "general_survey_section": "• ⟬ 🧭 General Surveying ⟭ •",
        "instruments_section": "• ⟬ 🔭 Instruments ⟭ •",
        "tools_section": "• ⟬ 🧰 Tools ⟭ •",
        "tip_section": "• ⟬ 💡 Surveying Tips ⟭ •",
        "quiz_section": "• ⟬ 🎯 Test Yourself ⟭ •",
        "language_section": "• ⟬ 🌐 Change Language ⟭ •",
        "admin_section": "• ⟬ ⚙️ Admin Panel ⟭ •",
        "choose_subject": "⌯ Choose a subject 📖",
        "choose_category": "⌯ Choose a section 📂",
        "choose_file": "⌯ Choose a file 📄",
        "choose_book": "⌯ Choose a book 📚",
        "choose_general_section": "⌯ Choose a section 🧭",
        "back": "• ⟬ 🔙 Back ⟭ •",
        "back_main_menu": "• ⟬ 🏠 Main Menu ⟭ •",
        "no_files": "⌯ No files yet ❌",
        "no_books": "⌯ No books yet ❌",
        "no_general_sections": "⌯ No sections yet ❌",
        "still_not_subscribed": "⌯ You're not subscribed to all channels yet! Join then press check ❌",
        "not_admin": "⌯ Sorry, this section is for admins only ⛔",
        "exercises_section": "• ⟬ 📝 Solved Exercises ⟭ •",
        "choose_quiz_subject": "🎯 Choose the subject to test yourself on:",
        "no_quiz_for_subject": "⌯ No questions for this subject yet ❌",
        "quiz_correct": "✅ Correct! 🎉",
        "quiz_wrong": "❌ Wrong. Try again!",
        "general_survey_welcome": "🧭 Welcome to General Surveying\nHere you'll find everything for surveyors:",
        "admin_panel_header": "✬︙ Admin Panel ✬︙\n• ┉ • ┉ • ┉ • ┉ • ┉ •",
        "admin_menu_materials": "• ⟬ 📘 Manage Study Materials ⟭ •",
        "admin_menu_books": "• ⟬ 📚 Manage Study Books ⟭ •",
        "admin_menu_general": "• ⟬ 🧭 Manage General Surveying ⟭ •",
        "admin_menu_admins": "• ⟬ 👥 Manage Admins ⟭ •",
        "admin_menu_broadcast": "• ⟬ 📢 Broadcast ⟭ •",
        "admin_menu_settings": "• ⟬ ⚙️ Bot Settings ⟭ •",
        "admin_menu_backup": "• ⟬ 📦 Backup & Reset ⟭ •",
        "admin_menu_close": "• ⟬ 🔙 Back to Main Menu ⟭ •",
        "no_tips": "⌯ No tips added yet.",
        "no_quiz": "⌯ No quiz questions added yet.",
        "no_instruments": "⌯ No instruments added yet.",
        "no_tools": "⌯ No tools added yet.",
        "choose_instrument": "⌯ Choose an instrument:",
        "choose_tool": "⌯ Choose a tool:",
    },
}

SUBSCRIBE_MESSAGE = (
    "✬︙ مرحباً بك عزيزي 👁‍🗨 ✬︙\n"
    "ـ• ┉ • ┉ • ┉ • ┉ • ┉ •\n"
    "⌯ لا يمكنك استخدام البوت قبل الاشتراك في القنوات التالية:\n"
    "⌯ بعد الاشتراك، اضغط على الزر أدناه لتأكيد الاشتراك."
)
CHECK_SUB_BUTTON_TEXT = "• ⟬ ✅ تأكيد الاشتراك ⟭ •"
CHOOSE_LANGUAGE_TEXT = (
    "✬︙ اختر لغة البوت ✬︙\n"
    "ـ• ┉ • ┉ • ┉ • ┉ • ┉ •\n"
    "⌯ Choose your bot language"
)

# =====================================================================================
#  3) دوال التحميل/الحفظ
# =====================================================================================

def _load_json(path: str, default):
    if not os.path.exists(path):
        return default
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def _save_json(path: str, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def load_materials() -> dict:
    return _load_json(MATERIALS_FILE, {})

def save_materials(materials: dict):
    _save_json(MATERIALS_FILE, materials)

def load_users() -> dict:
    return _load_json(USERS_FILE, {})

def save_users(users: dict):
    _save_json(USERS_FILE, users)

def load_custom_buttons() -> dict:
    return _load_json(CUSTOM_BUTTONS_FILE, {})

def save_custom_buttons(data: dict):
    _save_json(CUSTOM_BUTTONS_FILE, data)

def load_tips() -> list:
    return _load_json(TIPS_FILE, [])

def save_tips(data: list):
    _save_json(TIPS_FILE, data)

def load_quiz() -> dict:
    return _load_json(QUIZ_FILE, {})

def save_quiz(data: dict):
    _save_json(QUIZ_FILE, data)

def load_menu_labels() -> dict:
    return _load_json(MENU_LABELS_FILE, {})

def save_menu_labels(data: dict):
    _save_json(MENU_LABELS_FILE, data)

def load_instruments() -> list:
    return _load_json(INSTRUMENTS_FILE, [])

def save_instruments(data: list):
    _save_json(INSTRUMENTS_FILE, data)

def load_tools() -> list:
    return _load_json(TOOLS_FILE, [])

def save_tools(data: list):
    _save_json(TOOLS_FILE, data)

def load_study_books() -> dict:
    return _load_json(STUDY_BOOKS_FILE, {})

def save_study_books(data: dict):
    _save_json(STUDY_BOOKS_FILE, data)

def load_admins() -> dict:
    return _load_json(ADMINS_FILE, DEFAULT_ADMINS.copy())

def save_admins(data: dict):
    _save_json(ADMINS_FILE, data)

def load_general_survey() -> dict:
    return _load_json(GENERAL_SURVEY_FILE, {})

def save_general_survey(data: dict):
    _save_json(GENERAL_SURVEY_FILE, data)

def load_links() -> dict:
    return _load_json(LINKS_FILE, {})

def save_links(data: dict):
    _save_json(LINKS_FILE, data)

# =====================================================================================
#  4) دوال المساعدة العامة
# =====================================================================================

def t(obj: dict, lang: str, field: str = "title") -> str:
    """استخراج النص حسب اللغة"""
    return obj.get(f"{field}_{lang}") or obj.get(f"{field}_ar") or obj.get(f"{field}_en") or ""

def is_admin(user_id: int) -> bool:
    admins = load_admins()
    return str(user_id) in admins

def has_permission(user_id: int, permission: str) -> bool:
    admins = load_admins()
    uid = str(user_id)
    if uid not in admins:
        return False
    role = admins[uid]
    if role == "full_access":
        return True
    return role == permission

def register_user(user):
    users = load_users()
    uid = str(user.id)
    if uid not in users:
        users[uid] = {"lang": None, "name": user.full_name, "username": user.username}
    else:
        users[uid]["name"] = user.full_name
        users[uid]["username"] = user.username
    save_users(users)

def get_user_lang(user_id: int):
    users = load_users()
    entry = users.get(str(user_id))
    if entry and entry.get("lang"):
        return entry["lang"]
    return None

def set_user_lang(user_id: int, lang: str):
    users = load_users()
    uid = str(user_id)
    if uid not in users:
        users[uid] = {}
    users[uid]["lang"] = lang
    save_users(users)

def arrange_buttons(button_objs: list, layout: list) -> list:
    """توزيع الأزرار حسب التخطيط"""
    rows = []
    i = 0
    li = 0
    while i < len(button_objs):
        count = layout[li] if li < len(layout) else 1
        rows.append(button_objs[i:i + count])
        i += count
        li += 1
    return rows

def core_label(key: str, lang: str) -> str:
    overrides = load_menu_labels()
    if key in overrides:
        return t(overrides[key], lang)
    return TEXTS[lang][key]

def is_hidden(key: str) -> bool:
    labels = load_menu_labels()
    return labels.get(key, {}).get("hidden", False)

# =====================================================================================
#  5) الاشتراك الإجباري
# =====================================================================================

async def is_subscribed(user_id: int, context: ContextTypes.DEFAULT_TYPE) -> bool:
    if not REQUIRED_CHANNELS:
        return True
    for channel in REQUIRED_CHANNELS:
        identifier = channel.get("chat_id") or channel.get("username")
        if not identifier:
            continue
        try:
            member = await context.bot.get_chat_member(identifier, user_id)
            if member.status not in ("member", "administrator", "creator"):
                return False
        except Exception:
            return False
    return True

def subscribe_keyboard() -> InlineKeyboardMarkup:
    buttons = []
    for channel in REQUIRED_CHANNELS:
        link = channel.get("invite_link") or f"https://t.me/{channel.get('username','').lstrip('@')}"
        buttons.append([InlineKeyboardButton(f"📢 {channel['name']}", url=link)])
    buttons.append([InlineKeyboardButton(CHECK_SUB_BUTTON_TEXT, callback_data="check_sub")])
    return InlineKeyboardMarkup(buttons)

def language_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🇸🇦 العربية", callback_data="lang:ar"),
         InlineKeyboardButton("🇬🇧 English", callback_data="lang:en")]
    ])

# =====================================================================================
#  6) دوال إرسال الملفات والروابط
# =====================================================================================

async def send_file_or_link(bot, chat_id: int, file_id: str = None, file_url: str = None,
                            file_type: str = "document", caption: str = None):
    if file_url:
        text = f"{caption}\n\n🔗 [اضغط هنا لتحميل الملف]({file_url})" if caption else f"🔗 [تحميل الملف]({file_url})"
        await bot.send_message(chat_id=chat_id, text=text, parse_mode="Markdown", disable_web_page_preview=True)
        return

    if file_type == "video":
        await bot.send_video(chat_id=chat_id, video=file_id, caption=caption)
    elif file_type == "photo":
        await bot.send_photo(chat_id=chat_id, photo=file_id, caption=caption)
    elif file_type == "audio":
        await bot.send_audio(chat_id=chat_id, audio=file_id, caption=caption)
    elif file_type == "voice":
        await bot.send_voice(chat_id=chat_id, voice=file_id, caption=caption)
    elif file_type == "animation":
        await bot.send_animation(chat_id=chat_id, animation=file_id, caption=caption)
    else:
        await bot.send_document(chat_id=chat_id, document=file_id, caption=caption)

def detect_uploaded_file(message):
    if message.document:
        return message.document.file_id, "document"
    if message.video:
        return message.video.file_id, "video"
    if message.photo:
        return message.photo[-1].file_id, "photo"
    if message.audio:
        return message.audio.file_id, "audio"
    if message.voice:
        return message.voice.file_id, "voice"
    if message.animation:
        return message.animation.file_id, "animation"
    return None, None

# =====================================================================================
#  7) بناء لوحات المفاتيح
# =====================================================================================

def build_main_menu(user_id: int, lang: str) -> InlineKeyboardMarkup:
    labels = load_menu_labels()
    
    def is_hidden_key(key):
        return labels.get(key, {}).get("hidden", False)
    
    items = []
    core_keys = [
        "materials_section",
        "study_books_section",
        "general_survey_section",
        "instruments_section",
        "tools_section",
        "tip_section",
        "quiz_section",
        "language_section",
        "admin_section",
    ]
    
    for key in core_keys:
        if not is_hidden_key(key):
            label = TEXTS[lang][key]
            items.append((label, f"menu:{key.replace('_section', '')}"))
    
    custom_buttons = load_custom_buttons()
    for key, btn in custom_buttons.items():
        if not btn.get("hidden", False):
            label = f"• ⟬ {t(btn, lang)} ⟭ •"
            items.append((label, f"custom:{key}"))
    
    buttons = [InlineKeyboardButton(label, callback_data=cb) for label, cb in items]
    rows = arrange_buttons(buttons, MAIN_MENU_LAYOUT)
    return InlineKeyboardMarkup(rows)

def build_subjects_keyboard(materials: dict, lang: str, prefix: str = "subj") -> InlineKeyboardMarkup:
    buttons = [InlineKeyboardButton(t(s, lang), callback_data=f"{prefix}:{key}") for key, s in materials.items()]
    rows = arrange_buttons(buttons, SUBJECTS_MENU_LAYOUT)
    rows.append([InlineKeyboardButton(TEXTS[lang]["back_main_menu"], callback_data="back:menu")])
    return InlineKeyboardMarkup(rows)

def build_categories_keyboard(materials: dict, subject_key: str, lang: str, prefix: str = "cat") -> InlineKeyboardMarkup:
    subject = materials[subject_key]
    buttons = []
    for ckey in ["summaries", "videos", "exercises"]:
        if ckey in subject["categories"]:
            cat = subject["categories"][ckey]
            buttons.append([InlineKeyboardButton(t(cat, lang), callback_data=f"{prefix}:{subject_key}:{ckey}")])
    buttons.append([InlineKeyboardButton(TEXTS[lang]["back"], callback_data="menu:materials")])
    return InlineKeyboardMarkup(buttons)

def build_files_keyboard(materials: dict, subject_key: str, cat_key: str, lang: str) -> InlineKeyboardMarkup:
    files = materials[subject_key]["categories"][cat_key]["files"]
    buttons = [[InlineKeyboardButton(t(f, lang), callback_data=f"file:{subject_key}:{cat_key}:{idx}")] for idx, f in enumerate(files)]
    if not files:
        buttons.append([InlineKeyboardButton(TEXTS[lang]["no_files"], callback_data="noop")])
    buttons.append([InlineKeyboardButton(TEXTS[lang]["back"], callback_data=f"subj:{subject_key}")])
    return InlineKeyboardMarkup(buttons)

def build_study_books_keyboard(books_data: dict, lang: str) -> InlineKeyboardMarkup:
    buttons = [InlineKeyboardButton(t(s, lang), callback_data=f"books_subj:{key}") for key, s in books_data.items()]
    rows = arrange_buttons(buttons, SUBJECTS_MENU_LAYOUT)
    rows.append([InlineKeyboardButton(TEXTS[lang]["back_main_menu"], callback_data="back:menu")])
    return InlineKeyboardMarkup(rows)

def build_books_list_keyboard(books_data: dict, subject_key: str, lang: str) -> InlineKeyboardMarkup:
    subject = books_data[subject_key]
    books = subject.get("books", [])
    buttons = [[InlineKeyboardButton(t(b, lang), callback_data=f"book:{subject_key}:{idx}")] for idx, b in enumerate(books)]
    if not books:
        buttons.append([InlineKeyboardButton(TEXTS[lang]["no_books"], callback_data="noop")])
    buttons.append([InlineKeyboardButton(TEXTS[lang]["back"], callback_data="menu:study_books")])
    return InlineKeyboardMarkup(buttons)

def build_general_survey_keyboard(survey_data: dict, lang: str) -> InlineKeyboardMarkup:
    buttons = []
    for key, section in survey_data.items():
        if not section.get("hidden", False):
            buttons.append([InlineKeyboardButton(f"{section.get('icon', '📌')} {t(section, lang)}", callback_data=f"gen:{key}")])
    buttons.append([InlineKeyboardButton(TEXTS[lang]["back_main_menu"], callback_data="back:menu")])
    return InlineKeyboardMarkup(buttons)

def build_quiz_subjects_keyboard(materials: dict, lang: str) -> InlineKeyboardMarkup:
    buttons = [InlineKeyboardButton(t(s, lang), callback_data=f"quizsubj:{key}") for key, s in materials.items()]
    rows = arrange_buttons(buttons, SUBJECTS_MENU_LAYOUT)
    rows.append([InlineKeyboardButton(TEXTS[lang]["back_main_menu"], callback_data="back:menu")])
    return InlineKeyboardMarkup(buttons)

def build_quiz_keyboard(subject_key: str, question: dict, qidx: int, lang: str) -> InlineKeyboardMarkup:
    options = question.get(f"options_{lang}") or question.get("options_ar") or []
    buttons = [[InlineKeyboardButton(opt, callback_data=f"quiz:{subject_key}:{qidx}:{i}")] for i, opt in enumerate(options)]
    buttons.append([InlineKeyboardButton(TEXTS[lang]["back"], callback_data="menu:quiz")])
    return InlineKeyboardMarkup(buttons)

def build_gallery_list_keyboard(items: list, prefix: str, lang: str) -> InlineKeyboardMarkup:
    buttons = [[InlineKeyboardButton(t(it, lang, field="name"), callback_data=f"{prefix}:{idx}")] for idx, it in enumerate(items)]
    buttons.append([InlineKeyboardButton(TEXTS[lang]["back_main_menu"], callback_data="back:menu")])
    return InlineKeyboardMarkup(buttons)

# =====================================================================================
#  8) معالجات الطلاب
# =====================================================================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    register_user(user)
    if not await is_subscribed(user.id, context):
        await update.message.reply_text(SUBSCRIBE_MESSAGE, reply_markup=subscribe_keyboard())
        return
    await show_post_subscription_screen(context.bot, user.id, update.effective_chat.id)

async def show_post_subscription_screen(bot, user_id: int, chat_id: int, message_to_edit=None):
    lang = get_user_lang(user_id)
    if lang is None:
        text = CHOOSE_LANGUAGE_TEXT
        markup = language_keyboard()
    else:
        text = TEXTS[lang]["welcome"]
        markup = build_main_menu(user_id, lang)
    if message_to_edit is not None:
        await message_to_edit.edit_text(text, reply_markup=markup)
    else:
        await bot.send_message(chat_id=chat_id, text=text, reply_markup=markup)

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    data = query.data
    lang = get_user_lang(user_id) or "ar"

    if data == "check_sub":
        if await is_subscribed(user_id, context):
            await query.answer()
            await show_post_subscription_screen(context.bot, user_id, query.message.chat_id, message_to_edit=query.message)
        else:
            await query.answer(TEXTS[lang]["still_not_subscribed"], show_alert=True)
        return

    await query.answer()
    if data == "noop":
        return

    if data.startswith("lang:"):
        chosen = data.split(":")[1]
        set_user_lang(user_id, chosen)
        await query.edit_message_text(TEXTS[chosen]["welcome"], reply_markup=build_main_menu(user_id, chosen))
        return

    if data == "back:menu":
        await query.edit_message_text(TEXTS[lang]["welcome"], reply_markup=build_main_menu(user_id, lang))
        return

    # المواد
    if data == "menu:materials":
        materials = load_materials()
        text = f"⌯ اختر المادة 📖\nـ• ┉ • ┉ • ┉ • ┉ • ┉ •"
        await query.edit_message_text(text, reply_markup=build_subjects_keyboard(materials, lang))
        return

    # الكتب
    if data == "menu:study_books":
        books_data = load_study_books()
        if not books_data:
            back_kb = InlineKeyboardMarkup([[InlineKeyboardButton(TEXTS[lang]["back_main_menu"], callback_data="back:menu")]])
            await query.edit_message_text(TEXTS[lang]["no_books"], reply_markup=back_kb)
            return
        await query.edit_message_text(TEXTS[lang]["choose_book"], reply_markup=build_study_books_keyboard(books_data, lang))
        return

    # المساح العام
    if data == "menu:general_survey":
        survey_data = load_general_survey()
        if not survey_data:
            back_kb = InlineKeyboardMarkup([[InlineKeyboardButton(TEXTS[lang]["back_main_menu"], callback_data="back:menu")]])
            await query.edit_message_text(TEXTS[lang]["no_general_sections"], reply_markup=back_kb)
            return
        await query.edit_message_text(TEXTS[lang]["general_survey_welcome"], reply_markup=build_general_survey_keyboard(survey_data, lang))
        return

    # معلومات
    if data == "menu:tip":
        tips = load_tips()
        back_kb = InlineKeyboardMarkup([[InlineKeyboardButton(TEXTS[lang]["back_main_menu"], callback_data="back:menu")]])
        if not tips:
            await query.edit_message_text(TEXTS[lang]["no_tips"], reply_markup=back_kb)
        else:
            tip = random.choice(tips)
            await query.edit_message_text(f"💡 {t(tip, lang, field='text')}", reply_markup=back_kb)
        return

    # كويز
    if data == "menu:quiz":
        materials = load_materials()
        if not materials:
            back_kb = InlineKeyboardMarkup([[InlineKeyboardButton(TEXTS[lang]["back_main_menu"], callback_data="back:menu")]])
            await query.edit_message_text(TEXTS[lang]["no_quiz"], reply_markup=back_kb)
            return
        await query.edit_message_text(TEXTS[lang]["choose_quiz_subject"], reply_markup=build_quiz_subjects_keyboard(materials, lang))
        return

    # أجهزة
    if data == "menu:instruments":
        instruments = load_instruments()
        if not instruments:
            back_kb = InlineKeyboardMarkup([[InlineKeyboardButton(TEXTS[lang]["back_main_menu"], callback_data="back:menu")]])
            await query.edit_message_text(TEXTS[lang]["no_instruments"], reply_markup=back_kb)
            return
        await query.edit_message_text(TEXTS[lang]["choose_instrument"], reply_markup=build_gallery_list_keyboard(instruments, "instr", lang))
        return

    # أدوات
    if data == "menu:tools":
        tools = load_tools()
        if not tools:
            back_kb = InlineKeyboardMarkup([[InlineKeyboardButton(TEXTS[lang]["back_main_menu"], callback_data="back:menu")]])
            await query.edit_message_text(TEXTS[lang]["no_tools"], reply_markup=back_kb)
            return
        await query.edit_message_text(TEXTS[lang]["choose_tool"], reply_markup=build_gallery_list_keyboard(tools, "tool", lang))
        return

    # اللغة
    if data == "menu:language":
        await query.edit_message_text(CHOOSE_LANGUAGE_TEXT, reply_markup=language_keyboard())
        return

    # الأدمن
    if data == "menu:admin":
        if not is_admin(user_id):
            await query.edit_message_text(TEXTS[lang]["not_admin"], reply_markup=build_main_menu(user_id, lang))
            return
        from admin_handlers import admin_start_from_button
        await admin_start_from_button(update, context)
        return

    # اختيار مادة
    if data.startswith("subj:"):
        subject_key = data.split(":")[1]
        materials = load_materials()
        if subject_key not in materials:
            await query.edit_message_text("❌ المادة غير موجودة", reply_markup=build_main_menu(user_id, lang))
            return
        subject = materials[subject_key]
        await query.edit_message_text(
            f"{t(subject, lang)}\n{TEXTS[lang]['choose_category']}",
            reply_markup=build_categories_keyboard(materials, subject_key, lang)
        )
        return

    # اختيار قسم
    if data.startswith("cat:"):
        _, subject_key, cat_key = data.split(":")
        materials = load_materials()
        if subject_key not in materials or cat_key not in materials[subject_key]["categories"]:
            await query.edit_message_text("❌ القسم غير موجود", reply_markup=build_main_menu(user_id, lang))
            return
        cat = materials[subject_key]["categories"][cat_key]
        await query.edit_message_text(
            f"{t(cat, lang)}\n{TEXTS[lang]['choose_file']}",
            reply_markup=build_files_keyboard(materials, subject_key, cat_key, lang)
        )
        return

    # اختيار ملف
    if data.startswith("file:"):
        _, subject_key, cat_key, idx = data.split(":")
        idx = int(idx)
        materials = load_materials()
        if subject_key not in materials or cat_key not in materials[subject_key]["categories"]:
            return
        files = materials[subject_key]["categories"][cat_key]["files"]
        if idx < 0 or idx >= len(files):
            return
        file_item = files[idx]
        file_url = file_item.get("file_url")
        file_id = file_item.get("file_id")
        file_type = file_item.get("type", "document")
        caption = t(file_item, lang)
        await send_file_or_link(
            context.bot, query.message.chat_id,
            file_id=file_id, file_url=file_url,
            file_type=file_type, caption=caption
        )
        return

    # الكتب
    if data.startswith("books_subj:"):
        subject_key = data.split(":")[1]
        books_data = load_study_books()
        if subject_key not in books_data:
            await query.edit_message_text("❌ المادة غير موجودة", reply_markup=build_main_menu(user_id, lang))
            return
        await query.edit_message_text(
            f"📚 {t(books_data[subject_key], lang)}",
            reply_markup=build_books_list_keyboard(books_data, subject_key, lang)
        )
        return

    if data.startswith("book:"):
        _, subject_key, idx = data.split(":")
        idx = int(idx)
        books_data = load_study_books()
        if subject_key not in books_data:
            return
        books = books_data[subject_key].get("books", [])
        if idx < 0 or idx >= len(books):
            return
        book = books[idx]
        file_url = book.get("file_url")
        file_id = book.get("file_id")
        file_type = book.get("type", "document")
        caption = f"📖 {t(book, lang)}\n\n{t(book, lang, field='description')}" if book.get(f"description_{lang}") else f"📖 {t(book, lang)}"
        await send_file_or_link(
            context.bot, query.message.chat_id,
            file_id=file_id, file_url=file_url,
            file_type=file_type, caption=caption
        )
        return

    # المساح العام
    if data.startswith("gen:"):
        section_key = data.split(":")[1]
        survey_data = load_general_survey()
        if section_key not in survey_data:
            await query.edit_message_text("❌ القسم غير موجود", reply_markup=build_main_menu(user_id, lang))
            return
        section = survey_data[section_key]
        content = section.get(f"content_{lang}") or section.get("content_ar") or "المحتوى غير متوفر"
        back_kb = InlineKeyboardMarkup([[InlineKeyboardButton(TEXTS[lang]["back"], callback_data="menu:general_survey")]])
        if section.get("image_url"):
            await context.bot.send_photo(
                chat_id=query.message.chat_id,
                photo=section["image_url"],
                caption=f"*{t(section, lang)}*\n\n{content}",
                parse_mode="Markdown",
                reply_markup=back_kb
            )
        else:
            await query.edit_message_text(
                f"*{t(section, lang)}*\n\n{content}",
                parse_mode="Markdown",
                reply_markup=back_kb
            )
        return

    # الكويز
    if data.startswith("quizsubj:"):
        subject_key = data.split(":")[1]
        quiz_by_subject = load_quiz()
        questions = quiz_by_subject.get(subject_key, [])
        if not questions:
            back_kb = InlineKeyboardMarkup([[InlineKeyboardButton(TEXTS[lang]["back"], callback_data="menu:quiz")]])
            await query.edit_message_text(TEXTS[lang]["no_quiz_for_subject"], reply_markup=back_kb)
            return
        qidx = random.randrange(len(questions))
        question = questions[qidx]
        text = f"🎯 {t(question, lang, field='question')}"
        if question.get("image_url"):
            await context.bot.send_photo(
                chat_id=query.message.chat_id,
                photo=question["image_url"],
                caption=text,
                reply_markup=build_quiz_keyboard(subject_key, question, qidx, lang)
            )
        else:
            await query.edit_message_text(
                text,
                reply_markup=build_quiz_keyboard(subject_key, question, qidx, lang)
            )
        return

    if data.startswith("quiz:"):
        _, subject_key, qidx, optidx = data.split(":")
        qidx, optidx = int(qidx), int(optidx)
        quiz_by_subject = load_quiz()
        questions = quiz_by_subject.get(subject_key, [])
        if qidx >= len(questions):
            return
        question = questions[qidx]
        correct = optidx == question["correct_index"]
        result_line = TEXTS[lang]["quiz_correct"] if correct else TEXTS[lang]["quiz_wrong"]
        explanation = t(question, lang, field="explanation")
        text = f"🎯 {t(question, lang, field='question')}\n\n{result_line}"
        if explanation:
            text += f"\n\n💡 {explanation}"
        back_kb = InlineKeyboardMarkup([[InlineKeyboardButton(TEXTS[lang]["back"], callback_data="menu:quiz")]])
        await query.edit_message_text(text, reply_markup=back_kb)
        return

    # الأجهزة والأدوات
    if data.startswith("instr:"):
        idx = int(data.split(":")[1])
        instruments = load_instruments()
        if 0 <= idx < len(instruments):
            await send_gallery_item(context.bot, query.message.chat_id, instruments[idx], lang)
        return

    if data.startswith("tool:"):
        idx = int(data.split(":")[1])
        tools = load_tools()
        if 0 <= idx < len(tools):
            await send_gallery_item(context.bot, query.message.chat_id, tools[idx], lang)
        return

    # الأزرار المخصصة
    if data.startswith("custom:"):
        key = data.split(":")[1]
        btn = load_custom_buttons().get(key)
        if not btn:
            return
        if btn.get("kind") == "text":
            await context.bot.send_message(chat_id=query.message.chat_id, text=btn.get("text", ""))
        else:
            file_url = btn.get("file_url")
            file_id = btn.get("file_id")
            file_type = btn.get("file_type", "document")
            caption = t(btn, lang)
            await send_file_or_link(
                context.bot, query.message.chat_id,
                file_id=file_id, file_url=file_url,
                file_type=file_type, caption=caption
            )
        return

async def send_gallery_item(bot, chat_id: int, item: dict, lang: str):
    name = t(item, lang, field="name")
    desc = t(item, lang, field="desc")
    caption = f"*{name}*\n\n{desc}"
    photo_id = item.get("photo_file_id")
    photo_url = item.get("photo_url")
    if photo_url:
        await bot.send_photo(chat_id=chat_id, photo=photo_url, caption=caption, parse_mode="Markdown")
    elif photo_id:
        await bot.send_photo(chat_id=chat_id, photo=photo_id, caption=caption, parse_mode="Markdown")
    else:
        await bot.send_message(chat_id=chat_id, text=caption, parse_mode="Markdown")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = get_user_lang(update.effective_user.id) or "ar"
    await update.message.reply_text(
        "استخدم /start لعرض القائمة الرئيسية." if lang == "ar" else "Use /start to open the main menu."
    )

# =====================================================================================
#  9) تشغيل البوت
# =====================================================================================

def main():
    logging.basicConfig(level=logging.INFO)
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CallbackQueryHandler(button_handler))

    from admin_handlers import get_admin_conversation
    admin_conv = get_admin_conversation()
    app.add_handler(admin_conv)

    print("✅ البوت الأسطوري يعمل الآن...")
    app.run_polling()

if __name__ == "__main__":
    main()