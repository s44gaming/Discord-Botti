import os
import sys
import secrets
import threading
import requests
from flask import Flask, redirect, url_for, session, request, jsonify, render_template
from functools import wraps
import database
from config import DEV_USER_IDS, BOT_INFO_EDIT_PASSWORD

_REQ_TIMEOUT = 10
_REQ_HEADERS = {"User-Agent": "DiscordBot (Web Dashboard)"}

app = Flask(__name__, template_folder="web/templates", static_folder="web/static")
app.secret_key = os.getenv("FLASK_SECRET_KEY", secrets.token_hex(32))
app.config["PERMANENT_SESSION_LIFETIME"] = 86400

DISCORD_API = "https://discord.com/api/v10"
CLIENT_ID = os.getenv("DISCORD_CLIENT_ID")
CLIENT_SECRET = os.getenv("DISCORD_CLIENT_SECRET")
REDIRECT_URI = os.getenv("DISCORD_REDIRECT_URI", "http://localhost:5000/callback")
BASE_URL = os.getenv("BASE_URL", "http://localhost:5000")
BOT_TOKEN = os.getenv("DISCORD_TOKEN")

# Komennot – kukin voi kytkeä päälle/pois webissä
COMMAND_FEATURES = [
    ("ping", "Ping", "/ping – vastausajan tarkistus"),
    ("komennot_lista", "Komennot", "/komennot – näytä kaikki komennot (päivittyy automaattisesti)"),
    ("info", "Info", "/info – palvelimen tiedot"),
    ("tervehdys", "Tervehdys", "/tervehdys – tervehdys"),
    ("hallinta", "Hallinta", "/hallinta – linkki web-hallintaan"),
    ("kutsu", "Kutsu", "/kutsu – linkki lisätä botti palvelimelle (Apply bot)"),
    ("kutsuviesti", "Kutsuviesti", "/lähetäkutsu – lähettää yhteisön kutsulinkin kanavalle"),
    ("tiketti", "Tiketti", "Tikettijärjestelmä ja /tiketti_paneeli"),
    ("taso", "Taso", "/taso – näytä taso ja XP"),
    ("tasonboard", "Tasonboard", "/tasonboard – tasoTOP-10"),
    ("kolikko", "Kolikko", "/kolikko – heitä kolikkoa (kruuna/klaava)"),
    ("noppa", "Noppa", "/noppa – heitä noppaa (esim. 1d6, 2d20)"),
    ("8ball", "8-pallo", "/8ball – maaginen 8-pallo"),
    ("kps", "Kivi-paperi-sakset", "/kps – pelaa bottia vastaan"),
    ("arvaa", "Arvaa luku", "/arvaa_luku – arvaa luku 1–10"),
    ("arpa", "Arpa", "/arpa – arpa valitsee vaihtoehdoista"),
    ("ruletti", "Ruletti", "/ruletti – venäläinen ruletti (1/6)"),
    ("fivem", "FiveM", "/fivem – FiveM-palvelimen tila (asetukset webistä)"),
]

MOD_FEATURES = [
    ("kick", "Kick", "Potkaise jäsen"),
    ("ban", "Ban", "Estä jäsen"),
    ("mute", "Mute", "Mykistä (timeout)"),
    ("unmute", "Unmute", "Poista mykistys"),
    ("warn", "Varoitus", "Varoitus/varoitukset/poisto"),
    ("purge", "Clear", "/clear – poista viestejä"),
]

