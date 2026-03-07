"""/conference_schedule command."""

from __future__ import annotations

import discord
from discord import app_commands

from bot.formatting import fmt_conf_schedule_set
from bot.parsing import parse_conf_weeks


def register(tree: app_commands.CommandTree, bot_ref) -> None:
    @tree.command(
        name="conference_schedule",
        description="Enter a team's conference schedule for the current season.",
    )
    @app_commands.describe(
        team="The team whose schedule is being entered (from the official team list).",
        weeks="Space-separated week numbers (1–14) with conference games. E.g. '1 3 5 7 9 11'.",
    )
    async def conference_schedule(
        interaction: discord.Interaction, team: str, weeks: str
    ) -> None:
        if not await bot_ref.check_admin(interaction):
            return

        # Validate team
        if team not in bot_ref.valid_teams:
            await interaction.response.send_message(
                f"Unknown team: {team}. Team must be from the official team list.",
                ephemeral=True,
            )
            return

        # Parse and validate weeks
        try:
            week_list = parse_conf_weeks(weeks)
        except ValueError as e:
            await interaction.response.send_message(str(e), ephemeral=True)
            return

        state = bot_ref.get_guild_state(interaction.guild_id)
        updated = state.set_conference_schedule(team, week_list)

        msg = fmt_conf_schedule_set(team, week_list, updated=updated)
        if bot_ref.admin_warning(interaction.guild_id):
            msg = bot_ref.admin_warning(interaction.guild_id) + "\n\n" + msg

        await interaction.response.send_message(msg)

    @conference_schedule.autocomplete("team")
    async def team_autocomplete(
        interaction: discord.Interaction, current: str
    ) -> list[app_commands.Choice[str]]:
        matches = [
            app_commands.Choice(name=t, value=t)
            for t in sorted(bot_ref.valid_teams)
            if current.lower() in t.lower()
        ]
        return matches[:25]
