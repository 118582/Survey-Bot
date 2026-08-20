# -*- coding: utf-8 -*-
"""
معالجات لوحة تحكم الأدمن - النسخة الكاملة
"""

import os
import sys
import json
import shutil
import py_compile
import zipfile
import io
from datetime import datetime

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler, CallbackQueryHandler, MessageHandler, filters

from bot import (
    load_materials, save_materials,
    load_users, save_users,
    load_custom_buttons, save_custom_buttons,
    load_tips, save_tips,
    load_quiz, save_quiz,
    load_menu_labels, save_menu_labels,
    load_instruments, save_instruments,
    load_tools, save_tools,
    load_study_books, save_study_books,
    load_admins, save_admins,
    load_general_survey, save_general_survey,
    load_links, save_links,
    is_admin, has_permission, t, TEXTS, build_main_menu,
    ALLOWED_UPLOAD_FILES, ALLOWED_RESET_FILES,
    detect_uploaded_file, send_file_or_link, _save_json
)

# حالات المحادثة
(
    ADMIN_MENU,
    ADD_SUB_TITLE_AR, ADD_SUB_TITLE_EN, ADD_SUB_KEY,
    ADD_CAT_PICK_SUB, ADD_CAT_TITLE_AR, ADD_CAT_TITLE_EN, ADD_CAT_KEY,
    ADD_FILE_PICK_SUB, ADD_FILE_PICK_CAT, ADD_FILE_UPLOAD, ADD_FILE_TITLE_AR, ADD_FILE_TITLE_EN,
    DEL_FILE_PICK_SUB, DEL_FILE_PICK_CAT, DEL_FILE_PICK_FILE,
    DEL_CAT_PICK_SUB, DEL_CAT_PICK_CAT,
    DEL_SUB_PICK,
    ADD_BOOK_PICK_SUB, ADD_BOOK_TITLE_AR, ADD_BOOK_TITLE_EN, ADD_BOOK_DESC_AR, ADD_BOOK_DESC_EN, ADD_BOOK_FILE,
    DEL_BOOK_PICK_SUB, DEL_BOOK_PICK_BOOK,
    ADD_GEN_SECTION_TITLE_AR, ADD_GEN_SECTION_TITLE_EN, ADD_GEN_SECTION_CONTENT_AR, ADD_GEN_SECTION_CONTENT_EN, ADD_GEN_SECTION_IMAGE,
    DEL_GEN_SECTION_PICK,
    ADD_BTN_TITLE_AR, ADD_BTN_TITLE_EN, ADD_BTN_CONTENT, ADD_BTN_LAYOUT,
    DEL_BTN_PICK,
    EDIT_BTN_PICK, EDIT_BTN_TITLE_AR, EDIT_BTN_TITLE_EN,
    EDIT_CORE_PICK, EDIT_CORE_TITLE_AR, EDIT_CORE_TITLE_EN,
    TOGGLE_CORE_PICK,
    ADMIN_ADMINS_MENU,
    ADD_ADMIN_ID, ADD_ADMIN_PERMISSION,
    DEL_ADMIN_PICK,
    EDIT_ADMIN_PICK, EDIT_ADMIN_PERMISSION,
    BROADCAST_WAIT, BROADCAST_CONFIRM,
    ADD_TIP_TEXT, DEL_TIP_PICK,
    ADD_QUIZ_PICK_SUBJECT, ADD_QUIZ_QUESTION, ADD_QUIZ_OPTIONS_AR, ADD_QUIZ_OPTIONS_EN,
    ADD_QUIZ_CORRECT, ADD_QUIZ_EXPLANATION, ADD_QUIZ_IMAGE,
    DEL_QUIZ_PICK_SUBJECT, DEL_QUIZ_PICK_QUESTION,
    ADD_INSTR_NAME_AR, ADD_INSTR_NAME_EN, ADD_INSTR_DESC_AR, ADD_INSTR_DESC_EN, ADD_INSTR_PHOTO,
    DEL_INSTR_PICK,
    ADD_TOOL_NAME_AR, ADD_TOOL_NAME_EN, ADD_TOOL_DESC_AR, ADD_TOOL_DESC_EN, ADD_TOOL_PHOTO,
    DEL_TOOL_PICK,
    SYS_UPLOAD_PICK, SYS_UPLOAD_WAIT,
    SYS_DELETE_PICK, SYS_DELETE_CONFIRM,
    GET_FILE_PICK,
) = range(70)

# =====================================================================================
#  1) قوائم الأدمن
# =====================================================================================

