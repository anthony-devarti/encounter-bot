import discord
from discord import ui
from sea_travel_estimator import calculate_sea_travel

class SeaVesselView(ui.View):
    def __init__(self):
        super().__init__(timeout=60)

    @ui.button(label="⛵ Sailboat", style=discord.ButtonStyle.primary)
    async def sailboat(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_modal(
            SeaTravelModal(vessel_type="sailboat")
        )

    @ui.button(label="🚣 Rowboat", style=discord.ButtonStyle.secondary)
    async def rowboat(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_modal(
            SeaTravelModal(vessel_type="rowboat")
        )

class SeaEncounterRollView(ui.View):
    def __init__(self, probability: float):
        super().__init__(timeout=60)
        self.probability = probability
        self.used = False

    @ui.button(label="Roll for Random Encounter", emoji="🎲", style=discord.ButtonStyle.danger)
    async def roll(self, interaction: discord.Interaction, button: ui.Button):
        if self.used:
            return

        self.used = True

        import random
        hit = random.random() < self.probability

        msg = (
            "🎲 **A random encounter occurs at sea!**\n"
            "Use `/encounter` to determine what happens."
            if hit
            else "🎲 **No random encounters occur during the voyage.**"
        )

        await interaction.response.send_message(
            msg,
            ephemeral=True
        )


def build_sea_travel_embed(result: dict) -> discord.Embed:
    embed = discord.Embed(title="Sea Travel Estimate")

    embed.add_field(
        name="Travel Time",
        value=f'{result["travel_days"]} day(s)',
        inline=True,
    )

    embed.add_field(
        name="Rations",
        value=f'{result["rations_per_character"]} per character',
        inline=True,
    )

    embed.add_field(
        name="Encounter Risk",
        value=f'{int(result["encounter_probability"] * 100)}% chance',
        inline=False,
    )

    return embed


class SeaTravelModal(ui.Modal):
    calm = ui.TextInput(label="Calm sea hexes", default="0")
    rough = ui.TextInput(label="Rough sea hexes", default="0")
    unexplored = ui.TextInput(label="Unexplored sea hexes", default="0")

    def __init__(self, vessel_type: str):
        super().__init__(title=f"Sea Travel ({vessel_type.title()})")
        self.vessel_type = vessel_type

    async def on_submit(self, interaction: discord.Interaction):
        calm = int(self.calm.value)
        rough = int(self.rough.value)
        unexplored = int(self.unexplored.value)

        total = calm + rough
        if unexplored > total:
            unexplored = total

        result = calculate_sea_travel(
            vessel_type=self.vessel_type,
            calm_hexes=calm,
            rough_hexes=rough,
            unexplored_hexes=unexplored,
        )

        embed = build_sea_travel_embed(result)
        view = SeaEncounterRollView(result["encounter_probability"])

        await interaction.response.send_message(
            embed=embed,
            view=view,
            ephemeral=True,
        )
