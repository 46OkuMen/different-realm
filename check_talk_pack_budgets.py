"""
Installs a *live* per-row running-total formula into DiffRealm_Text.xlsx for any
sheet whose file loads into one of the game's fixed-size talk-pack buffers (see
reinsert.py's TALK_PACK_BUDGETS comment for the full story): MAIN.EXE's 0x6000
segment is packed wall-to-wall with zero free space, so a translation that doesn't
fit isn't a cosmetic overflow -- it silently corrupts whatever sits right after that
buffer (for HELP.TOS, that's SUB_PRO, the *currently executing* overlay program).

Run this once to install the formulas:

    python check_talk_pack_budgets.py

After that, column K on the SYSTEM.TOS/HELP.TOS sheets recalculates live in Excel as
you edit the English column -- no need to re-run this script unless you add/remove
rows (block count changes), edit a row's Japanese cell, or a brand-new control-code
tag shows up that isn't in the TagCosts reference sheet this installs.

How the per-row formula works: it takes LEN(text) and corrects it for every bracket
tag (e.g. '[LN]', '[Color7]') by swapping the tag's literal string length for its real
encoded byte cost, looked up from the hidden TagCosts sheet (built from rominfo.py's
CTRL table, the same source tos.py's encoder itself uses).

A block's *workbook* Japanese/English cells often don't cover its *whole* on-disk
body -- surrounding structural tags like '[Color7][FW]...[FW]' commonly sit outside
what got dumped as translatable text, and stay fixed regardless of translation. This
script diffs each workbook row's Japanese cell against that block's true full body
(read from original/REALM/TALK/<FILE>_parsed.TOS) and bakes the leftover byte count
in as a hidden per-row "Overhead" column that the live formula adds in. Blocks with
no workbook row at all (pure control-code blocks with no translatable text, e.g. a
lone [Portrait..] tag) can't get a per-row correction, so their total is folded into
the fixed header constant instead (see BaseOverhead in the hidden TagCosts sheet).

Known approximation gaps (rare in narrative English text, so left unhandled):
  - [Cmd..]/[Ctrl..]/[Portrait..]/[WindowUp..]/[WindowDown..]/[weird JIS..] inside a
    row's *own* translatable text specifically (as opposed to the surrounding
    structural overhead, which the per-row correction above already accounts for).
  - Dictionary-word compression (an English phrase happening to exactly match a
    translated NAME.TOS dictionary entry) -- not modeled.
Close to the budget line, confirm against the real build:
    python reinsert.py --allow-validation-warnings --translate-only=SYSTEM.TOS,HELP.TOS
    (then check the byte size of patched/TALK/SYSTEM.TOS / patched/TALK/HELP.TOS directly)
"""
import os

import openpyxl
from openpyxl.formatting.rule import CellIsRule
from openpyxl.styles import Font, PatternFill

import tos
from rominfo import CTRL
from reinsert import TALK_PACK_BUDGETS, SUB_T_BUDGET, BLANK_MARKER as _BLANK_MARKER_BYTES

# reinsert.py checks every TALK\*.TOS file against SUB_T_BUDGET by default (see its
# TALK_PACK_BUDGETS comment) rather than listing each one -- but the spreadsheet only
# needs live indicators for files that are actually being translated right now.
# Extend this as more TALK\*.TOS sheets get worked on.
TRACKED_BUDGETS = dict(TALK_PACK_BUDGETS)
TRACKED_BUDGETS.setdefault('AT01.TOS', SUB_T_BUDGET)
TRACKED_BUDGETS.setdefault('AT02.TOS', SUB_T_BUDGET)

BLANK_MARKER = _BLANK_MARKER_BYTES.decode('ascii')

WORKBOOK_PATH = 'DiffRealm_Text.xlsx'
HEADER_SIZE = 8  # 'tmp.PA' + 2-byte header, written once at the top of the file
SPEED_PREFIX_COST = 2  # apply_test_text_speed() always prepends [Spd28] (2 bytes) to translated text

TAGCOSTS_SHEET = 'TagCosts'

ORIGINAL_PARSED_PATH = {
    'SYSTEM.TOS': 'original/REALM/TALK/SYSTEM_parsed.TOS',
    'HELP.TOS': 'original/REALM/TALK/HELP_parsed.TOS',
    'AT01.TOS': 'original/REALM/TALK/AT01_parsed.TOS',
    'AT02.TOS': 'original/REALM/TALK/AT02_parsed.TOS',
}

