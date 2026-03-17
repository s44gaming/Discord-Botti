import json
import os
import sys
import secrets
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests
from flask import Flask, redirect, url_for, session, request, jsonify, render_template
from functools import wraps
import database
from config import DEV_USER_IDS, BOT_INFO_EDIT_PASSWORD

_REQ_TIMEOUT = 30
_REQ_HEADERS = {"User-Agent": "DiscordBot (Web Dashboard)"}
_CACHE_TTL = 90  # sekuntia Discord API -vastauksille
_CACHE_MAX_SIZE = 300  # max välimuistissa olevia avaimia (channels, roles)
_discord_cache = {}
_cache_keys_order = []  # FIFO eviction
_cache_lock = threading.Lock()

app = Flask(__name__, template_folder="web/templates", static_folder="web/static")
app.secret_key = os.getenv("FLASK_SECRET_KEY", secrets.token_hex(32))
app.config["PERMANENT_SESSION_LIFETIME"] = 86400
app.config["JSON_SORT_KEYS"] = False  # Nopeampi JSON-serialisointi


@app.errorhandler(Exception)
def _capture_unhandled(exc):
    """Tallentaa käsittelemättömät virheet kehittäjäportaalin virhelokiin."""
    from werkzeug.exceptions import HTTPException
    if isinstance(exc, HTTPException):
        return exc
    try:
        import shared_state
        shared_state.add_error(exc, "Flask")
    except Exception:
        pass
    return jsonify({"error": str(exc)}), 500

DISCORD_API = "https://discord.com/api/v10"
CLIENT_ID = os.getenv("DISCORD_CLIENT_ID")
CLIENT_SECRET = os.getenv("DISCORD_CLIENT_SECRET")
REDIRECT_URI = os.getenv("DISCORD_REDIRECT_URI", "http://localhost/callback")
BASE_URL = os.getenv("BASE_URL", "http://localhost")
BOT_TOKEN = os.getenv("DISCORD_TOKEN")

# Komennot – kukin voi kytkeä päälle/pois webissä
# Huom: Discord-komennon nimi muutetaan VAIN commands/*.py -tiedostoissa @app_commands.command(name="...")
# sekä komennot_lista.py COMMAND_TO_FEATURE -mappauksessa. Feature-avaimet (ping, taso, jne.) pysyvät tietokannassa.
COMMAND_FEATURES = [
    ("ping", "Ping", "/ping – check response time"),
    ("info", "Info", "/info – server info"),
    ("avatar", "Avatar", "/avatar – show profile picture"),
    ("userinfo", "Userinfo", "/userinfo – user details"),
    ("reverse", "Reverse", "/reverse – reverse text"),
    ("tempvoice", "TempVoice", "Temp voice panel (/tempvoice_panel)"),
    ("hallinta", "Admin", "/admin – link to web dashboard"),
    ("kutsuviesti", "Send invite", "/sendinvite – create invite link"),
    ("taso", "Level", "/level – show level and XP"),
    ("kolikko", "Coinflip", "/coinflip – heads or tails"),
    ("8ball", "8-ball", "/8ball – magic 8-ball"),
    ("arvaa", "Guess", "/guess – guess number 1–10"),
    ("ruletti", "Roulette", "/roulette – Russian roulette"),
    ("twitch", "Twitch", "Stream notifications (add streamers in web)"),
    ("afk", "AFK", "/afk – set AFK status"),
    ("muistutus", "Reminder", "/reminder – set reminder"),
    ("komennot_lista", "Commands", "/commands – list all commands"),
    ("tervehdys", "Hello", "/hello – greet"),
    ("kutsu", "Invite", "/invite – bot invite link"),
    ("tiketti", "Ticket", "Ticket system + /ticket_panel"),
    ("tasonboard", "Leaderboard", "/leaderboard – level top 10"),
    ("noppa", "Dice", "/dice – roll dice (e.g. 1d6, 2d20)"),
    ("kps", "RPS", "/rps – rock paper scissors"),
    ("arpa", "Choose", "/choose – pick from options"),
    ("fivem", "FiveM", "/fivem – FiveM server status"),
    ("ehdotus", "Suggestion", "/suggestion – send suggestion"),
    ("arvonta", "Giveaway", "/giveaway – pick winners (mod)"),
    ("poll", "Poll", "/poll – create poll"),
]

MOD_FEATURES = [
    ("kick", "Kick", "Kick member"),
    ("ban", "Ban", "Ban member"),
    ("mute", "Mute", "Mute (timeout)"),
    ("unmute", "Unmute", "Remove mute"),
    ("warn", "Warning", "Warn/warnings/remove"),
    ("purge", "Clear", "/clear – delete messages"),
    ("slowmode", "Slowmode", "/slowmode – slow channel messaging"),
    ("say", "Say", "/say – send message as bot"),
]

LOG_FEATURES = [
    ("mod_actions", "Moderation actions", "Log kick/ban/mute/warn/clear/slowmode/say"),
    ("member_join", "Member join", "Log when member joins"),
    ("member_leave", "Member leave", "Log when member leaves"),
    ("message_delete", "Message delete", "Log message deletion"),
    ("message_edit", "Message edit", "Log message edit"),
    ("voice_state", "Voice channel", "Log join/leave voice channels"),
]


def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user" not in session:
            return redirect(url_for("index"))
        return f(*args, **kwargs)
    return decorated


