# bot.py
from io import BytesIO
import os
from download import build_workbook_bytes
import aiohttp
import aiosqlite
import discord
from discord import app_commands

from config import DISCORD_TOKEN, DB_PATH
from db import init_db
from importer import import_workbook_bytes
from roller import roll_from_table
from region_ui import RegionSelectView
from config import README_URL
from delete_cmd import IrreversibleDeleteView, WARNING_TEXT_STAGE_1


INTENTS = discord.Intents.default()
TEMPLATE_PATH = os.path.join("Templates", "EncounterBotTemplate.xlsx")

class EncounterBot(discord.Client):
    def __init__(self):
        super().__init__(intents=INTENTS)
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        await init_db(DB_PATH)
        await self.tree.sync()


client = EncounterBot()

### Permissioning ###
def _is_admin(interaction: discord.Interaction) -> bool:
    user = interaction.user
    if not user or not isinstance(user, discord.Member):
        return False
    return user.guild_permissions.administrator
### End Permissioning ###

###
### Helper Functions ###
async def get_regions(db: aiosqlite.Connection, guild_id: int) -> list[tuple[int, str]]:
    cur = await db.execute(
        """
        SELECT region_id, region_name
        FROM region
        WHERE guild_id = ?
        ORDER BY sort_order ASC, region_id ASC
        """,
        (guild_id,),
    )
    rows = await cur.fetchall()
    return [(int(r["region_id"]), r["region_name"]) for r in rows]

async def get_region_name(db: aiosqlite.Connection, guild_id: int, region_id: int) -> str | None:
    cur = await db.execute(
        """
        SELECT region_name
        FROM region
        WHERE guild_id = ? AND region_id = ?
        """,
        (guild_id, region_id),
    )
    row = await cur.fetchone()
    return row["region_name"] if row else None

async def roll_encounter_embed(
    db: aiosqlite.Connection,
    guild_id: int,
    region: str | None,
) -> discord.Embed:
    """
    Rolls:
      - encounter_type (for the region)
      - encounter (for the region + type)
      - reward (for the region + type)
    """
    enc_type, enc_type_meta = await roll_from_table(db, guild_id, "encounter_type", region, None)
    encounter, enc_meta = await roll_from_table(db, guild_id, "encounter", region, enc_type)
    reward, rew_meta = await roll_from_table(db, guild_id, "reward", region, enc_type)

    region_label = None
    if region is not None:
        region_label = await get_region_name(db, guild_id, region)

    title = "Random Encounter" if region_label is None else f"Random Encounter: {region_label}"
    embed = discord.Embed(title=title)
    embed.add_field(name="Type", value=enc_type, inline=True)
    embed.add_field(name="Encounter", value=encounter, inline=False)
    embed.add_field(name="Reward", value=reward, inline=False)
    embed.set_footer(text=f"Type: {enc_type_meta} | Encounter: {enc_meta} | Reward: {rew_meta}")
    return embed

# Check for existing data
async def db_has_any_tables(db: aiosqlite.Connection, guild_id: int) -> bool:
    cur = await db.execute(
        "SELECT 1 FROM table_def WHERE guild_id = ? LIMIT 1",
        (guild_id,),
    )
    row = await cur.fetchone()
    return row is not None

### End of Helper Functions ###
###

###
### Slash Commands ###

