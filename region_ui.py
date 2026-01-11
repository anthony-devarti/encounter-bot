# region_ui.py
from __future__ import annotations

from typing import List, Callable, Awaitable, Tuple

import discord


RegionItem = Tuple[int, str]  # (region_id, region_name)


class RegionSelectView(discord.ui.View):
    def __init__(
        self,
        regions: List[RegionItem],
        on_pick: Callable[[discord.Interaction, int], Awaitable[None]],
        timeout: float = 60.0,
    ):
        super().__init__(timeout=timeout)
        self.regions = regions
        self.on_pick = on_pick

        if len(regions) <= 5:
            for region_id, region_name in regions:
                self.add_item(_RegionButton(label=region_name, region_id=region_id))
        else:
            self.add_item(_RegionDropdown(options=regions))

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        # Optional: restrict to the user who invoked /encounter
        return True


class _RegionButton(discord.ui.Button):
    def __init__(self, label: str, region_id: int):
        super().__init__(label=label, style=discord.ButtonStyle.primary)
        self.region_id = region_id

    async def callback(self, interaction: discord.Interaction):
        view: RegionSelectView = self.view  # type: ignore
        await view.on_pick(interaction, self.region_id)
        view.stop()


class _RegionDropdown(discord.ui.Select):
    def __init__(self, options: List[RegionItem]):
        super().__init__(
            placeholder="Choose a region...",
            min_values=1,
            max_values=1,
            options=[
                discord.SelectOption(label=region_name, value=str(region_id))
                for region_id, region_name in options
            ],
        )

    async def callback(self, interaction: discord.Interaction):
        view: RegionSelectView = self.view  # type: ignore
        picked_region_id = int(self.values[0])
        await view.on_pick(interaction, picked_region_id)
        view.stop()
