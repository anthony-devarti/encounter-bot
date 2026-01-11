from __future__ import annotations

import discord
import aiosqlite

WARNING_TEXT_STAGE_1 = (
    "## Danger\n"
    "This will permanently delete **all encounter table data** for this server.\n"
    "This cannot be undone.\n\n"
    "Click **I understand** to unlock the final delete button."
)

WARNING_TEXT_STAGE_2 = (
    "## Final confirmation\n"
    "Last chance. If you should not be doing this and don't have the data elsewhere, everyone will be REALLY mad at you.\n"
    "Click **Delete now** to permanently delete the encounter tables for this server.\n"
    "This cannot be undone."
)


async def delete_guild_data(db_path: str, guild_id: int) -> None:
    """
    Irreversibly deletes all stored data for a guild.
    Leaves the SQLite file intact.
    """
    async with aiosqlite.connect(db_path) as db:
        await db.execute("BEGIN")
        try:
            await db.execute("DELETE FROM region WHERE guild_id = ?", (guild_id,))
            await db.execute("DELETE FROM table_def WHERE guild_id = ?", (guild_id,))
            await db.execute("DELETE FROM guild_config WHERE guild_id = ?", (guild_id,))
            await db.commit()
        except Exception:
            await db.rollback()
            raise


class IrreversibleDeleteView(discord.ui.View):
    def __init__(self, *, requester_id: int, guild_id: int, db_path: str):
        super().__init__(timeout=60)
        self.requester_id = requester_id
        self.guild_id = guild_id
        self.db_path = db_path
        self.stage = 1

        # Stage 2 starts disabled
        for item in self.children:
            if isinstance(item, discord.ui.Button) and item.custom_id == "delete_stage2":
                item.disabled = True

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        # Only the original requester can click buttons.
        return interaction.user.id == self.requester_id

    @discord.ui.button(
        label="I understand",
        style=discord.ButtonStyle.danger,
        custom_id="delete_stage1",
    )
    async def stage1(self, interaction: discord.Interaction, button: discord.ui.button):
        self.stage = 2
        button.disabled = True

        for item in self.children:
            if isinstance(item, discord.ui.Button) and item.custom_id == "delete_stage2":
                item.disabled = False

        await interaction.response.edit_message(content=WARNING_TEXT_STAGE_2, view=self)

    @discord.ui.button(
        label="Delete now",
        style=discord.ButtonStyle.danger,
        custom_id="delete_stage2",
        disabled=True,
    )
    async def stage2(self, interaction: discord.Interaction, button: discord.ui.button):
        await delete_guild_data(self.db_path, self.guild_id)

        # Disable buttons after execution
        for item in self.children:
            if isinstance(item, discord.ui.Button):
                item.disabled = True

        await interaction.response.edit_message(
            content="✅ Deleted all encounter table data for this server.",
            view=self,
        )
        self.stop()

    @discord.ui.button(
        label="Cancel",
        style=discord.ButtonStyle.secondary,
        custom_id="delete_cancel",
    )
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.button):
        for item in self.children:
            if isinstance(item, discord.ui.button):
                item.disabled = True
        await interaction.response.edit_message(content="Cancelled. No changes were made.", view=self)
        self.stop()