COL_BLOCK = 'B'
COL_JAPANESE = 'E'
COL_ENGLISH = 'G'
COL_SUFFIX = 'I'
COL_OVERHEAD = 11    # column K (hidden helper)
COL_CUMULATIVE = 12  # column L
COL_OVERHEAD_LETTER = 'K'
COL_CUMULATIVE_LETTER = 'L'

OVER_FILL = PatternFill('solid', fgColor='FFC7CE')
OVER_FONT = Font(color='9C0006')
UNDER_FILL = PatternFill('solid', fgColor='C6EFCE')
UNDER_FONT = Font(color='006100')


def simple_bracket_tags():
    """{tag_string: real_encoded_byte_cost}, for CTRL entries that are a plain
    '[Tag]' with no internal parameters -- i.e. everything except the handful of
    custom-parsed tags (Cmd/Ctrl/Portrait/WindowUp/WindowDown/weird JIS)."""
    tags = {}
    for key, value in CTRL.items():
        if value.startswith(b'[') and value.endswith(b']'):
            tags[value.decode('latin1')] = len(key)
    return tags


def install_tagcosts_sheet(wb, tags):
    if TAGCOSTS_SHEET in wb.sheetnames:
        del wb[TAGCOSTS_SHEET]
    ws = wb.create_sheet(TAGCOSTS_SHEET)
    ws.sheet_state = 'hidden'
    ws['A1'] = 'Tag'
    ws['B1'] = 'ByteCost'
    for i, (tag, cost) in enumerate(sorted(tags.items()), start=2):
        ws.cell(row=i, column=1, value=tag)
        ws.cell(row=i, column=2, value=cost)
    return f'{TAGCOSTS_SHEET}!$A$2:$A${1 + len(tags)}', f'{TAGCOSTS_SHEET}!$B$2:$B${1 + len(tags)}'


def parse_blocks(path):
    """{block_num: [body_bytes, ...]} -- a list because a block can (rarely)
    appear more than once in the source (SUB.ASM concatenates duplicates)."""
    blocks = {}
    with open(path, 'rb') as f:
        for line in f:
            line = line.rstrip(b'\n')
            if not line.startswith(b'{'):
                continue
            try:
                num = int(line.split(b'}')[0].lstrip(b'{'))
            except ValueError:
                continue
            body = b'}'.join(line.split(b'}')[1:])
            blocks.setdefault(num, []).append(body)
    return blocks


def compute_overheads(sheet_name, ws, last_row):
    """Returns (per_row_overhead: {row: int}, base_overhead: int).

    per_row_overhead[row] is the byte count belonging to that block's on-disk
    body that isn't covered by any workbook Japanese cell -- assigned to the
    first row seen for each block, 0 for any repeats of the same block.
    base_overhead is the total for blocks with no workbook row at all (added
    once, as part of the fixed header baseline, since it never changes).
    """
    original_path = ORIGINAL_PARSED_PATH.get(sheet_name)
    if original_path is None or not os.path.isfile(original_path):
        return {}, 0

    blocks = parse_blocks(original_path)
    remaining_bodies = {num: list(bodies) for num, bodies in blocks.items()}

    per_row_overhead = {}
    seen_blocks = set()
    for row in range(2, last_row + 1):
        block = ws.cell(row=row, column=2).value
        if not block:
            continue
        block = int(block)
        japanese = ws.cell(row=row, column=5).value or ''

        if block in seen_blocks or block not in remaining_bodies or not remaining_bodies[block]:
            per_row_overhead[row] = 0
            continue
        seen_blocks.add(block)

        full_body = remaining_bodies[block].pop(0)
        full_size = len(tos.encode_block_body(full_body, sheet_name))
        jp_size = len(tos.encode_block_body(japanese.encode('shift_jis'), sheet_name))
        per_row_overhead[row] = max(0, full_size - jp_size)

    base_overhead = 0
    for num, bodies in remaining_bodies.items():
        if num in seen_blocks:
            continue
        for body in bodies:
            base_overhead += len(tos.encode_block_body(body, sheet_name)) + 2

    return per_row_overhead, base_overhead


