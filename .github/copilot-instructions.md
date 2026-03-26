# Copilot Instructions for glodia

## Project Overview

This is a **fan translation pipeline** for *Different Realm: Kuon no Kenja* (久遠の賢者), a PC-98 visual novel by Glodia. The tooling dumps Japanese text from game ROM files into an Excel workbook, where it's translated to English, then reinserts the translations into a patched HDI disk image.

## Commands

```sh
# Dump all TOS text into DiffRealm_Text.xlsx for translation
python dump_tos.py

# Reinsert translated text from Excel and apply ASM patches
python reinsert.py

# Extract DATA.BIN segments into individual files
python dump_databin_files.py

# Decode/encode individual TOS files
python tos.py decode <file.tos>
python tos.py encode <file_parsed.TOS>
```

There are no tests, linter, or CI pipeline.

## Architecture

### Translation Pipeline

```
original/*.hdi disk image
    ↓  dump_tos.py
DiffRealm_Text.xlsx  (one worksheet per TOS file; JP in col E, EN in col G)
    ↓  manual translation
    ↓  reinsert.py
patched/*.hdi disk image
```

### Key Modules

- **`tos.py`** — Core codec for the proprietary TOS binary text format. `decode_tos()` parses binary → human-readable `_parsed.TOS` files with `[ControlCode]` markers. `encode()` reverses this. There are separate `decode_data_tos()` / `encode_data_tos()` variants for the simpler DATA.BIN-embedded files.
- **`dump_tos.py`** — Walks all TOS files in `original/REALM/`, decodes them, intelligently splits text at natural boundaries (line breaks, screen clears, window width), and writes everything to a single Excel workbook. Uses `RealmString` (one translatable text unit) and `WindowLayout` (state machine tracking display width and screen position).
- **`reinsert.py`** — Reads translations from the Excel workbook, patches them into parsed TOS files, re-encodes to binary, and applies hand-crafted binary/ASM patches to `MAIN.EXE` and `CMAKE.BIN` (halfwidth ASCII support, 6→8 char name field, display bug fixes). Writes results to the destination HDI disk.
- **`rominfo.py`** — Central registry of game constants: disk paths, control code mappings (`CTRL` / `inverse_CTRL`), character name table (`NAMES` from `names-edit.pac`), `DATA_BIN_MAP` segment offsets, window widths, speed mappings.
- **`jis_x_0208.py`** — Loads `jis_x_0208.txt` (Unicode Consortium mapping) to build `jis_to_sjis` and `sjis_to_jis` lookup dicts.
- **`pict.py`** — Incomplete PNG→GEM/PICT image encoder. Mostly commented-out; not production-ready.

### External Dependency

The project depends on **`romtools`** (provides `romtools.disk.Disk`, `romtools.disk.Gamefile`, `romtools.dump.DumpExcel`). It also uses `openpyxl` (via romtools/dump_tos) for Excel I/O and `Pillow`/PIL in `pict.py`.

## TOS Binary Format

The game's text files use a custom binary format documented in `TOS.md`. Key byte ranges:

| Range | Meaning |
|-------|---------|
| `0x00` | End of block |
| `0x01` | Line break `[LN]` |
| `0x02` + N | Name reference (index into NAME.TOS) |
| `0x03` + N | 2-byte control code (voice, speed, color, spacing, etc.) |
| `0x04` | Halfwidth space |
| `0x05`–`0x15` | Game engine commands (skip to `0xFF` terminator) |
| `0x16`–`0x20` | Punctuation marks (mapped in `rominfo.MARKS`) |
| `0x21`–`0x4F` | JIS X 0208 two-byte character (read second byte) |
| `0x50`–`0x59` | Fullwidth numbers 0–9 |
| `0x5A`–`0xAC` | Hiragana |
| `0xAD`–`0xFF` | Katakana |

Control codes are represented as `[ControlCode]` tags in parsed files (e.g., `[LN]`, `[FW]`, `[Voice1E]`, `[Color6]`, `[Input]`, `[Clear]`). The full mapping lives in `rominfo.CTRL`.

## Conventions

