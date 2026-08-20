# -*- coding: utf-8 -*-
"""
=====================================================================================
   بوت المواد الدراسية -- النسخة الكاملة (اشتراك إجباري + لغتين + إدارة شاملة)
=====================================================================================

المميزات:
- اشتراك إجباري في أكتر من قناة (تحددهم انت في REQUIRED_CHANNELS تحت)
- دعم أكتر من أدمن (ADMIN_IDS)
- اختيار لغة (عربي / English) بعد الاشتراك، وقابلة للتغيير في أي وقت
- قائمة رئيسية بترتيب أزرار مخصص (زر - زرين - زر - زرين ...) قابل للتعديل
- قسم مواد دراسية (8 مواد، كل مادة فيها: ملخصات PDF / فيديوهات / شرح)
- قسم أدمن كامل: إضافة/حذف مواد، أقسام، ملفات (أي نوع)، أزرار مخصصة، إذاعة، باك أب
- كل التعديلات بتتحفظ تلقائياً في ملفات JSON، من غير ما تلمس الكود يدوياً

المتطلبات:
    pip install python-telegram-bot --upgrade
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
#  1) الإعدادات العامة -- هنا بس المفروض تعدّل غالباً
# =====================================================================================

# التوكن الخاص بالبوت
BOT_TOKEN = "8753500776:AAFf3i35j7ReiHae0eFlPH9Fx97-4LQL2Tg"

# آيدي كل الأدمنية المسموح لهم بأوامر الإدارة -- ضيف أي آيدي جديد في نفس القائمة
# مثال لإضافة أدمن تاني: ADMIN_IDS = [7724699440, 123456789, 987654321]
# ⚠️ أول آيدي في القائمة (ADMIN_IDS[0]) هو "المالك" (Owner) وله صلاحيات كاملة دايماً
# ولا يمكن حذفه أو تقييد صلاحياته إلا بتعديل الكود مباشرة. باقي الأدمنية في القائمة دي
# كمان صلاحياتهم كاملة تلقائياً. لو عايز أدمن بصلاحيات محدودة، ضيفه من داخل البوت
# نفسه (لوحة الأدمن -> الأدمنية -> إضافة) بدل ما تحطه هنا.
ADMIN_IDS = [
    7724699440,
    6004659847,
]

# ملف الأدمنية الإضافيين (اللي بيتضافوا من جوه البوت وليهم صلاحيات مخصصة)
ADMINS_FILE = "admins.json"

# فئات الصلاحيات المتاحة لتوزيعها على الأدمنية الإضافيين
PERMISSIONS = {
    "materials": "📚 المواد والكتب الدراسية",
    "general": "🧭 المساح العام (أجهزة/أدوات/مقالات)",
    "quiz": "🎯 الكويز والمعلومات",
    "menu_control": "🎛 التحكم في الأزرار والقوائم",
    "broadcast": "📢 الإذاعة",
    "files": "🗂 إدارة ملفات النظام",
}

# قنوات/جروبات الاشتراك الإجباري -- سيبها فاضية [] لو مش عايز اشتراك إجباري خالص
#
# فيه نوعين ممكن تضيفهم:
#
# 1) قناة/جروب عام (ليه يوزرنيم بيبدأ بـ @):
#    {"name": "اسم يظهر للمستخدم", "username": "@channel_username"}
#
# 2) قناة/جروب خاص (رابط دعوة زي https://t.me/+xxxxx بدون يوزرنيم):
#    القنوات والجروبات الخاصة معندهاش username، فمحتاج تجيب "chat_id" الرقمي بتاعها
#    عشان البوت يقدر يتحقق من الاشتراك (رابط الدعوة نفسه مش كافي للتحقق).
#    {"name": "اسم يظهر للمستخدم", "chat_id": -1001234567890, "invite_link": "https://t.me/+xxxxxxxxxxxxx"}
#
# 🆔 إزاي تجيب chat_id بتاع قناة/جروب خاص:
#    1. خلي البوت أدمن في القناة/الجروب الخاص (شرط أساسي عشان يقدر يتحقق أصلاً)
#    2. ابعت أي رسالة من القناة/الجروب وفروردها (Forward) لأي شات مع البوت وانت مسجل كأدمن
#    3. البوت هيرد عليك تلقائياً برقم الـ chat_id بتاعها (شوف دالة chatid_detector تحت)
#
# لإضافة أكتر من قناة/جروب، زوّد عنصر جديد بنفس الشكل في القائمة:
REQUIRED_CHANNELS = [
    # مثال قناة عامة:
    {"name": "اكسيز للمساحة", "username": "@axissurveying"},
    {"name": "تحديثات بوت اكسيز", "username": "@axis_updates"},
    {"name": "سنة تانية مساحة", "username": "@part2_survey"},
    {"name": "سنة تانية ري", "username": "@part2_leveling"},  
    # {"name": "", "username": "@axissurveying"},

    # مثال قناة خاصة (استبدل الأرقام بالـ chat_id الحقيقي اللي هتجيبه من chatid_detector):
     {"name": "اكسيز شات", "chat_id": -1003257254001, "invite_link": "https://t.me/+xnCCq2g-kxtmZWI8"},
    # {"name": "قناة الأخبار والتحديثات", "chat_id": -1002222222222, "invite_link": "https://t.me/+ZjlWlQ5r5fBhYmM8"},
]

# ملفات التخزين (بتتعمل تلقائياً لو مش موجودة، مش لازم تلمسها)
MATERIALS_FILE = "materials.json"
USERS_FILE = "users.json"
CUSTOM_BUTTONS_FILE = "custom_buttons.json"
TIPS_FILE = "tips.json"      # 💡 معلومة مساحية عشوائية
QUIZ_FILE = "quiz.json"      # 🎯 أسئلة الكويز (مقسمة حسب كل مادة)
MENU_LABELS_FILE = "menu_labels.json"  # أسماء أزرار القائمة الرئيسية الأساسية (لو الأدمن عدّلها)
INSTRUMENTS_FILE = "instruments.json"  # 🔭 الأجهزة المساحية
TOOLS_FILE = "tools.json"              # 🧰 الأدوات المساحية
BOOKS_FILE = "books.json"              # 📖 الكتب الدراسية (PDF/صور مقسمة حسب كل مادة)
GENERAL_FILE = "general_surveyor.json" # 🧭 قسم المساح العام (مقالات مساعدة عامة)

# الأزرار الأساسية الثابتة في القائمة الرئيسية (اللي ممكن تتعدل من لوحة الأدمن)
# المفتاح على اليسار هو المعرف الداخلي، والقيمة هي النص الافتراضي (لو الأدمن معدلش)
CORE_MENU_KEYS = {
    "materials_section": "menu:materials",
    "books_section": "menu:books",
    "instruments_section": "menu:instruments",
    "tools_section": "menu:tools",
    "general_section": "menu:general",
    "tip_section": "menu:tip",
    "quiz_section": "menu:quiz",
    "language_section": "menu:language",
    "admin_section": "menu:admin",
}

# الملفات المسموح استبدالها من داخل تليجرام (لوحة الأدمن -> رفع/استبدال ملف)
# ضيف اسم أي ملف تاني هنا لو عايز تقدر ترفعه وتستبدله من جوه البوت
ALLOWED_UPLOAD_FILES = [
    "bot.py", "requirements.txt", "Procfile",
    "materials.json", "custom_buttons.json", "tips.json", "quiz.json", "users.json",
    "instruments.json", "tools.json", "menu_labels.json", "books.json", "general_surveyor.json", "admins.json",
]

# الملفات المسموح "تصفيرها" (حذف بياناتها والرجوع لملف فاضي) من لوحة الأدمن
# متعمدين ما نحطش bot.py / requirements.txt / Procfile هنا لأن حذفهم هيوقف البوت تماماً
ALLOWED_RESET_FILES = [
    "materials.json", "custom_buttons.json", "tips.json", "quiz.json", "users.json",
    "instruments.json", "tools.json", "menu_labels.json", "books.json", "general_surveyor.json", "admins.json",
]

# نمط توزيع أزرار القائمة الرئيسية: كل رقم = عدد الأزرار في نفس الصف
# المثال ده معناه: زر لوحده / زرين جنب بعض / زر لوحده / زرين جنب بعض ...
# غيّر الأرقام براحتك (1 = زر لوحده، 2 = زرين، 3 = تلاتة...)
MAIN_MENU_LAYOUT = [1, 2, 1, 2, 1, 2, 1]

# نمط توزيع أزرار قائمة المواد الدراسية: زرين جنب بعض / زر لوحده / زرين / زر ...
SUBJECTS_MENU_LAYOUT = [2, 1, 2, 1, 2, 1, 2, 1]

# =====================================================================================
#  2) نصوص الواجهة (عربي / إنجليزي) -- عدّل أي نص هنا وهيتغير في كل البوت
# =====================================================================================

TEXTS = {
    "ar": {
        "welcome": "ـ• ┉ • ┉ • ┉ • ┉ • ┉ •\n✬︙مرحبا بك 👁‍🗨،\n✬︙يمكنك اختيار قسم من الاقسام التالية :\nـ• ┉ • ┉ • ┉ • ┉ • ┉ •",
        "materials_section": "⌯⪼📚 المواد الدراسية",
        "language_section": "⌯⪼🌐 تغيير اللغة",
        "admin_section": "⌯⪼⚙️  لوحة الأدمن",
        "choose_subject": "⌯⪼📖 اختر المادة :",
        "choose_category": "⌯⪼📂 اختر القسم:",
        "choose_file": "⌯⪼📄 اختر الملف:",
        "back": "🔙 𝙱𝙰𝙲𝙺",
        "back_main_menu": "✬︙🏠 القائمة الرئيسية︙✬",
        "no_files": "✬ لا توجد ملفات بعد",
        "still_not_subscribed": "لسه مش مشترك في كل القنوات! اشترك الأول ثم اضغط تحقق.",
        "tip_section": "⌯⪼💡 معلومة مساحية",
        "quiz_section": "⌯⪼🎯 اختبر نفسك",
        "no_tips": "لا توجد معلومات مضافة بعد.",
        "no_quiz": "لا توجد أسئلة مضافة بعد.",
        "quiz_correct": "✅⪼ إجابة صحيحة.",
        "quiz_wrong": "❌⋙ إجابة غلط.",
        "instruments_section": "⌯⪼🔭 الأجهزة المساحية",
        "tools_section": "⌯⪼🧰 الأدوات المساحية",
        "choose_instrument": "⌯⪼🔭 اختر الجهاز:",
        "choose_tool": "⌯⪼🧰 اختر الأداة:",
        "no_instruments": "❎⪼ لا توجد أجهزة مضافة بعد.",
        "no_tools": "❎⪼ لا توجد أدوات مضافة بعد.",
        "choose_quiz_subject": "‼️⌯⪼ اختر المادة اللي عايز تختبر نفسك فيها :\n",
        "no_quiz_for_subject": "لا توجد أسئلة على المادة دي لسه.",
        "books_section": "⌯⪼📖 الكتب الدراسية",
        "choose_books_subject": "⌯⪼📖 اختر المادة اللي عايز كتبها:\n",
        "choose_book": "⌯⪼📖 اختر الكتاب:\n",
        "no_books": "❎⪼ لا توجد كتب مضافة بعد.",
        "no_books_for_subject": "❎⪼ لا توجد كتب على المادة دي لسه.",
        "general_section": "⌯⪼🧭 المساح العام",
        "choose_general": "⌯⪼🧭 اختر القسم اللي عايز تعرف عنه أكتر:\n",
        "no_general": "❎⪼ لا توجد أقسام مضافة بعد.",
        "general_hub_title": "ـ• ┉ • ┉ • ┉ • ┉ • ┉ •\n🧭︱بوابة المساح العام\nكل حاجة محتاجها كمساح مش مرتبطة بمادة دراسية معينة 👇\nـ• ┉ • ┉ • ┉ • ┉ • ┉ •",
        "general_articles_button": "⌯⪼📚 مقالات ونصائح عامة",
    },
    "en": {
        "welcome": "Welcome 👋\nChoose from the menu below:",
        "materials_section": "📚 Study Materials",
        "language_section": "🌐 Change Language",
        "admin_section": "⚙️ Admin Panel",
        "choose_subject": "📖 Choose a subject:",
        "choose_category": "📂 Choose a section:",
        "choose_file": "📄 Choose a file:",
        "back": "⬅️ Back",
        "back_main_menu": "🏠 Main Menu",
        "no_files": "No files yet",
        "still_not_subscribed": "You're not subscribed to all channels yet! Join then press check.",
        "tip_section": "💡 Surveying Tip",
        "quiz_section": "🎯 Test Yourself",
        "no_tips": "No tips added yet.",
        "no_quiz": "No quiz questions added yet.",
        "quiz_correct": "✅ Correct answer!",
        "quiz_wrong": "❌ Wrong answer.",
        "instruments_section": "🔭 Surveying Instruments",
        "tools_section": "🧰 Surveying Tools",
        "choose_instrument": "🔭 Choose an instrument:",
        "choose_tool": "🧰 Choose a tool:",
        "no_instruments": "No instruments added yet.",
        "no_tools": "No tools added yet.",
        "choose_quiz_subject": "🎯 Choose the subject you want to test yourself on:",
        "no_quiz_for_subject": "No questions for this subject yet.",
        "books_section": "📖 Study Books",
        "choose_books_subject": "📖 Choose the subject:",
        "choose_book": "📖 Choose a book:",
        "no_books": "No books added yet.",
        "no_books_for_subject": "No books for this subject yet.",
        "general_section": "🧭 General Surveyor",
        "choose_general": "🧭 Choose a topic to learn more about:",
        "no_general": "No topics added yet.",
        "general_hub_title": "🧭 General Surveyor Hub\nEverything you need as a surveyor, not tied to a specific subject 👇",
        "general_articles_button": "📚 Articles & Tips",
    },
}

# نص طلب الاشتراك الإجباري (ثنائي اللغة لأنه بيظهر قبل ما المستخدم يختار لغته)
SUBSCRIBE_MESSAGE = (
    "ـ• ┉ • ┉ • ┉ • ┉ • ┉ •\n✬︙مرحبا بك عزيزي 👁‍🗨،\n✬︙لا يمڪنـك استخدام البوت ،\n✬︙عليك الإشتراڪك في القنوات الخاصة بالبوت اولاً لكي تتمكن من استخدامه\n•ـ ┉ • ┉ • ┉ • ┉ • ┉ •\n\n✬︙ بعد الاشتراك اضغط علي الزر ادناه لتأكيد الاشتراك"
)
CHECK_SUB_BUTTON_TEXT = "⌯✅ اشتركت ꫛ"
CHOOSE_LANGUAGE_TEXT = "ـ• ┉ • ┉ • ┉ • ┉ • ┉ •\n✬︙ اختر لغة البوت | Choose your bot language :\nـ• ┉ • ┉ • ┉ • ┉ • ┉ •"

# =====================================================================================
#  3) دوال تحميل/حفظ البيانات (materials / users / custom_buttons)
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


def load_quiz() -> list:
    return _load_json(QUIZ_FILE, [])


def save_quiz(data: list):
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


def load_books() -> dict:
    return _load_json(BOOKS_FILE, {})


def save_books(data: dict):
    _save_json(BOOKS_FILE, data)


def load_general() -> list:
    return _load_json(GENERAL_FILE, [])


def save_general(data: list):
    _save_json(GENERAL_FILE, data)


def load_admins() -> dict:
    return _load_json(ADMINS_FILE, {})


def save_admins(data: dict):
    _save_json(ADMINS_FILE, data)


def is_owner(user_id: int) -> bool:
    """المالك = أول آيدي في ADMIN_IDS، وهو الوحيد اللي يقدر يدير الأدمنية الآخرين."""
    return bool(ADMIN_IDS) and user_id == ADMIN_IDS[0]


def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS or str(user_id) in load_admins()


def has_permission(user_id: int, perm_key: str) -> bool:
    """المالك وأي أدمن في ADMIN_IDS ليهم كل الصلاحيات دايماً.
    الأدمنية المضافين من جوه البوت بيتحققوا حسب صلاحياتهم المسجلة في admins.json."""
    if user_id in ADMIN_IDS:
        return True
    admins = load_admins()
    entry = admins.get(str(user_id))
    if not entry:
        return False
    return entry.get("permissions", {}).get(perm_key, False)


# خريطة: أي زرار في لوحة الأدمن يحتاج أي صلاحية (لو مش موجود في الخريطة، متاح لأي أدمن بدون قيد)
PERMISSION_MAP = {
    "admin:add_subject": "materials", "admin:add_cat": "materials", "admin:add_file": "materials",
    "admin:del_file": "materials", "admin:del_cat": "materials", "admin:del_subject": "materials",
    "admin:add_book": "materials", "admin:del_book": "materials",
    "admin:add_instr": "general", "admin:del_instr": "general",
    "admin:add_tool": "general", "admin:del_tool": "general",
    "admin:add_general": "general", "admin:del_general": "general",
    "admin:add_tip": "quiz", "admin:del_tip": "quiz",
    "admin:add_quiz": "quiz", "admin:del_quiz": "quiz",
    "admin:add_btn": "menu_control", "admin:del_btn": "menu_control",
    "admin:edit_btn": "menu_control", "admin:edit_core": "menu_control", "admin:toggle_core": "menu_control",
    "admin:broadcast": "broadcast",
    "admin:sys_upload": "files", "admin:get_file": "files", "admin:sys_delete": "files",
    "admin:clean_temp": "files", "admin:restart_ask": "files",
}


# ---- تسجيل / قراءة بيانات المستخدم (اللغة + بياناته للإذاعة) ----

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
    return None  # يعني لسه محددش لغة


def set_user_lang(user_id: int, lang: str):
    users = load_users()
    uid = str(user_id)
    if uid not in users:
        users[uid] = {}
    users[uid]["lang"] = lang
    save_users(users)


# ---- دالة صغيرة لقراءة النص بلغة معينة من أي عنصر (مادة / قسم / ملف / زر) ----
def t(obj: dict, lang: str, field: str = "title") -> str:
    return obj.get(f"{field}_{lang}") or obj.get(f"{field}_ar") or obj.get(f"{field}_en") or ""


# =====================================================================================
#  4) الاشتراك الإجباري
# =====================================================================================

async def is_subscribed(user_id: int, context: ContextTypes.DEFAULT_TYPE) -> bool:
    if not REQUIRED_CHANNELS:
        return True
    for channel in REQUIRED_CHANNELS:
        # للقنوات الخاصة بنستخدم chat_id الرقمي، وللعامة بنستخدم username
        identifier = channel.get("chat_id") or channel.get("username")
        if not identifier:
            continue  # قناة متظبطش صح، متطلعش المستخدمين من الاستخدام بسببها
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
        # لو فيه رابط دعوة مخصص (زي القنوات الخاصة) استخدمه، وإلا ابنيه من الـ username
        link = channel.get("invite_link") or f"https://t.me/{channel.get('username','').lstrip('@')}"
        buttons.append([InlineKeyboardButton(f"📢 {channel['name']}", url=link)])
    buttons.append([InlineKeyboardButton(CHECK_SUB_BUTTON_TEXT, callback_data="check_sub")])
    return InlineKeyboardMarkup(buttons)


async def chatid_detector(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    أداة مساعدة للأدمن بس: لو فروردت (Forward) رسالة من قناة أو جروب خاص للبوت،
    هيرد عليك برقم الـ chat_id بتاعها عشان تحطه في REQUIRED_CHANNELS فوق.
    """
    if not is_admin(update.effective_user.id):
        return
    msg = update.message
    if msg.forward_from_chat:
        chat = msg.forward_from_chat
        await msg.reply_text(
            f"🆔 chat_id: `{chat.id}`\n📛 الاسم: {chat.title}\n\n"
            f"انسخ الرقم ده (بالسالب لو موجود) وحطه في REQUIRED_CHANNELS كـ chat_id.",
            parse_mode="Markdown",
        )