def dev_portal_required(f):
    """Vain DEV_USER_IDS -listassa olevat Discord-käyttäjät."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user" not in session:
            return redirect(url_for("index"))
        user_id = str(session.get("user", {}).get("id", ""))
        if not DEV_USER_IDS or user_id not in DEV_USER_IDS:
            return "Pääsy evätty. Kehittäjäoikeus vaaditaan.", 403
        return f(*args, **kwargs)
    return decorated


def _load_announcements():
    """Lataa ilmoitukset announcements.json -tiedostosta. JSON-muoto: [{"date":"...","title":"...","text":"..."}]"""
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "announcements.json")
    try:
        if os.path.isfile(path):
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
                return data if isinstance(data, list) else []
    except (json.JSONDecodeError, OSError):
        pass
    return []


def get_user_guilds():
    token = session.get("access_token")
    if not token:
        return []
    try:
        r = requests.get(
            f"{DISCORD_API}/users/@me/guilds",
            headers={"Authorization": f"Bearer {token}", **_REQ_HEADERS},
            timeout=_REQ_TIMEOUT
        )
    except requests.RequestException:
        raise
    if r.status_code != 200:
        return []
    guilds = r.json()
    ADMIN = 0x8
    return [g for g in guilds if (int(g.get("permissions", 0) or 0) & ADMIN) == ADMIN]


def bot_in_guild(guild_id: str) -> bool:
    """Tarkistaa onko botti palvelimella. Käyttää shared_state.bot tai API-kutsua."""
    try:
        import shared_state
        bot = shared_state.get_bot()
        if bot:
            return any(str(g.id) == str(guild_id) for g in bot.guilds)
    except Exception:
        pass
    if not BOT_TOKEN:
        return False
    try:
        r = requests.get(
            f"{DISCORD_API}/guilds/{guild_id}",
            headers={"Authorization": f"Bot {BOT_TOKEN}", **_REQ_HEADERS},
            timeout=_REQ_TIMEOUT
        )
        return r.status_code == 200
    except requests.RequestException:
        return False


def get_bot_invite_url(guild_id: str) -> str:
    """Palauttaa OAuth2-kutsulinkin, jossa palvelin valittu etukäteen."""
    if not CLIENT_ID:
        return ""
    base = "https://discord.com/api/oauth2/authorize"
    params = f"client_id={CLIENT_ID}&permissions=8&scope=bot%20applications.commands&guild_id={guild_id}"
    return f"{base}?{params}"


def _get_cached(key: str, fetcher):
    """Palauttaa välimuistista tai hakee ja tallentaa. Erottaa vanhat jos yli max."""
    now = time.monotonic()
    with _cache_lock:
        entry = _discord_cache.get(key)
        if entry and (now - entry["ts"]) < _CACHE_TTL:
            return entry["data"]
    data = fetcher()
    with _cache_lock:
        _discord_cache[key] = {"data": data, "ts": now}
        if key in _cache_keys_order:
            _cache_keys_order.remove(key)
        _cache_keys_order.append(key)
        while len(_discord_cache) > _CACHE_MAX_SIZE and _cache_keys_order:
            old_key = _cache_keys_order.pop(0)
            _discord_cache.pop(old_key, None)
    return data


def _fetch_guild_channels_raw(guild_id: str) -> list:
    """Yksi API-kutsu kaikille kanaville."""
    if not BOT_TOKEN:
        return []
    try:
        r = requests.get(
            f"{DISCORD_API}/guilds/{guild_id}/channels",
            headers={"Authorization": f"Bot {BOT_TOKEN}", **_REQ_HEADERS},
            timeout=_REQ_TIMEOUT
        )
        if r.status_code != 200:
            return []
        return r.json()
    except requests.RequestException:
        return []


def get_guild_channels(guild_id: str) -> list:
    """Hakee palvelimen tekstikanavat (type 0). Yksi API-kutsu kanaville."""
    all_ch = _get_cached(f"channels:{guild_id}", lambda: _fetch_guild_channels_raw(guild_id))
    channels = [c for c in all_ch if c.get("type") == 0]
    return sorted(channels, key=lambda x: (x.get("position", 0), x["name"]))


def get_guild_voice_channels(guild_id: str) -> list:
    """Hakee palvelimen ääni-/stagekanavat (type 2). Käyttää samaa välimuistia."""
    all_ch = _get_cached(f"channels:{guild_id}", lambda: _fetch_guild_channels_raw(guild_id))
    channels = [c for c in all_ch if c.get("type") == 2]
    return sorted(channels, key=lambda x: (x.get("position", 0), x["name"]))


def get_guild_categories(guild_id: str) -> list:
    """Hakee palvelimen kategoriat (type 4). Käyttää samaa välimuistia."""
    all_ch = _get_cached(f"channels:{guild_id}", lambda: _fetch_guild_channels_raw(guild_id))
    cats = [c for c in all_ch if c.get("type") == 4]
    return sorted(cats, key=lambda x: (x.get("position", 0), x["name"]))

def _fetch_guild_roles_raw(guild_id: str) -> list:
    if not BOT_TOKEN:
        return []
    try:
        r = requests.get(
            f"{DISCORD_API}/guilds/{guild_id}",
            headers={"Authorization": f"Bot {BOT_TOKEN}", **_REQ_HEADERS},
            timeout=_REQ_TIMEOUT
        )
        if r.status_code != 200:
            return []
        roles = r.json().get("roles", [])
        return [ro for ro in roles if not ro.get("managed")]
    except requests.RequestException:
        return []


def get_guild_roles(guild_id: str) -> list:
    """Hakee roolit bot-tokenilla. Välimuistissa 90 s."""
    roles = _get_cached(f"roles:{guild_id}", lambda: _fetch_guild_roles_raw(guild_id))
    return sorted(roles, key=lambda x: x.get("position", 0), reverse=True)


@app.route("/")
def index():
    if "user" in session:
        return redirect(url_for("dashboard"))
    return render_template("index.html", base_url=BASE_URL)


@app.route("/invite")
def invite():
    """Ohjaa Discord OAuth2 -kutsulinkille, jotta botti voidaan kutsua palvelimelle."""
    if not CLIENT_ID:
        return "Kutsulinkkiä ei ole konfiguroitu (DISCORD_CLIENT_ID puuttuu).", 503
    url = (
        f"https://discord.com/api/oauth2/authorize"
        f"?client_id={CLIENT_ID}"
        f"&permissions=8"
        f"&scope=bot%20applications.commands"
    )
    return redirect(url)


@app.route("/login")
def login():
    state = secrets.token_urlsafe(32)
    session["oauth_state"] = state
    url = (
        f"https://discord.com/api/oauth2/authorize"
        f"?client_id={CLIENT_ID}"
        f"&redirect_uri={REDIRECT_URI}"
        f"&response_type=code"
        f"&scope=identify guilds"
        f"&state={state}"
    )
    return redirect(url)


@app.route("/callback")
def callback():
    if request.args.get("state") != session.get("oauth_state"):
        return "Virhe: Väärä tila", 400
    code = request.args.get("code")
    if not code:
        return "Virhe: Koodi puuttuu", 400
    data = {
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": REDIRECT_URI,
    }
    r = requests.post(f"{DISCORD_API}/oauth2/token", data=data, timeout=_REQ_TIMEOUT)
    if r.status_code != 200:
        return f"Virhe kirjautumisessa: {r.text}", 400
    token_data = r.json()
    session["access_token"] = token_data["access_token"]
    session["refresh_token"] = token_data.get("refresh_token")
    session.permanent = True
    r = requests.get(
        f"{DISCORD_API}/users/@me",
        headers={"Authorization": f"Bearer {token_data['access_token']}", **_REQ_HEADERS},
        timeout=_REQ_TIMEOUT
    )
    if r.status_code != 200:
        return "Virhe käyttäjätietojen haussa", 400
    session["user"] = r.json()
    return redirect(url_for("dashboard"))


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))


@app.route("/dashboard")
@login_required
def dashboard():
    try:
        guilds = get_user_guilds()
    except requests.RequestException:
        user_id = str(session.get("user", {}).get("id", ""))
        is_dev = bool(DEV_USER_IDS and user_id in DEV_USER_IDS)
        return render_template(
            "dashboard.html",
            guilds=[],
            user=session["user"],
            is_dev=is_dev,
            error="Discord API ei vastannut ajoissa. Tarkista verkkoyhteys ja yritä uudelleen."
        ), 503
    def _check_guild(g):
        try:
            return g["id"], bot_in_guild(g["id"]), None
        except requests.RequestException:
            return g["id"], False, None

    with ThreadPoolExecutor(max_workers=min(5, max(1, len(guilds)))) as ex:
        futures = {ex.submit(_check_guild, g): g for g in guilds}
        for future in as_completed(futures):
            gid, bot_in, _ = future.result()
            g = next(x for x in guilds if x["id"] == gid)
            g["bot_in"] = bot_in
            g["invite_url"] = get_bot_invite_url(gid) if not bot_in else None
    user_id = str(session.get("user", {}).get("id", ""))
    is_dev = bool(DEV_USER_IDS and user_id in DEV_USER_IDS)
    # Uudet ominaisuudet – lisää ilmoituksia tiedostoon announcements.json
    announcements = _load_announcements()
    return render_template("dashboard.html", guilds=guilds, user=session["user"], is_dev=is_dev, announcements=announcements)


# ---------- Kehittäjäportaali ----------

@app.route("/dev")
@login_required
@dev_portal_required
def dev_portal():
    return render_template("dev.html", user=session["user"])


@app.route("/api/dev/stats")
@login_required
@dev_portal_required
def api_dev_stats():
    try:
        import platform
        import shared_state
        bot = shared_state.get_bot()
        uptime = shared_state.get_uptime()

        data = {
            "bot_ready": bot is not None,
            "latency_ms": round(bot.latency * 1000) if bot and hasattr(bot, "latency") else None,
            "guild_count": len(bot.guilds) if bot else 0,
            "user_count": sum(g.member_count or 0 for g in (bot.guilds if bot else [])),
            "uptime_seconds": round(uptime) if uptime is not None else None,
            "python_version": platform.python_version(),
            "platform": platform.system(),
            "platform_release": platform.release(),
            "extensions": list(bot.extensions.keys()) if bot else [],
            "command_count": _count_commands(bot) if bot else 0,
            "guilds": [
                {"id": str(g.id), "name": g.name, "members": g.member_count or 0}
                for g in (sorted(bot.guilds, key=lambda x: (x.member_count or 0), reverse=True) if bot else [])
            ],
        }
        try:
            import discord
            data["discord_version"] = discord.__version__
        except Exception:
            data["discord_version"] = None
        try:
            import psutil
            proc = psutil.Process(os.getpid())
            data["memory_mb"] = round(proc.memory_info().rss / 1024 / 1024, 1)
            data["cpu_percent"] = round(proc.cpu_percent(interval=0.1), 1)
        except Exception:
            data["memory_mb"] = None
            data["cpu_percent"] = None
        # Latenssin historia (graafille)
        if data.get("latency_ms") is not None:
            shared_state.push_latency_sample(data["latency_ms"])
        data["latency_history"] = shared_state.get_latency_history()
        if bot and hasattr(bot, "user") and bot.user:
            data["bot_username"] = str(bot.user)
            data["bot_id"] = str(bot.user.id)
        else:
            data["bot_username"] = data["bot_id"] = None
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


def _count_commands(bot):
    """Laske ladatut slash-komennot ja context menut."""
    try:
        count = 0
        for cmd in bot.tree.get_commands():
            count += 1
            if hasattr(cmd, "commands") and cmd.commands:
                count += len(cmd.commands)
        return count
    except Exception:
        return 0


@app.route("/api/dev/console")
@login_required
@dev_portal_required
def api_dev_console():
    try:
        import shared_state
        limit = min(500, max(1, request.args.get("limit", 200, type=int)))
        lines = shared_state.get_console_lines(limit)
        return jsonify({"lines": lines})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/dev/console/clear", methods=["POST"])
@login_required
@dev_portal_required
def api_dev_console_clear():
    try:
        import shared_state
        shared_state.clear_console()
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/dev/bot-info")
@login_required
@dev_portal_required
def api_dev_bot_info():
    """Näyttää botin tiedot (kuvaus, kehittäjät, kutsu). Salattua tiedostoa ei lueta ilman salasanaa."""
    try:
        import bot_info
        from config import BOT_DESCRIPTION, BOT_DEVELOPERS, BOT_INVITE_LINK, BOT_APPLY_URL
        return jsonify({
            "description": BOT_DESCRIPTION,
            "developers": BOT_DEVELOPERS,
            "invite_link": BOT_INVITE_LINK,
            "apply_bot_url": BOT_APPLY_URL,
            "protected": bot_info.encrypted_file_exists(),
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/dev/bot-info/save", methods=["POST"])
@login_required
@dev_portal_required
def api_dev_bot_info_save():
    """Tallentaa botin tiedot. Vaatii muokkaussalasanan."""
    try:
        import bot_info
        data = request.get_json() or {}
        password = (data.get("password") or "").strip()
        if not password:
            return jsonify({"success": False, "error": "Salasana puuttuu."}), 400
        if password != BOT_INFO_EDIT_PASSWORD:
            return jsonify({"success": False, "error": "Väärä salasana."}), 403
        ok = bot_info.save({
            "description": (data.get("description") or "").strip(),
            "developers": [x.strip() for x in (data.get("developers") or "").split(",") if x.strip()],
            "invite_link": (data.get("invite_link") or "").strip(),
            "apply_bot_url": (data.get("apply_bot_url") or "").strip(),
        }, password)
        if not ok:
            return jsonify({"success": False, "error": "Tallennus epäonnistui."}), 500
        return jsonify({"success": True, "message": "Botin tiedot tallennettu. Käynnistä botti uudelleen, jotta status päivittyy."})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/dev/start", methods=["POST"])
@login_required
@dev_portal_required
def api_dev_start():
    import shared_state
    if shared_state.get_bot() is not None:
        return jsonify({"success": False, "error": "Botti on jo käynnissä."}), 400
    import run
    threading.Thread(target=run.run_bot, daemon=True).start()
    return jsonify({"success": True, "message": "Botti käynnistyy..."})


def _do_restart():
    os.execv(sys.executable, [sys.executable] + sys.argv)


def _shutdown_bot_only():
    """Sammuttaa vain botin: katkaisee Discord-yhteyden, botti menee offline-tilaan eikä reagoi enää mihinkään."""
    import asyncio
    import shared_state
    bot = shared_state.get_bot()
    if not bot:
        shared_state.set_bot(None)
        return
    if bot.loop.is_running():
        future = asyncio.run_coroutine_threadsafe(bot.close(), bot.loop)
        try:
            future.result(timeout=15)
        except Exception:
            pass
    shared_state.set_bot(None)


@app.route("/api/dev/shutdown", methods=["POST"])
@login_required
@dev_portal_required
def api_dev_shutdown():
    threading.Timer(0.5, _shutdown_bot_only).start()
    return jsonify({"success": True, "message": "Botti sammutetaan, web jää päälle."})


@app.route("/api/dev/restart", methods=["POST"])
@login_required
@dev_portal_required
def api_dev_restart():
    threading.Timer(1.5, _do_restart).start()
    return jsonify({"success": True, "message": "Botti käynnistetään uudelleen..."})


@app.route("/api/dev/errors")
@login_required
@dev_portal_required
def api_dev_errors():
    try:
        import shared_state
        limit = min(100, max(1, request.args.get("limit", 20, type=int)))
        return jsonify({"errors": shared_state.get_recent_errors(limit)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/dev/errors/clear", methods=["POST"])
@login_required
@dev_portal_required
def api_dev_errors_clear():
    try:
        import shared_state
        shared_state.clear_errors()
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/dev/db-stats")
@login_required
@dev_portal_required
def api_dev_db_stats():
    try:
        stats = database.get_db_stats()
        if stats is None:
            return jsonify({"error": "Tietokantaa ei saatavilla", "ok": False}), 500
        return jsonify({"ok": True, "stats": stats})
    except Exception as e:
        return jsonify({"error": str(e), "ok": False}), 500


@app.route("/api/dev/env-keys")
@login_required
@dev_portal_required
def api_dev_env_keys():
    """Listaa ympäristömuuttujien nimet (ei arvoja) – tietoturvasyistä."""
    try:
        keys = sorted([k for k in os.environ.keys() if not k.startswith("SECRET") and "PASSWORD" not in k.upper() and "TOKEN" not in k.upper()])
        return jsonify({"keys": keys})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/dev/dependencies")
@login_required
@dev_portal_required
def api_dev_dependencies():
    """Listaa asennettujen riippuvuuksien versiot."""
    try:
        deps = {}
        for name in ["discord", "flask", "requests", "cryptography", "psutil", "dotenv"]:
            try:
                if name == "dotenv":
                    import dotenv
                    deps["python-dotenv"] = getattr(dotenv, "__version__", "?")
                elif name == "discord":
                    import discord
                    deps["discord.py"] = discord.__version__
                else:
                    m = __import__(name)
                    deps[name] = getattr(m, "__version__", "?")
            except ImportError:
                deps[name] = None
        return jsonify(deps)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/dev/backup")
@login_required
@dev_portal_required
def api_dev_backup():
    """Palauttaa kaikki palvelinasetukset JSON-muodossa (varmuuskopio)."""
    try:
        data = database.get_all_guild_settings_for_backup()
        from flask import Response
        return Response(
            json.dumps(data, indent=2, ensure_ascii=False),
            mimetype="application/json",
            headers={"Content-Disposition": "attachment; filename=bot_backup.json"}
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/dev/api-docs")
@login_required
@dev_portal_required
def api_dev_api_docs():
    """Listaa kehittäjäportaalin API-endpointit."""
    docs = [
        {"method": "GET", "path": "/api/dev/stats", "desc": "Bottin tilastot ja järjestelmätiedot"},
        {"method": "GET", "path": "/api/dev/console", "desc": "Konsoliloki (param: limit)"},
        {"method": "POST", "path": "/api/dev/console/clear", "desc": "Tyhjennä konsoli"},
        {"method": "GET", "path": "/api/dev/bot-info", "desc": "Botin metadata (kuvaus, kehittäjät, kutsu)"},
        {"method": "POST", "path": "/api/dev/bot-info/save", "desc": "Tallenna botin tiedot (vaatii salasanan)"},
        {"method": "POST", "path": "/api/dev/start", "desc": "Käynnistä botti"},
        {"method": "POST", "path": "/api/dev/shutdown", "desc": "Sammuta vain botti"},
        {"method": "POST", "path": "/api/dev/restart", "desc": "Käynnistä koko sovellus uudelleen"},
        {"method": "POST", "path": "/api/dev/guild/<id>/leave", "desc": "Poista botti palvelimelta"},
        {"method": "GET", "path": "/api/dev/errors", "desc": "Viimeisimmät virheet (param: limit)"},
        {"method": "POST", "path": "/api/dev/errors/clear", "desc": "Tyhjennä virheloki"},
        {"method": "GET", "path": "/api/dev/db-stats", "desc": "Tietokannan tilastot"},
        {"method": "GET", "path": "/api/dev/env-keys", "desc": "Ympäristömuuttujien nimet (ei arvoja)"},
        {"method": "GET", "path": "/api/dev/dependencies", "desc": "Riippuvuuksien versiot"},
        {"method": "GET", "path": "/api/dev/backup", "desc": "Lataa asetusten varmuuskopio JSON"},
        {"method": "GET", "path": "/api/dev/api-docs", "desc": "Tämä dokumentaatio"},
    ]
    return jsonify(docs)


@app.route("/api/dev/guild/<int:guild_id>/leave", methods=["POST"])
@login_required
@dev_portal_required
def api_dev_guild_leave(guild_id):
    import asyncio
    import shared_state
    bot = shared_state.get_bot()
    if not bot:
        return jsonify({"success": False, "error": "Botti ei ole käynnissä."}), 400
    guild = bot.get_guild(guild_id)
    if not guild:
        return jsonify({"success": False, "error": "Palvelinta ei löydy."}), 404
    try:
        future = asyncio.run_coroutine_threadsafe(guild.leave(), bot.loop)
        future.result(timeout=10)
        return jsonify({"success": True, "message": f"Botti poistui palvelimelta {guild.name}."})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/guild/<guild_id>")
@login_required
def guild_settings(guild_id):
    guilds = get_user_guilds()
    guild = next((g for g in guilds if g["id"] == guild_id), None)
    if not guild:
        return "Sinulla ei ole ylläpito-oikeuksia tähän palvelimeen.", 403
    if not bot_in_guild(guild_id):
        invite_url = get_bot_invite_url(guild_id)
        return render_template(
            "guild_invite.html",
            guild=guild,
            invite_url=invite_url,
            user=session["user"]
        )
    settings = database.get_guild_settings(guild_id)
    features = []
    for key, label, desc in COMMAND_FEATURES:
        features.append({
            "key": key,
            "label": label,
            "description": desc,
            "enabled": settings.get(key, True)
        })
    channels = [{"id": c["id"], "name": c["name"]} for c in get_guild_channels(guild_id)]
    voice_channels = [{"id": c["id"], "name": c["name"]} for c in get_guild_voice_channels(guild_id)]
    categories = [{"id": c["id"], "name": c["name"]} for c in get_guild_categories(guild_id)]
    roles = [{"id": r["id"], "name": r["name"]} for r in get_guild_roles(guild_id)]
    mod_roles = settings.get("mod_roles", [])
    ticket_settings = database.get_ticket_settings(guild_id)
    ticket_staff_role = ticket_settings.get("staff_role_id")
    ticket_category = ticket_settings.get("category_id")
    ticket_channel = ticket_settings.get("channel_id")
    ticket_transcript_channel = ticket_settings.get("transcript_channel_id")
    ticket_topics = ticket_settings.get("ticket_topics") or []
    ticket_panel_title = ticket_settings.get("panel_title") or "Tukitiketti"
    ticket_panel_description = ticket_settings.get("panel_description") or "Valitse tiketin aihe alta."
    mod_features = [{
        "key": k,
        "label": l,
        "description": d,
        "enabled": settings.get(f"mod_{k}", True)
    } for k, l, d in MOD_FEATURES]
    log_features = [{
        "key": k,
        "label": l,
        "description": d,
        "enabled": settings.get(f"log_{k}", True)
    } for k, l, d in LOG_FEATURES]
    log_channel = settings.get("log_channel_id") or settings.get("mod_log_channel_id")
    welcome_enabled = settings.get("welcome_enabled", False)
    welcome_channel = settings.get("welcome_channel_id")
    level_enabled = settings.get("level_enabled", False)
    level_channel = settings.get("level_channel_id")
    level_xp_per = int(settings.get("level_xp_per_message", 15))
    level_cooldown = int(settings.get("level_xp_cooldown", 60))
    level_roles = settings.get("level_roles") or {}
    if not isinstance(level_roles, dict):
        level_roles = {}
    text_no = settings.get("text_no_xp_channel_ids") or []
    voice_no = settings.get("voice_no_xp_channel_ids") or []
    fivem_host = settings.get("fivem_host") or ""
    fivem_port = settings.get("fivem_port") or "30120"
    fivem_channel = settings.get("fivem_channel_id")
    twitch_streamers = settings.get("twitch_streamers") or []
    twitch_channel = settings.get("twitch_channel_id")
    # Autorole, goodbye, starboard
    autorole_enabled = bool(settings.get("autorole_enabled", False))
    autorole_roles = settings.get("autorole_role_ids") or []
    if not isinstance(autorole_roles, list):
        autorole_roles = []
    goodbye_enabled = bool(settings.get("goodbye_enabled", False))
    goodbye_channel = settings.get("goodbye_channel_id")
    starboard_channel = settings.get("starboard_channel_id")
    starboard_min_stars = int(settings.get("starboard_min_stars", 3))
    starboard_enabled = bool(settings.get("starboard_enabled", True))
    reaction_roles_enabled = bool(settings.get("reaction_roles_enabled", False))
    reaction_roles = settings.get("reaction_roles") or []
    # Server stats (tilastokanavat)
    server_stats_settings = database.get_server_stats_settings(guild_id)
    # Ehdotus, AFK, Arvonta, Muistutus
    suggestion_enabled = bool(settings.get("suggestion_enabled", False))
    suggestion_channel = settings.get("suggestion_channel_id")
    afk_enabled = bool(settings.get("afk_enabled", True))
    giveaway_enabled = bool(settings.get("giveaway_enabled", True))
    reminder_enabled = bool(settings.get("reminder_enabled", True))
    reminder_max = int(settings.get("reminder_max_per_user", 5))
    reminder_cooldown = int(settings.get("reminder_cooldown_sec", 60))
    welcome_message = settings.get("welcome_message") or "Tervetuloa {mention} palvelimelle! 👋"
    goodbye_message = settings.get("goodbye_message") or "**{user}** lähti palvelimelta. 👋"
    return render_template(
        "guild_settings.html",
        guild=guild,
        fivem_host=fivem_host,
        fivem_port=fivem_port,
        fivem_channel=fivem_channel,
        twitch_streamers=twitch_streamers,
        twitch_channel=twitch_channel,
        features=features,
        mod_features=mod_features,
        roles=roles,
        mod_roles=mod_roles,
        log_features=log_features,
        channels=channels,
        log_channel=log_channel,
        categories=categories,
        ticket_staff_role=ticket_staff_role,
        ticket_category=ticket_category,
        ticket_channel=ticket_channel,
        ticket_transcript_channel=ticket_transcript_channel,
        ticket_topics=ticket_topics,
        ticket_panel_title=ticket_panel_title,
        ticket_panel_description=ticket_panel_description,
        welcome_enabled=welcome_enabled,
        welcome_channel=welcome_channel,
        level_enabled=level_enabled,
        level_channel=level_channel,
        level_xp_per=level_xp_per,
        level_cooldown=level_cooldown,
        level_roles=level_roles,
        voice_channels=voice_channels,
        level_voice_xp=bool(settings.get("voice_xp_enabled", False)),
        level_voice_xp_per=int(settings.get("voice_xp_per_minute", 10)),
        text_no_xp=text_no if isinstance(text_no, list) else [],
        voice_no_xp=voice_no if isinstance(voice_no, list) else [],
        autorole_enabled=autorole_enabled,
        autorole_roles=autorole_roles,
        goodbye_enabled=goodbye_enabled,
        goodbye_channel=goodbye_channel,
        starboard_channel=starboard_channel,
        starboard_min_stars=starboard_min_stars,
        starboard_enabled=starboard_enabled,
        reaction_roles_enabled=reaction_roles_enabled,
        reaction_roles=reaction_roles,
        server_stats_settings=server_stats_settings,
        suggestion_enabled=suggestion_enabled,
        suggestion_channel=suggestion_channel,
        afk_enabled=afk_enabled,
        giveaway_enabled=giveaway_enabled,
        reminder_enabled=reminder_enabled,
        reminder_max=reminder_max,
        reminder_cooldown=reminder_cooldown,
        welcome_message=welcome_message,
        goodbye_message=goodbye_message,
        user=session["user"]
    )


@app.route("/api/guild/<guild_id>/feature/<feature>", methods=["POST"])
@login_required
def toggle_feature(guild_id, feature):
    guilds = get_user_guilds()
    if not any(g["id"] == guild_id for g in guilds):
        return jsonify({"error": "Ei oikeuksia"}), 403
    valid_keys = [f[0] for f in COMMAND_FEATURES]
    if feature not in valid_keys:
        return jsonify({"error": "Tuntematon ominaisuus"}), 400
    data = request.get_json() or {}
    enabled = bool(data.get("enabled", True))
    settings = database.update_feature(guild_id, feature, enabled)
    return jsonify({"success": True, "settings": settings})


@app.route("/api/guild/<guild_id>/fivem/settings", methods=["POST"])
@login_required
def api_set_fivem_settings(guild_id):
    guilds = get_user_guilds()
    if not any(g["id"] == guild_id for g in guilds):
        return jsonify({"error": "Ei oikeuksia"}), 403
    data = request.get_json() or {}
    host = (data.get("host") or "").strip()
    port = (data.get("port") or "30120").strip() or "30120"
    channel_id = data.get("channel_id") or None
    if channel_id is not None:
        channel_id = str(channel_id) if channel_id else None
    database.set_fivem_settings(guild_id, host=host, port=port, channel_id=channel_id)
    return jsonify({"success": True})


@app.route("/api/guild/<guild_id>/twitch/settings", methods=["POST"])
@login_required
def api_set_twitch_settings(guild_id):
    guilds = get_user_guilds()
    if not any(g["id"] == guild_id for g in guilds):
        return jsonify({"error": "Ei oikeuksia"}), 403
    data = request.get_json() or {}
    streamers = data.get("streamers", [])
    if isinstance(streamers, list):
        streamers = [str(s).strip().lower() for s in streamers if s and str(s).strip()]
    else:
        streamers = []
    raw = data.get("channel_id")
    channel_id = str(raw).strip() if raw else None
    database.set_twitch_settings(guild_id, streamers=streamers, channel_id=channel_id)
    return jsonify({"success": True})


@app.route("/api/guild/<guild_id>/mod/log-channel", methods=["POST"])
@login_required
def api_set_mod_log_channel(guild_id):
    guilds = get_user_guilds()
    if not any(g["id"] == guild_id for g in guilds):
        return jsonify({"error": "Ei oikeuksia"}), 403
    data = request.get_json() or {}
    channel_id = data.get("channel_id")
    database.set_log_channel(guild_id, str(channel_id) if channel_id else None)
    return jsonify({"success": True})

@app.route("/api/guild/<guild_id>/mod/roles", methods=["POST"])
@login_required
def api_set_mod_roles(guild_id):
    guilds = get_user_guilds()
    if not any(g["id"] == guild_id for g in guilds):
        return jsonify({"error": "Ei oikeuksia"}), 403
    data = request.get_json() or {}
    role_ids = data.get("role_ids", [])
    database.set_mod_roles(guild_id, role_ids if isinstance(role_ids, list) else [])
    return jsonify({"success": True})


@app.route("/api/guild/<guild_id>/mod/feature/<action>", methods=["POST"])
@login_required
def api_toggle_mod_feature(guild_id, action):
    guilds = get_user_guilds()
    if not any(g["id"] == guild_id for g in guilds):
        return jsonify({"error": "Ei oikeuksia"}), 403
    valid = [x[0] for x in MOD_FEATURES]
    if action not in valid:
        return jsonify({"error": "Tuntematon ominaisuus"}), 400
    data = request.get_json() or {}
    enabled = bool(data.get("enabled", True))
    database.set_mod_action_enabled(guild_id, action, enabled)
    return jsonify({"success": True})


@app.route("/api/guild/<guild_id>/logs/feature/<log_key>", methods=["POST"])
@login_required
def api_toggle_log_feature(guild_id, log_key):
    guilds = get_user_guilds()
    if not any(g["id"] == guild_id for g in guilds):
        return jsonify({"error": "Ei oikeuksia"}), 403
    valid = [x[0] for x in LOG_FEATURES]
    if log_key not in valid:
        return jsonify({"error": "Tuntematon ominaisuus"}), 400
    data = request.get_json() or {}
    enabled = bool(data.get("enabled", True))
    database.set_log_enabled(guild_id, log_key, enabled)
    return jsonify({"success": True})


@app.route("/api/guild/<guild_id>/welcome/settings", methods=["POST"])
@login_required
def api_set_welcome_settings(guild_id):
    guilds = get_user_guilds()
    if not any(g["id"] == guild_id for g in guilds):
        return jsonify({"error": "Ei oikeuksia"}), 403
    data = request.get_json() or {}
    enabled = bool(data["enabled"]) if "enabled" in data else None
    channel_id = None
    if "channel_id" in data:
        ch = data["channel_id"]
        channel_id = str(ch) if ch else ""
    message = data.get("message") if "message" in data else None
    database.set_welcome_settings(guild_id, enabled=enabled, channel_id=channel_id, message=message)
    return jsonify({"success": True})


@app.route("/api/guild/<guild_id>/level/settings", methods=["POST"])
@login_required
def api_set_level_settings(guild_id):
    guilds = get_user_guilds()
    if not any(g["id"] == guild_id for g in guilds):
        return jsonify({"error": "Ei oikeuksia"}), 403
    data = request.get_json() or {}
    enabled = bool(data["enabled"]) if "enabled" in data else None
    channel_id = None
    if "channel_id" in data:
        ch = data["channel_id"]
        channel_id = str(ch) if ch else ""
    xp_per = data.get("xp_per_message") if "xp_per_message" in data else None
    cooldown = data.get("xp_cooldown") if "xp_cooldown" in data else None
    voice_enabled = data.get("voice_xp_enabled") if "voice_xp_enabled" in data else None
    voice_xp_per = data.get("voice_xp_per_minute") if "voice_xp_per_minute" in data else None
    text_no = data.get("text_no_xp_channel_ids") if "text_no_xp_channel_ids" in data else None
    voice_no = data.get("voice_no_xp_channel_ids") if "voice_no_xp_channel_ids" in data else None
    database.set_level_settings(guild_id, enabled=enabled, channel_id=channel_id,
                                xp_per_message=xp_per, xp_cooldown=cooldown,
                                voice_xp_enabled=voice_enabled, voice_xp_per_minute=voice_xp_per,
                                text_no_xp_channel_ids=text_no, voice_no_xp_channel_ids=voice_no)
    return jsonify({"success": True})


@app.route("/api/guild/<guild_id>/level/roles", methods=["POST"])
@login_required
def api_set_level_roles(guild_id):
    guilds = get_user_guilds()
    if not any(g["id"] == guild_id for g in guilds):
        return jsonify({"error": "Ei oikeuksia"}), 403
    data = request.get_json() or {}
    level_roles = data.get("level_roles") or {}
    if isinstance(level_roles, dict):
        level_roles = {str(k): str(v) for k, v in level_roles.items() if k and v}
    database.set_level_settings(guild_id, level_roles=level_roles)
    return jsonify({"success": True})


@app.route("/api/guild/<guild_id>/level/auto-create-roles", methods=["POST"])
@login_required
def api_auto_create_level_roles(guild_id):
    guilds = get_user_guilds()
    if not any(g["id"] == guild_id for g in guilds):
        return jsonify({"error": "Ei oikeuksia"}), 403
    if not BOT_TOKEN:
        return jsonify({"error": "Botti ei konfiguroitu"}), 500
    data = request.get_json() or {}
    levels = data.get("levels") or []
    if not isinstance(levels, list):
        levels = [int(x) for x in str(levels).replace(",", " ").split() if str(x).isdigit()]
    else:
        levels = [int(x) for x in levels if str(x).replace("-", "").isdigit()]
    levels = sorted(set(max(1, min(100, l)) for l in levels))[:20]
    if not levels:
        return jsonify({"error": "Anna tasot (esim. 5, 10, 15, 20)"}), 400
    created = {}
    for lvl in levels:
        r = requests.post(
            f"{DISCORD_API}/guilds/{guild_id}/roles",
            headers={"Authorization": f"Bot {BOT_TOKEN}", "Content-Type": "application/json", **_REQ_HEADERS},
            json={"name": f"Taso {lvl}", "color": 0x5865F2},
            timeout=_REQ_TIMEOUT
        )
        if r.status_code == 200:
            role = r.json()
            created[str(lvl)] = str(role["id"])
        else:
            break
    if created:
        s = database.get_guild_settings(guild_id)
        level_roles = s.get("level_roles") or {}
        level_roles.update(created)
        database.set_level_settings(guild_id, level_roles=level_roles)
    return jsonify({"success": True, "created": created})


@app.route("/api/guild/<guild_id>/autorole/settings", methods=["POST"])
@login_required
def api_set_autorole_settings(guild_id):
    guilds = get_user_guilds()
    if not any(g["id"] == guild_id for g in guilds):
        return jsonify({"error": "Ei oikeuksia"}), 403
    data = request.get_json() or {}
    enabled = bool(data["enabled"]) if "enabled" in data else None
    role_ids = data.get("role_ids")
    if role_ids is not None and not isinstance(role_ids, list):
        role_ids = []
    database.set_autorole_settings(guild_id, enabled=enabled, role_ids=role_ids)
    return jsonify({"success": True})


@app.route("/api/guild/<guild_id>/goodbye/settings", methods=["POST"])
@login_required
def api_set_goodbye_settings(guild_id):
    guilds = get_user_guilds()
    if not any(g["id"] == guild_id for g in guilds):
        return jsonify({"error": "Ei oikeuksia"}), 403
    data = request.get_json() or {}
    enabled = bool(data["enabled"]) if "enabled" in data else None
    channel_id = data.get("channel_id")
    if channel_id is not None:
        channel_id = str(channel_id) if channel_id else None
    message = data.get("message") if "message" in data else None
    database.set_goodbye_settings(guild_id, enabled=enabled, channel_id=channel_id, message=message)
    return jsonify({"success": True})


@app.route("/api/guild/<guild_id>/suggestion/settings", methods=["POST"])
@login_required
def api_set_suggestion_settings(guild_id):
    guilds = get_user_guilds()
    if not any(g["id"] == guild_id for g in guilds):
        return jsonify({"error": "Ei oikeuksia"}), 403
    data = request.get_json() or {}
    enabled = bool(data["enabled"]) if "enabled" in data else None
    channel_id = data.get("channel_id")
    channel_id = str(channel_id) if channel_id else None
    database.set_suggestion_settings(guild_id, enabled=enabled, channel_id=channel_id)
    return jsonify({"success": True})


@app.route("/api/guild/<guild_id>/afk/settings", methods=["POST"])
@login_required
def api_set_afk_settings(guild_id):
    guilds = get_user_guilds()
    if not any(g["id"] == guild_id for g in guilds):
        return jsonify({"error": "Ei oikeuksia"}), 403
    data = request.get_json() or {}
    enabled = bool(data["enabled"]) if "enabled" in data else None
    database.set_afk_settings(guild_id, enabled=enabled)
    return jsonify({"success": True})


@app.route("/api/guild/<guild_id>/giveaway/settings", methods=["POST"])
@login_required
def api_set_giveaway_settings(guild_id):
    guilds = get_user_guilds()
    if not any(g["id"] == guild_id for g in guilds):
        return jsonify({"error": "Ei oikeuksia"}), 403
    data = request.get_json() or {}
    enabled = bool(data["enabled"]) if "enabled" in data else None
    database.set_giveaway_settings(guild_id, enabled=enabled)
    return jsonify({"success": True})


@app.route("/api/guild/<guild_id>/reminder/settings", methods=["POST"])
@login_required
def api_set_reminder_settings(guild_id):
    guilds = get_user_guilds()
    if not any(g["id"] == guild_id for g in guilds):
        return jsonify({"error": "Ei oikeuksia"}), 403
    data = request.get_json() or {}
    enabled = bool(data["enabled"]) if "enabled" in data else None
    max_per = data.get("max_per_user")
    cooldown = data.get("cooldown_sec")
    database.set_reminder_settings(guild_id, enabled=enabled, max_per_user=max_per, cooldown_sec=cooldown)
    return jsonify({"success": True})


@app.route("/api/guild/<guild_id>/starboard/settings", methods=["POST"])
@login_required
def api_set_starboard_settings(guild_id):
    guilds = get_user_guilds()
    if not any(g["id"] == guild_id for g in guilds):
        return jsonify({"error": "Ei oikeuksia"}), 403
    data = request.get_json() or {}
    enabled = data.get("enabled") if "enabled" in data else None
    channel_id = data.get("channel_id")
    if channel_id is not None:
        channel_id = str(channel_id) if channel_id else None
    min_stars = data.get("min_stars")
    database.set_starboard_settings(guild_id, enabled=enabled, channel_id=channel_id, min_stars=min_stars)
    return jsonify({"success": True})


@app.route("/api/guild/<guild_id>/server-stats/settings", methods=["POST"])
@login_required
def api_set_server_stats_settings(guild_id):
    import asyncio
    guilds = get_user_guilds()
    if not any(g["id"] == guild_id for g in guilds):
        return jsonify({"error": "Ei oikeuksia"}), 403
    data = request.get_json() or {}
    enabled = data.get("enabled")
    category_name = data.get("category_name")
    stats = data.get("stats")
    labels = data.get("labels")
    if enabled is not None:
        database.set_server_stats_settings(guild_id, enabled=bool(enabled))
    if category_name is not None:
        database.set_server_stats_settings(guild_id, category_name=str(category_name).strip()[:100] or "SERVER STATS")
    if stats is not None and isinstance(stats, list):
        valid = ("members", "humans", "online", "offline")
        stats = [s for s in stats if str(s) in valid]
        if stats:
            database.set_server_stats_settings(guild_id, stats=stats)
    if labels is not None and isinstance(labels, dict):
        database.set_server_stats_settings(guild_id, labels=labels)
    # Luo/päivitä kanavat heti Tallenna-nappia painettaessa
    try:
        import shared_state
        from events import server_stats
        bot = shared_state.get_bot()
        if bot and bot.loop.is_running():
            future = asyncio.run_coroutine_threadsafe(
                server_stats.update_guild_server_stats_now(bot, int(guild_id)),
                bot.loop
            )
            future.result(timeout=15)
    except Exception:
        pass
    return jsonify({"success": True})


@app.route("/api/guild/<guild_id>/reaction-roles/settings", methods=["POST"])
@login_required
def api_set_reaction_roles_settings(guild_id):
    guilds = get_user_guilds()
    if not any(g["id"] == guild_id for g in guilds):
        return jsonify({"error": "Ei oikeuksia"}), 403
    data = request.get_json() or {}
    enabled = data.get("enabled") if "enabled" in data else None
    roles = data.get("roles", [])
    if isinstance(roles, list):
        roles = [
            {
                "message_id": str(r.get("message_id", "")).strip(),
                "channel_id": str(r.get("channel_id", "")).strip(),
                "emoji": str(r.get("emoji", ""))[:50],
                "role_id": str(r.get("role_id", "")).strip(),
            }
            for r in roles
            if r.get("message_id") and r.get("role_id")
        ]
    database.set_reaction_roles_settings(guild_id, enabled=enabled, roles=roles)
    return jsonify({"success": True})


@app.route("/api/guild/<guild_id>/ticket/settings", methods=["POST"])
@login_required
def api_set_ticket_settings(guild_id):
    guilds = get_user_guilds()
    if not any(g["id"] == guild_id for g in guilds):
        return jsonify({"error": "Ei oikeuksia"}), 403
    data = request.get_json() or {}
    staff_role = data.get("staff_role_id") or ""
    category = data.get("category_id") or ""
    channel = data.get("channel_id") or ""
    transcript_channel = data.get("transcript_channel_id") or ""
    database.set_ticket_settings(guild_id, staff_role_id=staff_role, category_id=category, channel_id=channel, transcript_channel_id=transcript_channel)
    return jsonify({"success": True})


@app.route("/api/guild/<guild_id>/ticket/topics", methods=["POST"])
@login_required
def api_set_ticket_topics(guild_id):
    guilds = get_user_guilds()
    if not any(g["id"] == guild_id for g in guilds):
        return jsonify({"error": "Ei oikeuksia"}), 403
    data = request.get_json() or {}
    topics_raw = data.get("topics", [])
    if not isinstance(topics_raw, list):
        topics_raw = []
    topics = []
    for t in topics_raw:
        if not isinstance(t, dict) or not t.get("label"):
            continue
        role_ids = t.get("role_ids")
        if isinstance(role_ids, list):
            role_ids = [str(r).strip() for r in role_ids if r]
        else:
            rid = t.get("role_id")
            role_ids = [str(rid).strip()] if rid else []
        topics.append({"label": str(t.get("label", ""))[:100], "description": str(t.get("description", ""))[:100], "emoji": str(t.get("emoji", ""))[:10], "role_ids": role_ids})
    panel_title = data.get("panel_title")
    panel_description = data.get("panel_description")
    database.set_ticket_topics(guild_id, topics=topics, panel_title=panel_title, panel_description=panel_description)
    return jsonify({"success": True})


@app.after_request
def add_cache_headers(response):
    """Staattisten tiedostojen välimuisti selaimessa – nopeampi uudelleenlataus."""
    if request.path.startswith("/static/"):
        response.cache_control.max_age = 86400
        response.cache_control.public = True
    return response


def create_app():
    return app

# Tekijänoikeudet S44Gaming kaikki oikeudet pidätetään. https://discord.gg/ujB4JHfgcg