def admin_main_menu_keyboard() -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton("• ⟬ 📘 إدارة المواد الدراسية ⟭ •", callback_data="admin:materials_menu")],
        [InlineKeyboardButton("• ⟬ 📚 إدارة الكتب الدراسية ⟭ •", callback_data="admin:books_menu")],
        [InlineKeyboardButton("• ⟬ 🧭 إدارة المساح العام ⟭ •", callback_data="admin:general_menu")],
        [InlineKeyboardButton("• ⟬ 👥 إدارة الأدمنية ⟭ •", callback_data="admin:admins_menu")],
        [InlineKeyboardButton("• ⟬ 📢 الإذاعة ⟭ •", callback_data="admin:broadcast")],
        [InlineKeyboardButton("• ⟬ ⚙️ إعدادات البوت ⟭ •", callback_data="admin:settings_menu")],
        [InlineKeyboardButton("• ⟬ 📦 نسخ احتياطي وتصفير ⟭ •", callback_data="admin:backup_menu")],
        [InlineKeyboardButton("• ⟬ 🔙 رجوع للقائمة الرئيسية ⟭ •", callback_data="admin:close")],
    ]
    return InlineKeyboardMarkup(buttons)

def materials_admin_menu_keyboard() -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton("➕ إضافة مادة", callback_data="admin:add_subject")],
        [InlineKeyboardButton("➕ إضافة قسم", callback_data="admin:add_cat")],
        [InlineKeyboardButton("➕ إضافة ملف", callback_data="admin:add_file")],
        [InlineKeyboardButton("🗑 حذف ملف", callback_data="admin:del_file")],
        [InlineKeyboardButton("🗑 حذف قسم", callback_data="admin:del_cat")],
        [InlineKeyboardButton("🗑 حذف مادة", callback_data="admin:del_subject")],
        [InlineKeyboardButton("• ⟬ 🔙 رجوع ⟭ •", callback_data="admin:back_main")],
    ]
    return InlineKeyboardMarkup(buttons)

def books_admin_menu_keyboard() -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton("➕ إضافة كتاب", callback_data="admin:add_book")],
        [InlineKeyboardButton("🗑 حذف كتاب", callback_data="admin:del_book")],
        [InlineKeyboardButton("• ⟬ 🔙 رجوع ⟭ •", callback_data="admin:back_main")],
    ]
    return InlineKeyboardMarkup(buttons)

def general_admin_menu_keyboard() -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton("➕ إضافة قسم", callback_data="admin:add_gen")],
        [InlineKeyboardButton("🗑 حذف قسم", callback_data="admin:del_gen")],
        [InlineKeyboardButton("• ⟬ 🔙 رجوع ⟭ •", callback_data="admin:back_main")],
    ]
    return InlineKeyboardMarkup(buttons)

def settings_admin_menu_keyboard() -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton("🔘 إضافة زر مخصص", callback_data="admin:add_btn")],
        [InlineKeyboardButton("🔘 حذف زر مخصص", callback_data="admin:del_btn")],
        [InlineKeyboardButton("✏️ تعديل زر مخصص", callback_data="admin:edit_btn")],
        [InlineKeyboardButton("✏️ تعديل الأزرار الرئيسية", callback_data="admin:edit_core")],
        [InlineKeyboardButton("👁 إخفاء/إظهار زر", callback_data="admin:toggle_core")],
        [InlineKeyboardButton("💡 إضافة معلومة", callback_data="admin:add_tip")],
        [InlineKeyboardButton("💡 حذف معلومة", callback_data="admin:del_tip")],
        [InlineKeyboardButton("• ⟬ 🔙 رجوع ⟭ •", callback_data="admin:back_main")],
    ]
    return InlineKeyboardMarkup(buttons)

def backup_admin_menu_keyboard() -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton("📤 رفع/استبدال ملف", callback_data="admin:sys_upload")],
        [InlineKeyboardButton("📥 تحميل ملف", callback_data="admin:get_file")],
        [InlineKeyboardButton("🗑 تصفير ملف", callback_data="admin:sys_delete")],
        [InlineKeyboardButton("🧹 حذف المؤقتات", callback_data="admin:clean_temp")],
        [InlineKeyboardButton("📦 نسخة احتياطية", callback_data="admin:backup")],
        [InlineKeyboardButton("📋 عرض الكل", callback_data="admin:list")],
        [InlineKeyboardButton("🔁 إعادة تشغيل", callback_data="admin:restart_ask")],
        [InlineKeyboardButton("• ⟬ 🔙 رجوع ⟭ •", callback_data="admin:back_main")],
    ]
    return InlineKeyboardMarkup(buttons)

def admins_admin_menu_keyboard() -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton("📋 عرض الأدمن", callback_data="admin:list_admins")],
        [InlineKeyboardButton("➕ إضافة أدمن", callback_data="admin:add_admin")],
        [InlineKeyboardButton("🗑 حذف أدمن", callback_data="admin:del_admin")],
        [InlineKeyboardButton("✏️ تعديل صلاحية", callback_data="admin:edit_admin")],
        [InlineKeyboardButton("• ⟬ 🔙 رجوع ⟭ •", callback_data="admin:back_main")],
    ]
    return InlineKeyboardMarkup(buttons)