def language_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton("【🇸🇦 العربية】", callback_data="lang:ar"),
          InlineKeyboardButton("【🇬🇧 English】", callback_data="lang:en")]]
    )


# =====================================================================================
#  5) دوال إرسال الملفات (بتدعم كل الأنواع: مستند / فيديو / صورة / صوت / رسالة صوتية / GIF)
# =====================================================================================

async def send_stored_file(bot, chat_id: int, file_id: str, file_type: str, caption: str = None):
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
    """يحدد نوع الملف اللي بعته الأدمن ويرجع (file_id, file_type) أو (None, None)."""
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


def parse_media_input(message):
    """
    ⭐ بوابة موحدة لكل الوسائط في البوت -- بتقبل رفع ملف مباشر أو رابط نصي.
    ترجع (source, kind):
      - لو رفع ملف من تليجرام: source = file_id
      - لو بعت رابط (http/https): source = الرابط نفسه، ونحاول نخمن نوعه من امتداد الرابط
    الاستخدام: بما إن send_photo/send_document/send_video/send_video في تليجرام
    بتقبل رابط خارجي بنفس طريقة الـ file_id بالظبط، مفيش أي تخزين إضافي مطلوب --
    البوت بيبعت اللينك زي ما هو والمستخدم بياخد الملف مباشرة من المصدر.
    """
    file_id, file_type = detect_uploaded_file(message)
    if file_id:
        return file_id, file_type

    if message.text:
        text = message.text.strip()
        if text.startswith("http://") or text.startswith("https://"):
            lower = text.lower().split("?")[0]  # نتجاهل أي query params وقت تخمين الامتداد
            if lower.endswith((".mp4", ".mov", ".mkv", ".webm")):
                return text, "video"
            if lower.endswith((".jpg", ".jpeg", ".png", ".webp", ".gif")):
                return text, "photo"
            if lower.endswith((".mp3", ".wav", ".ogg", ".m4a")):
                return text, "audio"
            # رابط بدون امتداد واضح (زي روابط اختصار Cutt/Bitly) -- نعتبره document افتراضياً
            return text, "document"

    return None, None


# =====================================================================================
#  6) بناء لوحات المفاتيح (Keyboards) الخاصة بالطلاب
# =====================================================================================

def arrange_buttons(button_objs: list, layout: list) -> list:
    """توزيع قائمة أزرار على صفوف حسب نمط layout. الباقي (لو زاد) بيتوزع زر في كل صف."""
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
    """يرجع اسم الزرار الأساسي: لو الأدمن غيّر الاسم فعلياً يستخدمه، وإلا الاسم الافتراضي من TEXTS.
    (بيتجاهل عمداً أي عنصر في menu_labels.json ملوش اسم متسجل فعلاً -- زي عناصر الإخفاء/الإظهار بس)"""
    overrides = load_menu_labels()
    entry = overrides.get(key)
    if entry and entry.get("title_ar"):
        return t(entry, lang)
    return TEXTS[lang][key]


def build_main_menu(user_id: int, lang: str) -> InlineKeyboardMarkup:
    labels = load_menu_labels()

    def is_hidden(key):
        return labels.get(key, {}).get("hidden", False)

    items = []
    if not is_hidden("materials_section"):
        items.append((core_label("materials_section", lang), "menu:materials"))
    if not is_hidden("books_section"):
        items.append((core_label("books_section", lang), "menu:books"))
    if not is_hidden("general_section"):
        items.append((core_label("general_section", lang), "menu:general"))
    if not is_hidden("quiz_section"):
        items.append((core_label("quiz_section", lang), "menu:quiz"))
    if not is_hidden("language_section"):
        items.append((core_label("language_section", lang), "menu:language"))
    if not is_hidden("admin_section"):
        items.append((core_label("admin_section", lang), "menu:admin"))

    # صفوف الأزرار الأساسية بالنمط الثابت MAIN_MENU_LAYOUT
    core_buttons = [InlineKeyboardButton(label, callback_data=cb) for label, cb in items]
    rows = arrange_buttons(core_buttons, MAIN_MENU_LAYOUT)

    # ---- الأزرار المخصصة اللي أضافها الأدمن، كل واحد بتنسيقه اللي اختاره وقت الإضافة ----
    # layout == "same_row" -> بيتضاف جنب آخر زر في آخر صف موجود
    # layout == "new_row" (الافتراضي) -> بياخد صف لوحده
    for key, btn in load_custom_buttons().items():
        button = InlineKeyboardButton(t(btn, lang), callback_data=f"custom:{key}")
        if btn.get("layout") == "same_row" and rows:
            rows[-1].append(button)
        else:
            rows.append([button])

    # =================================================================================
    # 🧩 مكان جاهز لإضافة أزرار تانية يدوياً في الكود مباشرة (اختياري)
    # فك التعليق عن أي سطر تحت وغيّر النص والـ callback_data حسب رغبتك،
    # وبعدين ضيف شرط جديد في دالة button_handler تحت يتعامل مع نفس الـ callback_data:
    #
    # rows.append([InlineKeyboardButton("📢 تواصل معنا" if lang == "ar" else "📢 Contact Us", callback_data="menu:contact")])
    # =================================================================================

    return InlineKeyboardMarkup(rows)


def build_subjects_keyboard(materials: dict, lang: str) -> InlineKeyboardMarkup:
    buttons = [InlineKeyboardButton(t(s, lang), callback_data=f"subj:{key}") for key, s in materials.items()]
    rows = arrange_buttons(buttons, SUBJECTS_MENU_LAYOUT)
    rows.append([InlineKeyboardButton(TEXTS[lang]["back_main_menu"], callback_data="back:menu")])
    return InlineKeyboardMarkup(rows)


def build_categories_keyboard(materials: dict, subject_key: str, lang: str) -> InlineKeyboardMarkup:
    subject = materials[subject_key]
    buttons = [
        [InlineKeyboardButton(t(c, lang), callback_data=f"cat:{subject_key}:{ckey}")]
        for ckey, c in subject["categories"].items()
    ]
    buttons.append([InlineKeyboardButton(TEXTS[lang]["back"], callback_data="menu:materials")])
    return InlineKeyboardMarkup(buttons)


def build_files_keyboard(materials: dict, subject_key: str, cat_key: str, lang: str) -> InlineKeyboardMarkup:
    files = materials[subject_key]["categories"][cat_key]["files"]
    buttons = [
        [InlineKeyboardButton(t(f, lang), callback_data=f"file:{subject_key}:{cat_key}:{idx}")]
        for idx, f in enumerate(files)
    ]
    if not files:
        buttons.append([InlineKeyboardButton(TEXTS[lang]["no_files"], callback_data="noop")])
    buttons.append([InlineKeyboardButton(TEXTS[lang]["back"], callback_data=f"subj:{subject_key}")])
    return InlineKeyboardMarkup(buttons)


# ---- بناء نص وأزرار سؤال الكويز ----
def build_quiz_question_text(question: dict, lang: str) -> str:
    return f"🎯 {t(question, lang, field='question')}"


def build_quiz_keyboard(subject_key: str, question: dict, qidx: int, lang: str) -> InlineKeyboardMarkup:
    options = question.get(f"options_{lang}") or question.get("options_ar") or []
    buttons = [
        [InlineKeyboardButton(opt, callback_data=f"quiz:{subject_key}:{qidx}:{i}")]
        for i, opt in enumerate(options)
    ]
    buttons.append([InlineKeyboardButton(TEXTS[lang]["back"], callback_data="menu:quiz")])
    return InlineKeyboardMarkup(buttons)


def build_quiz_subjects_keyboard(materials: dict, lang: str) -> InlineKeyboardMarkup:
    """قائمة المواد لاختيار الكويز -- بنفس أسماء وزخرفة المواد الدراسية بالظبط."""
    buttons = [InlineKeyboardButton(t(s, lang), callback_data=f"quizsubj:{key}") for key, s in materials.items()]
    rows = arrange_buttons(buttons, SUBJECTS_MENU_LAYOUT)
    rows.append([InlineKeyboardButton(TEXTS[lang]["back_main_menu"], callback_data="back:menu")])
    return InlineKeyboardMarkup(rows)


# ---- 🔭 الأجهزة و 🧰 الأدوات (نفس الشكل بالظبط، لكن بيانات منفصلة) ----
def build_gallery_list_keyboard(items: list, prefix: str, lang: str) -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(t(it, lang, field="name"), callback_data=f"{prefix}:{idx}")]
        for idx, it in enumerate(items)
    ]
    buttons.append([InlineKeyboardButton(TEXTS[lang]["back"], callback_data="menu:general")])
    return InlineKeyboardMarkup(buttons)


async def send_gallery_item(bot, chat_id: int, item: dict, lang: str):
    name = t(item, lang, field="name")
    desc = t(item, lang, field="desc")
    caption = f"*{name}*\n\n{desc}"
    photo_id = item.get("photo_file_id")
    if photo_id:
        await bot.send_photo(chat_id=chat_id, photo=photo_id, caption=caption, parse_mode="Markdown")
    else:
        await bot.send_message(chat_id=chat_id, text=caption, parse_mode="Markdown")


# ---- 📖 الكتب الدراسية (مقسمة حسب كل مادة، بنفس أسماء وزخرفة المواد) ----
def build_books_subjects_keyboard(materials: dict, lang: str) -> InlineKeyboardMarkup:
    buttons = [InlineKeyboardButton(t(s, lang), callback_data=f"bookssubj:{key}") for key, s in materials.items()]
    rows = arrange_buttons(buttons, SUBJECTS_MENU_LAYOUT)
    rows.append([InlineKeyboardButton(TEXTS[lang]["back_main_menu"], callback_data="back:menu")])
    return InlineKeyboardMarkup(rows)


def build_books_list_keyboard(subject_key: str, books: list, lang: str) -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(t(b, lang), callback_data=f"book:{subject_key}:{idx}")]
        for idx, b in enumerate(books)
    ]
    if not books:
        buttons.append([InlineKeyboardButton(TEXTS[lang]["no_books_for_subject"], callback_data="noop")])
    buttons.append([InlineKeyboardButton(TEXTS[lang]["back"], callback_data="menu:books")])
    return InlineKeyboardMarkup(buttons)


async def send_book_item(bot, chat_id: int, book: dict, lang: str):
    title = t(book, lang, field="title")
    desc = t(book, lang, field="desc")
    caption = f"*{title}*\n\n{desc}" if desc else f"*{title}*"
    file_id = book.get("file_id")
    file_type = book.get("type", "document")
    if file_type == "photo":
        await bot.send_photo(chat_id=chat_id, photo=file_id, caption=caption, parse_mode="Markdown")
    else:
        await bot.send_document(chat_id=chat_id, document=file_id, caption=caption, parse_mode="Markdown")


# ---- 🧭 المساح العام (مقالات مساعدة عامة، مش مرتبطة بمادة معينة) ----
def build_general_list_keyboard(items: list, lang: str) -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(t(it, lang), callback_data=f"general:{idx}")]
        for idx, it in enumerate(items)
    ]
    buttons.append([InlineKeyboardButton(TEXTS[lang]["back"], callback_data="menu:general")])
    return InlineKeyboardMarkup(buttons)


def build_general_hub_keyboard(lang: str) -> InlineKeyboardMarkup:
    """قائمة فروع 'المساح العام': الأجهزة، الأدوات، معلومة عشوائية، ومقالات ونصائح."""
    labels = load_menu_labels()

    def is_hidden(key):
        return labels.get(key, {}).get("hidden", False)

    items = []
    if not is_hidden("instruments_section"):
        items.append((core_label("instruments_section", lang), "menu:instruments"))
    if not is_hidden("tools_section"):
        items.append((core_label("tools_section", lang), "menu:tools"))
    if not is_hidden("tip_section"):
        items.append((core_label("tip_section", lang), "menu:tip"))
    items.append((TEXTS[lang]["general_articles_button"], "menu:general_articles"))

    buttons = [InlineKeyboardButton(label, callback_data=cb) for label, cb in items]
    rows = arrange_buttons(buttons, [1, 2, 1])
    rows.append([InlineKeyboardButton(TEXTS[lang]["back_main_menu"], callback_data="back:menu")])
    return InlineKeyboardMarkup(rows)


async def send_general_item(bot, chat_id: int, item: dict, lang: str):
    title = t(item, lang, field="title")
    content = t(item, lang, field="content")
    caption = f"*{title}*\n\n{content}"
    file_id = item.get("file_id")
    file_type = item.get("file_type", "")
    if file_id and file_type == "photo":
        await bot.send_photo(chat_id=chat_id, photo=file_id, caption=caption, parse_mode="Markdown")
    elif file_id:
        await bot.send_document(chat_id=chat_id, document=file_id, caption=caption, parse_mode="Markdown")
    else:
        await bot.send_message(chat_id=chat_id, text=caption, parse_mode="Markdown")


