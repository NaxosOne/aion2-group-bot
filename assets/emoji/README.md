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
| `gladiator.png` | Gladiator | `EMOJI_GLADIATOR` |
| `templar.png` | Templar | `EMOJI_TEMPLAR` |
| `assassin.png` | Assassin | `EMOJI_ASSASSIN` |
| `ranger.png` | Ranger | `EMOJI_RANGER` |
| `sorcerer.png` | Sorcerer | `EMOJI_SORCERER` |
| `spiritmaster.png` | Spiritmaster | `EMOJI_SPIRITMASTER` |
| `cleric.png` | Cleric | `EMOJI_CLERIC` |
| `chanter.png` | Chanter | `EMOJI_CHANTER` |
| `fistfighter.png` | Fist Fighter (unreleased) | `EMOJI_FIST_FIGHTER` |

`fistfighter.png` is drawn and ready but the class isn't in the game yet: it
is listed here so the pack is complete. Uncomment the `"Fist Fighter"` line in
`bot/config.py` on release and it joins every class menu on its own.

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
