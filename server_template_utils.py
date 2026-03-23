import discord


def _norm(name: str) -> str:
    return (name or "").strip().lower()


def extract_discord_template_code(template_url_or_code: str) -> str:
    raw = (template_url_or_code or "").strip()
    if not raw:
        return ""
    if "/" not in raw:
        return raw
    cleaned = raw.rstrip("/")
    return cleaned.split("/")[-1].split("?")[0].strip()


def template_from_discord_payload(payload: dict) -> dict:
    """Muuntaa Discordin guild template payloadin sisäiseen formaattiin."""
    src = payload.get("serialized_source_guild") or {}
    channels = src.get("channels") or []

    categories: list[dict] = []
    categories_by_id: dict[str, str] = {}
    text_channels: list[dict] = []
    voice_channels: list[dict] = []

    for ch in channels:
        if int(ch.get("type", -1)) != 4:
            continue
        name = (ch.get("name") or "").strip()[:100]
        if not name:
            continue
        cid = str(ch.get("id"))
        categories.append({"name": name})
        categories_by_id[cid] = name

    for ch in channels:
        ctype = int(ch.get("type", -1))
        name = (ch.get("name") or "").strip()[:100]
        if not name:
            continue
        parent_name = categories_by_id.get(str(ch.get("parent_id")), "")

        if ctype == 0:
            text_channels.append(
                {
                    "name": name,
                    "category": parent_name or None,
                    "topic": (ch.get("topic") or "")[:1024],
                    "nsfw": bool(ch.get("nsfw", False)),
                    "slowmode_delay": int(ch.get("rate_limit_per_user", 0) or 0),
                }
            )
        elif ctype == 2:
            voice_channels.append(
                {
                    "name": name,
                    "category": parent_name or None,
                    "bitrate": int(ch.get("bitrate", 64000) or 64000),
                    "user_limit": int(ch.get("user_limit", 0) or 0),
                }
            )

    return {
        "version": 1,
        "source": "discord_template",
        "source_name": (payload.get("name") or "").strip()[:100],
        "source_code": (payload.get("code") or "").strip(),
        "categories": categories,
        "text_channels": text_channels,
        "voice_channels": voice_channels,
    }


def capture_server_template(guild: discord.Guild) -> dict:
    categories: list[dict] = []
    category_by_id: dict[int, str] = {}

    for cat in sorted(guild.categories, key=lambda c: c.position):
        categories.append({"name": cat.name})
        category_by_id[cat.id] = cat.name

    text_channels: list[dict] = []
    voice_channels: list[dict] = []

    for channel in sorted(guild.channels, key=lambda c: (c.position, c.id)):
        if isinstance(channel, discord.TextChannel):
            text_channels.append(
                {
                    "name": channel.name,
                    "category": category_by_id.get(channel.category_id),
                    "topic": channel.topic or "",
                    "nsfw": bool(channel.nsfw),
                    "slowmode_delay": int(channel.slowmode_delay or 0),
                }
            )
        elif isinstance(channel, discord.VoiceChannel):
            voice_channels.append(
                {
                    "name": channel.name,
                    "category": category_by_id.get(channel.category_id),
                    "bitrate": int(channel.bitrate or 64000),
                    "user_limit": int(channel.user_limit or 0),
                }
            )

    return {
        "version": 1,
        "categories": categories,
        "text_channels": text_channels,
        "voice_channels": voice_channels,
    }


async def restore_server_template(guild: discord.Guild, template: dict) -> dict:
    created_categories = 0
    created_text = 0
    created_voice = 0
    skipped_existing = 0

    existing_categories: dict[str, discord.CategoryChannel] = {
        _norm(cat.name): cat for cat in guild.categories
    }

    for cat_data in template.get("categories", []):
        name = (cat_data.get("name") or "").strip()[:100]
        if not name:
            continue
        key = _norm(name)
        if key in existing_categories:
            skipped_existing += 1
            continue
        try:
            created = await guild.create_category(name=name, reason="Restore server template")
        except (discord.Forbidden, discord.HTTPException):
            continue
        existing_categories[key] = created
        created_categories += 1

    existing_text: set[tuple[str, str]] = set()
    existing_voice: set[tuple[str, str]] = set()

    for channel in guild.channels:
        if isinstance(channel, discord.TextChannel):
            cat_name = _norm(channel.category.name) if channel.category else ""
            existing_text.add((_norm(channel.name), cat_name))
        elif isinstance(channel, discord.VoiceChannel):
            cat_name = _norm(channel.category.name) if channel.category else ""
            existing_voice.add((_norm(channel.name), cat_name))

    for ch_data in template.get("text_channels", []):
        name = (ch_data.get("name") or "").strip()[:100]
        if not name:
            continue
        category_name = (ch_data.get("category") or "").strip()[:100]
        cat_key = _norm(category_name)
        key = (_norm(name), cat_key)
        if key in existing_text:
            skipped_existing += 1
            continue
        category = existing_categories.get(cat_key) if cat_key else None
        try:
            await guild.create_text_channel(
                name=name,
                category=category,
                topic=(ch_data.get("topic") or "")[:1024] or None,
                nsfw=bool(ch_data.get("nsfw", False)),
                slowmode_delay=max(0, min(21600, int(ch_data.get("slowmode_delay", 0) or 0))),
                reason="Restore server template",
            )
        except (discord.Forbidden, discord.HTTPException, ValueError):
            continue
        existing_text.add(key)
        created_text += 1

    for ch_data in template.get("voice_channels", []):
        name = (ch_data.get("name") or "").strip()[:100]
        if not name:
            continue
        category_name = (ch_data.get("category") or "").strip()[:100]
        cat_key = _norm(category_name)
        key = (_norm(name), cat_key)
        if key in existing_voice:
            skipped_existing += 1
            continue
        category = existing_categories.get(cat_key) if cat_key else None
        try:
            await guild.create_voice_channel(
                name=name,
                category=category,
                bitrate=max(8000, min(384000, int(ch_data.get("bitrate", 64000) or 64000))),
                user_limit=max(0, min(99, int(ch_data.get("user_limit", 0) or 0))),
                reason="Restore server template",
            )
        except (discord.Forbidden, discord.HTTPException, ValueError):
            continue
        existing_voice.add(key)
        created_voice += 1

    return {
        "created_categories": created_categories,
        "created_text_channels": created_text,
        "created_voice_channels": created_voice,
        "skipped_existing": skipped_existing,
    }