# =====================================================================================
#  7) شاشة ما بعد الاشتراك (لغة لسه متحددتش -> اختيار لغة / محددة -> القائمة الرئيسية)
# =====================================================================================

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


# =====================================================================================
#  8) معالجات الطلاب (start + التنقل بالأزرار)
# =====================================================================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    register_user(user)

    if not await is_subscribed(user.id, context):
        await update.message.reply_text(SUBSCRIBE_MESSAGE, reply_markup=subscribe_keyboard())
        return

    await show_post_subscription_screen(context.bot, user.id, update.effective_chat.id)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = get_user_lang(update.effective_user.id) or "ar"
    await update.message.reply_text(
        "استخدم /start لعرض القائمة الرئيسية." if lang == "ar" else "Use /start to open the main menu."
    )


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    data = query.data
    lang = get_user_lang(user_id) or "ar"

    # ---- إعادة التحقق من الاشتراك ----
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

    # ---- اختيار / تغيير اللغة ----
    if data.startswith("lang:"):
        chosen = data.split(":")[1]
        set_user_lang(user_id, chosen)
        await query.edit_message_text(TEXTS[chosen]["welcome"], reply_markup=build_main_menu(user_id, chosen))
        return

    if data == "menu:language":
        await query.edit_message_text(CHOOSE_LANGUAGE_TEXT, reply_markup=language_keyboard())
        return

    # ---- الرجوع للقائمة الرئيسية ----
    if data == "back:menu":
        await query.edit_message_text(TEXTS[lang]["welcome"], reply_markup=build_main_menu(user_id, lang))
        return

    # ---- قسم المواد الدراسية ----
    if data == "menu:materials":
        materials = load_materials()
        await query.edit_message_text(TEXTS[lang]["choose_subject"], reply_markup=build_subjects_keyboard(materials, lang))
        return

    # ---- 💡 معلومة مساحية عشوائية ----
    if data == "menu:tip":
        tips = load_tips()
        back_kb = InlineKeyboardMarkup([[InlineKeyboardButton(TEXTS[lang]["back"], callback_data="menu:general")]])
        if not tips:
            await query.edit_message_text(TEXTS[lang]["no_tips"], reply_markup=back_kb)
        else:
            tip = random.choice(tips)
            await query.edit_message_text(f"⋙💡︙\nـ• ┉ • ┉ • ┉ • ┉ • ┉ •\n{t(tip, lang, field='text')}\nـ• ┉ • ┉ • ┉ • ┉ • ┉ •", reply_markup=back_kb)
        return

    # ---- 📖 الكتب الدراسية ----
    if data == "menu:books":
        materials = load_materials()
        if not materials:
            back_kb = InlineKeyboardMarkup([[InlineKeyboardButton(TEXTS[lang]["back_main_menu"], callback_data="back:menu")]])
            await query.edit_message_text(TEXTS[lang]["no_books"], reply_markup=back_kb)
            return
        await query.edit_message_text(TEXTS[lang]["choose_books_subject"], reply_markup=build_books_subjects_keyboard(materials, lang))
        return

    if data.startswith("bookssubj:"):
        subject_key = data.split(":")[1]
        books_by_subject = load_books()
        books = books_by_subject.get(subject_key, [])
        await query.edit_message_text(TEXTS[lang]["choose_book"], reply_markup=build_books_list_keyboard(subject_key, books, lang))
        return

    if data.startswith("book:"):
        _, subject_key, idx = data.split(":")
        books_by_subject = load_books()
        books = books_by_subject.get(subject_key, [])
        idx = int(idx)
        if 0 <= idx < len(books):
            await send_book_item(context.bot, query.message.chat_id, books[idx], lang)
        return

    # ---- 🧭 المساح العام ----
    if data == "menu:general":
        await query.edit_message_text(TEXTS[lang]["general_hub_title"], reply_markup=build_general_hub_keyboard(lang))
        return

    if data == "menu:general_articles":
        general_items = load_general()
        back_kb = InlineKeyboardMarkup([[InlineKeyboardButton(TEXTS[lang]["back"], callback_data="menu:general")]])
        if not general_items:
            await query.edit_message_text(TEXTS[lang]["no_general"], reply_markup=back_kb)
            return
        await query.edit_message_text(TEXTS[lang]["choose_general"], reply_markup=build_general_list_keyboard(general_items, lang))
        return

    if data.startswith("general:"):
        idx = int(data.split(":")[1])
        general_items = load_general()
        if 0 <= idx < len(general_items):
            await send_general_item(context.bot, query.message.chat_id, general_items[idx], lang)
        return

    # ---- 🔭 الأجهزة المساحية ----
    if data == "menu:instruments":
        instruments = load_instruments()
        if not instruments:
            back_kb = InlineKeyboardMarkup([[InlineKeyboardButton(TEXTS[lang]["back"], callback_data="menu:general")]])
            await query.edit_message_text(TEXTS[lang]["no_instruments"], reply_markup=back_kb)
            return
        await query.edit_message_text(TEXTS[lang]["choose_instrument"], reply_markup=build_gallery_list_keyboard(instruments, "instr", lang))
        return

    if data.startswith("instr:"):
        idx = int(data.split(":")[1])
        instruments = load_instruments()
        if 0 <= idx < len(instruments):
            await send_gallery_item(context.bot, query.message.chat_id, instruments[idx], lang)
        return

    # ---- 🧰 الأدوات المساحية ----
    if data == "menu:tools":
        tools = load_tools()
        if not tools:
            back_kb = InlineKeyboardMarkup([[InlineKeyboardButton(TEXTS[lang]["back"], callback_data="menu:general")]])
            await query.edit_message_text(TEXTS[lang]["no_tools"], reply_markup=back_kb)
            return
        await query.edit_message_text(TEXTS[lang]["choose_tool"], reply_markup=build_gallery_list_keyboard(tools, "tool", lang))
        return

    if data.startswith("tool:"):
        idx = int(data.split(":")[1])
        tools = load_tools()
        if 0 <= idx < len(tools):
            await send_gallery_item(context.bot, query.message.chat_id, tools[idx], lang)
        return

    # ---- 🎯 كويز مقسم حسب المادة ----
    if data == "menu:quiz":
        materials = load_materials()
        if not materials:
            back_kb = InlineKeyboardMarkup([[InlineKeyboardButton(TEXTS[lang]["back_main_menu"], callback_data="back:menu")]])
            await query.edit_message_text(TEXTS[lang]["no_quiz"], reply_markup=back_kb)
            return
        await query.edit_message_text(TEXTS[lang]["choose_quiz_subject"], reply_markup=build_quiz_subjects_keyboard(materials, lang))
        return

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
        keyboard = build_quiz_keyboard(subject_key, question, qidx, lang)
        image_url = question.get("image_url")
        if image_url:
            # لو السؤال معاه صورة، الرسالة الجديدة لازم تبقى Photo مش نص (تليجرام ما بيسمحش تعديل نص لصورة)
            await context.bot.send_photo(chat_id=query.message.chat_id, photo=image_url, caption=build_quiz_question_text(question, lang), reply_markup=keyboard)
        else:
            await query.edit_message_text(build_quiz_question_text(question, lang), reply_markup=keyboard)
        return

    if data.startswith("quiz:"):
        _, subject_key, qidx, optidx = data.split(":")
        qidx, optidx = int(qidx), int(optidx)
        quiz_by_subject = load_quiz()
        question = quiz_by_subject[subject_key][qidx]
        correct = optidx == question["correct_index"]
        result_line = TEXTS[lang]["quiz_correct"] if correct else TEXTS[lang]["quiz_wrong"]
        explanation = t(question, lang, field="explanation")
        text = f"{build_quiz_question_text(question, lang)}\n\n{result_line}"
        if explanation:
            text += f"\n⋙💡︙\nـ• ┉ • ┉ • ┉ • ┉ • ┉ •\n {explanation}\nـ• ┉ • ┉ • ┉ • ┉ • ┉ •"
        back_kb = InlineKeyboardMarkup([[InlineKeyboardButton(TEXTS[lang]["back"], callback_data="menu:quiz")]])
        if question.get("image_url"):
            # الرسالة الأصلية كانت صورة، فبنعدّل الكابشن بتاعها بدل النص
            try:
                await query.edit_message_caption(caption=text, reply_markup=back_kb)
            except Exception:
                await context.bot.send_message(chat_id=query.message.chat_id, text=text, reply_markup=back_kb)
        else:
            await query.edit_message_text(text, reply_markup=back_kb)
        return

    materials = load_materials()
    parts = data.split(":")
    action = parts[0]

    if action == "subj":
        subject_key = parts[1]
        subject = materials[subject_key]
        await query.edit_message_text(
            f"{t(subject, lang)}\n{TEXTS[lang]['choose_category']}",
            reply_markup=build_categories_keyboard(materials, subject_key, lang),
        )

    elif action == "cat":
        subject_key, cat_key = parts[1], parts[2]
        cat = materials[subject_key]["categories"][cat_key]
        await query.edit_message_text(
            f"{t(cat, lang)}\n{TEXTS[lang]['choose_file']}",
            reply_markup=build_files_keyboard(materials, subject_key, cat_key, lang),
        )

    elif action == "file":
        subject_key, cat_key, idx = parts[1], parts[2], int(parts[3])
        file_item = materials[subject_key]["categories"][cat_key]["files"][idx]
        await send_stored_file(
            context.bot, query.message.chat_id,
            file_item["file_id"], file_item.get("type", "document"),
            caption=t(file_item, lang),
        )

    elif action == "custom":
        key = parts[1]
        btn = load_custom_buttons().get(key)
        if not btn:
            return
        if btn.get("kind") == "text":
            await context.bot.send_message(chat_id=query.message.chat_id, text=btn.get("text", ""))
        else:
            await send_stored_file(context.bot, query.message.chat_id, btn["file_id"], btn.get("file_type", "document"))

    # =================================================================================
    # 🧩 هنا تحط شرط أي زر تاني ضفته في build_main_menu فوق، مثال:
    #
    # elif data == "menu:contact":
    #     await query.edit_message_text("تواصل معنا على: ...", reply_markup=build_main_menu(user_id, lang))
    # =================================================================================


# =====================================================================================
#  9) لوحة تحكم الأدمن -- الحالات (Conversation States)
# =====================================================================================
(
    MENU,
    ADD_SUB_TITLE_AR, ADD_SUB_TITLE_EN, ADD_SUB_KEY,
    ADD_CAT_PICK_SUB, ADD_CAT_TITLE_AR, ADD_CAT_TITLE_EN, ADD_CAT_KEY,
    ADD_FILE_PICK_SUB, ADD_FILE_PICK_CAT, ADD_FILE_UPLOAD, ADD_FILE_TITLE_AR, ADD_FILE_TITLE_EN,
    DEL_FILE_PICK_SUB, DEL_FILE_PICK_CAT, DEL_FILE_PICK_FILE,
    DEL_CAT_PICK_SUB, DEL_CAT_PICK_CAT,
    DEL_SUB_PICK,
    ADD_BTN_TITLE_AR, ADD_BTN_TITLE_EN, ADD_BTN_CONTENT, ADD_BTN_LAYOUT,
    DEL_BTN_PICK,
    BROADCAST_WAIT, BROADCAST_CONFIRM,
    ADD_TIP_TEXT, DEL_TIP_PICK,
    ADD_QUIZ_PICK_SUBJECT, ADD_QUIZ_QUESTION, ADD_QUIZ_OPTIONS_AR, ADD_QUIZ_OPTIONS_EN, ADD_QUIZ_CORRECT, ADD_QUIZ_EXPLANATION, ADD_QUIZ_IMAGE,
    DEL_QUIZ_PICK_SUBJECT, DEL_QUIZ_PICK_QUESTION,
    SYS_UPLOAD_PICK, SYS_UPLOAD_WAIT,
    SYS_DELETE_PICK, SYS_DELETE_CONFIRM,
    EDIT_BTN_PICK, EDIT_BTN_TITLE_AR, EDIT_BTN_TITLE_EN,
    EDIT_CORE_PICK, EDIT_CORE_TITLE_AR, EDIT_CORE_TITLE_EN,
    GET_FILE_PICK,
    TOGGLE_CORE_PICK,
    ADD_INSTR_NAME_AR, ADD_INSTR_NAME_EN, ADD_INSTR_DESC_AR, ADD_INSTR_DESC_EN, ADD_INSTR_PHOTO,
    DEL_INSTR_PICK,
    ADD_TOOL_NAME_AR, ADD_TOOL_NAME_EN, ADD_TOOL_DESC_AR, ADD_TOOL_DESC_EN, ADD_TOOL_PHOTO,
    DEL_TOOL_PICK,
    ADD_BOOK_PICK_SUB, ADD_BOOK_TITLE_AR, ADD_BOOK_TITLE_EN, ADD_BOOK_DESC_AR, ADD_BOOK_DESC_EN, ADD_BOOK_FILE,
    DEL_BOOK_PICK_SUB, DEL_BOOK_PICK_BOOK,
    ADD_GEN_TITLE_AR, ADD_GEN_TITLE_EN, ADD_GEN_CONTENT_AR, ADD_GEN_CONTENT_EN, ADD_GEN_FILE,
    DEL_GEN_PICK,
    ADMINS_HUB, ADD_ADMIN_ID, DEL_ADMIN_PICK, PERM_PICK_ADMIN, PERM_TOGGLE,
    SYS_UPLOAD_NEW_NAME, SYS_UPLOAD_NEW_FILE,
) = range(82)


def admin_menu_keyboard() -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton("➕ إضافة", callback_data="admin:add_hub"),
         InlineKeyboardButton("🗑 حذف", callback_data="admin:del_hub")],
        [InlineKeyboardButton("✏️ تعديل", callback_data="admin:edit_hub"),
         InlineKeyboardButton("👁 إخفاء/إظهار زر رئيسي", callback_data="admin:toggle_core")],
        [InlineKeyboardButton("👥 الأدمنية والصلاحيات", callback_data="admin:admins_hub")],
        [InlineKeyboardButton("📢 إذاعة رسالة", callback_data="admin:broadcast")],
        [InlineKeyboardButton("📤 رفع/استبدال ملف", callback_data="admin:sys_upload"),
         InlineKeyboardButton("📥 تحميل ملف", callback_data="admin:get_file")],
        [InlineKeyboardButton("🗑 تصفير ملف بيانات", callback_data="admin:sys_delete"),
         InlineKeyboardButton("🧹 حذف الملفات المؤقتة", callback_data="admin:clean_temp")],
        [InlineKeyboardButton("🔁 إعادة تشغيل البوت", callback_data="admin:restart_ask")],
        [InlineKeyboardButton("📦 نسخة احتياطية", callback_data="admin:backup"),
         InlineKeyboardButton("📋 عرض كل شيء", callback_data="admin:list")],
        [InlineKeyboardButton("❌ إغلاق", callback_data="admin:close")],
        # =============================================================================
        # 🧩 لو عايز تضيف زر إدارة جديد في لوحة الأدمن، فك التعليق وعدّل عليه:
        # [InlineKeyboardButton("🆕 وظيفة جديدة", callback_data="admin:new_feature")],
        # وبعدين ضيف حالة (state) جديدة فوق + شرط في admin_menu_router تحت
        # =============================================================================
    ]
    return InlineKeyboardMarkup(buttons)


def admin_add_hub_keyboard() -> InlineKeyboardMarkup:
    """⭐ كل أزرار الإضافة في مكان واحد -- دوس على أي واحد يوديك لنفس الخطوات المعتادة بالظبط."""
    buttons = [
        [InlineKeyboardButton("📚 مادة", callback_data="admin:add_subject"),
         InlineKeyboardButton("📂 قسم لمادة", callback_data="admin:add_cat")],
        [InlineKeyboardButton("📄 ملف لمادة", callback_data="admin:add_file"),
         InlineKeyboardButton("📖 كتاب", callback_data="admin:add_book")],
        [InlineKeyboardButton("🔭 جهاز", callback_data="admin:add_instr"),
         InlineKeyboardButton("🧰 أداة", callback_data="admin:add_tool")],
        [InlineKeyboardButton("💡 معلومة", callback_data="admin:add_tip"),
         InlineKeyboardButton("🎯 سؤال كويز", callback_data="admin:add_quiz")],
        [InlineKeyboardButton("🧭 قسم مساح عام", callback_data="admin:add_general"),
         InlineKeyboardButton("🔘 زر مخصص", callback_data="admin:add_btn")],
        [InlineKeyboardButton("⬅️ رجوع", callback_data="admin:cancel")],
    ]
    return InlineKeyboardMarkup(buttons)


