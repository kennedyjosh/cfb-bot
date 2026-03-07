"""/teams command."""

from __future__ import annotations

import discord
from discord import app_commands

from bot.formatting import fmt_teams


def register(tree: app_commands.CommandTree, bot_ref) -> None:
    @tree.command(
        name="teams",
        description="List Discord members not mapped to a team.",
    )
    async def teams(interaction: discord.Interaction) -> None:
        if not await bot_ref.check_admin(interaction):
            return

        unresolved = bot_ref.get_unresolved_members(interaction.guild_id)
        ignored = [m.display_name for m in unresolved if m.is_ignored]
        unparsable = [m.display_name for m in unresolved if not m.is_ignored]

        msg = fmt_teams(ignored=ignored, unparsable=unparsable)
        if bot_ref.admin_warning(interaction.guild_id):
            msg = bot_ref.admin_warning(interaction.guild_id) + "\n\n" + msg

        await interaction.response.send_message(msg)
