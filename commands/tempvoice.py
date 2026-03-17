import discord
from discord import app_commands
from discord.ext import commands
import database


def _err(msg: str) -> str:
    return f"❌ {msg}"


async def _get_or_create_tempvoice_category(guild: discord.Guild) -> discord.CategoryChannel | None:
    for cat in guild.categories:
        if cat.name.lower() == "tempvoice":
            return cat
    try:
        return await guild.create_category(name="TempVoice", reason="TempVoice category")
    except (discord.Forbidden, discord.HTTPException):
        return None


def _tempvoice_overwrites(guild: discord.Guild, owner: discord.Member) -> dict:
    return {
        guild.default_role: discord.PermissionOverwrite(
            view_channel=True,
            connect=True,
            speak=True,
            stream=True,
            use_voice_activation=True,
            manage_channels=False,
            manage_permissions=False,
            move_members=False,
            mute_members=False,
            deafen_members=False,
        ),
        owner: discord.PermissionOverwrite(
            view_channel=True,
            connect=True,
            speak=True,
            stream=True,
            use_voice_activation=True,
            priority_speaker=True,
            move_members=True,
            mute_members=True,
            deafen_members=True,
            manage_channels=True,
            manage_permissions=True,
        ),
        guild.me: discord.PermissionOverwrite(
            view_channel=True,
            manage_channels=True,
            manage_permissions=True,
            connect=True,
            move_members=True,
        ),
    }


class TempVoiceCreateButton(discord.ui.Button):
    def __init__(self, bot):
        super().__init__(
            style=discord.ButtonStyle.primary,
            label="Luo TempVoice",
            custom_id="tempvoice_create",
        )
        self.bot = bot

    async def callback(self, interaction: discord.Interaction):
        if not interaction.guild or not isinstance(interaction.user, discord.Member):
            return await interaction.response.send_message(
                _err("Tätä voi käyttää vain palvelimella."),
                ephemeral=True,
            )
        if not await self.bot.is_feature_enabled(interaction.guild_id, "tempvoice"):
            return await interaction.response.send_message(
                _err("TempVoice-ominaisuus on pois päältä (web dashboard)."),
                ephemeral=True,
            )
        if not interaction.guild.me.guild_permissions.manage_channels:
            return await interaction.response.send_message(
                _err("Botilta puuttuu `Manage Channels`-oikeus."),
                ephemeral=True,
            )

        await interaction.response.defer(ephemeral=True)

        guild = interaction.guild
        owner = interaction.user

        category = await _get_or_create_tempvoice_category(guild)
        if not category:
            return await interaction.followup.send(
                _err("TempVoice-kategorian luonti epäonnistui (puuttuuko oikeuksia?)."),
                ephemeral=True,
            )

        name = f"🔊 {owner.display_name}"[:90]
        overwrites = _tempvoice_overwrites(guild, owner)
        try:
            channel = await guild.create_voice_channel(
                name=name,
                category=category,
                overwrites=overwrites,
                reason=f"TempVoice created by {owner} ({owner.id})",
            )
        except discord.Forbidden:
            return await interaction.followup.send(_err("Ei oikeuksia luoda äänikanavaa."), ephemeral=True)
        except discord.HTTPException:
            return await interaction.followup.send(_err("Äänikanavan luonti epäonnistui."), ephemeral=True)

        database.add_tempvoice_channel(str(guild.id), str(channel.id), str(owner.id))

        try:
            if owner.voice and owner.voice.channel and owner.voice.channel.guild.id == guild.id:
                await owner.move_to(channel, reason="Move to TempVoice")
        except (discord.Forbidden, discord.HTTPException):
            pass

        await interaction.followup.send(
            f"✅ TempVoice luotu: {channel.mention}\n"
            f"Vain sinulla on tähän kanavaan täydet hallintaoikeudet.",
            ephemeral=True,
        )


class TempVoicePanelView(discord.ui.View):
    def __init__(self, bot):
        super().__init__(timeout=None)
        self.add_item(TempVoiceCreateButton(bot))


class TempVoiceCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="tempvoice_panel", description="Send TempVoice panel")
    async def tempvoice_panel(self, interaction: discord.Interaction):
        if not interaction.guild:
            return await interaction.response.send_message(_err("Käytä palvelimella."), ephemeral=True)
        if not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message(_err("Vain ylläpitäjät."), ephemeral=True)
        if not await self.bot.is_feature_enabled(interaction.guild_id, "tempvoice"):
            return await interaction.response.send_message(
                _err("TempVoice on pois päältä (web dashboard)."),
                ephemeral=True,
            )

        embed = discord.Embed(
            title="TempVoice",
            description="Paina nappia luodaksesi oman väliaikaisen äänikanavan.\n"
                        "Jos kanava on tyhjä yli 5 minuuttia, se poistuu automaattisesti.",
            color=discord.Color.blurple(),
        )
        await interaction.channel.send(embed=embed, view=TempVoicePanelView(self.bot))
        await interaction.response.send_message("✅ TempVoice-paneeli lähetetty tähän kanavaan.", ephemeral=True)


async def setup(bot):
    bot.add_view(TempVoicePanelView(bot))
    await bot.add_cog(TempVoiceCog(bot))