def admin_del_hub_keyboard() -> InlineKeyboardMarkup:
    """⭐ كل أزرار الحذف في مكان واحد -- نفس فكرة الإضافة بالظبط."""
    buttons = [
        [InlineKeyboardButton("📚 مادة كاملة", callback_data="admin:del_subject"),
         InlineKeyboardButton("📂 قسم من مادة", callback_data="admin:del_cat")],
        [InlineKeyboardButton("📄 ملف من مادة", callback_data="admin:del_file"),
         InlineKeyboardButton("📖 كتاب", callback_data="admin:del_book")],
        [InlineKeyboardButton("🔭 جهاز", callback_data="admin:del_instr"),
         InlineKeyboardButton("🧰 أداة", callback_data="admin:del_tool")],
        [InlineKeyboardButton("💡 معلومة", callback_data="admin:del_tip"),
         InlineKeyboardButton("🎯 سؤال كويز", callback_data="admin:del_quiz")],
        [InlineKeyboardButton("🧭 قسم مساح عام", callback_data="admin:del_general"),
         InlineKeyboardButton("🔘 زر مخصص", callback_data="admin:del_btn")],
        [InlineKeyboardButton("⬅️ رجوع", callback_data="admin:cancel")],
    ]
    return InlineKeyboardMarkup(buttons)


def admin_edit_hub_keyboard() -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton("✏️ اسم زر مخصص", callback_data="admin:edit_btn")],
        [InlineKeyboardButton("✏️ أسماء الأزرار الرئيسية", callback_data="admin:edit_core")],
        [InlineKeyboardButton("⬅️ رجوع", callback_data="admin:cancel")],
    ]
    return InlineKeyboardMarkup(buttons)


def pick_subject_keyboard(materials: dict, prefix: str) -> InlineKeyboardMarkup:
    buttons = [[InlineKeyboardButton(t(s, "ar"), callback_data=f"{prefix}:{key}")] for key, s in materials.items()]
    buttons.append([InlineKeyboardButton("❌ إلغاء", callback_data="admin:cancel")])
    return InlineKeyboardMarkup(buttons)


def pick_category_keyboard(materials: dict, subject_key: str, prefix: str) -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(t(c, "ar"), callback_data=f"{prefix}:{subject_key}:{ckey}")]
        for ckey, c in materials[subject_key]["categories"].items()
    ]
    buttons.append([InlineKeyboardButton("❌ إلغاء", callback_data="admin:cancel")])
    return InlineKeyboardMarkup(buttons)


def pick_file_keyboard(materials: dict, subject_key: str, cat_key: str) -> InlineKeyboardMarkup:
    files = materials[subject_key]["categories"][cat_key]["files"]
    buttons = [
        [InlineKeyboardButton(t(f, "ar"), callback_data=f"delf:{subject_key}:{cat_key}:{idx}")]
        for idx, f in enumerate(files)
    ]
    buttons.append([InlineKeyboardButton("❌ إلغاء", callback_data="admin:cancel")])
    return InlineKeyboardMarkup(buttons)


def pick_custom_button_keyboard(buttons_dict: dict) -> InlineKeyboardMarkup:
    buttons = [[InlineKeyboardButton(t(b, "ar"), callback_data=f"delbtn:{key}")] for key, b in buttons_dict.items()]
    buttons.append([InlineKeyboardButton("❌ إلغاء", callback_data="admin:cancel")])
    return InlineKeyboardMarkup(buttons)


# ---- دخول لوحة الأدمن: عن طريق الأمر /admin أو زرار القائمة الرئيسية ----
async def admin_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("امر مسؤول عن اضافة وحذف وتعديل ملفات البوت (خاص بالمطور فقط).")
        return ConversationHandler.END
    await update.message.reply_text("ـ• ┉ • ┉ • ┉ • ┉ • ┉ •\n🔧 لـوحـة تـحـڪـم الادمـن :\nـ• ┉ • ┉ • ┉ • ┉ • ┉ •", reply_markup=admin_menu_keyboard())
    return MENU


async def admin_start_from_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not is_admin(query.from_user.id):
        await query.answer("• ⚠️︱ امر مسؤول عن اضافة وحذف وتعديل ملفات البوت خاص بالمطور فقط.", show_alert=True)
        return ConversationHandler.END
    await query.answer()
    await query.edit_message_text("ـ• ┉ • ┉ • ┉ • ┉ • ┉ •\n🔧 لـوحـــــة تـحـڪــم الادمـن :\nـ• ┉ • ┉ • ┉ • ┉ • ┉ •", reply_markup=admin_menu_keyboard())
    return MENU


# ---- توجيه القائمة الرئيسية للأدمن ----
async def admin_menu_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    user_id = query.from_user.id

    # ---- بوابة الصلاحيات: تتفعّل تلقائياً على أي زرار مسجل في PERMISSION_MAP ----
    required_perm = PERMISSION_MAP.get(data)
    if required_perm and not has_permission(user_id, required_perm):
        await query.answer("🚫 معندكش صلاحية الوصول للقسم ده. كلم المالك يديك الصلاحية.", show_alert=True)
        return MENU

    await query.answer()
    materials = load_materials()

    if data == "admin:close":
        user_id = query.from_user.id
        lang = get_user_lang(user_id) or "ar"
        await query.edit_message_text(TEXTS[lang]["welcome"], reply_markup=build_main_menu(user_id, lang))
        return ConversationHandler.END

    if data == "admin:cancel":
        await query.edit_message_text("ـ• ┉ • ┉ • ┉ • ┉ • ┉ •\n🔧 لـوحـة تـحـڪـم الادمـن :\nـ• ┉ • ┉ • ┉ • ┉ • ┉ •", reply_markup=admin_menu_keyboard())
        return MENU

    if data == "admin:add_hub":
        await query.edit_message_text("ـ• ┉ • ┉ • ┉ • ┉ • ┉ •\n➕︱اختر إيه اللي عايز تضيفه :\nـ• ┉ • ┉ • ┉ • ┉ • ┉ •", reply_markup=admin_add_hub_keyboard())
        return MENU

    if data == "admin:del_hub":
        await query.edit_message_text("ـ• ┉ • ┉ • ┉ • ┉ • ┉ •\n🗑︱اختر إيه اللي عايز تحذفه :\nـ• ┉ • ┉ • ┉ • ┉ • ┉ •", reply_markup=admin_del_hub_keyboard())
        return MENU

    if data == "admin:edit_hub":
        await query.edit_message_text("ـ• ┉ • ┉ • ┉ • ┉ • ┉ •\n✏️︱اختر إيه اللي عايز تعدّله :\nـ• ┉ • ┉ • ┉ • ┉ • ┉ •", reply_markup=admin_edit_hub_keyboard())
        return MENU

    if data == "admin:list":
        lines = ["📋 كل بيانات البوت:\n"]
        if not materials:
            lines.append("لا توجد مواد بعد.")
        for skey, sdata in materials.items():
            lines.append(f"✬︙ {t(sdata,'ar')} (key: {skey})")
            for ckey, cdata in sdata["categories"].items():
                lines.append(f"   └ {t(cdata,'ar')} (key: {ckey}) — {len(cdata['files'])} ملف")
        custom = load_custom_buttons()
        lines.append(f"\n✬︙ أزرار مخصصة: {len(custom)}")
        lines.append(f"✬︙ معلومات مساحية: {len(load_tips())}")
        total_quiz = sum(len(qs) for qs in load_quiz().values())
        lines.append(f"✬︙ أسئلة كويز (كل المواد): {total_quiz}")
        lines.append(f"✬︙ أجهزة مساحية: {len(load_instruments())}")
        lines.append(f"✬︙ أدوات مساحية: {len(load_tools())}")
        lines.append(f"✬︙ عدد المستخدمين المسجلين: {len(load_users())}")
        channels_display = ", ".join(
            f"{c['name']} ({c.get('username') or c.get('chat_id')})" for c in REQUIRED_CHANNELS
        ) if REQUIRED_CHANNELS else "لا يوجد"
        lines.append(f"✬︙ قنوات الاشتراك الإجباري: {channels_display}")
        lines.append(f"✬︙ الأدمنية (كاملة الصلاحيات): {', '.join(str(a) for a in ADMIN_IDS)}")
        lines.append(f"✬︙ أدمنية بصلاحيات مخصصة: {len(load_admins())}")
        await query.edit_message_text("\n".join(lines), reply_markup=admin_menu_keyboard())
        return MENU

    if data == "admin:backup":
        await send_backup(update, context)
        return MENU

    if data == "admin:add_subject":
        await query.edit_message_text("اكتب اسم المادة بالعربي :")
        return ADD_SUB_TITLE_AR

    if data == "admin:add_cat":
        if not materials:
            await query.edit_message_text("لا توجد مواد بعد.", reply_markup=admin_menu_keyboard())
            return MENU
        await query.edit_message_text("🪐︱اخـتـر الـمـادة لـعـرض الـمـلفـات الـخـاصـة بـهـا :", reply_markup=pick_subject_keyboard(materials, "acsub"))
        return ADD_CAT_PICK_SUB

    if data == "admin:add_file":
        if not materials:
            await query.edit_message_text("❌︱لا توجد مواد بعد.", reply_markup=admin_menu_keyboard())
            return MENU
        await query.edit_message_text("🪐︱اخـتـر الـمـادة لـعـرض الـمـلفـات الـخـاصـة بـهـا :", reply_markup=pick_subject_keyboard(materials, "afsub"))
        return ADD_FILE_PICK_SUB

    if data == "admin:del_file":
        if not materials:
            await query.edit_message_text("❌︱لا توجد مواد بعد.", reply_markup=admin_menu_keyboard())
            return MENU
        await query.edit_message_text("🪐︱اخـتـر الـمـادة لـعـرض الـمـلفـات الـخـاصـة بـهـا :", reply_markup=pick_subject_keyboard(materials, "dfsub"))
        return DEL_FILE_PICK_SUB

    if data == "admin:del_cat":
        if not materials:
            await query.edit_message_text("❌︱لا توجد مواد بعد.", reply_markup=admin_menu_keyboard())
            return MENU
        await query.edit_message_text("🪐︱اخـتـر الـمـادة لـعـرض الـمـلفـات الـخـاصـة بـهـا :", reply_markup=pick_subject_keyboard(materials, "dcsub"))
        return DEL_CAT_PICK_SUB

    if data == "admin:del_subject":
        if not materials:
            await query.edit_message_text("❌︱لا توجد مواد بعد.", reply_markup=admin_menu_keyboard())
            return MENU
        await query.edit_message_text("ـ• ┉ • ┉ • ┉ • ┉ • ┉ •\n⌯⪼ ️اخـتـر الـمـادة الـي عـايـز تـحـذفـهـا : \nـ• ┉ • ┉ • ┉ • ┉ • ┉ •", reply_markup=pick_subject_keyboard(materials, "delsub"))
        return DEL_SUB_PICK

    if data == "admin:add_btn":
        await query.edit_message_text("اكتب عنوان الزر بالعربي :")
        return ADD_BTN_TITLE_AR

    if data == "admin:del_btn":
        custom = load_custom_buttons()
        if not custom:
            await query.edit_message_text("❌︱لا توجد أزرار مخصصة بعد.", reply_markup=admin_menu_keyboard())
            return MENU
        await query.edit_message_text("ـ• ┉ • ┉ • ┉ • ┉ • ┉ •\n⌯⪼ اختر الزر اللي عايز تحذفه :\nـ• ┉ • ┉ • ┉ • ┉ • ┉ •", reply_markup=pick_custom_button_keyboard(custom))
        return DEL_BTN_PICK

    if data == "admin:broadcast":
        await query.edit_message_text("📢︱ابعت الرسالة اللي عايز تذيعها (نص / صورة / فيديو / ملف) :")
        return BROADCAST_WAIT

    if data == "admin:add_tip":
        await query.edit_message_text(
            "📜︱اكتب المعلومة/النصيحة بالشكل ده (سطرين):\n"
            "السطر الأول: النص بالعربي\n"
            "السطر التاني: النص بالإنجليزي\n\n"
            "مثال:\n"
            "الخطأ المسموح به في التسوية يعتمد على درجة الدقة المطلوبة\n"
            "The allowable error in leveling depends on the required precision"
        )
        return ADD_TIP_TEXT

    if data == "admin:del_tip":
        tips = load_tips()
        if not tips:
            await query.edit_message_text("لا توجد معلومات مضافة بعد.", reply_markup=admin_menu_keyboard())
            return MENU
        buttons = [[InlineKeyboardButton(tp.get("text_ar", "")[:40], callback_data=f"deltip:{i}")] for i, tp in enumerate(tips)]
        buttons.append([InlineKeyboardButton("❌ إلغاء", callback_data="admin:cancel")])
        await query.edit_message_text("ـ• ┉ • ┉ • ┉ • ┉ • ┉ •\n⌯⪼ اختر المعلومة اللي عايز تحذفها :\nـ• ┉ • ┉ • ┉ • ┉ • ┉ •", reply_markup=InlineKeyboardMarkup(buttons))
        return DEL_TIP_PICK

    if data == "admin:add_quiz":
        if not materials:
            await query.edit_message_text("❌︱لا توجد مواد بعد، أضف مادة أولاً.", reply_markup=admin_menu_keyboard())
            return MENU
        buttons = [[InlineKeyboardButton(t(s, "ar"), callback_data=f"quizaddsub:{key}")] for key, s in materials.items()]
        buttons.append([InlineKeyboardButton("❌ إلغاء", callback_data="admin:cancel")])
        await query.edit_message_text("ـ• ┉ • ┉ • ┉ • ┉ • ┉ •\n⌯⪼ اختر المادة اللي عايز تضيف السؤال ليها :\nـ• ┉ • ┉ • ┉ • ┉ • ┉ •", reply_markup=InlineKeyboardMarkup(buttons))
        return ADD_QUIZ_PICK_SUBJECT

    if data == "admin:del_quiz":
        if not materials:
            await query.edit_message_text("❌︱لا توجد مواد بعد.", reply_markup=admin_menu_keyboard())
            return MENU
        buttons = [[InlineKeyboardButton(t(s, "ar"), callback_data=f"quizdelsub:{key}")] for key, s in materials.items()]
        buttons.append([InlineKeyboardButton("❌ إلغاء", callback_data="admin:cancel")])
        await query.edit_message_text("ـ• ┉ • ┉ • ┉ • ┉ • ┉ •\n⌯⪼ اختر المادة اللي عايز تحذف سؤال منها :\nـ• ┉ • ┉ • ┉ • ┉ • ┉ •", reply_markup=InlineKeyboardMarkup(buttons))
        return DEL_QUIZ_PICK_SUBJECT

    if data == "admin:add_instr":
        await query.edit_message_text("ـ• ┉ • ┉ • ┉ • ┉ • ┉ •\nاكتب اسم الجهاز بالعربي :\nـ• ┉ • ┉ • ┉ • ┉ • ┉ •")
        return ADD_INSTR_NAME_AR

    if data == "admin:del_instr":
        instruments = load_instruments()
        if not instruments:
            await query.edit_message_text("❌︱لا توجد أجهزة مضافة بعد.", reply_markup=admin_menu_keyboard())
            return MENU
        buttons = [[InlineKeyboardButton(it.get("name_ar", "")[:40], callback_data=f"delinstr:{i}")] for i, it in enumerate(instruments)]
        buttons.append([InlineKeyboardButton("❌ إلغاء", callback_data="admin:cancel")])
        await query.edit_message_text("ـ• ┉ • ┉ • ┉ • ┉ • ┉ •\n⌯⪼ اختر الجهاز اللي عايز تحذفه :\n ـ• ┉ • ┉ • ┉ • ┉ • ┉ •", reply_markup=InlineKeyboardMarkup(buttons))
        return DEL_INSTR_PICK

    if data == "admin:add_tool":
        await query.edit_message_text("📜︱اكتب اسم الأداة بالعربي:")
        return ADD_TOOL_NAME_AR

    if data == "admin:del_tool":
        tools = load_tools()
        if not tools:
            await query.edit_message_text("لا توجد أدوات مضافة بعد 🚶.", reply_markup=admin_menu_keyboard())
            return MENU
        buttons = [[InlineKeyboardButton(tl.get("name_ar", "")[:40], callback_data=f"deltool:{i}")] for i, tl in enumerate(tools)]
        buttons.append([InlineKeyboardButton("❌ إلغاء", callback_data="admin:cancel")])
        await query.edit_message_text("ـ• ┉ • ┉ • ┉ • ┉ • ┉ •\n⌯⪼ اختر الاداة الـي عـايـز تـحـذفـهـا :\nـ• ┉ • ┉ • ┉ • ┉ • ┉ •", reply_markup=InlineKeyboardMarkup(buttons))
        return DEL_TOOL_PICK

    if data == "admin:add_book":
        if not materials:
            await query.edit_message_text("لا توجد مواد بعد، أضف مادة أولاً.", reply_markup=admin_menu_keyboard())
            return MENU
        buttons = [[InlineKeyboardButton(t(s, "ar"), callback_data=f"bookaddsub:{key}")] for key, s in materials.items()]
        buttons.append([InlineKeyboardButton("❌ إلغاء", callback_data="admin:cancel")])
        await query.edit_message_text("ـ• ┉ • ┉ • ┉ • ┉ • ┉ •\n📖︱اختر المادة الـي عـايـز تـضـيـف كـتـاب لـهـا :\nـ• ┉ • ┉ • ┉ • ┉ • ┉ •", reply_markup=InlineKeyboardMarkup(buttons))
        return ADD_BOOK_PICK_SUB

    if data == "admin:del_book":
        if not materials:
            await query.edit_message_text("لا توجد مواد بعد.", reply_markup=admin_menu_keyboard())
            return MENU
        buttons = [[InlineKeyboardButton(t(s, "ar"), callback_data=f"bookdelsub:{key}")] for key, s in materials.items()]
        buttons.append([InlineKeyboardButton("❌ إلغاء", callback_data="admin:cancel")])
        await query.edit_message_text("ـ• ┉ • ┉ • ┉ • ┉ • ┉ •\n📖︱اختر المادة الـي عـايـز تـحـذف كـتـاب مـنـهـا :\nـ• ┉ • ┉ • ┉ • ┉ • ┉ •", reply_markup=InlineKeyboardMarkup(buttons))
        return DEL_BOOK_PICK_SUB

    if data == "admin:add_general":
        await query.edit_message_text("🧭︱اكتب عنوان القسم بالعربي:")
        return ADD_GEN_TITLE_AR

    if data == "admin:del_general":
        general_items = load_general()
        if not general_items:
            await query.edit_message_text("لا توجد أقسام مضافة بعد.", reply_markup=admin_menu_keyboard())
            return MENU
        buttons = [[InlineKeyboardButton(g.get("title_ar", "")[:40], callback_data=f"delgen:{i}")] for i, g in enumerate(general_items)]
        buttons.append([InlineKeyboardButton("❌ إلغاء", callback_data="admin:cancel")])
        await query.edit_message_text("اختر القسم اللي عايز تحذفه:", reply_markup=InlineKeyboardMarkup(buttons))
        return DEL_GEN_PICK

    if data == "admin:admins_hub":
        if not is_owner(user_id):
            await query.edit_message_text("🚫 قسم الأدمنية متاح للمالك بس.", reply_markup=admin_menu_keyboard())
            return MENU
        buttons = InlineKeyboardMarkup([
            [InlineKeyboardButton("➕ إضافة أدمن", callback_data="admin:add_admin"),
             InlineKeyboardButton("➖ إزالة أدمن", callback_data="admin:remove_admin")],
            [InlineKeyboardButton("👥 الأدمنز", callback_data="admin:list_admins")],
            [InlineKeyboardButton("🔑 الصلاحيات", callback_data="admin:permissions")],
            [InlineKeyboardButton("❌ إلغاء", callback_data="admin:cancel")],
        ])
        await query.edit_message_text("ـ• ┉ • ┉ • ┉ • ┉ • ┉ •\n👥︱قسم الأدمنية\nـ• ┉ • ┉ • ┉ • ┉ • ┉ •", reply_markup=buttons)
        return ADMINS_HUB

    if data == "admin:sys_upload":
        buttons = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔄 استبدال ملف موجود", callback_data="admin:sys_upload_existing")],
            [InlineKeyboardButton("🆕 رفع ملف جديد", callback_data="admin:sys_upload_new")],
            [InlineKeyboardButton("❌ إلغاء", callback_data="admin:cancel")],
        ])
        await query.edit_message_text("📤︱عايز تعمل إيه؟", reply_markup=buttons)
        return MENU

    if data == "admin:sys_upload_existing":
        buttons = [[InlineKeyboardButton(f, callback_data=f"sysfile:{f}")] for f in ALLOWED_UPLOAD_FILES]
        buttons.append([InlineKeyboardButton("❌ إلغاء", callback_data="admin:cancel")])
        await query.edit_message_text(
            "📤 اختر الملف اللي عايز تستبدله (هيتاخد نسخة احتياطية منه تلقائياً قبل الاستبدال):",
            reply_markup=InlineKeyboardMarkup(buttons),
        )
        return SYS_UPLOAD_PICK

    if data == "admin:sys_upload_new":
        await query.edit_message_text(
            "🆕︱اكتب اسم الملف الجديد بالكامل، لازم ينتهي بـ .json\n"
            "مثال: my_new_data.json"
        )
        return SYS_UPLOAD_NEW_NAME

    if data == "admin:sys_delete":
        buttons = [[InlineKeyboardButton(f, callback_data=f"sysdel:{f}")] for f in ALLOWED_RESET_FILES]
        buttons.append([InlineKeyboardButton("❌ إلغاء", callback_data="admin:cancel")])
        await query.edit_message_text(
            "⚠️︱ اختر ملف البيانات اللي عايز تصفّره بالكامل (هيترجع فاضي تماماً):",
            reply_markup=InlineKeyboardMarkup(buttons),
        )
        return SYS_DELETE_PICK

    if data == "admin:restart_confirm":
        await query.edit_message_text("ـ• ┉ • ┉ • ┉ • ┉ • ┉ •\n⌯ 🔁 جاري إعادة تشغيل البوت... استنى شوية ودوس /start تاني.\nـ• ┉ • ┉ • ┉ • ┉ • ┉ •")
        os.execv(sys.executable, [sys.executable] + sys.argv)  # بيعيد تشغيل نفس العملية بالكود المحدّث

    if data == "admin:restart_ask":
        buttons = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ نعم، أعد التشغيل الآن", callback_data="admin:restart_confirm")],
            [InlineKeyboardButton("❌ إلغاء", callback_data="admin:cancel")],
        ])
        await query.edit_message_text("متأكد إنك عايز تعيد تشغيل البوت دلوقت؟", reply_markup=buttons)
        return MENU

    if data == "admin:get_file":
        existing = [f for f in ALLOWED_UPLOAD_FILES if os.path.exists(f)]
        if not existing:
            await query.edit_message_text("مفيش ملفات موجودة دلوقت.", reply_markup=admin_menu_keyboard())
            return MENU
        buttons = [[InlineKeyboardButton(f, callback_data=f"getfile:{f}")] for f in existing]
        buttons.append([InlineKeyboardButton("❌ إلغاء", callback_data="admin:cancel")])
        await query.edit_message_text("📥︱ اختر الملف اللي عايز تحمّله:", reply_markup=InlineKeyboardMarkup(buttons))
        return GET_FILE_PICK

    if data == "admin:clean_temp":
        removed = clean_temp_files()
        if removed:
            await query.edit_message_text("🧹 تم حذف الملفات المؤقتة دي:\n" + "\n".join(removed), reply_markup=admin_menu_keyboard())
        else:
            await query.edit_message_text("مفيش ملفات مؤقتة موجودة أصلاً. البوت نضيف ✅", reply_markup=admin_menu_keyboard())
        return MENU

    if data == "admin:toggle_core":
        labels = load_menu_labels()
        buttons = []
        for key in CORE_MENU_KEYS:
            hidden = labels.get(key, {}).get("hidden", False)
            status_icon = "🙈 مخفي" if hidden else "👁 ظاهر"
            display_name = t(labels[key], "ar") if key in labels and labels[key].get("title_ar") else TEXTS["ar"][key]
            buttons.append([InlineKeyboardButton(f"{status_icon} — {display_name}", callback_data=f"coretoggle:{key}")])
        buttons.append([InlineKeyboardButton("❌ إلغاء", callback_data="admin:cancel")])
        await query.edit_message_text("اضغط على أي زرار عشان تبدّل حالته (ظاهر/مخفي):", reply_markup=InlineKeyboardMarkup(buttons))
        return TOGGLE_CORE_PICK

    if data == "admin:edit_btn":
        custom = load_custom_buttons()
        if not custom:
            await query.edit_message_text("لا توجد أزرار مخصصة بعد.", reply_markup=admin_menu_keyboard())
            return MENU
        buttons = [[InlineKeyboardButton(t(b, "ar"), callback_data=f"editbtn:{key}")] for key, b in custom.items()]
        buttons.append([InlineKeyboardButton("❌ إلغاء", callback_data="admin:cancel")])
        await query.edit_message_text("اختر الزر اللي عايز تعدّل اسمه:", reply_markup=InlineKeyboardMarkup(buttons))
        return EDIT_BTN_PICK

    if data == "admin:edit_core":
        buttons = [[InlineKeyboardButton(TEXTS["ar"][key], callback_data=f"editcore:{key}")] for key in CORE_MENU_KEYS]
        buttons.append([InlineKeyboardButton("❌ إلغاء", callback_data="admin:cancel")])
        await query.edit_message_text("اختر الزرار الرئيسي اللي عايز تعدّل اسمه:", reply_markup=InlineKeyboardMarkup(buttons))
        return EDIT_CORE_PICK

    return MENU