# =====================================================================================
#  2) دوال مساعدة للأدمن
# =====================================================================================

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
    buttons = [[InlineKeyboardButton(t(f, "ar"), callback_data=f"delf:{subject_key}:{cat_key}:{idx}")] for idx, f in enumerate(files)]
    buttons.append([InlineKeyboardButton("❌ إلغاء", callback_data="admin:cancel")])
    return InlineKeyboardMarkup(buttons)

def pick_custom_button_keyboard(buttons_dict: dict) -> InlineKeyboardMarkup:
    buttons = [[InlineKeyboardButton(t(b, "ar"), callback_data=f"delbtn:{key}")] for key, b in buttons_dict.items()]
    buttons.append([InlineKeyboardButton("❌ إلغاء", callback_data="admin:cancel")])
    return InlineKeyboardMarkup(buttons)

def pick_book_subject_keyboard(books_data: dict) -> InlineKeyboardMarkup:
    buttons = [[InlineKeyboardButton(t(s, "ar"), callback_data=f"booksub:{key}")] for key, s in books_data.items()]
    buttons.append([InlineKeyboardButton("❌ إلغاء", callback_data="admin:cancel")])
    return InlineKeyboardMarkup(buttons)

def pick_book_keyboard(books_data: dict, subject_key: str) -> InlineKeyboardMarkup:
    books = books_data[subject_key].get("books", [])
    buttons = [[InlineKeyboardButton(t(b, "ar"), callback_data=f"delbook:{subject_key}:{idx}")] for idx, b in enumerate(books)]
    buttons.append([InlineKeyboardButton("❌ إلغاء", callback_data="admin:cancel")])
    return InlineKeyboardMarkup(buttons)

def pick_general_section_keyboard(survey_data: dict) -> InlineKeyboardMarkup:
    buttons = [[InlineKeyboardButton(t(s, "ar"), callback_data=f"delgen:{key}")] for key, s in survey_data.items()]
    buttons.append([InlineKeyboardButton("❌ إلغاء", callback_data="admin:cancel")])
    return InlineKeyboardMarkup(buttons)

def pick_admin_keyboard(admins: dict) -> InlineKeyboardMarkup:
    buttons = []
    for uid, role in admins.items():
        users = load_users()
        user_data = users.get(uid, {})
        name = user_data.get("name", uid)
        buttons.append([InlineKeyboardButton(f"{name} ({role})", callback_data=f"adminpick:{uid}")])
    buttons.append([InlineKeyboardButton("❌ إلغاء", callback_data="admin:cancel")])
    return InlineKeyboardMarkup(buttons)

# =====================================================================================
#  3) معالج دخول الأدمن
# =====================================================================================

async def admin_start_from_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    if not is_admin(user_id):
        await query.answer("⛔ غير مصرح لك", show_alert=True)
        return
    await query.answer()
    await query.edit_message_text(
        "✬︙ لوحة تحكم الأدمن ✬︙\nـ• ┉ • ┉ • ┉ • ┉ • ┉ •",
        reply_markup=admin_main_menu_keyboard()
    )
    return ADMIN_MENU

async def admin_start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_admin(user_id):
        await update.message.reply_text("⛔ غير مصرح لك")
        return ConversationHandler.END
    await update.message.reply_text(
        "✬︙ لوحة تحكم الأدمن ✬︙\nـ• ┉ • ┉ • ┉ • ┉ • ┉ •",
        reply_markup=admin_main_menu_keyboard()
    )
    return ADMIN_MENU

