import os
from dotenv import load_dotenv

load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
DISCORD_CLIENT_ID = os.getenv("DISCORD_CLIENT_ID")
DISCORD_CLIENT_SECRET = os.getenv("DISCORD_CLIENT_SECRET")
DISCORD_REDIRECT_URI = os.getenv("DISCORD_REDIRECT_URI", "http://localhost/callback")
FLASK_SECRET_KEY = os.getenv("FLASK_SECRET_KEY")
BASE_URL = os.getenv("BASE_URL", "http://localhost")
WEB_PORT = int(os.getenv("WEB_PORT", 80))
DEV_USER_IDS = [x.strip() for x in (os.getenv("DEV_USER_IDS") or "").split(",") if x.strip()]

# Botin status (kuvaus, kehittäjät, kutsu-linkki): data/bot_info.txt tai salattu data/bot_info.enc
def _load_bot_info():
    try:
        import bot_info
        password = os.getenv("BOT_INFO_EDIT_PASSWORD")
        info = bot_info.load(password)
        if info:
            return (
                (info.get("description") or "").strip() or "Monipalvelin-botti, hallinta: !hallinta",
                [x.strip() for x in (info.get("developers") or []) if x.strip()],
                (info.get("invite_link") or "").strip(),
                (info.get("apply_bot_url") or "").strip(),
            )
    except Exception:
        pass
    return (
        (os.getenv("BOT_DESCRIPTION") or "Monipalvelin-botti, hallinta: !hallinta").strip(),
        [x.strip() for x in (os.getenv("BOT_DEVELOPERS") or "").split(",") if x.strip()],
        (os.getenv("BOT_INVITE_LINK") or "").strip(),
        (os.getenv("BOT_APPLY_URL") or "").strip(),
    )

_bot_desc, _bot_devs, _bot_invite, _bot_apply = _load_bot_info()
BOT_DESCRIPTION = _bot_desc
BOT_DEVELOPERS = _bot_devs
BOT_INVITE_LINK = _bot_invite
BOT_APPLY_URL = _bot_apply

# Salasana botin tietojen muokkaukseen kehittäjäportaalissa (pakollinen salatun tiedoston käytölle)
BOT_INFO_EDIT_PASSWORD = (os.getenv("BOT_INFO_EDIT_PASSWORD") or "").strip()

# Tekijänoikeudet S44Gaming kaikki oikeudet pidätetään. https://discord.gg/ujB4JHfgcg
