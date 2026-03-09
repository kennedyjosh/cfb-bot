"""/request command group."""

from __future__ import annotations

import logging

import discord
from discord import app_commands

from bot.formatting import fmt_request_added, fmt_request_removed, fmt_request_show, fmt_request_show_all

log = logging.getLogger(__name__)


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

        log.debug(
            "Guild %d: /request add — user=%s team1=%r team2=%r",
            interaction.guild_id, interaction.user, team1, team2,
        )

        errors: list[str] = []
        if team1 not in bot_ref.valid_teams:
            errors.append(f"Unknown team: {team1}.")
        if team2 not in bot_ref.valid_teams:
            errors.append(f"Unknown team: {team2}.")
        if errors:
            log.warning(
                "Guild %d: /request add rejected — unknown team(s): %r vs %r (user=%s)",
                interaction.guild_id, team1, team2, interaction.user,
            )
            await interaction.response.send_message(
                "\n".join(errors), ephemeral=True
            )
            return

        if team1 == team2:
            log.warning(
                "Guild %d: /request add rejected — team scheduled against itself: %r (user=%s)",
                interaction.guild_id, team1, interaction.user,
            )
            await interaction.response.send_message(
                "A team cannot be scheduled against itself.", ephemeral=True
            )
            return

        state = bot_ref.get_guild_state(interaction.guild_id)

        if state.has_duplicate_request(team1, team2):
            log.warning(
                "Guild %d: /request add rejected — duplicate request: %s vs %s (user=%s)",
                interaction.guild_id, team1, team2, interaction.user,
            )
            await interaction.response.send_message(
                f"A request between {team1} and {team2} already exists.",
                ephemeral=True,
            )
            return

        state.add_request(team1, team2)
        total = len(state.requests)
        log.info(
            "Guild %d: /request add — %s vs %s (request #%d) (user=%s)",
            interaction.guild_id, team1, team2, total, interaction.user,
        )
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

    @request_group.command(
        name="remove", description="Remove a non-conference game request between two teams."
    )
    @app_commands.describe(
        team1="First team.",
        team2="Second team.",
    )
    async def request_remove(
        interaction: discord.Interaction, team1: str, team2: str
    ) -> None:
        if not await bot_ref.check_admin(interaction):
            return

        log.debug(
            "Guild %d: /request remove — user=%s team1=%r team2=%r",
            interaction.guild_id, interaction.user, team1, team2,
        )

        errors: list[str] = []
        if team1 not in bot_ref.valid_teams:
            errors.append(f"Unknown team: {team1}.")
        if team2 not in bot_ref.valid_teams:
            errors.append(f"Unknown team: {team2}.")
        if errors:
            await interaction.response.send_message("\n".join(errors), ephemeral=True)
            return

        state = bot_ref.get_guild_state(interaction.guild_id)
        found = state.remove_request(team1, team2)
        if not found:
            await interaction.response.send_message(
                f"No request between {team1} and {team2} exists.", ephemeral=True
            )
            return

        state.last_result = None
        log.info(
            "Guild %d: /request remove — %s vs %s (user=%s)",
            interaction.guild_id, team1, team2, interaction.user,
        )
        msg = fmt_request_removed(team1, team2)
        if bot_ref.admin_warning(interaction.guild_id):
            msg = bot_ref.admin_warning(interaction.guild_id) + "\n\n" + msg
        await interaction.response.send_message(msg)

    @request_remove.autocomplete("team1")
    @request_remove.autocomplete("team2")
    async def remove_team_autocomplete(
        interaction: discord.Interaction, current: str
    ) -> list[app_commands.Choice[str]]:
        matches = [
            app_commands.Choice(name=t, value=t)
            for t in sorted(bot_ref.valid_teams)
            if current.lower() in t.lower()
        ]
        return matches[:25]

    @request_group.command(
        name="show", description="Show requests involving a team."
    )
    @app_commands.describe(
        team="Team to look up (omit to use your own team).",
    )
    async def request_show(
        interaction: discord.Interaction, team: str | None = None
    ) -> None:
        if not await bot_ref.check_admin(interaction):
            return

        state = bot_ref.get_guild_state(interaction.guild_id)

        if team == "all":
            log.debug(
                "Guild %d: /request show all — user=%s",
                interaction.guild_id, interaction.user,
            )
            human_teams = set(bot_ref.get_human_teams(interaction.guild_id).keys())
            await interaction.response.send_message(fmt_request_show_all(state.requests, human_teams))
            return

        if team is None:
            # Resolve invoking user to their team
            human_teams = bot_ref.get_human_teams(interaction.guild_id)
            user_id = interaction.user.id
            team = next((t for t, uid in human_teams.items() if uid == user_id), None)
            if team is None:
                await interaction.response.send_message(
                    "You are not registered as a team in this dynasty. "
                    "Please pass a team name explicitly.",
                    ephemeral=True,
                )
                return
        elif team not in bot_ref.valid_teams:
            await interaction.response.send_message(
                f"Unknown team: {team}.", ephemeral=True
            )
            return

        log.debug(
            "Guild %d: /request show — user=%s team=%r",
            interaction.guild_id, interaction.user, team,
        )

        matching = [r for r in state.requests if r.team_a == team or r.team_b == team]
        await interaction.response.send_message(fmt_request_show(team, matching))

    @request_show.autocomplete("team")
    async def show_team_autocomplete(
        interaction: discord.Interaction, current: str
    ) -> list[app_commands.Choice[str]]:
        choices = []
        if "all".startswith(current.lower()):
            choices.append(app_commands.Choice(name="all", value="all"))
        choices += [
            app_commands.Choice(name=t, value=t)
            for t in sorted(bot_ref.valid_teams)
            if current.lower() in t.lower()
        ]
        return choices[:25]

    tree.add_command(request_group)