#import a database file
@client.tree.command(name="import", description="Import encounter and reward tables from an XLSX file.")
@app_commands.describe(file="XLSX workbook exported from the template")
async def import_cmd(interaction: discord.Interaction, file: discord.Attachment):
    if not interaction.guild_id:
        await interaction.response.send_message("This command must be used in a server.", ephemeral=True)
        return
    if not _is_admin(interaction):
        await interaction.response.send_message("Admin permission required.", ephemeral=True)
        return
    if not file.filename.lower().endswith(".xlsx"):
        await interaction.response.send_message("Upload an .xlsx file.", ephemeral=True)
        return

    await interaction.response.defer(ephemeral=True)

    # Download attachment bytes
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(file.url) as resp:
                if resp.status != 200:
                    await interaction.followup.send(f"Failed to download attachment. HTTP {resp.status}", ephemeral=True)
                    return
                data = await resp.read()
    except Exception as e:
        await interaction.followup.send(f"Failed to download attachment: {e}", ephemeral=True)
        return

    # Import into SQLite
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        counts, errors = await import_workbook_bytes(db, interaction.guild_id, data)

    if errors:
        # High-signal hints for the most common mistakes
        hint_lines = [
            "**✅ What to check**",
            "- Tab names must match the template exactly (capitalization + spacing).",
            "- Header row must be on row 1.",
            "- If using regions: include a tab named `Regions` with `region_id` and `region_name`.",
            "- If `Regions` exists, region tabs must be named like: `Encounter Types - 1`, `Encounter - 1 - Combat`, `Reward - 1 - Combat`.",
            f"- Workbook format help: {README_URL}",
            "",
            "**Validation errors:**",
        ]

        # List errors (cap to avoid message length issues)
        error_lines = []
        for err in errors[:15]:
            where = f"{err.tab}"
            if err.row:
                where += f" row {err.row}"
            error_lines.append(f"- {where}: {err.message}")

        if len(errors) > 15:
            error_lines.append(f"- … plus {len(errors) - 15} more")

        await interaction.followup.send(
            "**❌ Import failed. No changes were made.**\n\n"
            + "\n".join(hint_lines + error_lines),
            ephemeral=True,
        )
        return


    region_count = counts.regions if hasattr(counts, "regions") else 0
    region_line = f"- Regions: {region_count}\n" if region_count > 0 else "- Regions: 0 (default tables)\n"

    await interaction.followup.send(
        "**✅ Import succeeded**\n"
        f"{region_line}"
        f"- Encounter types: {counts.encounter_types}\n"
        f"- Encounter entries: {counts.encounter_entries}\n"
        f"- Reward entries: {counts.reward_entries}",
        ephemeral=True,
    )

# Generates an Encounter
@client.tree.command(name="encounter", description="Roll a random encounter and reward.")
async def encounter_cmd(interaction: discord.Interaction):
    if not interaction.guild_id:
        await interaction.response.send_message("This command must be used in a server.", ephemeral=True)
        return

    await interaction.response.defer()

    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        regions = await get_regions(db, interaction.guild_id)  # list[tuple[int,str]]

    async def on_pick(pick_interaction: discord.Interaction, region_id: int):
        async with aiosqlite.connect(DB_PATH) as db2:
            db2.row_factory = aiosqlite.Row
            embed = await roll_encounter_embed(db2, interaction.guild_id, region_id)
        await pick_interaction.response.edit_message(content=None, embed=embed, view=None)

    if len(regions) == 1:
        region_id = regions[0][0]
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            embed = await roll_encounter_embed(db, interaction.guild_id, region_id)
        await interaction.followup.send(embed=embed)
        return

    view = RegionSelectView(regions=regions, on_pick=on_pick)
    await interaction.followup.send("Pick a region:", view=view, ephemeral=True)

# Download the current encounter tables
DOWNLOAD_FALLBACK_TEMPLATE_PATH = os.path.join("Templates", "EncounterBotTemplate.xlsx")
@client.tree.command(name="download", description="Download the current encounters workbook.")
async def download_cmd(interaction: discord.Interaction):
    if not interaction.guild_id:
        await interaction.response.send_message("This command must be used in a server.", ephemeral=True)
        return

    await interaction.response.defer(ephemeral=True)

    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row

        if not await db_has_any_tables(db, interaction.guild_id):
            # DB is empty: serve the template, no exporter call
            if not os.path.exists(DOWNLOAD_FALLBACK_TEMPLATE_PATH):
                await interaction.followup.send(
                    f"No data imported yet, and template file is missing:\n`{DOWNLOAD_FALLBACK_TEMPLATE_PATH}`",
                    ephemeral=True,
                )
                return

            await interaction.followup.send(
                content="No encounters have been imported yet. Here’s the blank template.",
                file=discord.File(DOWNLOAD_FALLBACK_TEMPLATE_PATH, filename="EncounterBotTemplate.xlsx"),
                ephemeral=True,
            )
            return

        # DB has data: export workbook
        xlsx_bytes = await build_workbook_bytes(db, interaction.guild_id)

    # send exported bytes
    await interaction.followup.send(
        content="Here’s the current workbook from the database.",
        file=discord.File(fp=BytesIO(xlsx_bytes), filename="EncounterBotWorkbook.xlsx"),
        ephemeral=True,
    )

    if not interaction.guild_id:
        await interaction.response.send_message("This command must be used in a server.", ephemeral=True)
        return
    if not _is_admin(interaction):
        await interaction.response.send_message("Admin permission required.", ephemeral=True)
        return

    await interaction.response.defer(ephemeral=True)

    try:
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            xlsx_bytes = await build_workbook_bytes(db, interaction.guild_id)
    except Exception as e:
        await interaction.followup.send(f"Download failed: {e}", ephemeral=True)
        return

    file = discord.File(fp=BytesIO(xlsx_bytes), filename="encounter_tables.xlsx")
    await interaction.followup.send(content="It is recommended to keep the download of the working file saved locally, in case you need to roll back changes later", file=file, ephemeral=True)

