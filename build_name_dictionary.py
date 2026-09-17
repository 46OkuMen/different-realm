"""
Rebuilds NAME.TOS's 123-slot word-dictionary (see tos.py's load_english_dict_words()
docstring for the mechanism) from scratch, based purely on what's actually translated
right now. NAME.TOS's dictionary token space is a hard, fully-accounted-for ceiling --
0x02xx entries 0x00-0x15 and 0x91-0x98 are used for unrelated control codes, so there
is no room to add slots, only to change what the existing 123 hold. Per the user: sac-
rifice whatever isn't earning its slot in the currently-translated corpus and rebuild
around real usage. Re-run this any time more files get translated to keep it current.

Usage:
    python build_name_dictionary.py            # dry run, prints the proposed table
    python build_name_dictionary.py --write     # also writes it into the workbook

Algorithm: candidate words are every 3+ letter run appearing 2+ times across the
currently-translated corpus (AT01/AT02/SYSTEM/HELP). Slots are filled one at a time,
greedily picking whichever remaining candidate saves the most bytes *given the entries
already chosen* -- simulated with the same longest-match-first substitution the real
encoder uses, so a word entirely swallowed by an already-picked longer phrase (e.g.
"the" inside an already-picked "there") correctly stops earning credit for those
occurrences. Index 0 is always reserved for [PlayerName] (a hardcoded special case,
not a literal-text entry) and is never touched.
"""
import re
import sys

import openpyxl

WORKBOOK_PATH = 'DiffRealm_Text.xlsx'
CORPUS_FILES = ['AT01', 'AT02', 'SYSTEM', 'HELP']  # currently-translated files to learn from
TOTAL_SLOTS = 123
PLAYER_NAME_INDEX = 0
MIN_CANDIDATE_LEN = 3
MIN_OCCURRENCES = 2
TOKEN_BASE = 0x16


def load_corpus_text():
    """Plain English text (bracket tags stripped) from every currently-translated
    block across CORPUS_FILES, as one big string -- both for candidate extraction
    and as the simulation surface for measuring real savings."""
    chunks = []
    for name in CORPUS_FILES:
        with open(f'patched/{name}_parsed.TOS', 'rb') as f:
            lines = f.readlines()
        for line in lines:
            body = b'}'.join(line.rstrip(b'\n').split(b'}')[1:])
            body = re.sub(rb'\[[^\]]*\]', b' ', body)  # strip control tags
            try:
                chunks.append(body.decode('shift_jis', errors='ignore'))
            except Exception:
                pass
    return '\n'.join(chunks)


def candidate_words(corpus):
    counts = {}
    for m in re.finditer(r"[A-Za-z']+", corpus):
        w = m.group(0)
        if len(w) >= MIN_CANDIDATE_LEN:
            counts[w] = counts.get(w, 0) + 1
    return {w for w, c in counts.items() if c >= MIN_OCCURRENCES}


def greedy_substitute_savings(text, selected_words, candidate=None):
    """Bytes saved by longest-match-first substituting `selected_words` (+ candidate,
    if given) into `text`, matching tos.py's real dictionary-matching behavior exactly.
    Each substitution costs 2 bytes (the token) and frees len(match) bytes."""
    words = sorted(selected_words | ({candidate} if candidate else set()), key=len, reverse=True)
    saved = 0
    i = 0
    n = len(text)
    while i < n:
        for w in words:
            if text.startswith(w, i):
                saved += len(w) - 2
                i += len(w)
                break
        else:
            i += 1
    return saved


def build_dictionary():
    corpus = load_corpus_text()
    candidates = candidate_words(corpus)
    print(f'Corpus: {len(corpus)} chars across {CORPUS_FILES}. {len(candidates)} candidate words.')

    selected = []
    remaining = set(candidates)
    total_saved = 0

    while remaining and len(selected) < TOTAL_SLOTS - 1:
        best_word, best_gain = None, 0
        baseline = greedy_substitute_savings(corpus, set(selected))
        for w in remaining:
            gain = greedy_substitute_savings(corpus, set(selected), candidate=w) - baseline
            if gain > best_gain:
                best_word, best_gain = w, gain
        if best_word is None or best_gain <= 0:
            break
        selected.append(best_word)
        remaining.discard(best_word)
        total_saved += best_gain
        print(f'  slot {len(selected):3} (token 02{TOKEN_BASE + len(selected):02x}): '
              f'{best_word!r:25} +{best_gain} bytes (running total {total_saved})')

    print(f'\nFilled {len(selected)}/{TOTAL_SLOTS - 1} slots, {total_saved} bytes saved '
          f'across {CORPUS_FILES}.')
    return selected, total_saved


def write_to_workbook(selected):
    wb = openpyxl.load_workbook(WORKBOOK_PATH)
    ws = wb['NAME.TOS']
    for i in range(1, TOTAL_SLOTS):
        row = i + 2  # row 2 = index 0
        value = selected[i - 1] if i - 1 < len(selected) else ''
        ws.cell(row=row, column=7, value=value)  # column G = English
    wb.save(WORKBOOK_PATH)
    print(f'\nWrote {len(selected)} entries into NAME.TOS!G3:G{TOTAL_SLOTS + 1} and saved {WORKBOOK_PATH}.')


if __name__ == '__main__':
    selected, total_saved = build_dictionary()
    if '--write' in sys.argv:
        write_to_workbook(selected)
    else:
        print('\nDry run only -- pass --write to apply this to the workbook.')
