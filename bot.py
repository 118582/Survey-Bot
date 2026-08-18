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
ADMIN_IDS = [
    7724699440,
    # 123456789,   # <- فك التعليق وحط آيدي أدمن جديد هنا
]

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
    {"name": "قناة", "username": "@xo_survey"},

    # مثال قناة خاصة (استبدل الأرقام بالـ chat_id الحقيقي اللي هتجيبه من chatid_detector):
    # {"name": "قناة الشرح الرئيسية", "chat_id": -1001111111111, "invite_link": "https://t.me/+ER-qmAgVa9I0MTE0"},
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

# الأزرار الأساسية الثابتة في القائمة الرئيسية (اللي ممكن تتعدل من لوحة الأدمن)
# المفتاح على اليسار هو المعرف الداخلي، والقيمة هي النص الافتراضي (لو الأدمن معدلش)
CORE_MENU_KEYS = {
    "materials_section": "menu:materials",
    "instruments_section": "menu:instruments",
    "tools_section": "menu:tools",
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
    "instruments.json", "tools.json", "menu_labels.json",
]

# الملفات المسموح "تصفيرها" (حذف بياناتها والرجوع لملف فاضي) من لوحة الأدمن
# متعمدين ما نحطش bot.py / requirements.txt / Procfile هنا لأن حذفهم هيوقف البوت تماماً
ALLOWED_RESET_FILES = [
    "materials.json", "custom_buttons.json", "tips.json", "quiz.json", "users.json",
    "instruments.json", "tools.json", "menu_labels.json",
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
        "welcome": "أهلاً بك 👋\nاختر من القائمة اللي تحت:",
        "materials_section": "📚 المواد الدراسية",
        "language_section": "🌐 تغيير اللغة",
        "admin_section": "⚙️ لوحة الأدمن",
        "choose_subject": "📖 اختر المادة:",
        "choose_category": "📂 اختر القسم:",
        "choose_file": "📄 اختر الملف:",
        "back": "⬅️ رجوع",
        "back_main_menu": "🏠 القائمة الرئيسية",
        "no_files": "لا توجد ملفات بعد",
        "still_not_subscribed": "لسه مش مشترك في كل القنوات! اشترك الأول ثم اضغط تحقق.",
        "tip_section": "💡 معلومة مساحية",
        "quiz_section": "🎯 اختبر نفسك",
        "no_tips": "لا توجد معلومات مضافة بعد.",
        "no_quiz": "لا توجد أسئلة مضافة بعد.",
        "quiz_correct": "✅ إجابة صحيحة!",
        "quiz_wrong": "❌ إجابة غلط.",
        "instruments_section": "🔭 الأجهزة المساحية",
        "tools_section": "🧰 الأدوات المساحية",
        "choose_instrument": "🔭 اختر الجهاز:",
        "choose_tool": "🧰 اختر الأداة:",
        "no_instruments": "لا توجد أجهزة مضافة بعد.",
        "no_tools": "لا توجد أدوات مضافة بعد.",
        "choose_quiz_subject": "🎯 اختر المادة اللي عايز تختبر نفسك فيها:",
        "no_quiz_for_subject": "لا توجد أسئلة على المادة دي لسه.",
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
    },
}

# نص طلب الاشتراك الإجباري (ثنائي اللغة لأنه بيظهر قبل ما المستخدم يختار لغته)
SUBSCRIBE_MESSAGE = (
    "⚠️ لازم تشترك في القنوات دي الأول عشان تقدر تستخدم البوت:\n"
    "⚠️ You must join the channels below first to use the bot:"
)
CHECK_SUB_BUTTON_TEXT = "✅ اشتركت / I've Joined"
CHOOSE_LANGUAGE_TEXT = "🌐 اختر لغة البوت | Choose your bot language:"

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


def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


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
        [[InlineKeyboardButton("🇸🇦 العربية", callback_data="lang:ar"),
          InlineKeyboardButton("🇬🇧 English", callback_data="lang:en")]]
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
    """يرجع اسم الزرار الأساسي: لو الأدمن عدّله من لوحة التحكم يستخدم الاسم الجديد، وإلا الافتراضي من TEXTS."""
    overrides = load_menu_labels()
    if key in overrides:
        return t(overrides[key], lang)
    return TEXTS[lang][key]


