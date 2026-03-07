"""/request command group."""

from __future__ import annotations

import discord
from discord import app_commands

from bot.formatting import fmt_request_added


def register(tree: app_commands.CommandTree, bot_ref) -> None:
    request_group = app_commands.Group(
        name="request", description="Manage non-conference game requests."
    )

    @request_group.command(
        name="add", description="Add a non-conference game request between two teams."
    )
    @app_commands.describe(
        team1="First team (from the official team list).",
        team2="Second team (from the official team list).",
    )
    async def request_add(
        interaction: discord.Interaction, team1: str, team2: str
    ) -> None:
        if not await bot_ref.check_admin(interaction):
            return

        errors: list[str] = []
        if team1 not in bot_ref.valid_teams:
            errors.append(f"Unknown team: {team1}.")
        if team2 not in bot_ref.valid_teams:
            errors.append(f"Unknown team: {team2}.")
        if errors:
            await interaction.response.send_message(
                "\n".join(errors), ephemeral=True
            )
            return

        if team1 == team2:
            await interaction.response.send_message(
                "A team cannot be scheduled against itself.", ephemeral=True
            )
            return

        state = bot_ref.get_guild_state(interaction.guild_id)

        if state.has_duplicate_request(team1, team2):
            await interaction.response.send_message(
                f"A request between {team1} and {team2} already exists.",
                ephemeral=True,
            )
            return

        state.add_request(team1, team2)
        total = len(state.requests)
        msg = fmt_request_added(team1, team2, index=total, total=total)

        if bot_ref.admin_warning(interaction.guild_id):
            msg = bot_ref.admin_warning(interaction.guild_id) + "\n\n" + msg

        await interaction.response.send_message(msg)

    @request_add.autocomplete("team1")
    @request_add.autocomplete("team2")
    async def team_autocomplete(
        interaction: discord.Interaction, current: str
    ) -> list[app_commands.Choice[str]]:
        matches = [
            app_commands.Choice(name=t, value=t)
            for t in sorted(bot_ref.valid_teams)
            if current.lower() in t.lower()
        ]
        return matches[:25]

    tree.add_command(request_group)
