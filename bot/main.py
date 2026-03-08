"""Discord bot entry point. Initializes the client, registers commands, and starts the bot."""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from pathlib import Path

import discord
from discord import app_commands

from bot.commands import conf, request, schedule, teams
from bot.config import load_guild_config, load_valid_teams
from bot.log import ColoredFormatter, parse_log_level
from bot.formatting import ADMIN_WARNING, NO_PERMISSION
from bot.parsing import parse_display_name
from bot.state import GuildState

log = logging.getLogger(__name__)


@dataclass
class ResolvedMember:
    display_name: str
    team: str
    user_id: int


@dataclass
class UnresolvedMember:
    display_name: str
    is_ignored: bool  # True = matched ignore_regex; False = unparsable


class CFBBot(discord.Client):
    def __init__(self) -> None:
        intents = discord.Intents.default()
        intents.members = True
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)

        self.valid_teams: set[str] = load_valid_teams()

        # Per-guild data
        self._guild_states: dict[int, GuildState] = {}
        self._guild_configs: dict[int, dict] = {}
        self._human_teams: dict[int, dict[str, int]] = {}   # guild_id → {team → user_id}
        self._resolved: dict[int, list[ResolvedMember]] = {}
        self._unresolved: dict[int, list[UnresolvedMember]] = {}

        # Register all commands
        conf.register(self.tree, self)
        request.register(self.tree, self)
        schedule.register(self.tree, self)
        teams.register(self.tree, self)

    async def setup_hook(self) -> None:
        await self.tree.sync()

    async def on_ready(self) -> None:
        log.info("Logged in as %s (id=%s)", self.user, self.user.id)
        for guild in self.guilds:
            await self._init_guild(guild)

    async def on_guild_join(self, guild: discord.Guild) -> None:
        await self._init_guild(guild)

    async def _init_guild(self, guild: discord.Guild) -> None:
        config = load_guild_config(guild.id)
        self._guild_configs[guild.id] = config
        if guild.id not in self._guild_states:
            self._guild_states[guild.id] = GuildState()

        guild_config_path = Path(__file__).parent.parent / "config" / f"{guild.id}.toml"
        if not guild_config_path.exists():
            log.warning(
                "Guild %s (%d): no per-dynasty config found. "
                "Running with defaults. Create config/%d.toml to configure this dynasty.",
                guild.name, guild.id, guild.id,
            )

        await self._scrape_members(guild, config)
        log.info(
            "Guild %s (%d): %d human teams, %d unresolved",
            guild.name,
            guild.id,
            len(self._human_teams.get(guild.id, {})),
            len(self._unresolved.get(guild.id, [])),
        )

    async def _scrape_members(self, guild: discord.Guild, config: dict) -> None:
        name_regex: str = config.get("members", {}).get("name_regex", "^(?P<team>.+)$")
        ignore_regex: str = config.get("members", {}).get("ignore_regex", "inactive")

        human_teams: dict[str, int] = {}
        resolved: list[ResolvedMember] = []
        unresolved: list[UnresolvedMember] = []

        async for member in guild.fetch_members(limit=None):
            if member.bot:
                continue
            try:
                team_name, is_ignored = parse_display_name(
                    member.display_name,
                    name_regex,
                    ignore_regex,
                    self.valid_teams,
                )
            except ValueError as exc:
                log.error("Guild %d: %s — check members.name_regex in config", guild.id, exc)
                return
            if is_ignored:
                log.debug("  ignored:    %s", member.display_name)
                unresolved.append(UnresolvedMember(member.display_name, is_ignored=True))
            elif team_name is None:
                log.debug("  unresolved: %s", member.display_name)
                unresolved.append(UnresolvedMember(member.display_name, is_ignored=False))
            else:
                log.debug("  resolved:   %s → %s", member.display_name, team_name)
                human_teams[team_name] = member.id
                resolved.append(ResolvedMember(member.display_name, team_name, member.id))

        self._human_teams[guild.id] = human_teams
        self._resolved[guild.id] = resolved
        self._unresolved[guild.id] = unresolved

    # ------------------------------------------------------------------
    # Helpers used by command handlers
    # ------------------------------------------------------------------

    def get_guild_state(self, guild_id: int) -> GuildState:
        if guild_id not in self._guild_states:
            self._guild_states[guild_id] = GuildState()
        return self._guild_states[guild_id]

    def get_human_teams(self, guild_id: int) -> dict[str, int]:
        return self._human_teams.get(guild_id, {})

    def get_resolved_members(self, guild_id: int) -> list[ResolvedMember]:
        return self._resolved.get(guild_id, [])

    def get_unresolved_members(self, guild_id: int) -> list[UnresolvedMember]:
        return self._unresolved.get(guild_id, [])

    def admin_warning(self, guild_id: int) -> str:
        """Return the admin warning string if no admin is configured, else empty string."""
        config = self._guild_configs.get(guild_id, {})
        admin_id = config.get("admin", {}).get("id", "")
        return ADMIN_WARNING if not admin_id else ""

    async def check_admin(self, interaction: discord.Interaction) -> bool:
        """Return True if the invoker is authorized, else send an ephemeral error and return False."""
        config = self._guild_configs.get(interaction.guild_id, {})
        admin_id_str: str = config.get("admin", {}).get("id", "")

        if not admin_id_str:
            # No admin configured — allow everyone (warning emitted separately per response)
            return True

        try:
            admin_id = int(admin_id_str)
        except ValueError:
            log.warning("Invalid admin.id in config for guild %d: %r", interaction.guild_id, admin_id_str)
            return True

        member = interaction.user
        if not isinstance(member, discord.Member):
            await interaction.response.send_message(NO_PERMISSION, ephemeral=True)
            return False

        # Check user ID
        if member.id == admin_id:
            return True

        # Check role ID
        if any(role.id == admin_id for role in member.roles):
            return True

        await interaction.response.send_message(NO_PERMISSION, ephemeral=True)
        return False


def run() -> None:
    level = parse_log_level(os.environ.get("LOG_LEVEL", "INFO"))
    handler = logging.StreamHandler()
    handler.setFormatter(ColoredFormatter())
    logging.basicConfig(level=level, handlers=[handler])
    token = os.environ.get("DISCORD_TOKEN")
    if not token:
        raise RuntimeError("DISCORD_TOKEN environment variable is not set.")
    bot = CFBBot()
    bot.run(token)