def build_main_menu(user_id: int, lang: str) -> InlineKeyboardMarkup:
    labels = load_menu_labels()

    def is_hidden(key):
        return labels.get(key, {}).get("hidden", False)

    items = []
    if not is_hidden("materials_section"):
        items.append((core_label("materials_section", lang), "menu:materials"))
    if not is_hidden("instruments_section"):
        items.append((core_label("instruments_section", lang), "menu:instruments"))
    if not is_hidden("tools_section"):
        items.append((core_label("tools_section", lang), "menu:tools"))
    if not is_hidden("tip_section"):
        items.append((core_label("tip_section", lang), "menu:tip"))
    if not is_hidden("quiz_section"):
        items.append((core_label("quiz_section", lang), "menu:quiz"))
    if not is_hidden("language_section"):
        items.append((core_label("language_section", lang), "menu:language"))
    if is_admin(user_id) and not is_hidden("admin_section"):
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
    buttons.append([InlineKeyboardButton(TEXTS[lang]["back_main_menu"], callback_data="back:menu")])
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
        back_kb = InlineKeyboardMarkup([[InlineKeyboardButton(TEXTS[lang]["back_main_menu"], callback_data="back:menu")]])
        if not tips:
            await query.edit_message_text(TEXTS[lang]["no_tips"], reply_markup=back_kb)
        else:
            tip = random.choice(tips)
            await query.edit_message_text(f"💡 {t(tip, lang, field='text')}", reply_markup=back_kb)
        return

    # ---- 🔭 الأجهزة المساحية ----
    if data == "menu:instruments":
        instruments = load_instruments()
        if not instruments:
            back_kb = InlineKeyboardMarkup([[InlineKeyboardButton(TEXTS[lang]["back_main_menu"], callback_data="back:menu")]])
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
            back_kb = InlineKeyboardMarkup([[InlineKeyboardButton(TEXTS[lang]["back_main_menu"], callback_data="back:menu")]])
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
        await query.edit_message_text(
            build_quiz_question_text(questions[qidx], lang),
            reply_markup=build_quiz_keyboard(subject_key, questions[qidx], qidx, lang),
        )
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
            text += f"\n💡 {explanation}"
        back_kb = InlineKeyboardMarkup([[InlineKeyboardButton(TEXTS[lang]["back"], callback_data="menu:quiz")]])
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
    ADD_QUIZ_PICK_SUBJECT, ADD_QUIZ_QUESTION, ADD_QUIZ_OPTIONS_AR, ADD_QUIZ_OPTIONS_EN, ADD_QUIZ_CORRECT, ADD_QUIZ_EXPLANATION,
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
) = range(60)


def admin_menu_keyboard() -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton("➕ إضافة مادة", callback_data="admin:add_subject")],
        [InlineKeyboardButton("➕ إضافة قسم لمادة", callback_data="admin:add_cat"),
         InlineKeyboardButton("➕ إضافة ملف", callback_data="admin:add_file")],
        [InlineKeyboardButton("🗑 حذف ملف", callback_data="admin:del_file"),
         InlineKeyboardButton("🗑 حذف قسم", callback_data="admin:del_cat")],
        [InlineKeyboardButton("🗑 حذف مادة كاملة", callback_data="admin:del_subject")],
        [InlineKeyboardButton("🔘 إضافة زر مخصص", callback_data="admin:add_btn"),
         InlineKeyboardButton("🔘 حذف زر مخصص", callback_data="admin:del_btn")],
        [InlineKeyboardButton("✏️ تعديل اسم زر مخصص", callback_data="admin:edit_btn"),
         InlineKeyboardButton("✏️ تعديل أسماء الأزرار الرئيسية", callback_data="admin:edit_core")],
        [InlineKeyboardButton("💡 إضافة معلومة", callback_data="admin:add_tip"),
         InlineKeyboardButton("💡 حذف معلومة", callback_data="admin:del_tip")],
        [InlineKeyboardButton("🎯 إضافة سؤال كويز", callback_data="admin:add_quiz"),
         InlineKeyboardButton("🎯 حذف سؤال كويز", callback_data="admin:del_quiz")],
        [InlineKeyboardButton("🔭 إضافة جهاز", callback_data="admin:add_instr"),
         InlineKeyboardButton("🔭 حذف جهاز", callback_data="admin:del_instr")],
        [InlineKeyboardButton("🧰 إضافة أداة", callback_data="admin:add_tool"),
         InlineKeyboardButton("🧰 حذف أداة", callback_data="admin:del_tool")],
        [InlineKeyboardButton("📢 إذاعة رسالة", callback_data="admin:broadcast")],
        [InlineKeyboardButton("📤 رفع/استبدال ملف", callback_data="admin:sys_upload"),
         InlineKeyboardButton("📥 تحميل ملف", callback_data="admin:get_file")],
        [InlineKeyboardButton("🗑 تصفير ملف بيانات", callback_data="admin:sys_delete"),
         InlineKeyboardButton("🧹 حذف الملفات المؤقتة", callback_data="admin:clean_temp")],
        [InlineKeyboardButton("👁 إخفاء/إظهار زر رئيسي", callback_data="admin:toggle_core")],
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
        await update.message.reply_text("هذا الأمر مخصص للأدمن فقط.")
        return ConversationHandler.END
    await update.message.reply_text("🔧 لوحة تحكم الأدمن:", reply_markup=admin_menu_keyboard())
    return MENU