LOG_FEATURES = [
    ("mod_actions", "Moderaatiotoiminnot", "Kick/ban/mute/warn/clear -lokit"),
    ("member_join", "Jäsen liittyy", "Lokita kun jäsen liittyy"),
    ("member_leave", "Jäsen poistuu", "Lokita kun jäsen poistuu"),
    ("message_delete", "Viestin poisto", "Lokita viestin poisto"),
    ("message_edit", "Viestin muokkaus", "Lokita viestin muokkaus"),
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


def get_user_guilds():
    token = session.get("access_token")
    if not token:
        return []
    r = requests.get(
        f"{DISCORD_API}/users/@me/guilds",
        headers={"Authorization": f"Bearer {token}", **_REQ_HEADERS},
        timeout=_REQ_TIMEOUT
    )
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
    r = requests.get(
        f"{DISCORD_API}/guilds/{guild_id}",
        headers={"Authorization": f"Bot {BOT_TOKEN}", **_REQ_HEADERS},
        timeout=_REQ_TIMEOUT
    )
    return r.status_code == 200


def get_bot_invite_url(guild_id: str) -> str:
    """Palauttaa OAuth2-kutsulinkin, jossa palvelin valittu etukäteen."""
    if not CLIENT_ID:
        return ""
    base = "https://discord.com/api/oauth2/authorize"
    params = f"client_id={CLIENT_ID}&permissions=8&scope=bot%20applications.commands&guild_id={guild_id}"
    return f"{base}?{params}"


def get_guild_channels(guild_id: str) -> list:
    """Hakee palvelimen tekstikanavat bot-tokenilla. Bottin pitää olla palvelimella."""
    if not BOT_TOKEN:
        return []
    r = requests.get(
        f"{DISCORD_API}/guilds/{guild_id}/channels",
        headers={"Authorization": f"Bot {BOT_TOKEN}", **_REQ_HEADERS},
        timeout=_REQ_TIMEOUT
    )
    if r.status_code != 200:
        return []
    channels = [c for c in r.json() if c.get("type") == 0]
    return sorted(channels, key=lambda x: (x.get("position", 0), x["name"]))


def get_guild_voice_channels(guild_id: str) -> list:
    """Hakee palvelimen ääni-/stagekanavat (type 2)."""
    if not BOT_TOKEN:
        return []
    r = requests.get(
        f"{DISCORD_API}/guilds/{guild_id}/channels",
        headers={"Authorization": f"Bot {BOT_TOKEN}", **_REQ_HEADERS},
        timeout=_REQ_TIMEOUT
    )
    if r.status_code != 200:
        return []
    channels = [c for c in r.json() if c.get("type") == 2]
    return sorted(channels, key=lambda x: (x.get("position", 0), x["name"]))


def get_guild_categories(guild_id: str) -> list:
    """Hakee palvelimen kategoriat (type 4)."""
    if not BOT_TOKEN:
        return []
    r = requests.get(
        f"{DISCORD_API}/guilds/{guild_id}/channels",
        headers={"Authorization": f"Bot {BOT_TOKEN}", **_REQ_HEADERS},
        timeout=_REQ_TIMEOUT
    )
    if r.status_code != 200:
        return []
    cats = [c for c in r.json() if c.get("type") == 4]
    return sorted(cats, key=lambda x: (x.get("position", 0), x["name"]))

def get_guild_roles(guild_id: str) -> list:
    """Hakee roolit bot-tokenilla. Bottin pitää olla palvelimella."""
    if not BOT_TOKEN:
        return []
    r = requests.get(
        f"{DISCORD_API}/guilds/{guild_id}",
        headers={"Authorization": f"Bot {BOT_TOKEN}", **_REQ_HEADERS},
        timeout=_REQ_TIMEOUT
    )
    if r.status_code != 200:
        return []
    roles = r.json().get("roles", [])
    # poista managed-roolit (bot roolit)
    roles = [ro for ro in roles if not ro.get("managed")]
    return sorted(roles, key=lambda x: x.get("position", 0), reverse=True)


@app.route("/")
def index():
    if "user" in session:
        return redirect(url_for("dashboard"))
    return render_template("index.html", base_url=BASE_URL)


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
    guilds = get_user_guilds()
    for g in guilds:
        g["bot_in"] = bot_in_guild(g["id"])
        g["invite_url"] = get_bot_invite_url(g["id"]) if not g["bot_in"] else None
    user_id = str(session.get("user", {}).get("id", ""))
    is_dev = bool(DEV_USER_IDS and user_id in DEV_USER_IDS)
    return render_template("dashboard.html", guilds=guilds, user=session["user"], is_dev=is_dev)


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
        except Exception:
            data["memory_mb"] = None
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
    ticket_staff_role = settings.get("ticket_staff_role_id")
    ticket_category = settings.get("ticket_category_id")
    ticket_channel = settings.get("ticket_channel_id")
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
    return render_template(
        "guild_settings.html",
        guild=guild,
        fivem_host=fivem_host,
        fivem_port=fivem_port,
        fivem_channel=fivem_channel,
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
        channel_id = str(ch) if ch else ""  # "" = tyhjennä kanava
    database.set_welcome_settings(guild_id, enabled=enabled, channel_id=channel_id)
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
    database.set_ticket_settings(guild_id, staff_role_id=staff_role, category_id=category, channel_id=channel)
    return jsonify({"success": True})


def create_app():
    return app

# Tekijänoikeudet S44Gaming kaikki oikeudet pidätetään. https://discord.gg/ujB4JHfgcg
