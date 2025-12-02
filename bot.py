import os
import re
import cloudscraper
from bs4 import BeautifulSoup
from telegram.ext import Updater, MessageHandler, Filters, CommandHandler

TOKEN = os.getenv("TOKEN")
PROXY = os.getenv("PROXY")  # مثال: http://144.125.164.158:8080

if not TOKEN:
    raise ValueError("TOKEN is missing. Add TOKEN in Heroku Config Vars.")

# جهّز البروكسي (اختياري)
proxies = None
if PROXY and PROXY.strip():
    p = PROXY.strip()
    # لو المستخدم كتب IP:PORT فقط بدون http://
    if not p.startswith("http://") and not p.startswith("https://"):
        p = "http://" + p
    proxies = {"http": p, "https": p}

# cloudscraper لتجاوز بعض الحمايات
scraper = cloudscraper.create_scraper(
    browser={"browser": "chrome", "platform": "windows", "mobile": False}
)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9,ar;q=0.8",
}

def start(update, context):
    update.message.reply_text("🎬 ابعت اسم الفيلم/المسلسل (مثال: tenet)")

def google_find_subdl_pages(query: str, limit: int = 5):
    # نبحث في جوجل عن صفحات subdl subtitle
    q = f'site:subdl.com/subtitle {query}'
    url = "https://www.google.com/search?q=" + re.sub(r"\s+", "+", q.strip())

    html = scraper.get(url, headers=HEADERS, proxies=proxies, timeout=25).text
    soup = BeautifulSoup(html, "html.parser")

    links = []
    for a in soup.select("a"):
        href = a.get("href") or ""
        # جوجل بيحطها غالبًا /url?q=....
        m = re.search(r"(https://subdl\.com/subtitle/[^&]+)", href)
        if m:
            link = m.group(1)
            if link not in links:
                links.append(link)
        if len(links) >= limit:
            break
    return links

def extract_download_links(subtitle_page_url: str):
    html = scraper.get(subtitle_page_url, headers=HEADERS, proxies=proxies, timeout=25).text
    soup = BeautifulSoup(html, "html.parser")

    # SubDL بيكون فيه روابط download بأشكال مختلفة حسب الصفحة
    links = []

    # أي لينك فيه download أو zip
    for a in soup.select("a"):
        href = a.get("href") or ""
        text = (a.get_text() or "").strip().lower()

        if not href:
            continue

        # حوّل النسبي لمطلق
        if href.startswith("/"):
            href_full = "https://subdl.com" + href
        else:
            href_full = href

        if ("download" in href.lower()) or ("zip" in href.lower()) or ("download" in text):
            if href_full not in links:
                links.append(href_full)

    return links

def handle_text(update, context):
    q = (update.message.text or "").strip()
    if not q:
        update.message.reply_text("اكتب اسم صحيح.")
        return

    update.message.reply_text("⏳ بدوّر…")

    try:
        pages = google_find_subdl_pages(q, limit=5)
        if not pages:
            update.message.reply_text("❌ ملقتش صفحات ترجمة على SubDL (ممكن جوجل/البروكسي حاظرين). جرّب بروكسي تاني.")
            return

        # اختار أول صفحة subtitle
        page = pages[0]
        dl_links = extract_download_links(page)

        msg = f"✅ لقيت صفحة ترجمة:\n{page}\n"
        if dl_links:
            msg += "\n⬇️ روابط تحميل محتملة:\n" + "\n".join(dl_links[:5])
        else:
            msg += "\n⚠️ ملقتش زر تحميل في الصفحة دي (جرّب تفتح اللينك بنفسك أو جرّب نتيجة تانية)."

        update.message.reply_text(msg)

    except Exception as e:
        print("ERROR:", e)
        update.message.reply_text("⚠️ حصل خطأ (غالبًا البروكسي واقع/بطيء). جرّب بروكسي تاني.")

def main():
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_text))

    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()