# ---- إضافة مادة ----
async def add_sub_title_ar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["new_sub_ar"] = update.message.text.strip()
    await update.message.reply_text("📜︱اكتب اسم المادة بالإنجليزي:")
    return ADD_SUB_TITLE_EN


async def add_sub_title_en(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["new_sub_en"] = update.message.text.strip()
    await update.message.reply_text("📜︱اكتب معرّف قصير بالإنجليزي بدون مسافات (مثال: subject9):")
    return ADD_SUB_KEY


async def add_sub_key(update: Update, context: ContextTypes.DEFAULT_TYPE):
    key = update.message.text.strip().replace(" ", "_")
    materials = load_materials()
    if key in materials:
        await update.message.reply_text("المعرف مستخدم بالفعل، اكتب معرف تاني:")
        return ADD_SUB_KEY

    materials[key] = {
        "title_ar": context.user_data["new_sub_ar"],
        "title_en": context.user_data["new_sub_en"],
        "categories": {
            "summaries": {"title_ar": "📄 ملخصات PDF", "title_en": "📄 PDF Summaries", "files": []},
            "videos": {"title_ar": "🎥 الفيديوهات", "title_en": "🎥 Videos", "files": []},
            "exams": {"title_ar": "✅ أسئلة محلولة", "title_en": "✅ Solved Questions", "files": []},
        },
    }
    save_materials(materials)
    await update.message.reply_text("✅ تمت إضافة المادة (بـ 3 أقسام جاهزة تلقائياً).", reply_markup=admin_menu_keyboard())
    return MENU


# ---- إضافة قسم لمادة موجودة ----
async def add_cat_pick_sub(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data["target_subject"] = query.data.split(":")[1]
    await query.edit_message_text("اكتب اسم القسم بالعربي:")
    return ADD_CAT_TITLE_AR


async def add_cat_title_ar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["new_cat_ar"] = update.message.text.strip()
    await update.message.reply_text("اكتب اسم القسم بالإنجليزي:")
    return ADD_CAT_TITLE_EN


async def add_cat_title_en(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["new_cat_en"] = update.message.text.strip()
    await update.message.reply_text("اكتب معرّف قصير بالإنجليزي بدون مسافات:")
    return ADD_CAT_KEY


async def add_cat_key(update: Update, context: ContextTypes.DEFAULT_TYPE):
    key = update.message.text.strip().replace(" ", "_")
    subject_key = context.user_data["target_subject"]
    materials = load_materials()
    if key in materials[subject_key]["categories"]:
        await update.message.reply_text("المعرف مستخدم بالفعل داخل المادة دي، اكتب معرف تاني:")
        return ADD_CAT_KEY

    materials[subject_key]["categories"][key] = {
        "title_ar": context.user_data["new_cat_ar"],
        "title_en": context.user_data["new_cat_en"],
        "files": [],
    }
    save_materials(materials)
    await update.message.reply_text("✅ تمت إضافة القسم.", reply_markup=admin_menu_keyboard())
    return MENU


# ---- إضافة ملف ----
async def add_file_pick_sub(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    subject_key = query.data.split(":")[1]
    materials = load_materials()
    context.user_data["target_subject"] = subject_key
    await query.edit_message_text("✬︙ اختر القسم :", reply_markup=pick_category_keyboard(materials, subject_key, "afcat"))
    return ADD_FILE_PICK_CAT


async def add_file_pick_cat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    _, subject_key, cat_key = query.data.split(":")
    context.user_data["target_subject"] = subject_key
    context.user_data["target_category"] = cat_key
    await query.edit_message_text("📎 دلوقتي ابعت الملف (PDF / فيديو / صورة / صوت / GIF...):")
    return ADD_FILE_UPLOAD


async def add_file_upload(update: Update, context: ContextTypes.DEFAULT_TYPE):
    file_id, file_type = parse_media_input(update.message)
    if not file_id:
        await update.message.reply_text("من فضلك ابعت ملف مدعوم (مستند/فيديو/صورة/صوت/GIF) أو الصق رابط مباشر ليه.")
        return ADD_FILE_UPLOAD

    context.user_data["new_file_id"] = file_id
    context.user_data["new_file_type"] = file_type
    await update.message.reply_text("اكتب عنوان الملف بالعربي:")
    return ADD_FILE_TITLE_AR


async def add_file_title_ar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["new_file_ar"] = update.message.text.strip()
    await update.message.reply_text("اكتب عنوان الملف بالإنجليزي:")
    return ADD_FILE_TITLE_EN


async def add_file_title_en(update: Update, context: ContextTypes.DEFAULT_TYPE):
    title_en = update.message.text.strip()
    subject_key = context.user_data["target_subject"]
    cat_key = context.user_data["target_category"]

    materials = load_materials()
    materials[subject_key]["categories"][cat_key]["files"].append({
        "title_ar": context.user_data["new_file_ar"],
        "title_en": title_en,
        "file_id": context.user_data["new_file_id"],
        "type": context.user_data["new_file_type"],
    })
    save_materials(materials)
    await update.message.reply_text("✅ تمت إضافة الملف بنجاح.", reply_markup=admin_menu_keyboard())
    return MENU


# ---- حذف ملف ----
async def del_file_pick_sub(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    subject_key = query.data.split(":")[1]
    materials = load_materials()
    await query.edit_message_text("اختر القسم:", reply_markup=pick_category_keyboard(materials, subject_key, "dfcat"))
    return DEL_FILE_PICK_CAT


async def del_file_pick_cat(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
    materials = load_materials()
    removed = materials[subject_key]["categories"][cat_key]["files"].pop(int(idx))
    save_materials(materials)
    await query.edit_message_text(f"🗑 تم حذف الملف: {t(removed,'ar')}", reply_markup=admin_menu_keyboard())
    return MENU


# ---- حذف قسم ----
async def del_cat_pick_sub(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    subject_key = query.data.split(":")[1]
    materials = load_materials()
    await query.edit_message_text("اختر القسم اللي عايز تحذفه:", reply_markup=pick_category_keyboard(materials, subject_key, "dccat"))
    return DEL_CAT_PICK_CAT


async def del_cat_pick_cat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    _, subject_key, cat_key = query.data.split(":")
    materials = load_materials()
    removed = materials[subject_key]["categories"].pop(cat_key)
    save_materials(materials)
    await query.edit_message_text(f"🗑 تم حذف القسم: {t(removed,'ar')}", reply_markup=admin_menu_keyboard())
    return MENU


# ---- حذف مادة كاملة ----
async def del_sub_pick(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    subject_key = query.data.split(":")[1]
    materials = load_materials()
    removed = materials.pop(subject_key)
    save_materials(materials)
    await query.edit_message_text(f"🗑 تم حذف المادة بالكامل: {t(removed,'ar')}", reply_markup=admin_menu_keyboard())
    return MENU


# ---- إضافة زر مخصص ----
async def add_btn_title_ar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["new_btn_ar"] = update.message.text.strip()
    await update.message.reply_text("اكتب عنوان الزر بالإنجليزي:")
    return ADD_BTN_TITLE_EN


async def add_btn_title_en(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["new_btn_en"] = update.message.text.strip()
    await update.message.reply_text("ابعت النص أو الملف اللي هيتبعت للمستخدم لما يدوس الزر ده:")
    return ADD_BTN_CONTENT


async def add_btn_content(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message

    file_id, file_type = parse_media_input(message)
    if file_id:
        context.user_data["new_btn_kind"] = "file"
        context.user_data["new_btn_file_id"] = file_id
        context.user_data["new_btn_file_type"] = file_type
    elif message.text:
        context.user_data["new_btn_kind"] = "text"
        context.user_data["new_btn_text"] = message.text
    else:
        await message.reply_text("من فضلك ابعت نص أو ملف مدعوم.")
        return ADD_BTN_CONTENT

    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("➡️ بجانب آخر زر مضاف", callback_data="btnlayout:same_row")],
        [InlineKeyboardButton("⬇️ في سطر لوحده", callback_data="btnlayout:new_row")],
    ])
    await message.reply_text("اختر شكل الزر في القائمة الرئيسية:", reply_markup=buttons)
    return ADD_BTN_LAYOUT


async def add_btn_layout(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    layout = query.data.split(":", 1)[1]  # same_row أو new_row

    custom = load_custom_buttons()
    new_key = f"custom{len(custom) + 1}"

    entry = {
        "title_ar": context.user_data["new_btn_ar"],
        "title_en": context.user_data["new_btn_en"],
        "kind": context.user_data["new_btn_kind"],
        "layout": layout,
    }
    if entry["kind"] == "file":
        entry["file_id"] = context.user_data["new_btn_file_id"]
        entry["file_type"] = context.user_data["new_btn_file_type"]
    else:
        entry["text"] = context.user_data["new_btn_text"]

    custom[new_key] = entry
    save_custom_buttons(custom)

    await query.edit_message_text("✅ تمت إضافة الزر المخصص، هيظهر في القائمة الرئيسية فوراً.", reply_markup=admin_menu_keyboard())
    return MENU


# ---- حذف زر مخصص ----
async def del_btn_pick(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    key = query.data.split(":")[1]
    custom = load_custom_buttons()
    removed = custom.pop(key, None)
    save_custom_buttons(custom)
    name = t(removed, "ar") if removed else key
    await query.edit_message_text(f"🗑 تم حذف الزر: {name}", reply_markup=admin_menu_keyboard())
    return MENU


# ---- 💡 إضافة/حذف معلومة مساحية (Tips) ----
def _split_ar_en(text: str):
    """يقسم رسالة من سطرين لـ (عربي, إنجليزي). لو سطر واحد بس، يستخدمه للاتنين."""
    lines = [l.strip() for l in text.strip().split("\n") if l.strip()]
    if len(lines) >= 2:
        return lines[0], lines[1]
    if len(lines) == 1:
        return lines[0], lines[0]
    return "", ""


async def add_tip_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    ar, en = _split_ar_en(update.message.text)
    tips = load_tips()
    tips.append({"text_ar": ar, "text_en": en})
    save_tips(tips)
    await update.message.reply_text("✅ تمت إضافة المعلومة.", reply_markup=admin_menu_keyboard())
    return MENU


async def del_tip_pick(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    idx = int(query.data.split(":")[1])
    tips = load_tips()
    if 0 <= idx < len(tips):
        removed = tips.pop(idx)
        save_tips(tips)
        await query.edit_message_text(f"🗑 تم حذف: {removed.get('text_ar','')[:40]}", reply_markup=admin_menu_keyboard())
    else:
        await query.edit_message_text("العنصر ده مش موجود.", reply_markup=admin_menu_keyboard())
    return MENU


# ---- 🎯 إضافة/حذف سؤال كويز (مقسم حسب المادة) ----
async def add_quiz_pick_subject(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    subject_key = query.data.split(":", 1)[1]
    context.user_data["quiz_target_subject"] = subject_key
    await query.edit_message_text(
        "اكتب نص السؤال بالشكل ده (سطرين):\n"
        "السطر الأول: السؤال بالعربي\n"
        "السطر التاني: السؤال بالإنجليزي"
    )
    return ADD_QUIZ_QUESTION


async def add_quiz_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    ar, en = _split_ar_en(update.message.text)
    context.user_data["new_quiz_q_ar"] = ar
    context.user_data["new_quiz_q_en"] = en
    await update.message.reply_text("اكتب الاختيارات بالعربي مفصولة بفاصلة , (مثال: خطأ,صح,غير محدد):")
    return ADD_QUIZ_OPTIONS_AR


async def add_quiz_options_ar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    options_ar = [o.strip() for o in update.message.text.split(",") if o.strip()]
    if len(options_ar) < 2:
        await update.message.reply_text("لازم اختيارين على الأقل، مفصولين بفاصلة. جرب تاني:")
        return ADD_QUIZ_OPTIONS_AR
    context.user_data["new_quiz_options_ar"] = options_ar
    await update.message.reply_text("اكتب نفس الاختيارات بالإنجليزي مفصولة بفاصلة , بنفس الترتيب:")
    return ADD_QUIZ_OPTIONS_EN


async def add_quiz_options_en(update: Update, context: ContextTypes.DEFAULT_TYPE):
    options_en = [o.strip() for o in update.message.text.split(",") if o.strip()]
    context.user_data["new_quiz_options_en"] = options_en
    options_ar = context.user_data["new_quiz_options_ar"]
    numbered = "\n".join(f"{i+1}. {opt}" for i, opt in enumerate(options_ar))
    await update.message.reply_text(f"اكتب رقم الاختيار الصحيح:\n{numbered}")
    return ADD_QUIZ_CORRECT


async def add_quiz_correct(update: Update, context: ContextTypes.DEFAULT_TYPE):
    options_ar = context.user_data["new_quiz_options_ar"]
    try:
        correct_num = int(update.message.text.strip())
        if not (1 <= correct_num <= len(options_ar)):
            raise ValueError
    except ValueError:
        await update.message.reply_text(f"اكتب رقم صحيح من 1 لـ {len(options_ar)}:")
        return ADD_QUIZ_CORRECT

    context.user_data["new_quiz_correct"] = correct_num - 1
    await update.message.reply_text(
        "اكتب شرح الإجابة (اختياري) بالشكل ده (سطرين عربي/إنجليزي)، أو اكتب - لو مفيش شرح:"
    )
    return ADD_QUIZ_EXPLANATION


async def add_quiz_explanation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if text == "-":
        exp_ar, exp_en = "", ""
    else:
        exp_ar, exp_en = _split_ar_en(text)

    context.user_data["new_quiz_exp_ar"] = exp_ar
    context.user_data["new_quiz_exp_en"] = exp_en
    await update.message.reply_text("🖼️︱ابعت صورة توضيحية للسؤال أو الصق رابط صورة مباشر (اختياري)، أو اكتب - لتخطي:")
    return ADD_QUIZ_IMAGE


async def add_quiz_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    image_url = ""
    if message.text and message.text.strip() == "-":
        pass
    else:
        source, kind = parse_media_input(message)
        if source:
            image_url = source
        else:
            await message.reply_text("🖼️︱ابعت صورة، أو الصق رابط صورة مباشر، أو اكتب - لتخطي:")
            return ADD_QUIZ_IMAGE

    subject_key = context.user_data["quiz_target_subject"]
    quiz_by_subject = load_quiz()
    quiz_by_subject.setdefault(subject_key, [])
    quiz_by_subject[subject_key].append({
        "question_ar": context.user_data["new_quiz_q_ar"],
        "question_en": context.user_data["new_quiz_q_en"],
        "options_ar": context.user_data["new_quiz_options_ar"],
        "options_en": context.user_data["new_quiz_options_en"],
        "correct_index": context.user_data["new_quiz_correct"],
        "explanation_ar": context.user_data["new_quiz_exp_ar"],
        "explanation_en": context.user_data["new_quiz_exp_en"],
        "image_url": image_url,
    })
    save_quiz(quiz_by_subject)
    await message.reply_text("✅ تمت إضافة السؤال للمادة المختارة.", reply_markup=admin_menu_keyboard())
    return MENU


async def del_quiz_pick_subject(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    subject_key = query.data.split(":", 1)[1]
    quiz_by_subject = load_quiz()
    questions = quiz_by_subject.get(subject_key, [])
    if not questions:
        await query.edit_message_text("لا توجد أسئلة على المادة دي.", reply_markup=admin_menu_keyboard())
        return MENU
    context.user_data["quiz_target_subject"] = subject_key
    buttons = [[InlineKeyboardButton(q.get("question_ar", "")[:40], callback_data=f"delquizq:{i}")] for i, q in enumerate(questions)]
    buttons.append([InlineKeyboardButton("❌ إلغاء", callback_data="admin:cancel")])
    await query.edit_message_text("اختر السؤال اللي عايز تحذفه:", reply_markup=InlineKeyboardMarkup(buttons))
    return DEL_QUIZ_PICK_QUESTION


async def del_quiz_pick_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    idx = int(query.data.split(":")[1])
    subject_key = context.user_data["quiz_target_subject"]
    quiz_by_subject = load_quiz()
    questions = quiz_by_subject.get(subject_key, [])
    if 0 <= idx < len(questions):
        removed = questions.pop(idx)
        save_quiz(quiz_by_subject)
        await query.edit_message_text(f"🗑 تم حذف السؤال: {removed.get('question_ar','')[:40]}", reply_markup=admin_menu_keyboard())
    else:
        await query.edit_message_text("السؤال ده مش موجود.", reply_markup=admin_menu_keyboard())
    return MENU


# ---- 🔭 إضافة/حذف جهاز مساحي ----
async def add_instr_name_ar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["new_instr_name_ar"] = update.message.text.strip()
    await update.message.reply_text("اكتب اسم الجهاز بالإنجليزي:")
    return ADD_INSTR_NAME_EN


async def add_instr_name_en(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["new_instr_name_en"] = update.message.text.strip()
    await update.message.reply_text("اكتب وصف/استخدام الجهاز بالعربي:")
    return ADD_INSTR_DESC_AR


async def add_instr_desc_ar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["new_instr_desc_ar"] = update.message.text.strip()
    await update.message.reply_text("اكتب وصف/استخدام الجهاز بالإنجليزي:")
    return ADD_INSTR_DESC_EN


async def add_instr_desc_en(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["new_instr_desc_en"] = update.message.text.strip()
    await update.message.reply_text("ابعت صورة الجهاز، أو اكتب - لو مفيش صورة:")
    return ADD_INSTR_PHOTO


async def add_instr_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    photo_id = ""
    if message.text and message.text.strip() == "-":
        pass
    else:
        source, kind = parse_media_input(message)
        if source:
            photo_id = source
        else:
            await message.reply_text("📎︱ابعت صورة، أو الصق رابط صورة مباشر، أو اكتب - لتخطي الصورة:")
            return ADD_INSTR_PHOTO

    instruments = load_instruments()
    instruments.append({
        "name_ar": context.user_data["new_instr_name_ar"],
        "name_en": context.user_data["new_instr_name_en"],
        "desc_ar": context.user_data["new_instr_desc_ar"],
        "desc_en": context.user_data["new_instr_desc_en"],
        "photo_file_id": photo_id,
    })
    save_instruments(instruments)
    await message.reply_text("✅ تمت إضافة الجهاز.", reply_markup=admin_menu_keyboard())
    return MENU


async def del_instr_pick(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    idx = int(query.data.split(":")[1])
    instruments = load_instruments()
    if 0 <= idx < len(instruments):
        removed = instruments.pop(idx)
        save_instruments(instruments)
        await query.edit_message_text(f"🗑 تم حذف الجهاز: {removed.get('name_ar','')[:40]}", reply_markup=admin_menu_keyboard())
    else:
        await query.edit_message_text("الجهاز ده مش موجود.", reply_markup=admin_menu_keyboard())
    return MENU


# ---- 🧰 إضافة/حذف أداة مساحية (نفس فكرة الأجهزة بالظبط) ----
async def add_tool_name_ar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["new_tool_name_ar"] = update.message.text.strip()
    await update.message.reply_text("اكتب اسم الأداة بالإنجليزي:")
    return ADD_TOOL_NAME_EN


async def add_tool_name_en(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["new_tool_name_en"] = update.message.text.strip()
    await update.message.reply_text("اكتب وصف/استخدام الأداة بالعربي:")
    return ADD_TOOL_DESC_AR


async def add_tool_desc_ar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["new_tool_desc_ar"] = update.message.text.strip()
    await update.message.reply_text("اكتب وصف/استخدام الأداة بالإنجليزي:")
    return ADD_TOOL_DESC_EN


async def add_tool_desc_en(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["new_tool_desc_en"] = update.message.text.strip()
    await update.message.reply_text("ابعت صورة الأداة، أو اكتب - لو مفيش صورة:")
    return ADD_TOOL_PHOTO


async def add_tool_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    photo_id = ""
    if message.text and message.text.strip() == "-":
        pass
    else:
        source, kind = parse_media_input(message)
        if source:
            photo_id = source
        else:
            await message.reply_text("📎︱ابعت صورة، أو الصق رابط صورة مباشر، أو اكتب - لتخطي الصورة:")
            return ADD_TOOL_PHOTO

    tools = load_tools()
    tools.append({
        "name_ar": context.user_data["new_tool_name_ar"],
        "name_en": context.user_data["new_tool_name_en"],
        "desc_ar": context.user_data["new_tool_desc_ar"],
        "desc_en": context.user_data["new_tool_desc_en"],
        "photo_file_id": photo_id,
    })
    save_tools(tools)
    await message.reply_text("✅ تمت إضافة الأداة.", reply_markup=admin_menu_keyboard())
    return MENU


async def del_tool_pick(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    idx = int(query.data.split(":")[1])
    tools = load_tools()
    if 0 <= idx < len(tools):
        removed = tools.pop(idx)
        save_tools(tools)
        await query.edit_message_text(f"🗑 تم حذف الأداة: {removed.get('name_ar','')[:40]}", reply_markup=admin_menu_keyboard())
    else:
        await query.edit_message_text("الأداة دي مش موجودة.", reply_markup=admin_menu_keyboard())
    return MENU


# ---- 📤 رفع/استبدال ملف من داخل تليجرام (bot.py / أي ملف بيانات) ----
async def sys_upload_new_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = update.message.text.strip()
    if not name.endswith(".json") or "/" in name or ".." in name or " " in name:
        await update.message.reply_text("الاسم لازم ينتهي بـ .json وبدون مسافات أو رموز غريبة. جرب تاني:")
        return SYS_UPLOAD_NEW_NAME
    context.user_data["sys_new_filename"] = name
    await update.message.reply_text(f"📎︱دلوقتي ابعت الملف اللي هيتحفظ باسم «{name}»:")
    return SYS_UPLOAD_NEW_FILE


async def sys_upload_new_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    if not message.document:
        await message.reply_text("من فضلك ابعت الملف كـ Document.")
        return SYS_UPLOAD_NEW_FILE

    filename = context.user_data["sys_new_filename"]
    tg_file = await context.bot.get_file(message.document.file_id)
    await tg_file.download_to_drive(custom_path=filename)

    try:
        with open(filename, "r", encoding="utf-8") as f:
            json.load(f)
    except Exception as e:
        os.remove(filename)
        await message.reply_text(f"⚠️ الملف مش JSON سليم:\n`{e}`", parse_mode="Markdown", reply_markup=admin_menu_keyboard())
        return MENU

    await message.reply_text(f"✅ تم حفظ الملف الجديد «{filename}» بنجاح.", reply_markup=admin_menu_keyboard())
    return MENU


async def sys_upload_pick(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    filename = query.data.split(":", 1)[1]
    context.user_data["sys_target_file"] = filename
    await query.edit_message_text(f"📎 ابعت الملف الجديد كـ Document عشان يستبدل «{filename}»:")
    return SYS_UPLOAD_WAIT


async def sys_upload_wait(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    if not message.document:
        await message.reply_text("من فضلك ابعت الملف كـ Document (ملف مرفق)، مش صورة أو نص.")
        return SYS_UPLOAD_WAIT

    target = context.user_data["sys_target_file"]
    tmp_path = f"{target}.new"

    tg_file = await context.bot.get_file(message.document.file_id)
    await tg_file.download_to_drive(custom_path=tmp_path)

    # ---- تحقق من سلامة الملف قبل ما نستبدل بيه القديم ----
    if target.endswith(".py"):
        try:
            py_compile.compile(tmp_path, doraise=True)
        except Exception as e:
            os.remove(tmp_path)
            await message.reply_text(f"⚠️ الملف فيه خطأ برمجي، متقدرش تستخدمه:\n`{e}`", parse_mode="Markdown", reply_markup=admin_menu_keyboard())
            return MENU
    elif target.endswith(".json"):
        try:
            with open(tmp_path, "r", encoding="utf-8") as f:
                json.load(f)
        except Exception as e:
            os.remove(tmp_path)
            await message.reply_text(f"⚠️ الملف مش JSON سليم:\n`{e}`", parse_mode="Markdown", reply_markup=admin_menu_keyboard())
            return MENU

    # ---- ناخد نسخة احتياطية من الملف القديم قبل الاستبدال (لو موجود أصلاً) ----
    if os.path.exists(target):
        shutil.copy(target, f"{target}.bak")

    os.replace(tmp_path, target)

    if target == "bot.py":
        buttons = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔁 إعادة التشغيل الآن", callback_data="admin:restart_confirm")],
            [InlineKeyboardButton("⏭ لاحقاً", callback_data="admin:cancel")],
        ])
        await message.reply_text(
            f"✅ تم استبدال {target} بنجاح (اتاخدلك نسخة احتياطية باسم {target}.bak).\n"
            f"لازم تعمل ريستارت عشان الكود الجديد يشتغل فعلياً:",
            reply_markup=buttons,
        )
        return MENU

    await message.reply_text(f"✅ تم استبدال {target} بنجاح (اتاخدلك نسخة احتياطية باسم {target}.bak).", reply_markup=admin_menu_keyboard())
    return MENU


# ---- 🗑 تصفير ملف بيانات (رجوعه لملف فاضي) ----
async def sys_delete_pick(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    filename = query.data.split(":", 1)[1]
    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ متأكد، صفّره", callback_data=f"sysdelconfirm:{filename}")],
        [InlineKeyboardButton("❌ إلغاء", callback_data="admin:cancel")],
    ])
    await query.edit_message_text(f"⚠️ متأكد إنك عايز تصفّر {filename}؟ كل البيانات اللي فيه هتتمسح (هتتاخد نسخة احتياطية الأول).", reply_markup=buttons)
    return SYS_DELETE_CONFIRM


async def sys_delete_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    filename = query.data.split(":", 1)[1]

    if os.path.exists(filename):
        shutil.copy(filename, f"{filename}.bak")

    # الملفات اللي شكلها الطبيعي "list" لما تكون فاضية، والباقي "dict"
    list_type_files = ("tips.json", "instruments.json", "tools.json", "general_surveyor.json")
    empty_value = [] if filename in list_type_files else {}
    _save_json(filename, empty_value)

    await query.edit_message_text(f"🗑 تم تصفير {filename} (اتاخدلك نسخة احتياطية باسم {filename}.bak).", reply_markup=admin_menu_keyboard())
    return MENU


# ---- 🧹 حذف الملفات المؤقتة ----
def clean_temp_files() -> list:
    """بيدور على ملفات .bak و .new والمجلد __pycache__ ويمسحهم. بيرجع قائمة بأسماء اللي اتمسحوا."""
    removed = []
    for fname in os.listdir("."):
        if fname.endswith(".bak") or fname.endswith(".new"):
            try:
                os.remove(fname)
                removed.append(fname)
            except OSError:
                pass
    if os.path.isdir("__pycache__"):
        shutil.rmtree("__pycache__", ignore_errors=True)
        removed.append("__pycache__/")
    return removed


# ---- 📥 تحميل ملف من ملفات البوت الهيكلية ----
async def get_file_pick(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    filename = query.data.split(":", 1)[1]
    if not os.path.exists(filename):
        await query.edit_message_text(f"الملف {filename} مش موجود.", reply_markup=admin_menu_keyboard())
        return MENU
    await context.bot.send_document(chat_id=query.message.chat_id, document=open(filename, "rb"), filename=filename)
    await query.message.reply_text("🔧 لوحة تحكم الأدمن:", reply_markup=admin_menu_keyboard())
    return MENU


# ---- 👁 إخفاء/إظهار زرار رئيسي ----
async def toggle_core_pick(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    key = query.data.split(":", 1)[1]

    labels = load_menu_labels()
    if key not in labels:
        labels[key] = {}
    labels[key]["hidden"] = not labels[key].get("hidden", False)
    save_menu_labels(labels)

    status = "🙈 اتخفى" if labels[key]["hidden"] else "👁 بقى ظاهر"
    await query.edit_message_text(f"تم: {TEXTS['ar'][key]} {status}.", reply_markup=admin_menu_keyboard())
    return MENU


# ---- ✏️ تعديل اسم زر مخصص ----
async def edit_btn_pick(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    key = query.data.split(":", 1)[1]
    context.user_data["edit_btn_key"] = key
    await query.edit_message_text("اكتب الاسم الجديد بالعربي:")
    return EDIT_BTN_TITLE_AR


async def edit_btn_title_ar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["edit_btn_ar"] = update.message.text.strip()
    await update.message.reply_text("اكتب الاسم الجديد بالإنجليزي:")
    return EDIT_BTN_TITLE_EN


async def edit_btn_title_en(update: Update, context: ContextTypes.DEFAULT_TYPE):
    key = context.user_data["edit_btn_key"]
    custom = load_custom_buttons()
    if key in custom:
        custom[key]["title_ar"] = context.user_data["edit_btn_ar"]
        custom[key]["title_en"] = update.message.text.strip()
        save_custom_buttons(custom)
        await update.message.reply_text("✅ تم تعديل اسم الزر.", reply_markup=admin_menu_keyboard())
    else:
        await update.message.reply_text("الزر ده مش موجود.", reply_markup=admin_menu_keyboard())
    return MENU


# ---- ✏️ تعديل أسماء الأزرار الرئيسية ----
async def edit_core_pick(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    key = query.data.split(":", 1)[1]
    context.user_data["edit_core_key"] = key
    await query.edit_message_text(f"الاسم الحالي: {TEXTS['ar'][key]}\nاكتب الاسم الجديد بالعربي:")
    return EDIT_CORE_TITLE_AR


async def edit_core_title_ar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["edit_core_ar"] = update.message.text.strip()
    await update.message.reply_text("اكتب الاسم الجديد بالإنجليزي:")
    return EDIT_CORE_TITLE_EN


async def edit_core_title_en(update: Update, context: ContextTypes.DEFAULT_TYPE):
    key = context.user_data["edit_core_key"]
    labels = load_menu_labels()
    if key not in labels:
        labels[key] = {}
    labels[key]["title_ar"] = context.user_data["edit_core_ar"]
    labels[key]["title_en"] = update.message.text.strip()
    save_menu_labels(labels)
    await update.message.reply_text("✅ تم تعديل اسم الزرار الرئيسي.", reply_markup=admin_menu_keyboard())
    return MENU


# ---- 📖 إضافة/حذف كتاب دراسي (مقسم حسب المادة، بيقبل PDF أو صورة) ----
async def add_book_pick_sub(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    subject_key = query.data.split(":", 1)[1]
    context.user_data["book_target_subject"] = subject_key
    await query.edit_message_text("📖︱اكتب اسم الكتاب بالعربي:")
    return ADD_BOOK_TITLE_AR


async def add_book_title_ar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["new_book_title_ar"] = update.message.text.strip()
    await update.message.reply_text("📖︱اكتب اسم الكتاب بالإنجليزي:")
    return ADD_BOOK_TITLE_EN


async def add_book_title_en(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["new_book_title_en"] = update.message.text.strip()
    await update.message.reply_text("📝︱اكتب وصف مختصر للكتاب بالعربي (أو اكتب - لتخطي الوصف):")
    return ADD_BOOK_DESC_AR


async def add_book_desc_ar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    context.user_data["new_book_desc_ar"] = "" if text == "-" else text
    await update.message.reply_text("📝︱اكتب وصف مختصر للكتاب بالإنجليزي (أو اكتب - لتخطي الوصف):")
    return ADD_BOOK_DESC_EN


async def add_book_desc_en(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    context.user_data["new_book_desc_en"] = "" if text == "-" else text
    await update.message.reply_text("📎︱دلوقتي ابعت ملف الكتاب (PDF أو صورة):")
    return ADD_BOOK_FILE


async def add_book_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    file_id, file_type = parse_media_input(message)
    if not file_id or file_type not in ("document", "photo"):
        await message.reply_text("من فضلك ابعت ملف PDF أو صورة، أو الصق رابط مباشر لملف PDF/صورة.")
        return ADD_BOOK_FILE

    subject_key = context.user_data["book_target_subject"]
    books_by_subject = load_books()
    books_by_subject.setdefault(subject_key, [])
    books_by_subject[subject_key].append({
        "title_ar": context.user_data["new_book_title_ar"],
        "title_en": context.user_data["new_book_title_en"],
        "desc_ar": context.user_data["new_book_desc_ar"],
        "desc_en": context.user_data["new_book_desc_en"],
        "file_id": file_id,
        "type": file_type,
    })
    save_books(books_by_subject)
    await message.reply_text("✅ تمت إضافة الكتاب للمادة المختارة.", reply_markup=admin_menu_keyboard())
    return MENU


async def del_book_pick_sub(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    subject_key = query.data.split(":", 1)[1]
    books_by_subject = load_books()
    books = books_by_subject.get(subject_key, [])
    if not books:
        await query.edit_message_text("لا توجد كتب على المادة دي.", reply_markup=admin_menu_keyboard())
        return MENU
    context.user_data["book_target_subject"] = subject_key
    buttons = [[InlineKeyboardButton(b.get("title_ar", "")[:40], callback_data=f"delbookq:{i}")] for i, b in enumerate(books)]
    buttons.append([InlineKeyboardButton("❌ إلغاء", callback_data="admin:cancel")])
    await query.edit_message_text("اختر الكتاب اللي عايز تحذفه:", reply_markup=InlineKeyboardMarkup(buttons))
    return DEL_BOOK_PICK_BOOK


async def del_book_pick_book(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    idx = int(query.data.split(":")[1])
    subject_key = context.user_data["book_target_subject"]
    books_by_subject = load_books()
    books = books_by_subject.get(subject_key, [])
    if 0 <= idx < len(books):
        removed = books.pop(idx)
        save_books(books_by_subject)
        await query.edit_message_text(f"🗑 تم حذف الكتاب: {removed.get('title_ar','')[:40]}", reply_markup=admin_menu_keyboard())
    else:
        await query.edit_message_text("الكتاب ده مش موجود.", reply_markup=admin_menu_keyboard())
    return MENU


# ---- 🧭 إضافة/حذف قسم في المساح العام ----
async def add_gen_title_ar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["new_gen_title_ar"] = update.message.text.strip()
    await update.message.reply_text("🧭︱اكتب عنوان القسم بالإنجليزي:")
    return ADD_GEN_TITLE_EN


async def add_gen_title_en(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["new_gen_title_en"] = update.message.text.strip()
    await update.message.reply_text("📝︱اكتب محتوى القسم بالعربي:")
    return ADD_GEN_CONTENT_AR


async def add_gen_content_ar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["new_gen_content_ar"] = update.message.text.strip()
    await update.message.reply_text("📝︱اكتب محتوى القسم بالإنجليزي:")
    return ADD_GEN_CONTENT_EN


async def add_gen_content_en(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["new_gen_content_en"] = update.message.text.strip()
    await update.message.reply_text("📎︱ابعت صورة أو ملف مرفق (اختياري)، أو اكتب - لتخطي:")
    return ADD_GEN_FILE


async def add_gen_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    file_id, file_type = "", ""
    if message.text and message.text.strip() == "-":
        pass
    else:
        file_id, file_type = parse_media_input(message)
        if not file_id:
            await message.reply_text("ابعت صورة/ملف، أو الصق رابط مباشر، أو اكتب - لتخطي:")
            return ADD_GEN_FILE

    general_items = load_general()
    general_items.append({
        "title_ar": context.user_data["new_gen_title_ar"],
        "title_en": context.user_data["new_gen_title_en"],
        "content_ar": context.user_data["new_gen_content_ar"],
        "content_en": context.user_data["new_gen_content_en"],
        "file_id": file_id,
        "file_type": file_type,
    })
    save_general(general_items)
    await message.reply_text("✅ تمت إضافة القسم.", reply_markup=admin_menu_keyboard())
    return MENU


async def del_gen_pick(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    idx = int(query.data.split(":")[1])
    general_items = load_general()
    if 0 <= idx < len(general_items):
        removed = general_items.pop(idx)
        save_general(general_items)
        await query.edit_message_text(f"🗑 تم حذف: {removed.get('title_ar','')[:40]}", reply_markup=admin_menu_keyboard())
    else:
        await query.edit_message_text("القسم ده مش موجود.", reply_markup=admin_menu_keyboard())
    return MENU


# ---- 👥 قسم الأدمنية والصلاحيات (مقصور على المالك فقط) ----
def pick_admin_keyboard(prefix: str) -> InlineKeyboardMarkup:
    admins = load_admins()
    buttons = []
    for uid, entry in admins.items():
        name = entry.get("name") or uid
        buttons.append([InlineKeyboardButton(f"👤 {name} ({uid})", callback_data=f"{prefix}:{uid}")])
    buttons.append([InlineKeyboardButton("❌ إلغاء", callback_data="admin:cancel")])
    return InlineKeyboardMarkup(buttons)


def permissions_keyboard(target_uid: str) -> InlineKeyboardMarkup:
    admins = load_admins()
    entry = admins.get(target_uid, {})
    perms = entry.get("permissions", {})
    buttons = []
    for key, label in PERMISSIONS.items():
        status = "✅" if perms.get(key, False) else "❌"
        buttons.append([InlineKeyboardButton(f"{status} {label}", callback_data=f"permtoggle:{target_uid}:{key}")])
    buttons.append([InlineKeyboardButton("⬅️ رجوع", callback_data="admin:permissions")])
    return InlineKeyboardMarkup(buttons)


async def admins_hub_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = query.from_user.id

    if not is_owner(user_id):
        await query.edit_message_text("🚫 قسم الأدمنية متاح للمالك بس.", reply_markup=admin_menu_keyboard())
        return MENU

    if data == "admin:cancel":
        await query.edit_message_text("ـ• ┉ • ┉ • ┉ • ┉ • ┉ •\n🔧 لـوحـــــة تـحـڪــم الادمـن :\nـ• ┉ • ┉ • ┉ • ┉ • ┉ •", reply_markup=admin_menu_keyboard())
        return MENU

    if data == "admin:admins_hub":
        buttons = InlineKeyboardMarkup([
            [InlineKeyboardButton("➕ إضافة أدمن", callback_data="admin:add_admin"),
             InlineKeyboardButton("➖ إزالة أدمن", callback_data="admin:remove_admin")],
            [InlineKeyboardButton("👥 الأدمنز", callback_data="admin:list_admins")],
            [InlineKeyboardButton("🔑 الصلاحيات", callback_data="admin:permissions")],
            [InlineKeyboardButton("❌ إلغاء", callback_data="admin:cancel")],
        ])
        await query.edit_message_text("ـ• ┉ • ┉ • ┉ • ┉ • ┉ •\n👥︱قسم الأدمنية\nـ• ┉ • ┉ • ┉ • ┉ • ┉ •", reply_markup=buttons)
        return ADMINS_HUB

    if data == "admin:list_admins":
        lines = ["👥 قائمة الأدمنية:\n"]
        for uid in ADMIN_IDS:
            role = "👑 المالك" if uid == ADMIN_IDS[0] else "🌟 أدمن كامل الصلاحيات"
            lines.append(f"{role} — {uid}")
        admins = load_admins()
        if admins:
            lines.append("\n🔧 أدمنية بصلاحيات مخصصة:")
            for uid, entry in admins.items():
                name = entry.get("name") or uid
                active_perms = [PERMISSIONS[k] for k, v in entry.get("permissions", {}).items() if v]
                perms_text = "، ".join(active_perms) if active_perms else "بدون صلاحيات"
                lines.append(f"👤 {name} ({uid})\n    └ {perms_text}")
        back_kb = InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ رجوع", callback_data="admin:admins_hub")]])
        await query.edit_message_text("\n".join(lines), reply_markup=back_kb)
        return ADMINS_HUB

    if data == "admin:add_admin":
        await query.edit_message_text("✍️︱ابعت آيدي التليجرام (رقم) بتاع الأدمن الجديد:")
        return ADD_ADMIN_ID

    if data == "admin:remove_admin":
        admins = load_admins()
        if not admins:
            await query.edit_message_text("لا يوجد أدمنية مضافين من البوت.", reply_markup=admin_menu_keyboard())
            return MENU
        await query.edit_message_text("اختر الأدمن اللي عايز تزيله:", reply_markup=pick_admin_keyboard("removeadmin"))
        return DEL_ADMIN_PICK

    if data == "admin:permissions":
        admins = load_admins()
        if not admins:
            await query.edit_message_text("لا يوجد أدمنية مضافين من البوت عشان تعدّل صلاحياتهم.", reply_markup=admin_menu_keyboard())
            return MENU
        await query.edit_message_text("اختر الأدمن اللي عايز تعدّل صلاحياته:", reply_markup=pick_admin_keyboard("permadmin"))
        return PERM_PICK_ADMIN

    return ADMINS_HUB


async def add_admin_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if not text.isdigit():
        await update.message.reply_text("لازم تبعت رقم آيدي صحيح (أرقام بس). جرب تاني:")
        return ADD_ADMIN_ID

    uid = text
    admins = load_admins()
    admins[uid] = {"name": "", "permissions": {k: False for k in PERMISSIONS}}
    save_admins(admins)
    await update.message.reply_text(
        f"✅ تمت إضافة الأدمن {uid} بدون أي صلاحيات مفعّلة.\n"
        f"روح لقسم 🔑 الصلاحيات عشان تحدد له إيه اللي يقدر يعمله.",
        reply_markup=admin_menu_keyboard(),
    )
    return MENU


async def remove_admin_pick(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    uid = query.data.split(":")[1]
    admins = load_admins()
    removed = admins.pop(uid, None)
    save_admins(admins)
    if removed:
        await query.edit_message_text(f"🗑 تم إزالة الأدمن {uid}.", reply_markup=admin_menu_keyboard())
    else:
        await query.edit_message_text("الأدمن ده مش موجود.", reply_markup=admin_menu_keyboard())
    return MENU


async def perm_pick_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    uid = query.data.split(":")[1]
    context.user_data["perm_target_uid"] = uid
    await query.edit_message_text("🔑︱اضغط على أي صلاحية عشان تفعّلها أو تلغيها:", reply_markup=permissions_keyboard(uid))
    return PERM_TOGGLE


async def perm_toggle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    _, uid, perm_key = query.data.split(":")

    admins = load_admins()
    if uid not in admins:
        await query.edit_message_text("الأدمن ده مش موجود.", reply_markup=admin_menu_keyboard())
        return MENU

    admins[uid].setdefault("permissions", {})
    admins[uid]["permissions"][perm_key] = not admins[uid]["permissions"].get(perm_key, False)
    save_admins(admins)

    await query.edit_message_text("🔑︱اضغط على أي صلاحية عشان تفعّلها أو تلغيها:", reply_markup=permissions_keyboard(uid))
    return PERM_TOGGLE


# ---- الإذاعة (Broadcast) ----
async def broadcast_wait(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["broadcast_chat_id"] = update.message.chat_id
    context.user_data["broadcast_msg_id"] = update.message.message_id

    users_count = len(load_users())
    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ تأكيد الإرسال", callback_data="admin:broadcast_confirm")],
        [InlineKeyboardButton("❌ إلغاء", callback_data="admin:cancel")],
    ])
    await update.message.reply_text(f"هيتبعت الرسالة دي لعدد {users_count} مستخدم. متأكد؟", reply_markup=buttons)
    return BROADCAST_CONFIRM


async def broadcast_send(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    from_chat_id = context.user_data.get("broadcast_chat_id")
    msg_id = context.user_data.get("broadcast_msg_id")
    users = load_users()

    success, failed = 0, 0
    for uid in users.keys():
        try:
            await context.bot.copy_message(chat_id=int(uid), from_chat_id=from_chat_id, message_id=msg_id)
            success += 1
        except Exception:
            failed += 1

    await query.edit_message_text(f"📢 تم الإرسال بنجاح لـ {success} مستخدم، وفشل مع {failed}.", reply_markup=admin_menu_keyboard())
    return MENU


# ---- نسخة احتياطية (Backup) ----
async def send_backup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer("جاري تجهيز النسخة الاحتياطية...")

    files_to_backup = [MATERIALS_FILE, CUSTOM_BUTTONS_FILE, USERS_FILE, TIPS_FILE, QUIZ_FILE, INSTRUMENTS_FILE, TOOLS_FILE, MENU_LABELS_FILE, BOOKS_FILE, GENERAL_FILE, ADMINS_FILE, "bot.py"]
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zipf:
        for filename in files_to_backup:
            if os.path.exists(filename):
                zipf.write(filename)
    zip_buffer.seek(0)

    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M")
    await context.bot.send_document(
        chat_id=query.message.chat_id,
        document=zip_buffer,
        filename=f"backup_{timestamp}.zip",
        caption=f"📦 نسخة احتياطية بتاريخ {timestamp}",
    )


async def admin_cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("تم الإلغاء.", reply_markup=admin_menu_keyboard())
    return MENU


# =====================================================================================
#  10) تشغيل البوت
# =====================================================================================

def main():
    logging.basicConfig(level=logging.INFO)
    app = Application.builder().token(BOT_TOKEN).build()

    # أوامر الطلاب
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))

    # محادثة لوحة تحكم الأدمن (بالأمر /admin أو زرار "قسم الأدمن" في القائمة الرئيسية)
    admin_conv = ConversationHandler(
        entry_points=[
            CommandHandler("admin", admin_start),
            CallbackQueryHandler(admin_start_from_button, pattern="^menu:admin$"),
        ],
        states={
            MENU: [CallbackQueryHandler(admin_menu_router, pattern="^admin:")],

            ADD_SUB_TITLE_AR: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_sub_title_ar)],
            ADD_SUB_TITLE_EN: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_sub_title_en)],
            ADD_SUB_KEY: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_sub_key)],

            ADD_CAT_PICK_SUB: [CallbackQueryHandler(add_cat_pick_sub, pattern="^acsub:")],
            ADD_CAT_TITLE_AR: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_cat_title_ar)],
            ADD_CAT_TITLE_EN: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_cat_title_en)],
            ADD_CAT_KEY: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_cat_key)],

            ADD_FILE_PICK_SUB: [CallbackQueryHandler(add_file_pick_sub, pattern="^afsub:")],
            ADD_FILE_PICK_CAT: [CallbackQueryHandler(add_file_pick_cat, pattern="^afcat:")],
            ADD_FILE_UPLOAD: [MessageHandler(
                filters.Document.ALL | filters.VIDEO | filters.PHOTO | filters.AUDIO | filters.VOICE | filters.ANIMATION,
                add_file_upload,
            )],
            ADD_FILE_TITLE_AR: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_file_title_ar)],
            ADD_FILE_TITLE_EN: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_file_title_en)],

            DEL_FILE_PICK_SUB: [CallbackQueryHandler(del_file_pick_sub, pattern="^dfsub:")],
            DEL_FILE_PICK_CAT: [CallbackQueryHandler(del_file_pick_cat, pattern="^dfcat:")],
            DEL_FILE_PICK_FILE: [CallbackQueryHandler(del_file_pick_file, pattern="^delf:")],

            DEL_CAT_PICK_SUB: [CallbackQueryHandler(del_cat_pick_sub, pattern="^dcsub:")],
            DEL_CAT_PICK_CAT: [CallbackQueryHandler(del_cat_pick_cat, pattern="^dccat:")],

            DEL_SUB_PICK: [CallbackQueryHandler(del_sub_pick, pattern="^delsub:")],

            ADD_BTN_TITLE_AR: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_btn_title_ar)],
            ADD_BTN_TITLE_EN: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_btn_title_en)],
            ADD_BTN_CONTENT: [MessageHandler(
                filters.TEXT | filters.Document.ALL | filters.VIDEO | filters.PHOTO | filters.AUDIO | filters.VOICE | filters.ANIMATION,
                add_btn_content,
            )],
            ADD_BTN_LAYOUT: [CallbackQueryHandler(add_btn_layout, pattern="^btnlayout:")],
            DEL_BTN_PICK: [CallbackQueryHandler(del_btn_pick, pattern="^delbtn:")],

            BROADCAST_WAIT: [MessageHandler(
                filters.TEXT | filters.Document.ALL | filters.VIDEO | filters.PHOTO | filters.AUDIO | filters.VOICE | filters.ANIMATION,
                broadcast_wait,
            )],
            BROADCAST_CONFIRM: [
                CallbackQueryHandler(broadcast_send, pattern="^admin:broadcast_confirm$"),
                CallbackQueryHandler(admin_menu_router, pattern="^admin:"),
            ],

            ADD_TIP_TEXT: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_tip_text)],
            DEL_TIP_PICK: [CallbackQueryHandler(del_tip_pick, pattern="^deltip:")],

            ADD_QUIZ_PICK_SUBJECT: [CallbackQueryHandler(add_quiz_pick_subject, pattern="^quizaddsub:")],
            ADD_QUIZ_QUESTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_quiz_question)],
            ADD_QUIZ_OPTIONS_AR: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_quiz_options_ar)],
            ADD_QUIZ_OPTIONS_EN: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_quiz_options_en)],
            ADD_QUIZ_CORRECT: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_quiz_correct)],
            ADD_QUIZ_EXPLANATION: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_quiz_explanation)],
            ADD_QUIZ_IMAGE: [MessageHandler(
                filters.TEXT | filters.PHOTO | filters.Document.ALL,
                add_quiz_image,
            )],
            DEL_QUIZ_PICK_SUBJECT: [CallbackQueryHandler(del_quiz_pick_subject, pattern="^quizdelsub:")],
            DEL_QUIZ_PICK_QUESTION: [CallbackQueryHandler(del_quiz_pick_question, pattern="^delquizq:")],

            ADD_INSTR_NAME_AR: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_instr_name_ar)],
            ADD_INSTR_NAME_EN: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_instr_name_en)],
            ADD_INSTR_DESC_AR: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_instr_desc_ar)],
            ADD_INSTR_DESC_EN: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_instr_desc_en)],
            ADD_INSTR_PHOTO: [MessageHandler(filters.PHOTO | (filters.TEXT & ~filters.COMMAND), add_instr_photo)],
            DEL_INSTR_PICK: [CallbackQueryHandler(del_instr_pick, pattern="^delinstr:")],

            ADD_TOOL_NAME_AR: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_tool_name_ar)],
            ADD_TOOL_NAME_EN: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_tool_name_en)],
            ADD_TOOL_DESC_AR: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_tool_desc_ar)],
            ADD_TOOL_DESC_EN: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_tool_desc_en)],
            ADD_TOOL_PHOTO: [MessageHandler(filters.PHOTO | (filters.TEXT & ~filters.COMMAND), add_tool_photo)],
            DEL_TOOL_PICK: [CallbackQueryHandler(del_tool_pick, pattern="^deltool:")],

            ADD_BOOK_PICK_SUB: [CallbackQueryHandler(add_book_pick_sub, pattern="^bookaddsub:")],
            ADD_BOOK_TITLE_AR: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_book_title_ar)],
            ADD_BOOK_TITLE_EN: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_book_title_en)],
            ADD_BOOK_DESC_AR: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_book_desc_ar)],
            ADD_BOOK_DESC_EN: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_book_desc_en)],
            ADD_BOOK_FILE: [MessageHandler(filters.Document.ALL | filters.PHOTO, add_book_file)],
            DEL_BOOK_PICK_SUB: [CallbackQueryHandler(del_book_pick_sub, pattern="^bookdelsub:")],
            DEL_BOOK_PICK_BOOK: [CallbackQueryHandler(del_book_pick_book, pattern="^delbookq:")],

            ADD_GEN_TITLE_AR: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_gen_title_ar)],
            ADD_GEN_TITLE_EN: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_gen_title_en)],
            ADD_GEN_CONTENT_AR: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_gen_content_ar)],
            ADD_GEN_CONTENT_EN: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_gen_content_en)],
            ADD_GEN_FILE: [MessageHandler(
                filters.TEXT | filters.Document.ALL | filters.PHOTO | filters.VIDEO | filters.AUDIO | filters.VOICE | filters.ANIMATION,
                add_gen_file,
            )],
            DEL_GEN_PICK: [CallbackQueryHandler(del_gen_pick, pattern="^delgen:")],

            ADMINS_HUB: [CallbackQueryHandler(admins_hub_router, pattern="^admin:")],
            ADD_ADMIN_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_admin_id)],
            DEL_ADMIN_PICK: [
                CallbackQueryHandler(remove_admin_pick, pattern="^removeadmin:"),
                CallbackQueryHandler(admins_hub_router, pattern="^admin:"),
            ],
            PERM_PICK_ADMIN: [
                CallbackQueryHandler(perm_pick_admin, pattern="^permadmin:"),
                CallbackQueryHandler(admins_hub_router, pattern="^admin:"),
            ],
            PERM_TOGGLE: [
                CallbackQueryHandler(perm_toggle, pattern="^permtoggle:"),
                CallbackQueryHandler(admins_hub_router, pattern="^admin:"),
            ],

            SYS_UPLOAD_NEW_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, sys_upload_new_name)],
            SYS_UPLOAD_NEW_FILE: [MessageHandler(filters.Document.ALL, sys_upload_new_file)],
            SYS_UPLOAD_PICK: [CallbackQueryHandler(sys_upload_pick, pattern="^sysfile:")],
            SYS_UPLOAD_WAIT: [MessageHandler(filters.Document.ALL, sys_upload_wait)],
            SYS_DELETE_PICK: [CallbackQueryHandler(sys_delete_pick, pattern="^sysdel:")],
            SYS_DELETE_CONFIRM: [CallbackQueryHandler(sys_delete_confirm, pattern="^sysdelconfirm:")],

            EDIT_BTN_PICK: [CallbackQueryHandler(edit_btn_pick, pattern="^editbtn:")],
            EDIT_BTN_TITLE_AR: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_btn_title_ar)],
            EDIT_BTN_TITLE_EN: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_btn_title_en)],

            EDIT_CORE_PICK: [CallbackQueryHandler(edit_core_pick, pattern="^editcore:")],
            EDIT_CORE_TITLE_AR: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_core_title_ar)],
            EDIT_CORE_TITLE_EN: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_core_title_en)],

            GET_FILE_PICK: [CallbackQueryHandler(get_file_pick, pattern="^getfile:")],
            TOGGLE_CORE_PICK: [CallbackQueryHandler(toggle_core_pick, pattern="^coretoggle:")],
        },
        fallbacks=[
            CommandHandler("cancel", admin_cancel_command),
            CallbackQueryHandler(admin_menu_router, pattern="^admin:"),
        ],
    )
    app.add_handler(admin_conv)

    # أزرار الطلاب العادية (لازم تكون بعد محادثة الأدمن عشان الأولوية تبقى للأدمن)
    app.add_handler(CallbackQueryHandler(button_handler))

    # أداة مساعدة للأدمن: فورورد رسالة من قناة/جروب خاص يرجع الـ chat_id بتاعها
    # شغالة في أي وقت (حتى لو الأدمن مش داخل لوحة التحكم)
    app.add_handler(MessageHandler(filters.FORWARDED, chatid_detector), group=1)

    print("✅ البوت يعمل الآن...")
    app.run_polling()


if __name__ == "__main__":
    main()
