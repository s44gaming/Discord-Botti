import discord
import asyncio
from discord.ext import commands
import database


async def setup(bot: commands.Bot):
    EMPTY_DELETE_AFTER_SEC = 5 * 60
    _pending_deletes: dict[int, asyncio.Task] = {}

    async def _cancel_pending(channel_id: int):
        task = _pending_deletes.pop(channel_id, None)
        if task and not task.done():
            task.cancel()

    async def _schedule_cleanup_if_empty(channel: discord.VoiceChannel | None):
        if not channel or not isinstance(channel, discord.VoiceChannel):
            return
        try:
            if channel.members:
                await _cancel_pending(channel.id)
                return
        except Exception:
            return

        try:
            if not database.is_tempvoice_channel(str(channel.id)):
                return
        except Exception:
            return

        if channel.id in _pending_deletes and not _pending_deletes[channel.id].done():
            return

        async def _do_delete():
            try:
                await asyncio.sleep(EMPTY_DELETE_AFTER_SEC)
                try:
                    fresh = channel.guild.get_channel(channel.id)
                except Exception:
                    fresh = None
                if not fresh or not isinstance(fresh, discord.VoiceChannel):
                    return
                if fresh.members:
                    return
                if not database.is_tempvoice_channel(str(fresh.id)):
                    return
                try:
                    await fresh.delete(reason="TempVoice empty for 5 minutes - auto cleanup")
                except (discord.Forbidden, discord.HTTPException):
                    return
                finally:
                    try:
                        database.remove_tempvoice_channel(str(fresh.id))
                    except Exception:
                        pass
            except asyncio.CancelledError:
                return
            finally:
                _pending_deletes.pop(channel.id, None)

        _pending_deletes[channel.id] = asyncio.create_task(_do_delete())

    async def on_voice_state_update(member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
        if before.channel and before.channel != after.channel:
            await _schedule_cleanup_if_empty(before.channel if isinstance(before.channel, discord.VoiceChannel) else None)
        if after.channel and before.channel != after.channel:
            if isinstance(after.channel, discord.VoiceChannel):
                await _cancel_pending(after.channel.id)

    async def on_guild_channel_delete(channel: discord.abc.GuildChannel):
        if isinstance(channel, discord.VoiceChannel):
            try:
                await _cancel_pending(channel.id)
                database.remove_tempvoice_channel(str(channel.id))
            except Exception:
                pass

    bot.add_listener(on_voice_state_update, "on_voice_state_update")
    bot.add_listener(on_guild_channel_delete, "on_guild_channel_delete")

