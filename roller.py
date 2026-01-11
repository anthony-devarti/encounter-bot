# roller.py
from __future__ import annotations

import random
from typing import Optional, Tuple

import aiosqlite


def _pick_weighted(items: list[tuple[str, int]]) -> str:
    total = sum(w for _, w in items)
    r = random.randint(1, total)
    acc = 0
    for val, w in items:
        acc += w
        if r <= acc:
            return val
    return items[-1][0]


async def roll_from_table(
    db: aiosqlite.Connection,
    guild_id: int,
    group_key: str,
    region_id: Optional[int],
    type_key: Optional[str],
) -> Tuple[str, str]:
    cur = await db.execute(
        """
        SELECT id, roll_mode, max_roll
        FROM table_def
        WHERE guild_id = ?
          AND group_key = ?
          AND region_id IS ?
          AND type_key IS ?
        """,
        (guild_id, group_key, region_id, type_key),
    )
    t = await cur.fetchone()
    if not t:
        raise RuntimeError(f"Missing table: {group_key} region={region_id} type={type_key}")

    table_id = t["id"]
    mode = t["roll_mode"]
    max_roll = t["max_roll"]

    cur = await db.execute(
        """
        SELECT min_roll, max_roll, weight, result
        FROM table_entry
        WHERE table_id = ?
        ORDER BY sort_order ASC
        """,
        (table_id,),
    )
    rows = await cur.fetchall()
    if not rows:
        raise RuntimeError("Table has no entries")

    if mode == "uniform":
        result = random.choice(rows)["result"]
        return result, "uniform"

    if mode == "weight":
        items = [(r["result"], r["weight"]) for r in rows if r["weight"] is not None]
        if not items:
            raise RuntimeError("Weight mode table has no valid weights")
        result = _pick_weighted(items)
        return result, "weight"

    if mode == "range":
        if not max_roll:
            raise RuntimeError("Range mode table missing max_roll")
        roll = random.randint(1, int(max_roll))
        for r in rows:
            mi = r["min_roll"]
            ma = r["max_roll"]
            if mi is None or ma is None:
                continue
            if mi <= roll <= ma:
                return r["result"], f"range d{max_roll}={roll}"
        raise RuntimeError(f"No range matched roll {roll}")

    raise RuntimeError(f"Unknown roll_mode {mode}")
