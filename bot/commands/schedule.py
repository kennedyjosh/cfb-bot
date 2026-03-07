"""/schedule and /schedule show commands."""

from __future__ import annotations

import discord
from discord import app_commands

from bot.formatting import fmt_schedule_result, fmt_schedule_show
from solver.model import SolverInput, Team
from solver.scheduler import solve


def register(tree: app_commands.CommandTree, bot_ref) -> None:
    schedule_group = app_commands.Group(
        name="schedule", description="Run or view the non-conference schedule."
    )

    @schedule_group.command(
        name="run",
        description="Run the solver and post the full schedule results.",
    )
    async def schedule_run(interaction: discord.Interaction) -> None:
        if not await bot_ref.check_admin(interaction):
            return

        state = bot_ref.get_guild_state(interaction.guild_id)

        if not state.requests:
            await interaction.response.send_message(
                "No requests have been added. Use /request add to add games before running the schedule.",
                ephemeral=True,
            )
            return

        human_teams = set(bot_ref.get_human_teams(interaction.guild_id).keys())
        missing = state.teams_missing_conf_schedule(human_teams)
        if missing:
            missing_str = ", ".join(missing)
            await interaction.response.send_message(
                f"Cannot run schedule: no conference schedule found for the following teams: "
                f"{missing_str}. Use /conference_schedule to enter their schedules first.",
                ephemeral=True,
            )
            return

        # Build solver input
        teams: dict[str, Team] = {}
        for team_name, weeks in state.conference_schedules.items():
            teams[team_name] = Team(
                name=team_name,
                conference_weeks=frozenset(weeks),
                is_cpu=False,
            )

        solver_input = SolverInput(teams=teams, requests=state.requests)
        result = solve(solver_input)
        state.last_result = result

        msg = fmt_schedule_result(result)
        if bot_ref.admin_warning(interaction.guild_id):
            msg = bot_ref.admin_warning(interaction.guild_id) + "\n\n" + msg

        await interaction.response.send_message(msg)

    @schedule_group.command(
        name="show",
        description="Display the non-conference schedule for a single team.",
    )
    @app_commands.describe(team="The team to look up (from the official team list).")
    async def schedule_show(interaction: discord.Interaction, team: str) -> None:
        if not await bot_ref.check_admin(interaction):
            return

        if team not in bot_ref.valid_teams:
            await interaction.response.send_message(
                f"Unknown team: {team}. Team must be from the official team list.",
                ephemeral=True,
            )
            return

        state = bot_ref.get_guild_state(interaction.guild_id)

        if state.last_result is None:
            await interaction.response.send_message(
                "No schedule has been generated yet. Run /schedule run first.",
                ephemeral=True,
            )
            return

        team_assignments = [
            a
            for a in state.last_result.assignments
            if a.request.team_a == team or a.request.team_b == team
        ]

        msg = fmt_schedule_show(team, team_assignments)
        if bot_ref.admin_warning(interaction.guild_id):
            msg = bot_ref.admin_warning(interaction.guild_id) + "\n\n" + msg

        await interaction.response.send_message(msg)

    @schedule_show.autocomplete("team")
    async def team_autocomplete(
        interaction: discord.Interaction, current: str
    ) -> list[app_commands.Choice[str]]:
        matches = [
            app_commands.Choice(name=t, value=t)
            for t in sorted(bot_ref.valid_teams)
            if current.lower() in t.lower()
        ]
        return matches[:25]

    tree.add_command(schedule_group)
