import os
import requests
import re
from bs4 import BeautifulSoup
from telegram.ext import Updater, MessageHandler, Filters, CommandHandler

TOKEN = os.getenv("TOKEN")

def start(update, context):
    update.message.reply_text("🎬 ابعت اسم الفيلم وهجيبلك الترجمة من SubDL مباشرة 🔥")

def google_subdl(query):
    q = f"site:subdl.com/subtitle {query} arabic"
    url = f"https://www.google.com/search?q={q}"
    headers = {"User-Agent": "Mozilla/5.0"}

    html = requests.get(url, headers=headers).text
    soup = BeautifulSoup(html, "html.parser")

    links = []

    for a in soup.select("a"):
        href = a.get("href", "")
        match = re.search(r"https://subdl\.com\/subtitle\/[^&]+", href)
        if match:
            links.append(match.group(0))

    return links[:5]  # أول 5 نتائج

def handle_text(update, context):
    film = update.message.text
    update.message.reply_text("⏳ ببحث في SubDL…")

    results = google_subdl(film)

    if not results:
        update.message.reply_text("❌ ملقيتش ترجمة على SubDL.")
        return

    first = results[0]
    update.message.reply_text(f"✔ لقيت ترجمة:\n{first}")

def main():
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_text))
    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()
