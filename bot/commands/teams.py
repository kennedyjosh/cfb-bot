"""/teams command."""

from __future__ import annotations

import logging

import discord
from discord import app_commands

from bot.formatting import fmt_teams

log = logging.getLogger(__name__)


def register(tree: app_commands.CommandTree, bot_ref) -> None:
    @tree.command(
        name="teams",
        description="List all Discord members and their team assignments.",
    )
    async def teams(interaction: discord.Interaction) -> None:
        if not await bot_ref.check_admin(interaction):
            return

        resolved = bot_ref.get_resolved_members(interaction.guild_id)
        unresolved = bot_ref.get_unresolved_members(interaction.guild_id)

        log.debug(
            "Guild %d: /teams — %d resolved, %d unrecognized",
            interaction.guild_id,
            len(resolved),
            len(unresolved),
        )

        resolved_pairs = [(m.team, m.user_id) for m in resolved]
        unrecognized = [m.display_name for m in unresolved]

        msg = fmt_teams(resolved=resolved_pairs, unrecognized=unrecognized)
        if bot_ref.admin_warning(interaction.guild_id):
            msg = bot_ref.admin_warning(interaction.guild_id) + "\n\n" + msg

        await interaction.response.send_message(
            msg,
            allowed_mentions=discord.AllowedMentions(users=False),
        )
