import os
import re
import requests
from flask import Flask, request

app = Flask(__name__)

BOT_TOKEN = os.environ["BOT_TOKEN"]
SUBSOURCE_API_KEY = os.environ["SUBSOURCE_API_KEY"]

# أهم متغير: base
# مثال شائع: https://api.subsource.net/api/v1
SUBSOURCE_BASE = os.environ.get("SUBSOURCE_BASE", "https://api.subsource.net/api/v1").rstrip("/")

# Paths (تقدر تغيّرها من Heroku بدون تعديل الكود)
# لو الدوكس عندك مختلف: عدّل المتغيرات دي في Config Vars
MOVIES_SEARCH_PATH = os.environ.get("MOVIES_SEARCH_PATH", "/movies/search")
SUBTITLES_LIST_PATH = os.environ.get("SUBTITLES_LIST_PATH", "/subtitles")
SUBTITLE_DOWNLOAD_PATH = os.environ.get("SUBTITLE_DOWNLOAD_PATH", "/subtitles/{id}/download")

# Auth header style: X_API_KEY | BEARER | API_KEY_HEADER_NAME
AUTH_MODE = os.environ.get("AUTH_MODE", "X_API_KEY")  # الافتراضي
API_KEY_HEADER_NAME = os.environ.get("API_KEY_HEADER_NAME", "X-API-Key")  # لو AUTH_MODE=API_KEY_HEADER_NAME

TG_API = f"https://api.telegram.org/bot{BOT_TOKEN}"

def tg_send(chat_id: int, text: str):
    requests.post(
        f"{TG_API}/sendMessage",
        json={"chat_id": chat_id, "text": text, "disable_web_page_preview": True},
        timeout=30
    ).raise_for_status()

def _auth_headers():
    base = {
        "Accept": "application/json",
        "User-Agent": "SubSourceTelegramBot/1.0",
    }

    if AUTH_MODE == "BEARER":
        base["Authorization"] = f"Bearer {SUBSOURCE_API_KEY}"
        return base

    if AUTH_MODE == "API_KEY_HEADER_NAME":
        base[API_KEY_HEADER_NAME] = SUBSOURCE_API_KEY
        return base

    # AUTH_MODE == "X_API_KEY" (افتراضي)
    base["X-API-Key"] = SUBSOURCE_API_KEY
    return base

def subsource_request(method: str, path: str, params=None):
    url = SUBSOURCE_BASE + (path if path.startswith("/") else ("/" + path))
    r = requests.request(method, url, headers=_auth_headers(), params=params, timeout=30)
    # لو عايز تشوف URL في اللوجز: اطبعها
    print(f"[SubSource] {method} {r.url} -> {r.status_code}")
    r.raise_for_status()
    # بعض الـ APIs بترجع نص بدل JSON في download info
    try:
        return r.json()
    except Exception:
        return {"raw": r.text}

def normalize_lang(token: str):
    m = {
        "ar": "arabic", "arabic": "arabic",
        "en": "english", "english": "english",
        "fr": "french", "french": "french",
        "es": "spanish", "spanish": "spanish",
        "de": "german", "german": "german",
        "it": "italian", "italian": "italian",
        "tr": "turkish", "turkish": "turkish",
        "fa": "persian", "persian": "persian",
    }
    return m.get(token.lower(), "arabic")

def parse_sub_command(text: str):
    # /sub Tenet ar
    # /sub The Dark Knight english
    parts = text.strip().split()
    if not parts or parts[0].lower() not in ["/sub", "/subtitle"]:
        return None

    if len(parts) == 1:
        return {"query": "", "lang": "arabic", "want_download": False}

    want_download = False
    if parts[-1].lower() in ["-d", "--download"]:
        want_download = True
        parts = parts[:-1]

    lang = "arabic"
    if len(parts) >= 3 and re.fullmatch(r"[a-zA-Z]+", parts[-1]) and parts[-1].lower() in [
        "ar","en","fr","es","de","it","tr","fa",
        "arabic","english","french","spanish","german","italian","turkish","persian"
    ]:
        lang = normalize_lang(parts[-1])
        q = " ".join(parts[1:-1]).strip()
    else:
        q = " ".join(parts[1:]).strip()

    return {"query": q, "lang": lang, "want_download": want_download}

