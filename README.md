# Encounter Bot

A Discord bot that rolls **random encounters** (and matching rewards) from a spreadsheet workbook.

No LLMs. No web integrations. No complex config UI. Your workbook *is* the config.

## Features

- ✅ Roll encounters from curated tables
- ✅ Rewards automatically match the encounter type (no extra reward-type roll)
- ✅ Optional **regions** (buttons up to 5, dropdown if 6+)
- ✅ Upload tables using `/import` (XLSX)
- ✅ Download current tables using `/download`
- ✅ Download a blank annotated template using `/template`
- ✅ “Two-click confirmation” permanent delete command (`/irreversably_delete`)
- ✅ Simple permissions: server owners restrict GM commands via Discord settings

## How It Works

When you run `/encounter`, the bot rolls:

1. **Encounter Type** from `Encounter Types - <region_id>`
2. **Encounter** from `Encounter - <region_id> - <Type>`
3. **Reward** from `Reward - <region_id> - <Type>`

Encounter type drives the reward.

## Commands

### Player Commands

- **`/encounter`**  
  Rolls an encounter and matching reward.  
  If regions exist, you’ll pick a region first.

- **`/help`**  
  Shows short usage instructions and links to this README.

### GM/Admin Commands

- **`/import`**  
  Upload an XLSX workbook and import it into the bot database.

- **`/download`**  
  Downloads the currently stored workbook (what’s in the DB).  
  If nothing has been imported yet, it downloads the template workbook instead.

- **`/template`**  
  Downloads the blank template workbook shipped with the project.

- **`/irreversably_delete`**  
  Permanently deletes all imported encounter data for this server.  
  Requires 2 confirmation clicks.

## Workbook Format (XLSX)

### Regional Workbook Layout (Recommended)

This is the current standard layout. It avoids Excel’s 31-character sheet name limit and supports long region names cleanly.

#### Required Sheet: `Regions`

| region_id | region_name |
|---:|---|
| 1 | The Grassy Peninsula |
| 2 | The Northlands |

Rules:

- `region_id` must be a **positive integer**
- `region_name` is what appears in Discord UI

#### Required Sheets Per Region

For each `region_id = N` in `Regions`, add:

- `Encounter Types - N`
- `Encounter - N - <Type>` (one tab per type)
- `Reward - N - <Type>` (one tab per type)

Example types: `Combat`, `Social`, `Travel`

If your type sheet includes:

- Combat
- Social
- Travel

Then you must have all of the following (for each region):

- `Encounter - 1 - Combat`
- `Encounter - 1 - Social`
- `Encounter - 1 - Travel`

and:

- `Reward - 1 - Combat`
- `Reward - 1 - Social`
- `Reward - 1 - Travel`

**Important:** Type names are case and spacing sensitive because they must match the tab name exactly.

### Non-Regional Workbook Layout (Optional)

If you do not want regions, delete the `Regions` tab and use:

- `Encounter Types`
- `Encounter - <Type>`
- `Reward - <Type>`

## Column Rules

- All headers must be on **row 1**
- Do not rename required columns
- You can add extra columns (notes, tags, etc.) and the bot will ignore them

## Roll Modes

Each sheet supports **one** roll mode. The bot auto-detects which mode is being used based on the columns present.

### Uniform Mode (equal chance)

Use only:

**Encounter Types sheet**

- `type`

**Encounter / Reward sheet**

- `result`

Every row has equal probability.

### Weighted Mode

Use:

**Encounter Types sheet**

- `weight` (positive integer)
- `type`

**Encounter / Reward sheet**

- `weight` (positive integer)
- `result`

Higher weight means more likely.

### Range Mode (dice table)

Use:

**Encounter Types sheet**

- `min` (int)
- `max` (int)
- `type`

**Encounter / Reward sheet**

- `min` (int)
- `max` (int)
- `result`

Rules:

- ranges must not overlap
- `min <= max`

Example:

| min | max | result |
|---:|---:|---|
| 1 | 40 | Bandits |
| 41 | 70 | Merchant |
| 71 | 100 | Monster |

### Important Rule: Don’t mix modes

Don’t mix columns. For example:

- if a sheet has any `weight` values, it’s treated as weighted mode
- if a sheet has `min/max`, it’s treated as range mode

## Recommended Workflow

1. Run **`/template`** and download the workbook template.
2. Fill it out in Excel or Google Sheets (export to XLSX).
3. Upload it with **`/import`**
4. Test with **`/encounter`**
5. Export current state with **`/download`** (useful for backups)

## Command Permissions (GM Only)

By default, Discord may show slash commands to everyone in the server. This bot expects server owners/admins to restrict GM/admin commands via Discord’s command permissions.

### Restrict commands to the `GM` role

1. In Discord, open **Server Settings**
2. Go to **Integrations**
3. Select the bot under **Bots and Apps**
4. Open **Commands**
5. For each GM/admin command (recommended):
   - `/import`
   - `/download`
   - `/template`
   - `/irreversably_delete`

Disable access for `@everyone` and enable access for `GM`.

After this:

- only users with the **GM** role will see those commands
- players won’t see them or be able to run them

## Template Workbook

This repository includes a workbook at:

- `./Templates/EncounterBotTemplate.xlsx`

It includes:

- a `README` sheet with instructions
- header comments explaining required columns
- example regions, types, encounters, and rewards
