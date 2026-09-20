"""
Rebuilds NAME.TOS's 123-slot word-dictionary (see tos.py's load_english_dict_words()
docstring for the mechanism) from CHARACTER_NAMES below.

Why names only: the engine draws every 0x02xx dictionary token in the name color, so
whatever is in this table gets highlighted in dialogue. An earlier version filled the
table with the corpus's most byte-saving words ("the", "you", "Everyone", "party"...),
which turned those words orange everywhere. Compression and highlighting can't be
separated without an engine patch, so the table holds only real character names --
the one case where the highlight is wanted.

Slot numbers matter: still-untranslated Japanese text keeps referring to the original
slots (1 = ストックマン, 3 = シーセア, ...), and those references display whatever
English is in that slot. So each name goes in the slot of its original Japanese entry;
names with no original entry go in the reserve ("予備"/"未使用") slots. Every other slot
is written as [BLANK] (an empty entry; the slot count and numbering are unchanged).
NAME.TOS lives in DATA.BIN, which has almost no free space (reinsert.py's
DATA_BIN_BUDGET), and those ~550 bytes of unused Japanese words are what make room
for English item and monster names. The cost: untranslated Japanese lines that
reference a blanked slot print nothing for that word -- but untranslated kana
already renders as garbage in the patched build (its bytes are the ASCII font range).
Set BLANK_UNUSED_SLOTS = False to keep the Japanese instead.

Matching is a raw substring match (no word boundaries), longest entry first. Before
adding a name, check it doesn't occur inside ordinary English words (e.g. "Prim" would
match inside "Primary").

Usage:
    python build_name_dictionary.py            # dry run, prints the table
    python build_name_dictionary.py --write     # also writes it into the workbook
"""
import sys

import openpyxl

WORKBOOK_PATH = 'DiffRealm_Text.xlsx'
TOTAL_SLOTS = 123  # index 0 is reserved for [PlayerName] and never touched
TOKEN_BASE = 0x16
BLANK_UNUSED_SLOTS = True

CHARACTER_NAMES = {
    # Original Japanese name slots
    1: 'Stockman',    # ストックマン
    2: 'Riesach',     # リーザッハ
    3: 'Thesea',      # シーセア
    4: 'Rubbereel',   # ラバリール
    5: 'Shudrahl',    # シュドラール
    6: 'Tybalt',      # ティボルト
    9: 'Rachel',      # レイチェル
    # Reserve slots, for names with no original entry
    31: 'Brombarome',
    75: 'Livra',
    76: 'Lifte',
    77: 'Phonames',
    78: 'Broemel',
    79: 'Ribnaam',
    80: 'Zambazica',
    81: 'Vajra',
    82: 'Rulikorov',
    83: 'Zimbas',
    84: 'Catappi',
    85: 'Kuniharu',
    86: 'Sparr',
}


def write_to_workbook(names):
    wb = openpyxl.load_workbook(WORKBOOK_PATH)
    ws = wb['NAME.TOS']
    for i in range(1, TOTAL_SLOTS):
        blank = '[BLANK]' if BLANK_UNUSED_SLOTS else ''
        ws.cell(row=i + 2, column=7, value=names.get(i, blank))  # row 2 = index 0, column G = English
    wb.save(WORKBOOK_PATH)
    print(f'Wrote {len(names)} names into NAME.TOS and saved {WORKBOOK_PATH}.')


if __name__ == '__main__':
    assert all(0 < slot < TOTAL_SLOTS for slot in CHARACTER_NAMES)
    assert len(set(CHARACTER_NAMES.values())) == len(CHARACTER_NAMES)
    for slot, name in sorted(CHARACTER_NAMES.items()):
        print(f'  slot {slot:3} (token 02{TOKEN_BASE + slot:02x}): {name!r}')
    if '--write' in sys.argv:
        write_to_workbook(CHARACTER_NAMES)
    else:
        print('\nDry run only -- pass --write to apply this to the workbook.')
