"""
Näyttää kaikki käytettävissä olevat slash-komennot. Päivittyy automaattisesti kun komentoja lisätään.
Näyttää jokaiselle Päällä/Pois-tilan (web-asetuksista).
"""
import discord
from discord import app_commands
from discord.ext import commands

# Komento -> feature-avain (web-hallinnan COMMAND_FEATURES)
COMMAND_TO_FEATURE = {
    "ping": "ping",
    "info": "info",
    "avatar": "avatar",
    "userinfo": "userinfo",
    "reverse": "reverse",
    "tempvoice_panel": "tempvoice",
    "admin": "hallinta",
    "sendinvite": "kutsuviesti",
    "level": "taso",
    "coinflip": "kolikko",
    "8ball": "8ball",
    "guess": "arvaa",
    "roulette": "ruletti",
    "afk": "afk",
    "reminder": "muistutus",
    "commands": "komennot_lista",
    "hello": "tervehdys",
    "invite": "kutsu",
    "ticket_panel": "tiketti",
    "leaderboard": "tasonboard",
    "dice": "noppa",
    "rps": "kps",
    "choose": "arpa",
    "fivem": "fivem",
    "suggestion": "ehdotus",
    "giveaway": "arvonta",
    "kick": "mod_kick",
    "ban": "mod_ban",
    "mute": "mod_mute",
    "unmute": "mod_unmute",
    "warn": "mod_warn",
    "warnings": "mod_warn",
    "clearwarns": "mod_warn",
    "clear": "mod_purge",
    "slowmode": "mod_slowmode",
    "say": "mod_say",
    "poll": "poll",
}


class KomennotListaCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def _kerää_kaikki_komennot(self):
        """Kerää kaikki puun komennot (päivittyy aina kun puu muuttuu)."""
        rivit = []
        for cmd in self.bot.tree.walk_commands():
            if not getattr(cmd, "name", None):
                continue
            nimi = getattr(cmd, "qualified_name", None) or cmd.name
            kuvaus = getattr(cmd, "description", None) or "–"
            if not kuvaus or kuvaus == "…":
                kuvaus = "–"
            rivit.append((nimi, kuvaus[:80] if kuvaus else "–"))
        return sorted(rivit, key=lambda x: x[0].lower())

    @app_commands.command(name="commands", description="Show all bot commands")
    async def komennot(self, interaction: discord.Interaction):
        enabled = await self.bot.is_feature_enabled(interaction.guild_id, "komennot_lista")
        if not enabled:
            await interaction.response.send_message(
                "⚠️ This command is disabled. Enable it in web dashboard.",
                ephemeral=True
            )
            return
        lista = self._kerää_kaikki_komennot()
        if not lista:
            await interaction.response.send_message("No commands found.", ephemeral=True)
            return

        settings = self.bot._db.get_guild_settings(str(interaction.guild_id)) if interaction.guild_id else {}
        def _on_off(cmd_name: str) -> str:
            feat = COMMAND_TO_FEATURE.get(cmd_name)
            if feat is None:
                return "–"
            val = settings.get(feat, True)
            return "🟢 On" if val else "🔴 Off"

        # Jaetaan useampaan fieldiin (max 1024 merkkiä per field) jotta mobiililla ja PC:llä kaikki näkyy
        CHUNK_LEN = 10
        chunks = [lista[i : i + CHUNK_LEN] for i in range(0, len(lista), CHUNK_LEN)]
        total = len(chunks)
        embed = discord.Embed(
            title="Bot commands",
            description="All slash commands. 🟢 On / 🔴 Off = web dashboard → General → Commands.",
            color=discord.Color.blue()
        )
        for idx, chunk in enumerate(chunks, 1):
            lines = [f"**/{nimi}** — {_on_off(nimi)} — {kuvaus}" for nimi, kuvaus in chunk]
            text = "\n".join(lines)
            name = f"Commands ({idx}/{total})" if total > 1 else "Commands"
            embed.add_field(name=name, value=text or "–", inline=False)
        embed.set_footer(text="On/Off: web dashboard → General → Commands")
        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot):
    await bot.add_cog(KomennotListaCog(bot))

# Tekijänoikeudet S44Gaming kaikki oikeudet pidätetään. https://discord.gg/ujB4JHfgcg