# Download the empty template file
@client.tree.command(name="template", description="Download a template with instructions on how to fill it in.")
async def template_cmd(interaction: discord.Interaction):
    if not os.path.exists(TEMPLATE_PATH):
        await interaction.response.send_message(
            f"Template file not found on server:\n`{TEMPLATE_PATH}`",
            ephemeral=True,
        )
        return

    await interaction.response.send_message(
        content="Here's the template workbook. Fill it out, then upload it using **/import**.",
        file=discord.File(TEMPLATE_PATH, filename="EncounterBotTemplate.xlsx"),
        ephemeral=True,
    )
    
# Delete the existing database (with a warning)
@client.tree.command(name="irreversably_delete", description="Permanently and irreversably delete the encounter table.",)
async def irreversably_delete_cmd(interaction: discord.Interaction):
    if not interaction.guild_id:
        await interaction.response.send_message("This command must be used in a server.", ephemeral=True)
        return

    # You said you'll manage access via Discord command permissions (GM role), so no code check here.

    view = IrreversibleDeleteView(
        requester_id=interaction.user.id,
        guild_id=interaction.guild_id,
        db_path=DB_PATH,
    )
    await interaction.response.send_message(WARNING_TEXT_STAGE_1, view=view, ephemeral=True)

# Help Explain the bot's usage
@client.tree.command(name="help", description="Learn to use the encounter bot.")
async def help_cmd(interaction: discord.Interaction):
    embed = discord.Embed(title="Encounter Bot Help")

    embed.add_field(
        name="Quick Start",
        value=(
            "1) Run **/import** and upload your XLSX encounter workbook.\n"
            "2) Run **/encounter** to roll an encounter.\n"
            "If multiple regions exist, you'll pick one (buttons up to 5, dropdown for 6+).\n"
            "3) Run **/download** to export the current tables as XLSX for editing. \n"
            "4) Run **/template** to download a blank export table with setup instructions \n"
            "5) Run **/irreversably_delete** to delete all encounter tables. You better be sure this is what you want to do\n \n"
            
            "To edit your encounter tables, just download, edit the file in your editor of choice then upload your changed file.\n"
            "It's up to you to make sure that you keep the previous version of the tables in case you need to revert them."
        ),
        inline=False,
    )

    embed.add_field(
        name="Commands",
        value=(
            "**/import** (admin only)\n"
            "Upload an XLSX workbook and import it into the bot.\n\n"
            "**/download** (admin only)\n"
            "Download the currently imported workbook.\n\n"
            "**/encounter**\n"
            "Roll an encounter + matching reward.\n\n"
            "**/help**\n"
            "Show this help message."
        ),
        inline=False,
    )

    embed.add_field(
        name="XLSX Format (Default, no regions)",
        value=(
            "Tabs:\n"
            "- `Encounter Types`\n"
            "- `Encounter - <Type>`\n"
            "- `Reward - <Type>`\n\n"
            "Columns:\n"
            "- Types tab: `type`\n"
            "- Encounter/Reward tabs: `result`"
        ),
        inline=False,
    )

    embed.add_field(
        name="XLSX Format (Regions)",
        value=(
            "Tabs:\n"
            "- `Encounter Types - <Region>`\n"
            "- `Encounter - <Region> - <Type>`\n"
            "- `Reward - <Region> - <Type>`\n\n"
            "Columns:\n"
            "- Types tab: `type`\n"
            "- Encounter/Reward tabs: `result`"
        ),
        inline=False,
    )
    
    embed.add_field(
        name="More Detailed Help",
        value=f"[Open README]({README_URL})",
        inline=False,
    )


    embed.set_footer(text="Tip: keep header row on row 1, and keep tab names exact.")
    await interaction.response.send_message(embed=embed, ephemeral=True)

### End Slash Commands ###
###

if __name__ == "__main__":
    client.run(DISCORD_TOKEN)
