import os
import requests
from flask import Flask, request

app = Flask(__name__)

BOT_TOKEN = os.environ["BOT_TOKEN"]
SUBSOURCE_API_KEY = os.environ["SUBSOURCE_API_KEY"]

# 1) حط الـ Base URL من Swagger (Servers)
SUBSOURCE_BASE = os.environ.get("SUBSOURCE_BASE", "https://subsource.net")  # عدّلها حسب الدوكس

TG_API = f"https://api.telegram.org/bot{BOT_TOKEN}"

def tg_send(chat_id: int, text: str):
    requests.post(
        f"{TG_API}/sendMessage",
        json={"chat_id": chat_id, "text": text, "disable_web_page_preview": True},
        timeout=30,
    ).raise_for_status()

def subsource_request(method: str, path: str, params=None):
    """
    2) عدّل طريقة توثيق الـ API Key حسب الدوكس:
       - لو Header: Authorization: Bearer <key> أو X-API-Key
       - لو Query: api_key=<key>
    """
    url = SUBSOURCE_BASE.rstrip("/") + path

    headers = {
        # مثال شائع — عدّله حسب الدوكس
        "Authorization": f"Bearer {SUBSOURCE_API_KEY}",
        # أو: "X-API-Key": SUBSOURCE_API_KEY
    }

    r = requests.request(method, url, headers=headers, params=params, timeout=30)
    r.raise_for_status()
    return r.json()

def pick_lang_token(user_lang: str):
    # حسب الموجود في SubSource نفسه (arabic/english...) زي صفحات الموقع
    # مثال: https://subsource.net/subtitle/.../arabic/... :contentReference[oaicite:3]{index=3}
    m = {
        "ar": "arabic",
        "arabic": "arabic",
        "en": "english",
        "english": "english",
        "fr": "french",
        "es": "spanish",
        "de": "german",
        "it": "italian",
        "tr": "turkish",
        "fa": "persian",
    }
    return m.get(user_lang.lower(), "arabic")

def handle_query(q: str, lang: str):
    """
    3) هنا بقى حط endpoints الصح من Swagger.
       أنا حاطط "شكل" منطقي بناءً على الوظائف المذكورة (SearchMovies/GetSubtitles/Download). :contentReference[oaicite:4]{index=4}
    """

    # مثال: Search movies
    # عدّل المسار والباراميترز حسب الدوكس
    movies = subsource_request("GET", "/api/movies/search", params={"query": q})
    if not movies:
        return f"ملقتش نتائج لـ: {q}"

    movie = movies[0]
    movie_id = movie.get("id") or movie.get("movieId")

    # مثال: Get subtitles
    subs = subsource_request("GET", "/api/subtitles", params={"movieId": movie_id, "language": lang})
    if not subs:
        return f"لقيت الفيلم بس ملقتش ترجمات ({lang})."

    # رجّع أحسن 5
    lines = [f"نتائج لـ: {movie.get('title','(بدون عنوان)')}"]
    for i, s in enumerate(subs[:5], start=1):
        sid = s.get("id") or s.get("subtitleId")
        name = s.get("releaseName") or s.get("name") or "Subtitle"
        # مثال: Download link endpoint (عدّله حسب الدوكس)
        lines.append(f"{i}) {name} | id={sid}")

    return "\n".join(lines)

@app.post("/webhook")
def webhook():
    update = request.get_json(force=True, silent=True) or {}
    msg = update.get("message") or {}
    chat_id = (msg.get("chat") or {}).get("id")
    text = (msg.get("text") or "").strip()

    if not chat_id:
        return "ok"

    if not text.startswith("/sub"):
        tg_send(chat_id, "اكتب:\n/sub اسم الفيلم او المسلسل اللغة\nمثال:\n/sub The Bear ar")
        return "ok"

    parts = text.split(maxsplit=2)
    if len(parts) < 2:
        tg_send(chat_id, "اكتب اسم العمل بعد /sub")
        return "ok"

    q = parts[1] if len(parts) == 2 else parts[1] + " " + parts[2]
    # لو آخر كلمة لغة (ar/en/arabic/english...)
    tokens = q.split()
    lang = "arabic"
    if tokens and tokens[-1].lower() in ["ar","en","arabic","english","fr","es","de","it","tr","fa","french","spanish","german","italian","turkish","persian"]:
        lang = pick_lang_token(tokens[-1])
        q = " ".join(tokens[:-1]).strip()

    try:
        reply = handle_query(q, lang)
    except requests.HTTPError as e:
        reply = f"حصل خطأ من SubSource API: {str(e)}"

    tg_send(chat_id, reply)
    return "ok"

@app.get("/")
def home():
    return "OK"
