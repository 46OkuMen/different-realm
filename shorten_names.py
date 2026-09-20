"""
Temporary short English for ITEM.TOS / MONSTER.TOS so they fit in DATA.BIN.

DATA.BIN (NAME/ITEM/WORD/MONSTER name lists) must fit reinsert.py's
DATA_BIN_BUDGET, and the full translations are ~1.4 KB too long. This:
  - blanks ITEM.TOS's filler slots (オプション１０５, アイテム１２０ x26, イベント１６０ x26,
    ...), which the game never shows, and
  - replaces names over 15 cells (the Item Info header limit, see check_text_fit.py)
    with the abbreviations in SHORT.
The original English is kept in the Comments column as "full: ...", so nothing is
lost; re-running after new translations arrive re-applies the same mapping.

    python shorten_names.py           # dry run
    python shorten_names.py --write   # edit DiffRealm_Text.xlsx
"""
import re
import sys

import openpyxl

WORKBOOK = 'DiffRealm_Text.xlsx'
BLANK = '[BLANK]'
COMMENT_COL = 9  # 0-based: column J, "Comments"
FILLER_JP = re.compile(r'^(防具|オプション|アイテム|イベント|サイオ)[０-９]+$|^ｘｘｘ$')

SHORT = {
    # ITEM.TOS
    'Quality Heat-Resistant Outfit': 'Fine Heat Suit',
    'Heat-Resistant Outfit': 'Heat Suit',
    'Electromagnetic Shield': 'EM Shield',
    'Herbivorous Dragon Egg': 'Herbivore Egg',
    'Carnivorous Dragon Egg': 'Carnivore Egg',
    'Ishmael East Sea Chart': 'East Sea Chart',
    'Ishmael North Map': 'North Map',
    'Ishmael South Map': 'South Map',
    'Leopard Leather Boots': 'Leopard Boots',
    'Ultra-Gravity Hammer': 'Gravity Hammer',
    'High Frequency Blade': 'HF Blade',
    'Leather Padded Shirt': 'Leather Vest',
    'Cotton Padded Shirt': 'Padded Shirt',
    'Safflower Bee Nectar': 'Bee Nectar',
    'Great Reptilian Fang': 'Great Fang',
    'Reinforced Armor': 'Reinf. Armor',
    'Reinforced Armor +1': 'Reinf. Armor +1',
    'Reinforced Armor +2': 'Reinf. Armor +2',
    'Reinforced Armor +3': 'Reinf. Armor +3',
    'Reinforced Armor +4': 'Reinf. Armor +4',
    'Short Leather Coat': 'Leather Jacket',
    'Long Leather Coat': 'Leather Coat',
    'Industrial Burner': 'Ind. Burner',
    'Knife: Nightbloom': 'Nightbloom',
    'Magnetic Necklace': 'Mag. Necklace',
    'Magnetic Warmband': 'Mag. Warmband',
    'Dimensional Shift': 'Phase Shift',
    'Crystal Earrings': 'Crystal Earring',
    # MONSTER.TOS
    'Carnivorous Fanged Turtle': 'Fanged Turtle',
    'Herculean Tamajiro Type 3': 'Tamajiro Type 3',
    'Auto Battery: Tea Cloth': 'Tea Turret',
    'Auto Battery: Cannon': 'Auto Cannon',
    'Carnivorous Hemit Crab': 'Hermit Crab',
    'Juvenile Triceratops': 'Triceratops Jr.',
    'Mashed Potato (Rev.)': 'Mashed Potato+',
    'Sand Olive Flounder': 'Olive Flounder',
    'Great Horned Rhino': 'Horned Rhino',
    'Two-Headed Monkey': '2-Headed Monkey',
    'Man-Faced Octopus': 'Manface Octopus',
    'Man-Eating Plant': 'Maneater Plant',
    'Wasteland Finley': 'Desert Finley',
}


def main(write):
    wb = openpyxl.load_workbook(WORKBOOK)
    changed = 0
    for sheet in ('ITEM.TOS', 'MONSTER.TOS'):
        for r in wb[sheet].iter_rows(min_row=2):
            jp, en = r[4].value, r[6].value
            if not jp or not en:
                continue
            comment = r[COMMENT_COL].value
            full = comment[len('full: '):] if isinstance(comment, str) and comment.startswith('full: ') else en
            if sheet == 'ITEM.TOS' and FILLER_JP.match(jp):
                new = BLANK
            else:
                new = SHORT.get(full, full)
            if new != en:
                print(f'{sheet}: {en!r} -> {new!r}')
                changed += 1
            if new != full:
                r[COMMENT_COL].value = 'full: ' + full
            r[6].value = new
    print(f'{changed} rows changed')
    if write:
        wb.save(WORKBOOK)


if __name__ == '__main__':
    main('--write' in sys.argv)
