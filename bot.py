import os
import requests
from bs4 import BeautifulSoup
from telegram.ext import Updater, MessageHandler, Filters, CommandHandler


# اقرأ التوكن من Heroku
TOKEN = os.getenv("TOKEN")

print("TOKEN FROM HEROKU:", TOKEN)  # Debug يظهر في اللوج

if not TOKEN:
    raise ValueError("❌ TOKEN not found in environment variables!")


def start(update, context):
    update.message.reply_text("🎬 أهلاً! ابعت اسم الفيلم وهجيبلك الترجمة.")


def search_subdl(query):
    url = f"https://subdl.com/search/{query.replace(' ', '%20')}"
    headers = {"User-Agent": "Mozilla/5.0"}

    r = requests.get(url, headers=headers)
    soup = BeautifulSoup(r.text, "html.parser")

    results = []
    for item in soup.select(".sub-title"):
        title = item.text.strip()
        link = "https://subdl.com" + item.find("a")["href"]
        results.append((title, link))

    return results


def handle_text(update, context):
    query = update.message.text
    update.message.reply_text("⏳ جاري البحث…")

    try:
        results = search_subdl(query)
        if not results:
            update.message.reply_text("❌ مفيش ترجمة للاسم ده.")
            return

        title, link = results[0]

        update.message.reply_text(
            f"✔️ لقيت ترجمة:\n"
            f"🎬 {title}\n"
            f"🔗 {link}"
        )

    except Exception as e:
        update.message.reply_text("⚠️ حصل خطأ.")
        print("ERROR:", e)


def main():
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_text))

    updater.start_polling()
    updater.idle()


if __name__ == "__main__":
    main()
