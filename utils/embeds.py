"""
دالة موحدة لإنشاء الـ Embeds مع فوتر موحّد وتصميم أنظف.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

import discord

CREDITS_TEXT = "discord.gg/row"
SEPARATOR = "────────────────────"


def branded_embed(
    *,
    title: Optional[str] = None,
    description: Optional[str] = None,
    color: Optional[discord.Color] = None,
    timestamp: bool | datetime | None = None,
    **kwargs,
) -> discord.Embed:
    """إنشاء إمبد موحّد الشكل مع فوتر ROW."""
    if color is None:
        color = discord.Color.blurple()

    embed = discord.Embed(title=title, description=description, color=color, **kwargs)

    if timestamp is True:
        embed.timestamp = datetime.now(timezone.utc)
    elif isinstance(timestamp, datetime):
        embed.timestamp = timestamp

    embed.set_footer(text=CREDITS_TEXT)
    return embed


def section_text(*lines: str) -> str:
    """سطور مرتبة مع فاصل اختياري."""
    return "\n".join(line for line in lines if line is not None)


def bullet_list(items: list[str], bullet: str = "•") -> str:
    return "\n".join(f"{bullet} {item}" for item in items if item)
