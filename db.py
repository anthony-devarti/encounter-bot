import aiosqlite
from pathlib import Path

async def init_db(db_path: str, schema_path: str = "schema.sql") -> None:
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    async with aiosqlite.connect(db_path) as db:
        db.row_factory = aiosqlite.Row
        with open(schema_path, "r", encoding="utf-8") as f:
            await db.executescript(f.read())
        await db.commit()

def connect(db_path: str) -> aiosqlite.Connection:
    return aiosqlite.connect(db_path)