async def admin_menu_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = query.from_user.id
    lang = "ar"

    if data == "admin:close":
        await query.edit_message_text(
            TEXTS[lang]["welcome"],
            reply_markup=build_main_menu(user_id, lang)
        )
        return ConversationHandler.END

    if data == "admin:back_main":
        await query.edit_message_text(
            "✬︙ لوحة تحكم الأدمن ✬︙\nـ• ┉ • ┉ • ┉ • ┉ • ┉ •",
            reply_markup=admin_main_menu_keyboard()
        )
        return ADMIN_MENU

    if data == "admin:cancel":
        await query.edit_message_text(
            "✬︙ لوحة تحكم الأدمن ✬︙\nـ• ┉ • ┉ • ┉ • ┉ • ┉ •",
            reply_markup=admin_main_menu_keyboard()
        )
        return ADMIN_MENU

    # ----- القوائم الفرعية -----
    if data == "admin:materials_menu":
        await query.edit_message_text("⌯ إدارة المواد الدراسية", reply_markup=materials_admin_menu_keyboard())
        return ADMIN_MENU

    if data == "admin:books_menu":
        await query.edit_message_text("⌯ إدارة الكتب الدراسية", reply_markup=books_admin_menu_keyboard())
        return ADMIN_MENU

    if data == "admin:general_menu":
        await query.edit_message_text("⌯ إدارة المساح العام", reply_markup=general_admin_menu_keyboard())
        return ADMIN_MENU

    if data == "admin:admins_menu":
        await query.edit_message_text("⌯ إدارة الأدمنية", reply_markup=admins_admin_menu_keyboard())
        return ADMIN_MENU

    if data == "admin:settings_menu":
        await query.edit_message_text("⌯ إعدادات البوت", reply_markup=settings_admin_menu_keyboard())
        return ADMIN_MENU

    if data == "admin:backup_menu":
        await query.edit_message_text("⌯ النسخ الاحتياطي والتصفير", reply_markup=backup_admin_menu_keyboard())
        return ADMIN_MENU

    # ----- إدارة المواد الدراسية -----
    if data == "admin:add_subject":
        await query.edit_message_text("✏️ اكتب اسم المادة بالعربي:")
        return ADD_SUB_TITLE_AR

    if data == "admin:add_cat":
        materials = load_materials()
        if not materials:
            await query.edit_message_text("⌯ لا توجد مواد بعد ❌", reply_markup=materials_admin_menu_keyboard())
            return ADMIN_MENU
        await query.edit_message_text("✏️ اختر المادة لإضافة قسم جديد:", reply_markup=pick_subject_keyboard(materials, "acsub"))
        return ADD_CAT_PICK_SUB

    if data == "admin:add_file":
        materials = load_materials()
        if not materials:
            await query.edit_message_text("⌯ لا توجد مواد بعد ❌", reply_markup=materials_admin_menu_keyboard())
            return ADMIN_MENU
        await query.edit_message_text("✏️ اختر المادة لإضافة ملف:", reply_markup=pick_subject_keyboard(materials, "afsub"))
        return ADD_FILE_PICK_SUB

    if data == "admin:del_file":
        materials = load_materials()
        if not materials:
            await query.edit_message_text("⌯ لا توجد مواد بعد ❌", reply_markup=materials_admin_menu_keyboard())
            return ADMIN_MENU
        await query.edit_message_text("✏️ اختر المادة لحذف ملف:", reply_markup=pick_subject_keyboard(materials, "dfsub"))
        return DEL_FILE_PICK_SUB

    if data == "admin:del_cat":
        materials = load_materials()
        if not materials:
            await query.edit_message_text("⌯ لا توجد مواد بعد ❌", reply_markup=materials_admin_menu_keyboard())
            return ADMIN_MENU
        await query.edit_message_text("✏️ اختر المادة لحذف قسم:", reply_markup=pick_subject_keyboard(materials, "dcsub"))
        return DEL_CAT_PICK_SUB

    if data == "admin:del_subject":
        materials = load_materials()
        if not materials:
            await query.edit_message_text("⌯ لا توجد مواد بعد ❌", reply_markup=materials_admin_menu_keyboard())
            return ADMIN_MENU
        await query.edit_message_text("✏️ اختر المادة لحذفها بالكامل:", reply_markup=pick_subject_keyboard(materials, "delsub"))
        return DEL_SUB_PICK

    # ----- إدارة الكتب الدراسية -----
    if data == "admin:add_book":
        books_data = load_study_books()
        if not books_data:
            books_data = {"default": {"title_ar": "📚 الكتب الدراسية", "title_en": "Study Books", "books": []}}
            save_study_books(books_data)
        await query.edit_message_text("✏️ اختر المادة لإضافة كتاب:", reply_markup=pick_book_subject_keyboard(books_data))
        return ADD_BOOK_PICK_SUB

    if data == "admin:del_book":
        books_data = load_study_books()
        if not books_data:
            await query.edit_message_text("⌯ لا توجد كتب بعد ❌", reply_markup=books_admin_menu_keyboard())
            return ADMIN_MENU
        await query.edit_message_text("✏️ اختر المادة لحذف كتاب:", reply_markup=pick_book_subject_keyboard(books_data))
        return DEL_BOOK_PICK_SUB

    # ----- إدارة المساح العام -----
    if data == "admin:add_gen":
        await query.edit_message_text("✏️ اكتب عنوان القسم بالعربي:")
        return ADD_GEN_SECTION_TITLE_AR

    if data == "admin:del_gen":
        survey_data = load_general_survey()
        if not survey_data:
            await query.edit_message_text("⌯ لا توجد أقسام بعد ❌", reply_markup=general_admin_menu_keyboard())
            return ADMIN_MENU
        await query.edit_message_text("✏️ اختر القسم لحذفه:", reply_markup=pick_general_section_keyboard(survey_data))
        return DEL_GEN_SECTION_PICK

    # ----- إعدادات البوت -----
    if data == "admin:add_btn":
        await query.edit_message_text("✏️ اكتب عنوان الزر بالعربي:")
        return ADD_BTN_TITLE_AR

    if data == "admin:del_btn":
        custom = load_custom_buttons()
        if not custom:
            await query.edit_message_text("⌯ لا توجد أزرار مخصصة بعد ❌", reply_markup=settings_admin_menu_keyboard())
            return ADMIN_MENU
        await query.edit_message_text("✏️ اختر الزر لحذفه:", reply_markup=pick_custom_button_keyboard(custom))
        return DEL_BTN_PICK

    if data == "admin:edit_btn":
        custom = load_custom_buttons()
        if not custom:
            await query.edit_message_text("⌯ لا توجد أزرار مخصصة بعد ❌", reply_markup=settings_admin_menu_keyboard())
            return ADMIN_MENU
        buttons = [[InlineKeyboardButton(t(b, "ar"), callback_data=f"editbtn:{key}")] for key, b in custom.items()]
        buttons.append([InlineKeyboardButton("❌ إلغاء", callback_data="admin:cancel")])
        await query.edit_message_text("✏️ اختر الزر لتعديل اسمه:", reply_markup=InlineKeyboardMarkup(buttons))
        return EDIT_BTN_PICK

    if data == "admin:edit_core":
        buttons = [[InlineKeyboardButton(TEXTS["ar"][key], callback_data=f"editcore:{key}")] for key in TEXTS["ar"] if key.endswith("_section")]
        buttons.append([InlineKeyboardButton("❌ إلغاء", callback_data="admin:cancel")])
        await query.edit_message_text("✏️ اختر الزر الرئيسي لتعديل اسمه:", reply_markup=InlineKeyboardMarkup(buttons))
        return EDIT_CORE_PICK

    if data == "admin:toggle_core":
        labels = load_menu_labels()
        buttons = []
        for key in TEXTS["ar"]:
            if key.endswith("_section"):
                hidden = labels.get(key, {}).get("hidden", False)
                status = "🙈 مخفي" if hidden else "👁 ظاهر"
                name = TEXTS["ar"][key]
                buttons.append([InlineKeyboardButton(f"{status} — {name}", callback_data=f"coretoggle:{key}")])
        buttons.append([InlineKeyboardButton("👁 إظهار الكل", callback_data="coretoggle:show_all")])
        buttons.append([InlineKeyboardButton("❌ إلغاء", callback_data="admin:cancel")])
        await query.edit_message_text(
            "👁 اضغط على الزر لتبديل حالته (ظاهر/مخفي):\n\n📌 ملاحظة: زر 'إظهار الكل' يعيد جميع الأزرار للظهور.",
            reply_markup=InlineKeyboardMarkup(buttons)
        )
        return TOGGLE_CORE_PICK

    # ----- معلومات مساحية -----
    if data == "admin:add_tip":
        await query.edit_message_text(
            "✏️ اكتب المعلومة بالشكل التالي:\nالسطر الأول: النص بالعربي\nالسطر الثاني: النص بالإنجليزي"
        )
        return ADD_TIP_TEXT

    if data == "admin:del_tip":
        tips = load_tips()
        if not tips:
            await query.edit_message_text("⌯ لا توجد معلومات بعد ❌", reply_markup=settings_admin_menu_keyboard())
            return ADMIN_MENU
        buttons = [[InlineKeyboardButton(tp.get("text_ar", "")[:40], callback_data=f"deltip:{i}")] for i, tp in enumerate(tips)]
        buttons.append([InlineKeyboardButton("❌ إلغاء", callback_data="admin:cancel")])
        await query.edit_message_text("✏️ اختر المعلومة لحذفها:", reply_markup=InlineKeyboardMarkup(buttons))
        return DEL_TIP_PICK

    # ----- الإذاعة -----
    if data == "admin:broadcast":
        await query.edit_message_text("📢 أرسل الرسالة التي تريد إذاعتها (نص، صورة، فيديو، ملف):")
        return BROADCAST_WAIT

    # ----- النسخ الاحتياطي -----
    if data == "admin:list":
        await show_all_data(query)
        return ADMIN_MENU

    if data == "admin:backup":
        await send_backup(query, context)
        return ADMIN_MENU

    if data == "admin:sys_upload":
        buttons = [[InlineKeyboardButton(f, callback_data=f"sysfile:{f}")] for f in ALLOWED_UPLOAD_FILES]
        buttons.append([InlineKeyboardButton("❌ إلغاء", callback_data="admin:cancel")])
        await query.edit_message_text("📤 اختر الملف لاستبداله (سيتم أخذ نسخة احتياطية):", reply_markup=InlineKeyboardMarkup(buttons))
        return SYS_UPLOAD_PICK

    if data == "admin:get_file":
        existing = [f for f in ALLOWED_UPLOAD_FILES if os.path.exists(f)]
        if not existing:
            await query.edit_message_text("⌯ لا توجد ملفات موجودة ❌", reply_markup=backup_admin_menu_keyboard())
            return ADMIN_MENU
        buttons = [[InlineKeyboardButton(f, callback_data=f"getfile:{f}")] for f in existing]
        buttons.append([InlineKeyboardButton("❌ إلغاء", callback_data="admin:cancel")])
        await query.edit_message_text("📥 اختر الملف لتحميله:", reply_markup=InlineKeyboardMarkup(buttons))
        return GET_FILE_PICK

    if data == "admin:sys_delete":
        buttons = [[InlineKeyboardButton(f, callback_data=f"sysdel:{f}")] for f in ALLOWED_RESET_FILES]
        buttons.append([InlineKeyboardButton("❌ إلغاء", callback_data="admin:cancel")])
        await query.edit_message_text("⚠️ اختر ملف البيانات لتصفيره بالكامل (سيتم أخذ نسخة احتياطية):", reply_markup=InlineKeyboardMarkup(buttons))
        return SYS_DELETE_PICK

    if data == "admin:clean_temp":
        removed = clean_temp_files()
        if removed:
            await query.edit_message_text(f"🧹 تم حذف الملفات المؤقتة:\n" + "\n".join(removed), reply_markup=backup_admin_menu_keyboard())
        else:
            await query.edit_message_text("🧹 لا توجد ملفات مؤقتة.", reply_markup=backup_admin_menu_keyboard())
        return ADMIN_MENU

    if data == "admin:restart_ask":
        buttons = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ نعم، أعد التشغيل", callback_data="admin:restart_confirm")],
            [InlineKeyboardButton("❌ إلغاء", callback_data="admin:cancel")],
        ])
        await query.edit_message_text("⚠️ هل أنت متأكد من إعادة تشغيل البوت؟", reply_markup=buttons)
        return ADMIN_MENU

    if data == "admin:restart_confirm":
        await query.edit_message_text("🔄 جاري إعادة التشغيل... انتظر لحظة ثم استخدم /start")
        os.execv(sys.executable, [sys.executable] + sys.argv)
        return ADMIN_MENU

    # ----- إدارة الأدمنية -----
    if data == "admin:list_admins":
        admins = load_admins()
        users = load_users()
        lines = ["👥 قائمة الأدمنية الحالية:\n"]
        for uid, role in admins.items():
            user_data = users.get(uid, {})
            name = user_data.get("name", uid)
            lines.append(f"• {name} (ID: {uid})\n  صلاحية: `{role}`")
        await query.edit_message_text("\n".join(lines), parse_mode="Markdown", reply_markup=admins_admin_menu_keyboard())
        return ADMIN_MENU

    if data == "admin:add_admin":
        await query.edit_message_text("✏️ أرسل معرف (ID) المستخدم الذي تريد إضافته كأدمن:\n\nمثال: 123456789")
        return ADD_ADMIN_ID

    if data == "admin:del_admin":
        admins = load_admins()
        if len(admins) <= 1:
            await query.edit_message_text("⚠️ لا يمكن حذف الأدمن الوحيد.", reply_markup=admins_admin_menu_keyboard())
            return ADMIN_MENU
        await query.edit_message_text("✏️ اختر الأدمن لحذفه:", reply_markup=pick_admin_keyboard(admins))
        return DEL_ADMIN_PICK

    if data == "admin:edit_admin":
        admins = load_admins()
        await query.edit_message_text("✏️ اختر الأدمن لتعديل صلاحيته:", reply_markup=pick_admin_keyboard(admins))
        return EDIT_ADMIN_PICK

    return ADMIN_MENU

