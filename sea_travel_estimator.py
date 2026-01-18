import math


HEX_MILES = 3

# Hexes per day by vessel and conditions
SAILBOAT_HEX_PER_DAY = 16        # calm or rough
ROWBOAT_CALM_HEX_PER_DAY = 4     # 8 hours of rowing
ROWBOAT_ROUGH_HEX_PER_DAY = 2    # heavily penalized


def calculate_sea_travel(
    vessel_type: str,
    calm_hexes: int,
    rough_hexes: int,
    unexplored_hexes: int,
):
    """
    Calculates sea travel time, ration usage, and encounter probability.

    Returns a dict compatible with land travel output.
    """

    total_hexes = calm_hexes + rough_hexes

    # Clamp unexplored
    if unexplored_hexes > total_hexes:
        unexplored_hexes = total_hexes

    # ----- SPEED LOGIC -----

    if vessel_type == "sailboat":
        calm_days = calm_hexes / SAILBOAT_HEX_PER_DAY
        rough_days = rough_hexes / SAILBOAT_HEX_PER_DAY

    elif vessel_type == "rowboat":
        calm_days = calm_hexes / ROWBOAT_CALM_HEX_PER_DAY
        rough_days = rough_hexes / ROWBOAT_ROUGH_HEX_PER_DAY

    else:
        raise ValueError(f"Unknown vessel type: {vessel_type}")

    travel_days = math.ceil(calm_days + rough_days)

    # ----- RATIONS -----
    # Same rule as land: 1 ration per day of travel
    rations_per_character = travel_days

    # ----- ENCOUNTER LOGIC -----
    # 10% per explored hex, 25% per unexplored hex
    explored_hexes = total_hexes - unexplored_hexes

    no_encounter_prob = (0.9 ** explored_hexes) * (0.75 ** unexplored_hexes)
    encounter_probability = 1.0 - no_encounter_prob

    return {
        "travel_days": travel_days,
        "rations_per_character": rations_per_character,
        "encounter_probability": encounter_probability,
        "forced_march_saves": [],        # not applicable at sea
        "forced_hexes_gained": 0,         # not applicable at sea
    }