- **File flow**: `original/` contains pristine game files extracted from the source HDI. `patched/` contains the output. Never modify files in `original/`.
- **Parsed TOS naming**: Decoded TOS files get a `_parsed` suffix (e.g., `AT01_parsed.TOS`). Encoded files get `_encoded` (e.g., `AT01_encoded.TOS`).
- **DATA.BIN files** (NAME.TOS, ITEM.TOS, WORD.TOS, MONSTER.TOS) are packed into a single `DATA.BIN` with offsets defined in `rominfo.DATA_BIN_MAP`. Use `dump_databin_files.py` to split them, and `tos.write_data_tos()` / `tos.reinsert_data_tos()` to repack.
- **Binary patches** in `reinsert.py` are documented inline with their purpose (e.g., enabling halfwidth ASCII, expanding the name field). Each patch is a `gf.edit(offset, bytes)` call.
- **DIET compression**: Some game files are compressed with DOS `DIET.EXE`. Editing these requires decompressing, editing, re-compressing on a DOS HDI in Neko Project II, then extracting. See `notes.md` § DIETing.
- **Window width**: Text display has two widths — `FULL` (32 chars) and `PORTRAIT` (28 chars, when a character portrait is shown). Translations must respect these limits.
- **Name color wrapping**: During reinsertion, character names in dialogue are wrapped with `[Color6]...[Color7]` to display in a distinct color.
- **Package import**: The project imports itself as `from glodia import tos` — the repo root is the `glodia` package (has `__init__.py`).

## Original Game Source (`Different Realms Source\`)

The repo includes the **complete original x86 assembly source code** for the game. This is invaluable for understanding binary offsets when writing patches in `reinsert.py`.

### Toolchain

- **OPTASM** assembler + **OLINK** linker (LSI Japan toolchain, targeting 80186+)
- **LSICMAKE** / **MS_MAKE** for builds
- **TCOMP.EXE** (`DEVELOP\TCOMP\`) — the original TOS script compiler
- **DIET.EXE** — DOS executable compressor used on some binaries

### Source Layout

| Directory | Contents |
|-----------|----------|
| `SRC\` | All game ASM source, headers, and MAKEFILE |
| `SRC\DOC\` | Design docs, data tables, developer notes (Japanese, dated ~Feb 1992) |
| `SRC\TALK\`, `SRC\MAP\` | TOS dialogue/map script sources |
| `DEVELOP\` | Build tools: `LSIC86\`, `TCOMP\`, `MDDRV\`, `WIN\` (image utils) |
| `TOOL\` | Developer utilities: `VZ.COM` (editor), `DIET.EXE`, `WINP.INT` (image viewer), batch scripts |
| `PROJECT\` | Neko Project II emulator setup with build-environment HDI |

### Key ASM Modules

| Module | Role |
|--------|------|
| `MAIN.ASM` | Main loop, initialization, demo mode |
| `TOS.ASM` / `TOSSUB.ASM` | TOS dialogue engine — command parsing, parameter handling, talk data reading |
| `WINDOW.ASM` | Window drawing, kanji character rendering, text positioning |
| `MPRINT.ASM` | Menu text printing, formatted numbers, YES/NO dialogs |
| `CMAKE.ASM` | Character creation & name entry screen |
| `WORK.ASM` | Global memory layout and game state variables |
| `FIGHT.ASM` + `FSUB/FTHINK/FACTION/FROOT.ASM` | Battle system (overlay module) |
| `COMM.H` / `MACROS.H` / `LABELS.H` | Shared constants, macros, label definitions |

### Build Structure

MAIN.EXE is linked from ~18 core ASM modules. Overlay modules (`.BIN`, `.VIS`) are compiled separately with a shared base (`shead.obj` + `work.obj` + `public.obj`) and loaded at runtime starting at segment offset `A000H`. The MAKEFILE enforces size limits (MAIN.EXE = 38 blocks / 38,912 bytes).

### Memory Map (from `COMM.H` / `WORK.ASM`)

- `6000H` (Page 1): Main program (64K)
- `7000H` (Page 2): Character data
- `8000H` (Page 3): Screen buffer
- Key variables: `USER_NAME` (8 bytes), `GOLD` (4 bytes), `MAP_X`/`MAP_Y`, `BITMAP` (128 bytes of scenario flags), `TK_VAL` (52 bytes of dialogue variables)

### Relationship to Binary Patches

The `gf.edit(offset, bytes)` calls in `reinsert.py` patch compiled machine code at specific addresses. Cross-reference these offsets against the ASM source to understand what's being changed — e.g., the `CMAKE.BIN` patches modify name-entry logic in `CMAKE.ASM`, and the `MAIN.EXE` patches alter font table math in `MAIN.ASM`.
