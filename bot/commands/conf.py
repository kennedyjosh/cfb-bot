"""/conference_schedule command."""

from __future__ import annotations

import logging

import discord
from discord import app_commands

from bot.formatting import fmt_conf_schedule_set
from bot.parsing import parse_conf_weeks

log = logging.getLogger(__name__)


def register(tree: app_commands.CommandTree, bot_ref) -> None:
    @tree.command(
        name="conference_schedule",
        description="Enter a team's conference schedule for the current season.",
    )
    @app_commands.describe(
        team="The team whose schedule is being entered (from the official team list).",
        weeks="Space-separated week numbers (1–14) with conference games. E.g. '1 3 5 7 9 11'.",
        home_games="Number of home games among those conference weeks.",
    )
    async def conference_schedule(
        interaction: discord.Interaction, team: str, weeks: str, home_games: int
    ) -> None:
        if not await bot_ref.check_admin(interaction):
            return

        log.debug(
            "Guild %d: /conference_schedule — user=%s team=%r weeks=%r home_games=%d",
            interaction.guild_id, interaction.user, team, weeks, home_games,
        )

        # Validate team
        if team not in bot_ref.valid_teams:
            log.warning(
                "Guild %d: /conference_schedule rejected — unknown team %r (user=%s)",
                interaction.guild_id, team, interaction.user,
            )
            await interaction.response.send_message(
                f"Unknown team: {team}. Team must be from the official team list.",
                ephemeral=True,
            )
            return

        # Parse and validate weeks
        try:
            week_list = parse_conf_weeks(weeks)
        except ValueError as e:
            log.warning(
                "Guild %d: /conference_schedule rejected — invalid weeks %r for %s: %s (user=%s)",
                interaction.guild_id, weeks, team, e, interaction.user,
            )
            await interaction.response.send_message(str(e), ephemeral=True)
            return

        state = bot_ref.get_guild_state(interaction.guild_id)
        updated = state.set_conference_schedule(team, week_list, home_games=home_games)

        log.info(
            "Guild %d: /conference_schedule — %s %s: weeks=%s home_games=%d (user=%s)",
            interaction.guild_id,
            "updated" if updated else "set",
            team, sorted(week_list), home_games, interaction.user,
        )

        msg = fmt_conf_schedule_set(team, week_list, home_games=home_games, updated=updated)
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