async def admin_start_from_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not is_admin(query.from_user.id):
        await query.answer("هذا القسم مخصص للأدمن فقط.", show_alert=True)
        return ConversationHandler.END
    await query.answer()
    await query.edit_message_text("🔧 لوحة تحكم الأدمن:", reply_markup=admin_menu_keyboard())
    return MENU


# ---- توجيه القائمة الرئيسية للأدمن ----
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
        lines = ["📋 كل بيانات البوت:\n"]
        if not materials:
            lines.append("لا توجد مواد بعد.")
        for skey, sdata in materials.items():
            lines.append(f"📚 {t(sdata,'ar')} (key: {skey})")
            for ckey, cdata in sdata["categories"].items():
                lines.append(f"   └ {t(cdata,'ar')} (key: {ckey}) — {len(cdata['files'])} ملف")
        custom = load_custom_buttons()
        lines.append(f"\n🔘 أزرار مخصصة: {len(custom)}")
        lines.append(f"💡 معلومات مساحية: {len(load_tips())}")
        total_quiz = sum(len(qs) for qs in load_quiz().values())
        lines.append(f"🎯 أسئلة كويز (كل المواد): {total_quiz}")
        lines.append(f"🔭 أجهزة مساحية: {len(load_instruments())}")
        lines.append(f"🧰 أدوات مساحية: {len(load_tools())}")
        lines.append(f"👥 عدد المستخدمين المسجلين: {len(load_users())}")
        channels_display = ", ".join(
            f"{c['name']} ({c.get('username') or c.get('chat_id')})" for c in REQUIRED_CHANNELS
        ) if REQUIRED_CHANNELS else "لا يوجد"
        lines.append(f"📢 قنوات الاشتراك الإجباري: {channels_display}")
        lines.append(f"👤 الأدمنية: {', '.join(str(a) for a in ADMIN_IDS)}")
        await query.edit_message_text("\n".join(lines), reply_markup=admin_menu_keyboard())
        return MENU

    if data == "admin:backup":
        await send_backup(update, context)
        return MENU

    if data == "admin:add_subject":
        await query.edit_message_text("اكتب اسم المادة بالعربي:")
        return ADD_SUB_TITLE_AR

    if data == "admin:add_cat":
        if not materials:
            await query.edit_message_text("لا توجد مواد بعد.", reply_markup=admin_menu_keyboard())
            return MENU
        await query.edit_message_text("اختر المادة:", reply_markup=pick_subject_keyboard(materials, "acsub"))
        return ADD_CAT_PICK_SUB

    if data == "admin:add_file":
        if not materials:
            await query.edit_message_text("لا توجد مواد بعد.", reply_markup=admin_menu_keyboard())
            return MENU
        await query.edit_message_text("اختر المادة:", reply_markup=pick_subject_keyboard(materials, "afsub"))
        return ADD_FILE_PICK_SUB

    if data == "admin:del_file":
        if not materials:
            await query.edit_message_text("لا توجد مواد بعد.", reply_markup=admin_menu_keyboard())
            return MENU
        await query.edit_message_text("اختر المادة:", reply_markup=pick_subject_keyboard(materials, "dfsub"))
        return DEL_FILE_PICK_SUB

    if data == "admin:del_cat":
        if not materials:
            await query.edit_message_text("لا توجد مواد بعد.", reply_markup=admin_menu_keyboard())
            return MENU
        await query.edit_message_text("اختر المادة:", reply_markup=pick_subject_keyboard(materials, "dcsub"))
        return DEL_CAT_PICK_SUB

    if data == "admin:del_subject":
        if not materials:
            await query.edit_message_text("لا توجد مواد بعد.", reply_markup=admin_menu_keyboard())
            return MENU
        await query.edit_message_text("اختر المادة اللي عايز تحذفها:", reply_markup=pick_subject_keyboard(materials, "delsub"))
        return DEL_SUB_PICK

    if data == "admin:add_btn":
        await query.edit_message_text("اكتب عنوان الزر بالعربي:")
        return ADD_BTN_TITLE_AR

    if data == "admin:del_btn":
        custom = load_custom_buttons()
        if not custom:
            await query.edit_message_text("لا توجد أزرار مخصصة بعد.", reply_markup=admin_menu_keyboard())
            return MENU
        await query.edit_message_text("اختر الزر اللي عايز تحذفه:", reply_markup=pick_custom_button_keyboard(custom))
        return DEL_BTN_PICK

    if data == "admin:broadcast":
        await query.edit_message_text("📢 ابعت الرسالة اللي عايز تذيعها (نص / صورة / فيديو / ملف):")
        return BROADCAST_WAIT

    if data == "admin:add_tip":
        await query.edit_message_text(
            "اكتب المعلومة/النصيحة بالشكل ده (سطرين):\n"
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
        await query.edit_message_text("اختر المعلومة اللي عايز تحذفها:", reply_markup=InlineKeyboardMarkup(buttons))
        return DEL_TIP_PICK

    if data == "admin:add_quiz":
        if not materials:
            await query.edit_message_text("لا توجد مواد بعد، أضف مادة أولاً.", reply_markup=admin_menu_keyboard())
            return MENU
        buttons = [[InlineKeyboardButton(t(s, "ar"), callback_data=f"quizaddsub:{key}")] for key, s in materials.items()]
        buttons.append([InlineKeyboardButton("❌ إلغاء", callback_data="admin:cancel")])
        await query.edit_message_text("اختر المادة اللي عايز تضيف السؤال ليها:", reply_markup=InlineKeyboardMarkup(buttons))
        return ADD_QUIZ_PICK_SUBJECT

    if data == "admin:del_quiz":
        if not materials:
            await query.edit_message_text("لا توجد مواد بعد.", reply_markup=admin_menu_keyboard())
            return MENU
        buttons = [[InlineKeyboardButton(t(s, "ar"), callback_data=f"quizdelsub:{key}")] for key, s in materials.items()]
        buttons.append([InlineKeyboardButton("❌ إلغاء", callback_data="admin:cancel")])
        await query.edit_message_text("اختر المادة اللي عايز تحذف سؤال منها:", reply_markup=InlineKeyboardMarkup(buttons))
        return DEL_QUIZ_PICK_SUBJECT

    if data == "admin:add_instr":
        await query.edit_message_text("اكتب اسم الجهاز بالعربي:")
        return ADD_INSTR_NAME_AR

    if data == "admin:del_instr":
        instruments = load_instruments()
        if not instruments:
            await query.edit_message_text("لا توجد أجهزة مضافة بعد.", reply_markup=admin_menu_keyboard())
            return MENU
        buttons = [[InlineKeyboardButton(it.get("name_ar", "")[:40], callback_data=f"delinstr:{i}")] for i, it in enumerate(instruments)]
        buttons.append([InlineKeyboardButton("❌ إلغاء", callback_data="admin:cancel")])
        await query.edit_message_text("اختر الجهاز اللي عايز تحذفه:", reply_markup=InlineKeyboardMarkup(buttons))
        return DEL_INSTR_PICK

    if data == "admin:add_tool":
        await query.edit_message_text("اكتب اسم الأداة بالعربي:")
        return ADD_TOOL_NAME_AR

    if data == "admin:del_tool":
        tools = load_tools()
        if not tools:
            await query.edit_message_text("لا توجد أدوات مضافة بعد.", reply_markup=admin_menu_keyboard())
            return MENU
        buttons = [[InlineKeyboardButton(tl.get("name_ar", "")[:40], callback_data=f"deltool:{i}")] for i, tl in enumerate(tools)]
        buttons.append([InlineKeyboardButton("❌ إلغاء", callback_data="admin:cancel")])
        await query.edit_message_text("اختر الأداة اللي عايز تحذفها:", reply_markup=InlineKeyboardMarkup(buttons))
        return DEL_TOOL_PICK

    if data == "admin:sys_upload":
        buttons = [[InlineKeyboardButton(f, callback_data=f"sysfile:{f}")] for f in ALLOWED_UPLOAD_FILES]
        buttons.append([InlineKeyboardButton("❌ إلغاء", callback_data="admin:cancel")])
        await query.edit_message_text(
            "📤 اختر الملف اللي عايز تستبدله (هيتاخد نسخة احتياطية منه تلقائياً قبل الاستبدال):",
            reply_markup=InlineKeyboardMarkup(buttons),
        )
        return SYS_UPLOAD_PICK

    if data == "admin:sys_delete":
        buttons = [[InlineKeyboardButton(f, callback_data=f"sysdel:{f}")] for f in ALLOWED_RESET_FILES]
        buttons.append([InlineKeyboardButton("❌ إلغاء", callback_data="admin:cancel")])
        await query.edit_message_text(
            "⚠️ اختر ملف البيانات اللي عايز تصفّره بالكامل (هيترجع فاضي تماماً):",
            reply_markup=InlineKeyboardMarkup(buttons),
        )
        return SYS_DELETE_PICK

    if data == "admin:restart_confirm":
        await query.edit_message_text("🔁 جاري إعادة تشغيل البوت... استنى شوية ودوس /start تاني.")
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
        await query.edit_message_text("📥 اختر الملف اللي عايز تحمّله:", reply_markup=InlineKeyboardMarkup(buttons))
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
    await update.message.reply_text("اكتب اسم المادة بالإنجليزي:")
    return ADD_SUB_TITLE_EN


async def add_sub_title_en(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["new_sub_en"] = update.message.text.strip()
    await update.message.reply_text("اكتب معرّف قصير بالإنجليزي بدون مسافات (مثال: subject9):")
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
            "explanations": {"title_ar": "📝 الشرح", "title_en": "📝 Explanations", "files": []},
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
    await query.edit_message_text("اختر القسم:", reply_markup=pick_category_keyboard(materials, subject_key, "afcat"))
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
    file_id, file_type = detect_uploaded_file(update.message)
    if not file_id:
        await update.message.reply_text("من فضلك ابعت ملف مدعوم (مستند/فيديو/صورة/صوت/GIF).")
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

    file_id, file_type = detect_uploaded_file(message)
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

    subject_key = context.user_data["quiz_target_subject"]
    quiz_by_subject = load_quiz()
    quiz_by_subject.setdefault(subject_key, [])
    quiz_by_subject[subject_key].append({
        "question_ar": context.user_data["new_quiz_q_ar"],
        "question_en": context.user_data["new_quiz_q_en"],
        "options_ar": context.user_data["new_quiz_options_ar"],
        "options_en": context.user_data["new_quiz_options_en"],
        "correct_index": context.user_data["new_quiz_correct"],
        "explanation_ar": exp_ar,
        "explanation_en": exp_en,
    })
    save_quiz(quiz_by_subject)
    await update.message.reply_text("✅ تمت إضافة السؤال للمادة المختارة.", reply_markup=admin_menu_keyboard())
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
    if message.photo:
        photo_id = message.photo[-1].file_id
    elif message.text and message.text.strip() != "-":
        await message.reply_text("ابعت صورة فعلية أو اكتب - لتخطي الصورة:")
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
    if message.photo:
        photo_id = message.photo[-1].file_id
    elif message.text and message.text.strip() != "-":
        await message.reply_text("ابعت صورة فعلية أو اكتب - لتخطي الصورة:")
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
    list_type_files = ("tips.json", "instruments.json", "tools.json")
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

    files_to_backup = [MATERIALS_FILE, CUSTOM_BUTTONS_FILE, USERS_FILE, TIPS_FILE, QUIZ_FILE, INSTRUMENTS_FILE, TOOLS_FILE, MENU_LABELS_FILE, "bot.py"]
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
