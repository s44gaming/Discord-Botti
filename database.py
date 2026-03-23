import math
import sqlite3
import json
import os
from contextlib import contextmanager

DB_PATH = os.path.join(os.path.dirname(__file__), "data", "bot.db")
_TIMEOUT = 5.0  # sekunteja, estää lukitukset


@contextmanager
def _get_conn():
    """Yhteyden konteksti: varmistaa sulkemisen ja tukee Flask-säikeitä."""
    conn = sqlite3.connect(DB_PATH, timeout=_TIMEOUT)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.execute("PRAGMA cache_size=-64000")
        conn.execute("PRAGMA temp_store=MEMORY")
        conn.execute("PRAGMA busy_timeout=10000")  # 10s odotus lukitukselle
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

DEFAULT_MOD_FEATURES = {
    "kick": True,
    "ban": True,
    "mute": True,
    "unmute": True,
    "warn": True,
    "purge": True,
    "slowmode": True,
    "say": True,
}

DEFAULT_LOG_FEATURES = {
    "mod_actions": True,
    "member_join": True,
    "member_leave": True,
    "message_delete": True,
    "message_edit": True,
    "voice_state": True,
}


def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    with _get_conn() as conn:
        c = conn.cursor()
        c.execute("""
            CREATE TABLE IF NOT EXISTS guild_settings (
                guild_id TEXT PRIMARY KEY,
                features TEXT DEFAULT '{}',
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                username TEXT,
                discriminator TEXT,
                avatar TEXT,
                access_token TEXT,
                refresh_token TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS warns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                mod_id TEXT NOT NULL,
                reason TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS user_xp (
                guild_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                xp INTEGER DEFAULT 0,
                PRIMARY KEY (guild_id, user_id)
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS afk_users (
                guild_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                reason TEXT,
                set_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (guild_id, user_id)
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS reminders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                channel_id TEXT NOT NULL,
                message TEXT,
                fire_at REAL NOT NULL
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS tempvoice_channels (
                guild_id TEXT NOT NULL,
                channel_id TEXT PRIMARY KEY,
                owner_id TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)


def add_tempvoice_channel(guild_id: str, channel_id: str, owner_id: str) -> None:
    with _get_conn() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO tempvoice_channels (guild_id, channel_id, owner_id, created_at) VALUES (?, ?, ?, datetime('now'))",
            (str(guild_id), str(channel_id), str(owner_id))
        )


def remove_tempvoice_channel(channel_id: str) -> None:
    with _get_conn() as conn:
        conn.execute("DELETE FROM tempvoice_channels WHERE channel_id = ?", (str(channel_id),))


def is_tempvoice_channel(channel_id: str) -> bool:
    with _get_conn() as conn:
        row = conn.execute(
            "SELECT 1 FROM tempvoice_channels WHERE channel_id = ?",
            (str(channel_id),)
        ).fetchone()
    return bool(row)


def get_tempvoice_owner(channel_id: str) -> str | None:
    with _get_conn() as conn:
        row = conn.execute(
            "SELECT owner_id FROM tempvoice_channels WHERE channel_id = ?",
            (str(channel_id),)
        ).fetchone()
    return str(row[0]) if row and row[0] else None


def get_guild_settings(guild_id: str) -> dict:
    with _get_conn() as conn:
        c = conn.cursor()
        c.execute("SELECT features FROM guild_settings WHERE guild_id = ?", (str(guild_id),))
        row = c.fetchone()
    if row:
        return json.loads(row[0])
    return {}


def set_guild_settings(guild_id: str, features: dict) -> None:
    with _get_conn() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO guild_settings (guild_id, features, updated_at) VALUES (?, ?, datetime('now'))",
            (str(guild_id), json.dumps(features))
        )


def update_feature(guild_id: str, feature: str, enabled: bool) -> dict:
    settings = get_guild_settings(guild_id)
    settings[feature] = enabled
    set_guild_settings(guild_id, settings)
    return settings


def is_feature_enabled(guild_id: str, feature: str) -> bool:
    settings = get_guild_settings(guild_id)
    return settings.get(feature, True)


def get_log_channel(guild_id: str) -> str | None:
    """Palauttaa logikanavan ID:n tai None (takautuvasti mod_log_channel_id)."""
    settings = get_guild_settings(guild_id)
    ch = settings.get("log_channel_id") or settings.get("mod_log_channel_id")
    return str(ch) if ch else None


def set_log_channel(guild_id: str, channel_id: str | None) -> None:
    """Asettaa logikanavan. channel_id=None poistaa valinnan."""
    settings = get_guild_settings(guild_id)
    if channel_id:
        settings["log_channel_id"] = str(channel_id)
    else:
        settings.pop("log_channel_id", None)
    set_guild_settings(guild_id, settings)


def get_mod_roles(guild_id: str) -> list[str]:
    settings = get_guild_settings(guild_id)
    roles = settings.get("mod_roles", [])
    if not isinstance(roles, list):
        return []
    return [str(r) for r in roles]


def set_mod_roles(guild_id: str, role_ids: list) -> None:
    settings = get_guild_settings(guild_id)
    if not isinstance(role_ids, list):
        role_ids = []
    settings["mod_roles"] = [str(r) for r in role_ids]
    set_guild_settings(guild_id, settings)


def is_mod_action_enabled(guild_id: str, action: str) -> bool:
    settings = get_guild_settings(guild_id)
    return bool(settings.get(f"mod_{action}", DEFAULT_MOD_FEATURES.get(action, True)))


def set_mod_action_enabled(guild_id: str, action: str, enabled: bool) -> None:
    settings = get_guild_settings(guild_id)
    settings[f"mod_{action}"] = bool(enabled)
    set_guild_settings(guild_id, settings)


def is_log_enabled(guild_id: str, log_key: str) -> bool:
    settings = get_guild_settings(guild_id)
    return bool(settings.get(f"log_{log_key}", DEFAULT_LOG_FEATURES.get(log_key, True)))


def set_log_enabled(guild_id: str, log_key: str, enabled: bool) -> None:
    settings = get_guild_settings(guild_id)
    settings[f"log_{log_key}"] = bool(enabled)
    set_guild_settings(guild_id, settings)


def get_fivem_settings(guild_id: str) -> dict:
    """Palauttaa FiveM-asetukset: host, port, channel_id (status kanavalle)."""
    settings = get_guild_settings(guild_id)
    return {
        "host": (settings.get("fivem_host") or "").strip(),
        "port": str(settings.get("fivem_port") or "30120").strip() or "30120",
        "channel_id": settings.get("fivem_channel_id") or None,
    }


def set_fivem_settings(guild_id: str, host: str | None = None, port: str | None = None, channel_id: str | None = None) -> None:
    s = get_guild_settings(guild_id)
    if host is not None:
        s["fivem_host"] = str(host).strip() if host else ""
    if port is not None:
        s["fivem_port"] = str(port).strip() if port else "30120"
    if channel_id is not None:
        s["fivem_channel_id"] = str(channel_id) if channel_id else None
    set_guild_settings(guild_id, s)


def get_twitch_settings(guild_id: str) -> dict:
    """Palauttaa Twitch-asetukset: streamers (lista käyttäjänimistä), channel_id."""
    settings = get_guild_settings(guild_id)
    streamers = settings.get("twitch_streamers") or []
    if not isinstance(streamers, list):
        streamers = []
    return {
        "streamers": [str(s).strip().lower() for s in streamers if s and str(s).strip()],
        "channel_id": settings.get("twitch_channel_id") or None,
    }


def set_twitch_settings(guild_id: str, streamers: list | None = None, channel_id: str | None = None) -> None:
    s = get_guild_settings(guild_id)
    if streamers is not None:
        s["twitch_streamers"] = [str(x).strip().lower() for x in streamers if x and str(x).strip()]
    s["twitch_channel_id"] = str(channel_id).strip() if channel_id else None
    set_guild_settings(guild_id, s)


def add_warn(guild_id: str, user_id: str, mod_id: str, reason: str = "") -> int:
    with _get_conn() as conn:
        c = conn.execute(
            "INSERT INTO warns (guild_id, user_id, mod_id, reason) VALUES (?, ?, ?, ?)",
            (str(guild_id), str(user_id), str(mod_id), (reason or "Ei syytä")),
        )
        return int(c.lastrowid or 0)


def get_user_warns(guild_id: str, user_id: str) -> list[dict]:
    with _get_conn() as conn:
        rows = conn.execute(
            "SELECT id, mod_id, reason, created_at FROM warns WHERE guild_id = ? AND user_id = ? ORDER BY created_at DESC",
            (str(guild_id), str(user_id)),
        ).fetchall()
    return [{"id": r[0], "mod_id": r[1], "reason": r[2], "created_at": r[3]} for r in rows]


def _topic_role_ids(t: dict) -> list:
    """Palauttaa aiheen roolit listana. Tukee vanhaa role_id kenttää."""
    role_ids = t.get("role_ids")
    if isinstance(role_ids, list):
        return [str(r).strip() for r in role_ids if r]
    rid = t.get("role_id")
    return [str(rid).strip()] if rid else []


def get_ticket_settings(guild_id: str) -> dict:
    """Palauttaa tiketti-asetukset: staff_role_id, category_id, channel_id, transcript_channel_id, ticket_topics, panel_title, panel_description."""
    settings = get_guild_settings(guild_id)
    topics = settings.get("ticket_topics") or []
    if not isinstance(topics, list):
        topics = []
    return {
        "staff_role_id": settings.get("ticket_staff_role_id"),
        "category_id": settings.get("ticket_category_id"),
        "channel_id": settings.get("ticket_channel_id"),
        "transcript_channel_id": settings.get("ticket_transcript_channel_id"),
        "ticket_topics": [
            {
                "label": str(t.get("label", ""))[:100],
                "description": str(t.get("description", ""))[:100],
                "emoji": str(t.get("emoji", ""))[:10],
                "role_ids": _topic_role_ids(t),
            }
            for t in topics if isinstance(t, dict) and t.get("label")
        ],
        "panel_title": (settings.get("ticket_panel_title") or "Tukitiketti").strip()[:256],
        "panel_description": (settings.get("ticket_panel_description") or "Valitse tiketin aihe alta.").strip()[:1000],
    }


def set_ticket_topics(guild_id: str, topics: list, panel_title: str | None = None, panel_description: str | None = None) -> None:
    """Asettaa tikettiaiheet ja valinnaisesti paneelin otsikon ja kuvauksen."""
    s = get_guild_settings(guild_id)
    if topics is not None:
        s["ticket_topics"] = []
        for t in topics:
            if not isinstance(t, dict) or not t.get("label"):
                continue
            role_ids = t.get("role_ids")
            if isinstance(role_ids, list):
                role_ids = [str(r).strip() for r in role_ids if r]
            else:
                rid = t.get("role_id")
                role_ids = [str(rid).strip()] if rid else []
            s["ticket_topics"].append({
                "label": str(t.get("label", ""))[:100],
                "description": str(t.get("description", ""))[:100],
                "emoji": str(t.get("emoji", ""))[:10],
                "role_ids": role_ids,
            })
    if panel_title is not None:
        s["ticket_panel_title"] = str(panel_title).strip()[:256] if panel_title else "Tukitiketti"
    if panel_description is not None:
        s["ticket_panel_description"] = str(panel_description).strip()[:1000] if panel_description else "Valitse tiketin aihe alta."
    set_guild_settings(guild_id, s)


def get_welcome_settings(guild_id: str) -> dict:
    """Palauttaa tervetuloa-asetukset: enabled, channel_id, message (valinnainen, {user} {server} {member_count} {mention})."""
    settings = get_guild_settings(guild_id)
    return {
        "enabled": bool(settings.get("welcome_enabled", False)),
        "channel_id": settings.get("welcome_channel_id"),
        "message": (settings.get("welcome_message") or "Tervetuloa {mention} palvelimelle! 👋").strip(),
    }


def set_welcome_settings(guild_id: str, enabled: bool | None = None, channel_id: str | None = None, message: str | None = None) -> None:
    s = get_guild_settings(guild_id)
    if enabled is not None:
        s["welcome_enabled"] = bool(enabled)
    if channel_id is not None:
        if channel_id:
            s["welcome_channel_id"] = str(channel_id)
        else:
            s.pop("welcome_channel_id", None)
    if message is not None:
        s["welcome_message"] = str(message).strip() if message else "Tervetuloa {mention} palvelimelle! 👋"
    set_guild_settings(guild_id, s)


def get_autorole_settings(guild_id: str) -> dict:
    """Autorole: role_ids lista rooleja joita uudet jäsenet saavat."""
    settings = get_guild_settings(guild_id)
    roles = settings.get("autorole_role_ids") or []
    if not isinstance(roles, list):
        roles = []
    return {"enabled": bool(settings.get("autorole_enabled", False)), "role_ids": [str(r) for r in roles]}


def set_autorole_settings(guild_id: str, enabled: bool | None = None, role_ids: list | None = None) -> None:
    s = get_guild_settings(guild_id)
    if enabled is not None:
        s["autorole_enabled"] = bool(enabled)
    if role_ids is not None:
        s["autorole_role_ids"] = [str(r) for r in role_ids if r]
    set_guild_settings(guild_id, s)


def get_goodbye_settings(guild_id: str) -> dict:
    """Poistumisviesti: enabled, channel_id, message ({user} {server})."""
    settings = get_guild_settings(guild_id)
    return {
        "enabled": bool(settings.get("goodbye_enabled", False)),
        "channel_id": settings.get("goodbye_channel_id"),
        "message": (settings.get("goodbye_message") or "**{user}** lähti palvelimelta. 👋").strip(),
    }


def set_goodbye_settings(guild_id: str, enabled: bool | None = None, channel_id: str | None = None, message: str | None = None) -> None:
    s = get_guild_settings(guild_id)
    if enabled is not None:
        s["goodbye_enabled"] = bool(enabled)
    if channel_id is not None:
        if channel_id:
            s["goodbye_channel_id"] = str(channel_id)
        else:
            s.pop("goodbye_channel_id", None)
    if message is not None:
        s["goodbye_message"] = str(message).strip() if message else "**{user}** lähti palvelimelta. 👋"
    set_guild_settings(guild_id, s)


def get_suggestion_settings(guild_id: str) -> dict:
    """Ehdotusjärjestelmä: enabled, channel_id."""
    settings = get_guild_settings(guild_id)
    return {
        "enabled": bool(settings.get("suggestion_enabled", False)),
        "channel_id": settings.get("suggestion_channel_id"),
    }


def set_suggestion_settings(guild_id: str, enabled: bool | None = None, channel_id: str | None = None) -> None:
    s = get_guild_settings(guild_id)
    if enabled is not None:
        s["suggestion_enabled"] = bool(enabled)
    if channel_id is not None:
        s["suggestion_channel_id"] = str(channel_id) if channel_id else None
    set_guild_settings(guild_id, s)


def get_afk_settings(guild_id: str) -> dict:
    """AFK: enabled."""
    settings = get_guild_settings(guild_id)
    return {"enabled": bool(settings.get("afk_enabled", True))}


def set_afk_settings(guild_id: str, enabled: bool | None = None) -> None:
    s = get_guild_settings(guild_id)
    if enabled is not None:
        s["afk_enabled"] = bool(enabled)
    set_guild_settings(guild_id, s)


def get_giveaway_settings(guild_id: str) -> dict:
    """Arvonta: enabled (mod-only)."""
    settings = get_guild_settings(guild_id)
    return {"enabled": bool(settings.get("giveaway_enabled", True))}


def set_giveaway_settings(guild_id: str, enabled: bool | None = None) -> None:
    s = get_guild_settings(guild_id)
    if enabled is not None:
        s["giveaway_enabled"] = bool(enabled)
    set_guild_settings(guild_id, s)


def get_reminder_settings(guild_id: str) -> dict:
    """Muistutus: enabled, max_per_user, cooldown_sec."""
    settings = get_guild_settings(guild_id)
    return {
        "enabled": bool(settings.get("reminder_enabled", True)),
        "max_per_user": int(settings.get("reminder_max_per_user", 5)),
        "cooldown_sec": int(settings.get("reminder_cooldown_sec", 60)),
    }


def set_reminder_settings(guild_id: str, enabled: bool | None = None, max_per_user: int | None = None, cooldown_sec: int | None = None) -> None:
    s = get_guild_settings(guild_id)
    if enabled is not None:
        s["reminder_enabled"] = bool(enabled)
    if max_per_user is not None:
        s["reminder_max_per_user"] = max(1, min(20, int(max_per_user)))
    if cooldown_sec is not None:
        s["reminder_cooldown_sec"] = max(30, min(3600, int(cooldown_sec)))
    set_guild_settings(guild_id, s)


def get_starboard_settings(guild_id: str) -> dict:
    """Starboard: enabled, channel_id, min_stars."""
    settings = get_guild_settings(guild_id)
    return {
        "enabled": bool(settings.get("starboard_enabled", True)),
        "channel_id": settings.get("starboard_channel_id"),
        "min_stars": int(settings.get("starboard_min_stars", 3)),
    }


def set_starboard_settings(guild_id: str, enabled: bool | None = None, channel_id: str | None = None, min_stars: int | None = None) -> None:
    s = get_guild_settings(guild_id)
    if enabled is not None:
        s["starboard_enabled"] = bool(enabled)
    if channel_id is not None:
        if channel_id:
            s["starboard_channel_id"] = str(channel_id)
        else:
            s.pop("starboard_channel_id", None)
    if min_stars is not None:
        s["starboard_min_stars"] = max(1, min(20, int(min_stars)))
    set_guild_settings(guild_id, s)


def set_ticket_settings(guild_id: str, staff_role_id: str | None = None, category_id: str | None = None, channel_id: str | None = None, transcript_channel_id: str | None = None) -> None:
    s = get_guild_settings(guild_id)
    if staff_role_id is not None:
        if staff_role_id:
            s["ticket_staff_role_id"] = str(staff_role_id)
        else:
            s.pop("ticket_staff_role_id", None)
    if category_id is not None:
        if category_id:
            s["ticket_category_id"] = str(category_id)
        else:
            s.pop("ticket_category_id", None)
    if channel_id is not None:
        if channel_id:
            s["ticket_channel_id"] = str(channel_id)
        else:
            s.pop("ticket_channel_id", None)
    if transcript_channel_id is not None:
        if transcript_channel_id:
            s["ticket_transcript_channel_id"] = str(transcript_channel_id)
        else:
            s.pop("ticket_transcript_channel_id", None)
    set_guild_settings(guild_id, s)


def get_level_settings(guild_id: str) -> dict:
    """Levelli-asetukset: enabled, channel_id, xp_per_message, xp_cooldown, level_roles,
    voice_xp_enabled, voice_xp_per_minute, text_no_xp_channels, voice_no_xp_channels."""
    settings = get_guild_settings(guild_id)
    level_roles = settings.get("level_roles") or {}
    if not isinstance(level_roles, dict):
        level_roles = {}
    text_no = settings.get("text_no_xp_channel_ids") or []
    voice_no = settings.get("voice_no_xp_channel_ids") or []
    if not isinstance(text_no, list):
        text_no = []
    if not isinstance(voice_no, list):
        voice_no = []
    return {
        "enabled": bool(settings.get("level_enabled", False)),
        "channel_id": settings.get("level_channel_id"),
        "xp_per_message": int(settings.get("level_xp_per_message", 15)),
        "xp_cooldown": int(settings.get("level_xp_cooldown", 60)),
        "level_roles": {str(k): str(v) for k, v in level_roles.items()},
        "voice_xp_enabled": bool(settings.get("voice_xp_enabled", False)),
        "voice_xp_per_minute": int(settings.get("voice_xp_per_minute", 10)),
        "text_no_xp_channel_ids": [str(c) for c in text_no],
        "voice_no_xp_channel_ids": [str(c) for c in voice_no],
    }


def set_level_settings(guild_id: str, enabled: bool | None = None, channel_id: str | None = None,
                       xp_per_message: int | None = None, xp_cooldown: int | None = None,
                       level_roles: dict | None = None, voice_xp_enabled: bool | None = None,
                       voice_xp_per_minute: int | None = None,
                       text_no_xp_channel_ids: list | None = None,
                       voice_no_xp_channel_ids: list | None = None) -> None:
    s = get_guild_settings(guild_id)
    if enabled is not None:
        s["level_enabled"] = bool(enabled)
    if channel_id is not None:
        if channel_id:
            s["level_channel_id"] = str(channel_id)
        else:
            s.pop("level_channel_id", None)
    if xp_per_message is not None:
        s["level_xp_per_message"] = max(1, min(100, int(xp_per_message)))
    if xp_cooldown is not None:
        s["level_xp_cooldown"] = max(10, min(300, int(xp_cooldown)))
    if level_roles is not None:
        s["level_roles"] = {str(k): str(v) for k, v in level_roles.items()}
    if voice_xp_enabled is not None:
        s["voice_xp_enabled"] = bool(voice_xp_enabled)
    if voice_xp_per_minute is not None:
        s["voice_xp_per_minute"] = max(1, min(100, int(voice_xp_per_minute)))
    if text_no_xp_channel_ids is not None:
        s["text_no_xp_channel_ids"] = [str(c) for c in text_no_xp_channel_ids if c]
    if voice_no_xp_channel_ids is not None:
        s["voice_no_xp_channel_ids"] = [str(c) for c in voice_no_xp_channel_ids if c]
    set_guild_settings(guild_id, s)


def get_user_xp(guild_id: str, user_id: str) -> tuple[int, int]:
    """Palauttaa (xp, level) -parin."""
    with _get_conn() as conn:
        row = conn.execute(
            "SELECT xp FROM user_xp WHERE guild_id = ? AND user_id = ?",
            (str(guild_id), str(user_id)),
        ).fetchone()
    xp = int(row[0]) if row else 0
    level = _xp_to_level(xp)
    return xp, level


def _xp_to_level(xp: int) -> int:
    """Laske taso XP-pisteistä. Taso N vaatii 100*N XP:tä (taso 1=100, 2=200 lisää jne)."""
    if xp <= 0:
        return 0
    # total_xp_for_level(L) = 100 * L*(L+1)/2
    # xp = 100 * L*(L+1)/2  =>  L^2 + L - 2*xp/100 = 0  =>  L = (-1 + sqrt(1+8*xp/100))/2
    level = int((math.sqrt(1 + 8 * xp / 100) - 1) / 2)
    return max(0, level)


def _xp_for_level(level: int) -> int:
    """XP määrä tason saavuttamiseen."""
    return 100 * level * (level + 1) // 2


def add_user_xp(guild_id: str, user_id: str, amount: int) -> tuple[int, int, bool]:
    """Lisää XP:tä. Palauttaa (uusi_xp, uusi_level, taso_nousi)."""
    with _get_conn() as conn:
        row = conn.execute(
            "SELECT xp FROM user_xp WHERE guild_id = ? AND user_id = ?",
            (str(guild_id), str(user_id)),
        ).fetchone()
        old_xp = int(row[0]) if row else 0
        old_level = _xp_to_level(old_xp)
        new_xp = old_xp + amount
        conn.execute(
            "INSERT INTO user_xp (guild_id, user_id, xp) VALUES (?, ?, ?) "
            "ON CONFLICT(guild_id, user_id) DO UPDATE SET xp = excluded.xp",
            (str(guild_id), str(user_id), new_xp),
        )
    new_level = _xp_to_level(new_xp)
    return new_xp, new_level, new_level > old_level


def get_leaderboard(guild_id: str, limit: int = 10) -> list[tuple[str, int, int]]:
    """Palauttaa top-käyttäjät: [(user_id, xp, level), ...]"""
    with _get_conn() as conn:
        rows = conn.execute(
            "SELECT user_id, xp FROM user_xp WHERE guild_id = ? ORDER BY xp DESC LIMIT ?",
            (str(guild_id), limit),
        ).fetchall()
    return [(r[0], r[1], _xp_to_level(r[1])) for r in rows]


def clear_warns(guild_id: str, user_id: str) -> int:
    with _get_conn() as conn:
        c = conn.execute("DELETE FROM warns WHERE guild_id = ? AND user_id = ?", (str(guild_id), str(user_id)))
        return int(c.rowcount or 0)


def set_afk(guild_id: str, user_id: str, reason: str = "") -> None:
    with _get_conn() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO afk_users (guild_id, user_id, reason, set_at) VALUES (?, ?, ?, datetime('now'))",
            (str(guild_id), str(user_id), (reason or "AFK")[:500]),
        )


def get_afk(guild_id: str, user_id: str) -> dict | None:
    with _get_conn() as conn:
        row = conn.execute(
            "SELECT reason, set_at FROM afk_users WHERE guild_id = ? AND user_id = ?",
            (str(guild_id), str(user_id)),
        ).fetchone()
    if row:
        return {"reason": row[0] or "AFK", "set_at": row[1]}
    return None


def clear_afk(guild_id: str, user_id: str) -> bool:
    with _get_conn() as conn:
        c = conn.execute("DELETE FROM afk_users WHERE guild_id = ? AND user_id = ?", (str(guild_id), str(user_id)))
        return (c.rowcount or 0) > 0


def add_reminder(guild_id: str, user_id: str, channel_id: str, message: str, fire_at: float) -> int:
    with _get_conn() as conn:
        c = conn.execute(
            "INSERT INTO reminders (guild_id, user_id, channel_id, message, fire_at) VALUES (?, ?, ?, ?, ?)",
            (str(guild_id), str(user_id), str(channel_id), (message or "")[:500], fire_at),
        )
        return int(c.lastrowid or 0)


def get_due_reminders(now: float) -> list[dict]:
    with _get_conn() as conn:
        rows = conn.execute(
            "SELECT id, guild_id, user_id, channel_id, message FROM reminders WHERE fire_at <= ?",
            (now,),
        ).fetchall()
    return [{"id": r[0], "guild_id": r[1], "user_id": r[2], "channel_id": r[3], "message": r[4]} for r in rows]


def delete_reminder(reminder_id: int) -> None:
    with _get_conn() as conn:
        conn.execute("DELETE FROM reminders WHERE id = ?", (reminder_id,))


def count_user_reminders(guild_id: str, user_id: str) -> int:
    with _get_conn() as conn:
        row = conn.execute(
            "SELECT COUNT(*) FROM reminders WHERE guild_id = ? AND user_id = ?",
            (str(guild_id), str(user_id)),
        ).fetchone()
    return int(row[0]) if row else 0


def get_db_stats() -> dict | None:
    """Palauttaa tietokannan tilastot (taulut, rivimäärät). None jos ei saatavilla."""
    try:
        with _get_conn() as conn:
            tables = [
                "guild_settings", "users", "warns", "user_xp",
                "afk_users", "reminders"
            ]
            stats = {}
            for t in tables:
                try:
                    row = conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()
                    stats[t] = int(row[0]) if row else 0
                except Exception:
                    stats[t] = 0
            # Levyn käyttö (SQLite)
            try:
                size = os.path.getsize(DB_PATH)
                stats["db_size_bytes"] = size
                stats["db_size_mb"] = round(size / 1024 / 1024, 2)
            except Exception:
                stats["db_size_bytes"] = None
                stats["db_size_mb"] = None
            return stats
    except Exception:
        return None


def get_reaction_roles_settings(guild_id: str) -> dict:
    """Reaction roles: enabled, roles (lista {message_id, channel_id, emoji, role_id})."""
    settings = get_guild_settings(guild_id)
    roles = settings.get("reaction_roles") or []
    if not isinstance(roles, list):
        roles = []
    return {"enabled": bool(settings.get("reaction_roles_enabled", False)), "roles": roles}


def set_reaction_roles_settings(guild_id: str, enabled: bool | None = None, roles: list | None = None) -> None:
    s = get_guild_settings(guild_id)
    if enabled is not None:
        s["reaction_roles_enabled"] = bool(enabled)
    if roles is not None:
        s["reaction_roles"] = [r for r in roles if isinstance(r, dict) and r.get("message_id") and r.get("role_id")]
    set_guild_settings(guild_id, s)


DEFAULT_STAT_LABELS = {
    "members": "Jäsenet",
    "humans": "Ihmiset",
    "online": "Online",
    "offline": "Offline",
}


def get_server_stats_settings(guild_id: str) -> dict:
    """Palvelimen tilastokanavat: enabled, category_id, category_name, stats, channel_ids, labels."""
    settings = get_guild_settings(guild_id)
    stats = settings.get("server_stats_stats") or ["members", "humans", "online", "offline"]
    if not isinstance(stats, list):
        stats = ["members", "humans", "online", "offline"]
    channel_ids = settings.get("server_stats_channel_ids") or {}
    if not isinstance(channel_ids, dict):
        channel_ids = {}
    labels = settings.get("server_stats_labels") or {}
    if not isinstance(labels, dict):
        labels = {}
    labels = {k: (str(v).strip()[:50] or DEFAULT_STAT_LABELS.get(k, k)) for k, v in labels.items()}
    return {
        "enabled": bool(settings.get("server_stats_enabled", False)),
        "category_id": settings.get("server_stats_category_id"),
        "category_name": (settings.get("server_stats_category_name") or "SERVER STATS").strip()[:100],
        "stats": [s for s in stats if s in ("members", "humans", "online", "offline")] or ["members", "humans", "online", "offline"],
        "channel_ids": {str(k): str(v) for k, v in channel_ids.items()},
        "labels": {**{k: DEFAULT_STAT_LABELS[k] for k in DEFAULT_STAT_LABELS}, **labels},
    }


def set_server_stats_settings(
    guild_id: str,
    enabled: bool | None = None,
    category_id: str | None = None,
    category_name: str | None = None,
    stats: list | None = None,
    channel_ids: dict | None = None,
    labels: dict | None = None,
) -> None:
    """Tallentaa palvelimen tilastokanavien asetukset."""
    s = get_guild_settings(guild_id)
    if enabled is not None:
        s["server_stats_enabled"] = bool(enabled)
    if category_id is not None:
        s["server_stats_category_id"] = str(category_id) if category_id else None
    if category_name is not None:
        s["server_stats_category_name"] = str(category_name).strip()[:100] if category_name else "SERVER STATS"
    if stats is not None:
        valid = ("members", "humans", "online", "offline")
        s["server_stats_stats"] = [x for x in stats if x in valid] or ["members", "humans", "online", "offline"]
    if channel_ids is not None and isinstance(channel_ids, dict):
        s["server_stats_channel_ids"] = {str(k): str(v) for k, v in channel_ids.items() if k and v}
    if labels is not None and isinstance(labels, dict):
        valid = ("members", "humans", "online", "offline")
        s["server_stats_labels"] = {str(k): str(v).strip()[:50] for k, v in labels.items() if k in valid and v}
    set_guild_settings(guild_id, s)


def get_all_guild_settings_for_backup() -> dict:
    """Palauttaa kaikki palvelimien asetukset varmuuskopiota varten."""
    with _get_conn() as conn:
        rows = conn.execute(
            "SELECT guild_id, features, updated_at FROM guild_settings"
        ).fetchall()
    return {
        row[0]: {
            "features": json.loads(row[1]) if row[1] else {},
            "updated_at": row[2],
        }
        for row in rows
    }


def get_server_template(guild_id: str) -> dict:
    settings = get_guild_settings(guild_id)
    template = settings.get("server_template")
    if not isinstance(template, dict):
        return {}
    return template


def set_server_template(guild_id: str, template: dict) -> None:
    s = get_guild_settings(guild_id)
    s["server_template"] = template if isinstance(template, dict) else {}
    set_guild_settings(guild_id, s)

# Tekijänoikeudet S44Gaming kaikki oikeudet pidätetään. https://discord.gg/ujB4JHfgcg
