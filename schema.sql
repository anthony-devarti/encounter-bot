PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS guild_config (
  guild_id INTEGER PRIMARY KEY,
  updated_at TEXT NOT NULL
);

-- Maps numeric region IDs (used in sheet/tab names) to display names.
CREATE TABLE IF NOT EXISTS region (
  guild_id INTEGER NOT NULL,
  region_id INTEGER NOT NULL,
  region_name TEXT NOT NULL,
  sort_order INTEGER NOT NULL,
  PRIMARY KEY (guild_id, region_id),
  FOREIGN KEY(guild_id) REFERENCES guild_config(guild_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS table_def (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  guild_id INTEGER NOT NULL,
  group_key TEXT NOT NULL,          -- encounter_type, encounter, reward
  region_id INTEGER,                -- NULL means default (no region)
  type_key TEXT,                    -- NULL for encounter_type
  roll_mode TEXT NOT NULL,          -- uniform, weight, range
  max_roll INTEGER,                 -- for range mode
  updated_at TEXT NOT NULL,
  UNIQUE(guild_id, group_key, region_id, type_key),
  FOREIGN KEY(guild_id) REFERENCES guild_config(guild_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS table_entry (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  table_id INTEGER NOT NULL,
  min_roll INTEGER,
  max_roll INTEGER,
  weight INTEGER,
  result TEXT NOT NULL,
  sort_order INTEGER NOT NULL,
  FOREIGN KEY(table_id) REFERENCES table_def(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_table_def_lookup
ON table_def (guild_id, group_key, region_id, type_key);

CREATE INDEX IF NOT EXISTS idx_region_lookup
ON region (guild_id, sort_order, region_id);
