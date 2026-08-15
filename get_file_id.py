# -*- coding: utf-8 -*-
"""
سكربت مساعد للحصول على file_id
================================
الطريقة:
1) شغّل هذا السكربت (منفصل عن bot.py الرئيسي)
2) افتح البوت في تليجرام وأرسل له أي ملف PDF أو فيديو
3) سيرد عليك البوت بالـ file_id الخاص بذلك الملف
4) انسخ الـ file_id والصقه في materials.json داخل الملف المناسب

المتطلبات:
    pip install python-telegram-bot --upgrade
"""

from telegram import Update
from telegram.ext import Application, MessageHandler, ContextTypes, filters

# نفس توكن البوت (يمكن استخدام نفس البوت أو بوت تجريبي منفصل)
BOT_TOKEN = "8753500776:AAFf3i35j7ReiHae0eFlPH9Fx97-4LQL2Tg"


async def handle_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """يستقبل أي ملف (PDF أو فيديو) ويرد بمعلوماته."""
    message = update.message

    if message.document:
        file_id = message.document.file_id
        file_name = message.document.file_name
        await message.reply_text(
            f"📄 نوع الملف: document\n"
            f"الاسم: {file_name}\n\n"
            f"file_id:\n`{file_id}`",
            parse_mode="Markdown",
        )

    elif message.video:
        file_id = message.video.file_id
        await message.reply_text(
            f"🎥 نوع الملف: video\n\n"
            f"file_id:\n`{file_id}`",
            parse_mode="Markdown",
        )

    else:
        await message.reply_text("أرسل ملف PDF أو فيديو فقط.")


def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.Document.ALL | filters.VIDEO, handle_file))
    print("✅ سكربت الحصول على file_id يعمل... أرسل ملفاً للبوت الآن")
    app.run_polling()


if __name__ == "__main__":
    main()