def pick_first_id(obj, keys):
    for k in keys:
        if isinstance(obj, dict) and k in obj and obj[k] is not None:
            return obj[k]
    return None

def ensure_list(resp):
    # بعض الـ APIs بترجع {items:[...]} أو {results:[...]} أو list مباشرة
    if isinstance(resp, list):
        return resp
    if isinstance(resp, dict):
        for k in ["items", "results", "data"]:
            if k in resp and isinstance(resp[k], list):
                return resp[k]
    return []

def handle_search(query: str, lang: str):
    # 1) Search movies
    movies_resp = subsource_request("GET", MOVIES_SEARCH_PATH, params={"query": query})
    movies = ensure_list(movies_resp)
    if not movies:
        return f"ملقتش نتائج لـ: {query}"

    movie = movies[0]
    movie_id = pick_first_id(movie, ["id", "movieId", "tmdbId"])
    title = movie.get("title") or movie.get("name") or str(movie_id)

    if not movie_id:
        return f"لقيت نتيجة بس مش قادر أقرأ movie id.\nRaw: {movie}"

    # 2) List subtitles
    subs_resp = subsource_request("GET", SUBTITLES_LIST_PATH, params={"movieId": movie_id, "language": lang})
    subs = ensure_list(subs_resp)
    if not subs:
        return f"لقيت: {title}\nبس ملقتش ترجمات للغة ({lang})."

    lines = [f"🎬 {title}", f"🌐 Language: {lang}", ""]
    for i, s in enumerate(subs[:5], start=1):
        sid = pick_first_id(s, ["id", "subtitleId"])
        name = s.get("releaseName") or s.get("name") or s.get("title") or "Subtitle"
        rating = s.get("rating") or s.get("score")
        extra = []
        if rating is not None:
            extra.append(f"rating={rating}")
        if sid is None:
            lines.append(f"{i}) {name}")
        else:
            lines.append(f"{i}) {name}  (id: {sid})" + (f"  [{' ,'.join(extra)}]" if extra else ""))

    lines.append("")
    lines.append("لو عايز تحميل مباشر: اكتب /sub <name> <lang> --download (لو الـ API بيدعم download endpoint).")
    return "\n".join(lines)

@app.post("/webhook")
def webhook():
    update = request.get_json(force=True, silent=True) or {}
    msg = update.get("message") or update.get("edited_message") or {}
    chat_id = (msg.get("chat") or {}).get("id")
    text = (msg.get("text") or "").strip()

    if not chat_id:
        return "ok"

    cmd = parse_sub_command(text)
    if cmd is None:
        tg_send(chat_id, "اكتب:\n/sub اسم الفيلم او المسلسل اللغة\nمثال:\n/sub Tenet ar\n/sub The Bear english")
        return "ok"

    if not cmd["query"]:
        tg_send(chat_id, "اكتب اسم العمل بعد /sub\nمثال: /sub Tenet ar")
        return "ok"

    try:
        reply = handle_search(cmd["query"], cmd["lang"])
    except requests.HTTPError as e:
        # خلي الرسالة مفيدة وفيها URL اللي اتضربت (موجودة في اللوجز)
        reply = f"حصل خطأ من SubSource API: {str(e)}\n" \
                f"راجع Heroku Logs وشوف هل الـ BASE/PATH/Auth صح."
    except Exception as e:
        reply = f"خطأ غير متوقع: {e}"

    tg_send(chat_id, reply)
    return "ok"

@app.get("/")
def home():
    return "OK"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "5000")))
