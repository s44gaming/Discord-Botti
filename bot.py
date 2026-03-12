import asyncio
import os
import discord
from discord.ext import commands
import database
from config import BOT_DESCRIPTION, BOT_DEVELOPERS, BOT_INVITE_LINK


async def _load_extensions(bot, folder: str):
    """Lataa kaikki extensionit annetusta kansiosta."""
    path = os.path.join(os.path.dirname(__file__), folder)
    for name in sorted(os.listdir(path)):
        if name.endswith(".py") and not name.startswith("_"):
            module_name = name[:-3]
            ext = f"{folder}.{module_name}"
            try:
                await bot.load_extension(ext)
                print(f"  Ladattu: {ext}")
            except Exception as e:
                print(f"  Virhe ladattaessa {ext}: {e}")


class Bot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.guilds = True
        intents.members = True
        intents.message_content = True
        intents.voice_states = True
        super().__init__(
            command_prefix="!",
            intents=intents,
            description="Monipalvelin Discord -botti hallittavalla web-käyttöliittymällä"
        )
        self._db = database

    def get_tree(self):
        return self.tree

    async def is_feature_enabled(self, guild_id: int, feature: str) -> bool:
        return self._db.is_feature_enabled(str(guild_id), feature)

    def get_log_channel(self, guild_id: int) -> int | None:
        """Palauttaa palvelimen logikanavan ID:n tai None."""
        ch = self._db.get_log_channel(str(guild_id))
        return int(ch) if ch else None

    def is_log_enabled(self, guild_id: int, log_key: str) -> bool:
        return self._db.is_log_enabled(str(guild_id), log_key)

    def get_mod_roles(self, guild_id: int) -> list[str]:
        return self._db.get_mod_roles(str(guild_id))

    def has_mod_permission(self, member: discord.Member) -> bool:
        """Ylläpitäjä tai webissä määritelty mod-rooli."""
        if member.guild_permissions.administrator:
            return True
        try:
            mod_role_ids = {int(rid) for rid in self.get_mod_roles(member.guild.id)}
        except Exception:
            mod_role_ids = set()
        return any(r.id in mod_role_ids for r in member.roles)

    def is_mod_action_enabled(self, guild_id: int, action: str) -> bool:
        return self._db.is_mod_action_enabled(str(guild_id), action)

    def get_ticket_settings(self, guild_id: int) -> dict:
        return self._db.get_ticket_settings(str(guild_id))

    def get_welcome_settings(self, guild_id: int) -> dict:
        return self._db.get_welcome_settings(str(guild_id))

    def get_level_settings(self, guild_id: int) -> dict:
        return self._db.get_level_settings(str(guild_id))

    def get_fivem_settings(self, guild_id: int) -> dict:
        return self._db.get_fivem_settings(str(guild_id))

    def get_twitch_settings(self, guild_id: int) -> dict:
        return self._db.get_twitch_settings(str(guild_id))

    def get_autorole_settings(self, guild_id: int) -> dict:
        return self._db.get_autorole_settings(str(guild_id))

    def get_goodbye_settings(self, guild_id: int) -> dict:
        return self._db.get_goodbye_settings(str(guild_id))

    def get_starboard_settings(self, guild_id: int) -> dict:
        return self._db.get_starboard_settings(str(guild_id))

    def get_suggestion_settings(self, guild_id: int) -> dict:
        return self._db.get_suggestion_settings(str(guild_id))

    def get_afk_settings(self, guild_id: int) -> dict:
        return self._db.get_afk_settings(str(guild_id))

    def get_giveaway_settings(self, guild_id: int) -> dict:
        return self._db.get_giveaway_settings(str(guild_id))

    def get_reminder_settings(self, guild_id: int) -> dict:
        return self._db.get_reminder_settings(str(guild_id))

    def get_reaction_roles_settings(self, guild_id: int) -> dict:
        return self._db.get_reaction_roles_settings(str(guild_id))

    def _presence_text(self) -> str:
        """Status-teksti: palvelimien määrä, kuvaus, kehittäjät, kutsu (max 128 merkkiä)."""
        n = len(self.guilds)
        palvelimet = f"{n} palvelimella" if n != 1 else "1 palvelimella"
        devs = ", ".join(BOT_DEVELOPERS[:5]) if BOT_DEVELOPERS else ""
        desc = (BOT_DESCRIPTION or "Tietoa: !info").strip()[:50]
        parts = [palvelimet, desc]
        if devs:
            parts.append("Kehittäjät: " + devs[:40])
        if BOT_INVITE_LINK:
            parts.append("discord.gg/…")
        text = " | ".join(parts)
        return text[:128]

    async def update_presence(self):
        """Päivittää botin statuksen (näkyy kaikilla palvelimilla)."""
        text = self._presence_text()
        activity = discord.Activity(type=discord.ActivityType.watching, name=text)
        await self.change_presence(activity=activity, status=discord.Status.online)

    async def login(self, token: str):
        """Login with retry on Discord 503."""
        for attempt in range(1, 6):
            try:
                await super().login(token)
                return
            except discord.errors.DiscordServerError:
                if attempt < 5:
                    delay = 2**attempt
                    print(f"Discord API 503, yritetään kirjautumista uudelleen {attempt}/5 ({delay}s)...")
                    await asyncio.sleep(delay)
                else:
                    raise

    async def setup_hook(self):
        print("Ladataan extentioita...")
        await _load_extensions(self, "commands")
        await _load_extensions(self, "events")
        for attempt in range(1, 6):
            try:
                await self.tree.sync()
                print("Slash-komennot synkronoitu")
                break
            except discord.errors.DiscordServerError as e:
                if attempt < 5:
                    delay = 2**attempt
                    print(f"Discord API 503, yritetään uudelleen {attempt}/5 ({delay}s)...")
                    await asyncio.sleep(delay)
                else:
                    raise


def create_bot():
    return Bot()

# Tekijänoikeudet S44Gaming kaikki oikeudet pidätetään. https://discord.gg/ujB4JHfgcg
