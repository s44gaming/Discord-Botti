import discord
from discord import app_commands
from discord.ext import commands
import requests
import os
import asyncio

import database
from server_template_utils import (
    capture_server_template,
    restore_server_template,
    extract_discord_template_code,
    template_from_discord_payload,
)


def _err(message: str) -> str:
    return f"❌ {message}"


class ServerTemplateCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="template_save", description="Tallenna palvelimen nykyinen kanavamalli")
    async def template_save(self, interaction: discord.Interaction):
        if not interaction.guild:
            return await interaction.response.send_message(_err("Käytä tätä palvelimella."), ephemeral=True)
        if not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message(_err("Vain ylläpitäjät voivat käyttää tätä."), ephemeral=True)

        template = capture_server_template(interaction.guild)
        database.set_server_template(str(interaction.guild.id), template)
        await interaction.response.send_message(
            "✅ Palvelinmalli tallennettu.\nVoit palauttaa sen komennolla `/template_restore` tai webistä.",
            ephemeral=True,
        )

    @app_commands.command(
        name="template_restore",
        description="Palauta tallennettu palvelinmalli (luo vain puuttuvat kanavat)",
    )
    async def template_restore(self, interaction: discord.Interaction):
        if not interaction.guild:
            return await interaction.response.send_message(_err("Käytä tätä palvelimella."), ephemeral=True)
        if not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message(_err("Vain ylläpitäjät voivat käyttää tätä."), ephemeral=True)
        if not interaction.guild.me.guild_permissions.manage_channels:
            return await interaction.response.send_message(
                _err("Botilta puuttuu `Manage Channels`-oikeus."),
                ephemeral=True,
            )

        template = database.get_server_template(str(interaction.guild.id))
        if not template:
            return await interaction.response.send_message(
                _err("Tallennettua palvelinmallia ei löydy. Aja ensin `/template_save`."),
                ephemeral=True,
            )

        await interaction.response.defer(ephemeral=True, thinking=True)
        stats = await restore_server_template(interaction.guild, template)
        await interaction.followup.send(
            "✅ Palautus valmis.\n"
            f"- Luodut kategoriat: {stats['created_categories']}\n"
            f"- Luodut tekstikanavat: {stats['created_text_channels']}\n"
            f"- Luodut äänikanavat: {stats['created_voice_channels']}\n"
            f"- Ohitetut (oli jo olemassa): {stats['skipped_existing']}",
            ephemeral=True,
        )

    @app_commands.command(
        name="template_restore_link",
        description="Palauta palvelinmalli discord.new-linkistä (luo vain puuttuvat)",
    )
    @app_commands.describe(link="Esim. https://discord.new/xxXxxxxxxxxx")
    async def template_restore_link(self, interaction: discord.Interaction, link: str):
        if not interaction.guild:
            return await interaction.response.send_message(_err("Käytä tätä palvelimella."), ephemeral=True)
        if not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message(_err("Vain ylläpitäjät voivat käyttää tätä."), ephemeral=True)
        if not interaction.guild.me.guild_permissions.manage_channels:
            return await interaction.response.send_message(
                _err("Botilta puuttuu `Manage Channels`-oikeus."),
                ephemeral=True,
            )

        code = extract_discord_template_code(link)
        if not code:
            return await interaction.response.send_message(_err("Virheellinen discord.new-linkki tai template-koodi."), ephemeral=True)

        await interaction.response.defer(ephemeral=True, thinking=True)
        try:
            payload = await asyncio.to_thread(_fetch_discord_template_payload, code)
            template = template_from_discord_payload(payload)
            database.set_server_template(str(interaction.guild.id), template)
            stats = await restore_server_template(interaction.guild, template)
        except Exception as e:
            return await interaction.followup.send(_err(f"Template-linkin käyttö epäonnistui: {e}"), ephemeral=True)

        await interaction.followup.send(
            "✅ Discord-template palautettu ja tallennettu malliksi.\n"
            f"- Luodut kategoriat: {stats['created_categories']}\n"
            f"- Luodut tekstikanavat: {stats['created_text_channels']}\n"
            f"- Luodut äänikanavat: {stats['created_voice_channels']}\n"
            f"- Ohitetut (oli jo olemassa): {stats['skipped_existing']}",
            ephemeral=True,
        )


def _fetch_discord_template_payload(code: str) -> dict:
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        raise RuntimeError("DISCORD_TOKEN puuttuu.")
    r = requests.get(
        f"https://discord.com/api/v10/guilds/templates/{code}",
        headers={"Authorization": f"Bot {token}", "User-Agent": "DiscordBot (ServerTemplate)"},
        timeout=30,
    )
    if r.status_code != 200:
        raise RuntimeError(f"Discord API virhe ({r.status_code})")
    data = r.json()
    if not isinstance(data, dict) or not data.get("serialized_source_guild"):
        raise RuntimeError("Template-data puuttuu tai on virheellinen.")
    return data


async def setup(bot):
    await bot.add_cog(ServerTemplateCog(bot))