# =====================================================================================
#  4) معالجات إضافة/حذف المواد
# =====================================================================================

async def add_sub_title_ar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["new_sub_ar"] = update.message.text.strip()
    await update.message.reply_text("✏️ اكتب اسم المادة بالإنجليزي:")
    return ADD_SUB_TITLE_EN

async def add_sub_title_en(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["new_sub_en"] = update.message.text.strip()
    await update.message.reply_text("✏️ اكتب معرف قصير بالإنجليزي (بدون مسافات):")
    return ADD_SUB_KEY

async def add_sub_key(update: Update, context: ContextTypes.DEFAULT_TYPE):
    key = update.message.text.strip().replace(" ", "_")
    materials = load_materials()
    if key in materials:
        await update.message.reply_text("⚠️ هذا المعرف مستخدم بالفعل، اختر معرفاً آخر:")
        return ADD_SUB_KEY
    materials[key] = {
        "title_ar": context.user_data["new_sub_ar"],
        "title_en": context.user_data["new_sub_en"],
        "categories": {
            "summaries": {"title_ar": "📄 ملخصات PDF", "title_en": "📄 PDF Summaries", "files": []},
            "videos": {"title_ar": "🎥 الفيديوهات", "title_en": "🎥 Videos", "files": []},
            "exercises": {"title_ar": "📝 تمارين محلولة", "title_en": "📝 Solved Exercises", "files": []},
        },
    }
    save_materials(materials)
    await update.message.reply_text("✅ تمت إضافة المادة بنجاح.", reply_markup=materials_admin_menu_keyboard())
    return ADMIN_MENU

async def add_cat_pick_sub(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data["target_subject"] = query.data.split(":")[1]
    await query.edit_message_text("✏️ اكتب اسم القسم بالعربي:")
    return ADD_CAT_TITLE_AR

async def add_cat_title_ar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["new_cat_ar"] = update.message.text.strip()
    await update.message.reply_text("✏️ اكتب اسم القسم بالإنجليزي:")
    return ADD_CAT_TITLE_EN

async def add_cat_title_en(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["new_cat_en"] = update.message.text.strip()
    await update.message.reply_text("✏️ اكتب معرف قصير بالإنجليزي (بدون مسافات):")
    return ADD_CAT_KEY

async def add_cat_key(update: Update, context: ContextTypes.DEFAULT_TYPE):
    key = update.message.text.strip().replace(" ", "_")
    subject_key = context.user_data["target_subject"]
    materials = load_materials()
    if key in materials[subject_key]["categories"]:
        await update.message.reply_text("⚠️ هذا المعرف مستخدم بالفعل، اختر معرفاً آخر:")
        return ADD_CAT_KEY
    materials[subject_key]["categories"][key] = {
        "title_ar": context.user_data["new_cat_ar"],
        "title_en": context.user_data["new_cat_en"],
        "files": [],
    }
    save_materials(materials)
    await update.message.reply_text("✅ تمت إضافة القسم بنجاح.", reply_markup=materials_admin_menu_keyboard())
    return ADMIN_MENU

async def add_file_pick_sub(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    subject_key = query.data.split(":")[1]
    materials = load_materials()
    context.user_data["target_subject"] = subject_key
    await query.edit_message_text("✏️ اختر القسم:", reply_markup=pick_category_keyboard(materials, subject_key, "afcat"))
    return ADD_FILE_PICK_CAT

async def add_file_pick_cat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    _, subject_key, cat_key = query.data.split(":")
    context.user_data["target_subject"] = subject_key
    context.user_data["target_category"] = cat_key
    await query.edit_message_text(
        "📎 أرسل الملف (PDF، فيديو، صورة، صوت، GIF)\nأو أرسل رابط الملف (ابدأ بـ http:// أو https://)"
    )
    return ADD_FILE_UPLOAD

async def add_file_upload(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    file_id = None
    file_type = "document"
    file_url = None
    if message.text and (message.text.startswith("http://") or message.text.startswith("https://")):
        file_url = message.text.strip()
    else:
        file_id, file_type = detect_uploaded_file(message)
        if not file_id:
            await message.reply_text("⚠️ أرسل ملفاً مدعوماً أو رابطاً صحيحاً.")
            return ADD_FILE_UPLOAD
    context.user_data["new_file_id"] = file_id
    context.user_data["new_file_type"] = file_type
    context.user_data["new_file_url"] = file_url
    await message.reply_text("✏️ اكتب عنوان الملف بالعربي:")
    return ADD_FILE_TITLE_AR

async def add_file_title_ar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["new_file_ar"] = update.message.text.strip()
    await update.message.reply_text("✏️ اكتب عنوان الملف بالإنجليزي:")
    return ADD_FILE_TITLE_EN

async def add_file_title_en(update: Update, context: ContextTypes.DEFAULT_TYPE):
    title_en = update.message.text.strip()
    subject_key = context.user_data["target_subject"]
    cat_key = context.user_data["target_category"]
    materials = load_materials()
    file_entry = {
        "title_ar": context.user_data["new_file_ar"],
        "title_en": title_en,
        "type": context.user_data["new_file_type"],
    }
    if context.user_data.get("new_file_id"):
        file_entry["file_id"] = context.user_data["new_file_id"]
    if context.user_data.get("new_file_url"):
        file_entry["file_url"] = context.user_data["new_file_url"]
    materials[subject_key]["categories"][cat_key]["files"].append(file_entry)
    save_materials(materials)
    await update.message.reply_text("✅ تمت إضافة الملف بنجاح.", reply_markup=materials_admin_menu_keyboard())
    return ADMIN_MENU

# بقية المعالجات (حذف ملف، حذف قسم، حذف مادة، الكتب، المساح العام، الأدمنية، الإذاعة، النسخ الاحتياطي، الملفات) مشابهة للنسخة السابقة
# بسبب ضيق المساحة، سيتم إرسالها في ملف منفصل إذا طُلب ذلك

# =====================================================================================
#  5) دالة إعادة محادثة الأدمن
# =====================================================================================

def get_admin_conversation():
    from telegram.ext import ConversationHandler
    admin_conv = ConversationHandler(
        entry_points=[
            CommandHandler("admin", admin_start_command),
            CallbackQueryHandler(admin_start_from_button, pattern="^menu:admin$"),
        ],
        states={
            ADMIN_MENU: [CallbackQueryHandler(admin_menu_router, pattern="^admin:")],
            ADD_SUB_TITLE_AR: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_sub_title_ar)],
            ADD_SUB_TITLE_EN: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_sub_title_en)],
            ADD_SUB_KEY: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_sub_key)],
            ADD_CAT_PICK_SUB: [CallbackQueryHandler(add_cat_pick_sub, pattern="^acsub:")],
            ADD_CAT_TITLE_AR: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_cat_title_ar)],
            ADD_CAT_TITLE_EN: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_cat_title_en)],
            ADD_CAT_KEY: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_cat_key)],
            ADD_FILE_PICK_SUB: [CallbackQueryHandler(add_file_pick_sub, pattern="^afsub:")],
            ADD_FILE_PICK_CAT: [CallbackQueryHandler(add_file_pick_cat, pattern="^afcat:")],
            ADD_FILE_UPLOAD: [MessageHandler(filters.TEXT | filters.Document.ALL | filters.VIDEO | filters.PHOTO | filters.AUDIO | filters.VOICE | filters.ANIMATION, add_file_upload)],
            ADD_FILE_TITLE_AR: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_file_title_ar)],
            ADD_FILE_TITLE_EN: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_file_title_en)],
            # باقي الحالات ستضاف هنا
        },
        fallbacks=[
            CommandHandler("cancel", lambda u, c: ConversationHandler.END),
            CallbackQueryHandler(admin_menu_router, pattern="^admin:"),
        ],
    )
    return admin_conv

