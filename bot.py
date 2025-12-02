import os
import cloudscraper
from bs4 import BeautifulSoup
from telegram.ext import Updater, MessageHandler, Filters, CommandHandler

TOKEN = os.getenv("TOKEN")
print("TOKEN:", TOKEN)

scraper = cloudscraper.create_scraper()  # bypass Cloudflare


def start(update, context):
    update.message.reply_text("🎬 ابعت اسم الفيلم او المسلسل وهجيبلك الترجمة 🔥")


def search_subdl(query):
    url = f"https://subdl.com/search?query={query.replace(' ', '+')}"
    html = scraper.get(url).text

    soup = BeautifulSoup(html, "html.parser")

    results = []

    # العنصر الصحيح في SubDL
    for item in soup.select("div.col-md-10 a"):
        title = item.text.strip()
        link = "https://subdl.com" + item["href"]
        results.append((title, link))

    return results


def handle_text(update, context):
    query = update.message.text
    update.message.reply_text("⏳ جاري البحث…")

    results = search_subdl(query)

    if not results:
        update.message.reply_text("❌ مفيش ترجمة للاسم ده.")
        return

    title, link = results[0]

    update.message.reply_text(
        f"✔️ لقيت ترجمة:\n🎬 {title}\n🔗 {link}"
    )


def main():
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_text))
    updater.start_polling()
    updater.idle()


if __name__ == "__main__":
    main()
