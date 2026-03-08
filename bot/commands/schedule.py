"""/schedule and /schedule show commands."""

from __future__ import annotations

import logging
import time

import discord
from discord import app_commands

log = logging.getLogger(__name__)

from bot.formatting import fmt_schedule_result, fmt_schedule_show
from solver.model import SolverInput, SolverResult, Team
from solver.scheduler import assign_home_away, solve


def register(tree: app_commands.CommandTree, bot_ref) -> None:
    schedule_group = app_commands.Group(
        name="schedule", description="Run or view the non-conference schedule."
    )

    @schedule_group.command(
        name="create",
        description="Run the solver and post the full schedule results.",
    )
    async def schedule_create(interaction: discord.Interaction) -> None:
        if not await bot_ref.check_admin(interaction):
            return

        state = bot_ref.get_guild_state(interaction.guild_id)

        log.info(
            "Guild %d: /schedule create — %d requests, %d conf schedules (user=%s)",
            interaction.guild_id, len(state.requests),
            len(state.conference_schedules), interaction.user,
        )

        if not state.requests:
            log.warning("Guild %d: /schedule create rejected — no requests", interaction.guild_id)
            await interaction.response.send_message(
                "No requests have been added. Use /request add to add games before running the schedule.",
                ephemeral=True,
            )
            return

        human_teams = set(bot_ref.get_human_teams(interaction.guild_id).keys())
        missing = state.teams_missing_conf_schedule(human_teams)
        if missing:
            log.warning(
                "Guild %d: /schedule create rejected — missing conf schedules: %s",
                interaction.guild_id, ", ".join(missing),
            )
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
                conference_home_games=state.conference_home_games.get(team_name, 0),
            )

        # (1) Log each human team's nc_cap and conference weeks
        log.debug("Guild %d: /schedule create — human teams in solver input:", interaction.guild_id)
        for team_name, team in sorted(teams.items()):
            log.debug(
                "  %s: nc_cap=%d, conf_weeks=%s",
                team_name, team.nc_cap, sorted(team.conference_weeks),
            )

        # (2) Log CPU teams that will be auto-registered by the solver
        cpu_teams = sorted({
            name
            for req in state.requests
            for name in (req.team_a, req.team_b)
            if name not in teams
        })
        if cpu_teams:
            log.debug(
                "Guild %d: /schedule create — CPU teams auto-registered: %s",
                interaction.guild_id, ", ".join(cpu_teams),
            )

        solver_input = SolverInput(teams=teams, requests=state.requests)

        # (3) Log solver wall-clock time
        t0 = time.monotonic()
        result = solve(solver_input)
        elapsed = time.monotonic() - t0
        log.debug("Guild %d: /schedule create — solver took %.3fs", interaction.guild_id, elapsed)

        # Assign home/away for all scheduled games
        assigned = assign_home_away(result.assignments, teams)
        result = SolverResult(assignments=assigned, unscheduled=result.unscheduled)

        state.last_result = result

        log.info(
            "Guild %d: /schedule create — %d/%d requests fulfilled, %d unscheduled",
            interaction.guild_id,
            len(result.assignments), len(state.requests), len(result.unscheduled),
        )

        # (4) Log each fulfilled assignment
        for a in sorted(result.assignments, key=lambda a: (a.week, a.request.team_a)):
            log.debug(
                "  Week %d: %s vs. %s (home=%s)",
                a.week, a.request.team_a, a.request.team_b, a.home_team or "unset",
            )

        # (5) Log unscheduled requests
        for r in result.unscheduled:
            log.debug("  unscheduled: %s vs. %s", r.team_a, r.team_b)

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

        log.debug(
            "Guild %d: /schedule show — team=%r (user=%s)",
            interaction.guild_id, team, interaction.user,
        )

        if team not in bot_ref.valid_teams:
            log.warning(
                "Guild %d: /schedule show rejected — unknown team %r (user=%s)",
                interaction.guild_id, team, interaction.user,
            )
            await interaction.response.send_message(
                f"Unknown team: {team}. Team must be from the official team list.",
                ephemeral=True,
            )
            return

        state = bot_ref.get_guild_state(interaction.guild_id)

        if state.last_result is None:
            log.warning(
                "Guild %d: /schedule show rejected — no schedule generated yet (user=%s)",
                interaction.guild_id, interaction.user,
            )
            await interaction.response.send_message(
                "No schedule has been generated yet. Run /schedule create first.",
                ephemeral=True,
            )
            return

        team_assignments = [
            a
            for a in state.last_result.assignments
            if a.request.team_a == team or a.request.team_b == team
        ]

        log.debug(
            "Guild %d: /schedule show — %s has %d NC game(s)",
            interaction.guild_id, team, len(team_assignments),
        )

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
