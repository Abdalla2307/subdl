import requests
from bs4 import BeautifulSoup
from telegram.ext import Updater, MessageHandler, Filters, CommandHandler
import zipfile
import os
import uuid

TOKEN = "PUT_YOUR_TELEGRAM_BOT_TOKEN_HERE"


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


def get_download_link(page_url):
    headers = {"User-Agent": "Mozilla/5.0"}
    r = requests.get(page_url, headers=headers)
    soup = BeautifulSoup(r.text, "html.parser")

    btn = soup.select_one("a#downloadButton")
    if not btn:
        return None

    return "https://subdl.com" + btn["href"]


def download_and_extract(url):
    headers = {"User-Agent": "Mozilla/5.0"}

    r = requests.get(url, headers=headers)
    zip_name = f"temp_{uuid.uuid4()}.zip"

    with open(zip_name, "wb") as f:
        f.write(r.content)

    with zipfile.ZipFile(zip_name, "r") as zip_ref:
        zip_ref.extractall("subs")

    os.remove(zip_name)

    for file in os.listdir("subs"):
        if file.endswith(".srt"):
            return os.path.join("subs", file)

    return None


def start(update, context):
    update.message.reply_text(
        "🎬 أهلاً! أرسل اسم الفيلم أو المسلسل وسأرسل لك الترجمة SRT مباشرة."
    )


def handle_text(update, context):
    query = update.message.text
    update.message.reply_text("⏳ جاري البحث…")

    try:
        results = search_subdl(query)
        if not results:
            update.message.reply_text("❌ لم أجد أي ترجمة.")
            return

        title, page_url = results[0]
        update.message.reply_text(f"✔️ تم العثور على: {title}\n⏳ جاري تحميل الترجمة…")

        dl_link = get_download_link(page_url)
        if not dl_link:
            update.message.reply_text("⚠️ لم أجد رابط التنزيل.")
            return

        srt_file = download_and_extract(dl_link)
        if not srt_file:
            update.message.reply_text("⚠️ لم أستطع استخراج ملف SRT.")
            return

        update.message.reply_document(open(srt_file, "rb"))
        os.remove(srt_file)

    except Exception as e:
        print(e)
        update.message.reply_text("⚠️ حدث خطأ أثناء تنفيذ العملية.")


def main():
    if not os.path.exists("subs"):
        os.mkdir("subs")

    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_text))

    updater.start_polling()
    updater.idle()


if __name__ == "__main__":
    main()
