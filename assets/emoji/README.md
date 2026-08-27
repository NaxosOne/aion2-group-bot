# Kisk emoji pack

Icons for the roles and the event types, drawn to stay readable at Discord's
emoji size (about 24 px). PNG files are 128×128 with a transparent
background; the `.svg` next to each one is the editable source.

| File | Used for | `.env` variable |
| --- | --- | --- |
| `tank.png` | Tank role | `EMOJI_TANK` |
| `heal.png` | Heal role | `EMOJI_HEAL` |
| `dps.png` | DPS role | `EMOJI_DPS` |
| `dungeon.png` | Dungeon events | `EMOJI_DUNGEON` |
| `raid.png` | Raid events | `EMOJI_RAID` |
| `battleground.png` | Battleground events | `EMOJI_BATTLEGROUND` |
| `pvp.png` | PvP events | `EMOJI_PVP` |
| `rift.png` | Rift events | `EMOJI_RIFT` |
| `abyss.png` | Abyss events | `EMOJI_ABYSS` |
| `other.png` | Other events | `EMOJI_OTHER` |

## Installing them

1. Open the [developer portal](https://discord.com/developers/applications),
   pick the Kisk application, then the **Emojis** tab.
2. Upload each PNG and name it after its file (`tank`, `dungeon`, ...).
3. The portal shows a code for each one, like `<:tank:123456789012345678>`.
   Copy them into your `.env`:

   ```
   EMOJI_TANK=<:tank:123456789012345678>
   EMOJI_DUNGEON=<:dungeon:123456789012345679>
   ```

4. Restart the bot. Any variable left empty keeps the Unicode default.

Application emojis work in every server the bot is in — members don't have to
install anything. They show up in embeds, buttons and messages; Discord
renders slash-command choice lists as plain text, so those keep the Unicode
emojis.