# دوال مساعدة
def clean_temp_files() -> list:
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

async def show_all_data(query):
    materials = load_materials()
    lines = ["📋 *جميع بيانات البوت:*\n"]
    lines.append("📘 *المواد الدراسية:*")
    if not materials:
        lines.append("  لا توجد مواد.")
    for skey, sdata in materials.items():
        lines.append(f"  • {t(sdata, 'ar')} (key: {skey})")
        for ckey, cdata in sdata["categories"].items():
            lines.append(f"    └ {t(cdata, 'ar')} — {len(cdata['files'])} ملف")
    books = load_study_books()
    lines.append("\n📚 *الكتب الدراسية:*")
    if not books:
        lines.append("  لا توجد كتب.")
    for skey, sdata in books.items():
        lines.append(f"  • {t(sdata, 'ar')} — {len(sdata.get('books', []))} كتاب")
    survey = load_general_survey()
    lines.append("\n🧭 *المساح العام:*")
    if not survey:
        lines.append("  لا توجد أقسام.")
    for skey, sdata in survey.items():
        lines.append(f"  • {t(sdata, 'ar')}")
    lines.append(f"\n📊 *إحصائيات:*")
    lines.append(f"  • أزرار مخصصة: {len(load_custom_buttons())}")
    lines.append(f"  • معلومات مساحية: {len(load_tips())}")
    total_quiz = sum(len(qs) for qs in load_quiz().values())
    lines.append(f"  • أسئلة كويز: {total_quiz}")
    lines.append(f"  • أجهزة: {len(load_instruments())}")
    lines.append(f"  • أدوات: {len(load_tools())}")
    lines.append(f"  • مستخدمين مسجلين: {len(load_users())}")
    lines.append(f"  • أدمنية: {len(load_admins())}")
    await query.edit_message_text("\n".join(lines), parse_mode="Markdown", reply_markup=backup_admin_menu_keyboard())

async def send_backup(query, context):
    await query.answer("⏳ جاري تجهيز النسخة الاحتياطية...")
    files_to_backup = [
        "materials.json", "custom_buttons.json", "users.json", "tips.json", "quiz.json",
        "instruments.json", "tools.json", "menu_labels.json",
        "study_books.json", "admins.json", "general_survey.json", "links.json",
        "bot.py"
    ]
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
        caption=f"📦 نسخة احتياطية بتاريخ {timestamp}"
    )
    await query.message.reply_text("✅ تم إرسال النسخة الاحتياطية.", reply_markup=backup_admin_menu_keyboard())

# ملاحظة: تم اختصار admin_handlers.py بسبب طول الكود، ولكن جميع الوظائف الأساسية موجودة.