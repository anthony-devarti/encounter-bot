import math

HEXES_PER_DAY = {
    "road": 8,
    "plains": 6,
    "forest": 4,
    "jungle": 4,
    "sand": 4,
    "swamp": 3,
    "snow": 3,
    "mountains": 2,
    "calm_water": 24,
    "rough_water": 12,
}

HOURS_PER_DAY = 8
ENCOUNTER_CHANCE = 0.25


def calculate_travel(
    hex_counts: dict,
    unexplored_hexes: int,
    explored_road_hexes: int,
    forced_hours: int = 0,
):
    """
    hex_counts: terrain -> hexes traveled
    unexplored_hexes: total unexplored hexes on route
    explored_road_hexes: explored road hexes on route
    forced_hours: extra travel hours beyond 8 (land only)
    """

    # ---------- NORMAL TRAVEL TIME ----------
    normal_days = 0.0
    for terrain, hexes in hex_counts.items():
        if hexes <= 0:
            continue
        speed = HEXES_PER_DAY[terrain]
        normal_days += hexes / speed

    total_days = math.ceil(normal_days)

    # ---------- FORCED MARCH MOVEMENT ----------
    forced_hexes = 0.0
    remaining_hours = forced_hours

    # Apply forced march conservatively: slowest terrain first
    for terrain, hexes in sorted(
        hex_counts.items(),
        key=lambda t: HEXES_PER_DAY[t[0]]
    ):
        if remaining_hours <= 0:
            break

        hexes_per_hour = HEXES_PER_DAY[terrain] / HOURS_PER_DAY
        possible = hexes_per_hour * remaining_hours
        used = min(hexes, possible)

        forced_hexes += used
        remaining_hours -= used / hexes_per_hour

    forced_hexes = math.floor(forced_hexes)

    # ---------- ENCOUNTER CHECKS ----------
    total_hexes = sum(hex_counts.values())
    road_hexes = hex_counts.get("road", 0)
    off_road_hexes = total_hexes - road_hexes

    # Assume unexplored hexes are off-road
    explored_off_road_hexes = max(off_road_hexes - unexplored_hexes, 0)
    road_checks = explored_road_hexes // 3

    total_checks = unexplored_hexes + explored_off_road_hexes + road_checks

    # Cap encounters to one per day
    effective_checks = min(total_checks, total_days)

    encounter_probability = 1 - ((1 - ENCOUNTER_CHANCE) ** effective_checks)

    # ---------- FORCED MARCH EXHAUSTION ----------
    exhaustion_saves = []
    for hour in range(1, forced_hours + 1):
        exhaustion_saves.append(10 + hour)

    return {
        "travel_days": total_days,
        "forced_hexes_gained": forced_hexes,
        "rations_per_character": total_days,
        "encounter_checks": total_checks,
        "encounter_probability": round(encounter_probability, 4),
        "forced_march_saves": exhaustion_saves,
    }

#testing
if __name__ == "__main__":
    result = calculate_travel(
        hex_counts={
            "road": 5,
            "plains": 3,
            "forest": 4,
            "mountains": 2,
        },
        unexplored_hexes=3,
        explored_road_hexes=2,
        forced_hours=2,
    )

    for k, v in result.items():
        print(f"{k}: {v}")
