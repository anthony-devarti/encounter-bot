import discord
from discord import ui

from travel_estimator import calculate_travel
from sea_travel_ui import SeaVesselView

# ----- Land Vessel Selection -----
class LandVesselView(ui.View):
    def __init__(self):
        super().__init__(timeout=60)

    @ui.button(label="🚶 On Foot", style=discord.ButtonStyle.primary)
    async def foot(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_modal(
            LandRouteModal(vessel_type="foot")
        )

    @ui.button(label="🐎 Mounted", style=discord.ButtonStyle.secondary)
    async def mount(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_modal(
            LandRouteModal(vessel_type="mount")
        )

# ---------- ENTRY VIEW ----------

class TravelModeView(ui.View):
    def __init__(self):
        super().__init__(timeout=60)

    @ui.button(label="🧭 Land", style=discord.ButtonStyle.primary)
    async def land(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_message(
            "Choose vessel type:",
            view=LandVesselView(),
            ephemeral=True
)

    @ui.button(label="⚓ Sea", style=discord.ButtonStyle.secondary)
    async def sea(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_message(
            "Choose vessel type:",
            view=SeaVesselView(),
            ephemeral=True
)

# ---------- Land MODAL 1 ----------

class LandRouteModal(ui.Modal, title="Land Travel (1/2): Route"):
    total_hexes = ui.TextInput(label="Total hexes", default="0")
    road_hexes = ui.TextInput(label="Road hexes", default="0")
    unexplored_hexes = ui.TextInput(label="Unexplored hexes", default="0")
    
    def __init__(self, vessel_type: str):
        super().__init__()
        self.vessel_type = vessel_type

    async def on_submit(self, interaction: discord.Interaction):
        total = int(self.total_hexes.value)
        road = int(self.road_hexes.value)
        unexplored = int(self.unexplored_hexes.value)

        route_data = {
            "total_hexes": total,
            "road_hexes": road,
            "unexplored_hexes": unexplored,
            "vessel_type": self.vessel_type
        }

        # ----- CASE 1: ALL ROAD -----
        if total == road:
            hex_counts = {"road": road}

            result = calculate_travel(
                hex_counts=hex_counts,
                unexplored_hexes=unexplored,
                explored_road_hexes=road,
                vessel_type=self.vessel_type,
                # vvv not incorporated yet vvv
                forced_hours=0,
            )

            embed = build_travel_embed(result)
            view = EncounterRollView(result["encounter_probability"])

            await interaction.response.send_message(
                embed=embed,
                view=view,
                ephemeral=True,
            )
            return

        # ----- CASE 2: OFF-ROAD EXISTS -----
        off_road_required = total - road

        view = ContinueToOffRoadView(route_data)

        await interaction.response.send_message(
            (
                f"**Route Summary**\n"
                f"- Travel method: **{self.vessel_type}**\n"
                f"- Total hexes: **{total}**\n"
                f"- Road hexes: **{road}**\n"
                f"- Off-road hexes to allocate: **{off_road_required}**\n\n"
                f"Continue to off-road terrain:"
            ),
            view=view,
            ephemeral=True,
        )


# ---------- CONTINUE VIEW ----------

class ContinueToOffRoadView(ui.View):
    def __init__(self, route_data: dict):
        super().__init__(timeout=60)
        self.route_data = route_data

    @ui.button(label="Continue to Off-Road Terrain", style=discord.ButtonStyle.primary)
    async def continue_(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_modal(LandOffRoadModal(self.route_data))


# ---------- MODAL 2 ----------

class LandOffRoadModal(ui.Modal):
    plains = ui.TextInput(label="Plains (easy terrain)", default="0")
    rough = ui.TextInput(label="Forest / Jungle / Sand (rough terrain)", default="0")
    harsh = ui.TextInput(label="Mountains / Swamp / Snow (harsh terrain)", default="0")

    def __init__(self, route_data: dict):
        off_road_required = route_data["total_hexes"] - route_data["road_hexes"]
        super().__init__(
            title=f"Assign {off_road_required} Off-Road Hexes"
        )
        self.route_data = route_data

    async def on_submit(self, interaction: discord.Interaction):
        total = self.route_data["total_hexes"]
        road = self.route_data["road_hexes"]
        unexplored = self.route_data["unexplored_hexes"]

        plains = int(self.plains.value)
        rough = int(self.rough.value)
        harsh = int(self.harsh.value)

        off_road_required = total - road
        off_road_entered = plains + rough + harsh

        # ----- VALIDATION FAILURE -----
        if off_road_entered != off_road_required:
            view = RetryOffRoadView(self.route_data)

            await interaction.response.send_message(
                (
                    f"❌ **Invalid terrain breakdown**\n\n"
                    f"You must allocate exactly **{off_road_required}** off-road hexes.\n"
                    f"You entered **{off_road_entered}**.\n\n"
                    f"Click below to reopen the off-road terrain form."
                ),
                view=view,
                ephemeral=True,
            )
            return

        hex_counts = {
            "road": road,
            "plains": plains,
            "forest": rough,
            "mountains": harsh,
        }

        result = calculate_travel(
            hex_counts=hex_counts,
            unexplored_hexes=unexplored,
            explored_road_hexes=road,
            vessel_type=self.route_data['vessel_type'],
            forced_hours=0,
        )

        embed = build_travel_embed(result)
        view = EncounterRollView(result["encounter_probability"])

        await interaction.response.send_message(
            embed=embed,
            view=view,
            ephemeral=True,
        )


# ---------- RETRY VIEW ----------

class RetryOffRoadView(ui.View):
    def __init__(self, route_data: dict):
        super().__init__(timeout=60)
        self.route_data = route_data

    @ui.button(label="Reopen Off-Road Terrain", style=discord.ButtonStyle.primary)
    async def retry(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_modal(LandOffRoadModal(self.route_data))


# ---------- OUTPUT ----------

def build_travel_embed(result: dict) -> discord.Embed:
    embed = discord.Embed(title="Travel Estimate")

    vessel_type = result.get("vessel_type", "foot")
    if vessel_type == "mount":
        travel_method = "Mounted"
    if vessel_type == "foot":
        travel_method = "On Foot"
    
    embed.add_field(
        name="Travel Method",
        value=travel_method,
        inline=True,
    )
    
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

    if result["forced_march_saves"]:
        embed.add_field(
            name="Forced March",
            value=(
                f'Extra hexes: {result["forced_hexes_gained"]}\n'
                f'CON saves: {", ".join(map(str, result["forced_march_saves"]))}'
            ),
            inline=False,
        )

    embed.add_field(
        name="Encounter Risk",
        value=f'{int(result["encounter_probability"] * 100)}% chance',
        inline=False,
    )

    return embed


# ---------- ROLL BUTTON ----------

class EncounterRollView(ui.View):
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
            "🎲 **A random encounter occurs during the journey!**\n"
            "Use `/encounter` to determine what happens."
            if hit
            else "🎲 **No random encounters occur during the journey.**"
        )

        await interaction.response.send_message(
            msg,
            ephemeral=True
        )