def row_bytes_formula(row, tag_range, cost_range):
    # An English cell of exactly BLANK_MARKER (reinsert.py's sentinel) ships the block
    # as empty -- 0 content bytes, just the +2 block/terminator overhead below -- as
    # opposed to a genuinely blank English cell, which falls back to the Japanese text.
    is_blank_marker = f'{COL_ENGLISH}{row}="{BLANK_MARKER}"'
    text = (
        f'IF({COL_ENGLISH}{row}<>"",{COL_ENGLISH}{row}&{COL_SUFFIX}{row},{COL_JAPANESE}{row})'
    )
    tag_savings = (
        f'SUMPRODUCT((LEN({text})-LEN(SUBSTITUTE({text},{tag_range},"")))'
        f'/LEN({tag_range})*(LEN({tag_range})-{cost_range}))'
    )
    speed_bonus = f'IF({COL_ENGLISH}{row}<>"",{SPEED_PREFIX_COST},0)'
    # +2 fixed per-block overhead: 1 block-number byte + 1 trailing 0x00 terminator.
    # +{overhead_ref}: this block's structural bytes outside the Japanese/English
    # cells (surrounding tags like [Color7]/[FW]) that stay fixed regardless of
    # translation -- see compute_overheads().
    overhead_ref = f'{COL_OVERHEAD_LETTER}{row}'
    normal_case = f'LEN({text})-{tag_savings}+{speed_bonus}+2+{overhead_ref}'
    return f'IF({COL_BLOCK}{row}="",0,IF({is_blank_marker},2+{overhead_ref},{normal_case}))'


def install_sheet(wb, sheet_name, budget, tag_range, cost_range):
    if sheet_name not in wb.sheetnames:
        print(f'  {sheet_name}: not in workbook, skipping')
        return
    ws = wb[sheet_name]
    last_row = ws.max_row

    per_row_overhead, base_overhead = compute_overheads(sheet_name, ws, last_row)

    ws.cell(row=1, column=COL_OVERHEAD, value='Overhead (hidden helper)')
    ws.cell(row=1, column=COL_CUMULATIVE, value='Encoded bytes (cum.)')
    ws.column_dimensions[COL_OVERHEAD_LETTER].hidden = True

    for row in range(2, last_row + 1):
        ws.cell(row=row, column=COL_OVERHEAD, value=per_row_overhead.get(row, 0))

        rb = row_bytes_formula(row, tag_range, cost_range)
        if row == 2:
            formula = f'={HEADER_SIZE + base_overhead}+{rb}'
        else:
            formula = f'={COL_CUMULATIVE_LETTER}{row - 1}+{rb}'
        ws.cell(row=row, column=COL_CUMULATIVE, value=formula)

    cum_range = f'{COL_CUMULATIVE_LETTER}2:{COL_CUMULATIVE_LETTER}{last_row}'
    ws.conditional_formatting.add(
        cum_range, CellIsRule(operator='greaterThan', formula=[str(budget)], fill=OVER_FILL, font=OVER_FONT)
    )
    ws.conditional_formatting.add(
        cum_range,
        CellIsRule(operator='lessThanOrEqual', formula=[str(budget)], fill=UNDER_FILL, font=UNDER_FONT),
    )

    last_cum = f'{COL_CUMULATIVE_LETTER}{last_row}'
    ws.cell(
        row=1,
        column=COL_CUMULATIVE + 1,
        value=(
            f'="Buffer budget: {budget} bytes | Encoded total: "&{last_cum}'
            f'&" bytes | "&IF({last_cum}>{budget},"OVER by "&({last_cum}-{budget})&" bytes",'
            f'({budget}-{last_cum})&" bytes to spare")'
        ),
    )
    print(
        f'  {sheet_name}: live formula installed through row {last_row} '
        f'(budget {budget}, fixed baseline {HEADER_SIZE + base_overhead} incl. '
        f'{base_overhead} bytes from blocks with no workbook row)'
    )


def main():
    wb = openpyxl.load_workbook(WORKBOOK_PATH)
    tags = simple_bracket_tags()
    tag_range, cost_range = install_tagcosts_sheet(wb, tags)
    print(f'Installing live talk-pack budget formulas in {WORKBOOK_PATH} ({len(tags)} known tags):')
    for sheet_name, budget in TRACKED_BUDGETS.items():
        install_sheet(wb, sheet_name, budget, tag_range, cost_range)
    wb.save(WORKBOOK_PATH)
    print('Saved. Column L now recalculates live in Excel as you edit English/Suffix cells.')


if __name__ == '__main__':
    main()
