import os
import sys
import tempfile
from pathlib import Path
from shutil import copyfile
from rominfo import SRC_DISK, DEST_DISK, DATA_BIN_FILES, NAMES, CTRL, SPEED_INCREASES
from romtools.disk import Disk, Gamefile, Block
from romtools.dump import DumpExcel
from glodia import tos
from build_script_viewer_data import (
    PLAYER_NAME_EN,
    build_validation,
    bytes_to_unicode_tagged,
    extract_metadata,
    extract_tags,
    load_translations,
    reconstruct_english_block,
    strip_tags_for_display,
)

DUMP_XLS_PATH = 'DiffRealm_Text.xlsx'
Dump = DumpExcel(DUMP_XLS_PATH)

OriginalDiffRealm = Disk(SRC_DISK)
TargetDiffRealm = Disk(DEST_DISK)

NAME_VISIBLE_LEN = 8
NAME_BUFFER_LEN = 10
# NM_CLR_NAME's REP STOSB count: how many blank ("_") markers get written into the
# name buffer. NM_PRINT hands the whole buffer to KANJI, which prints until it hits
# the 0x00 terminator -- so this is also exactly how many underscore placeholders
# the name-entry screen draws. It must match NAME_VISIBLE_LEN: at 9 it drew a 9th
# placeholder slot that nothing could ever fill, since the 8-char cap (the
# CMP AX,NAME_VISIBLE_LEN at 0x9ef) stops input at 8.
NAME_CLEAR_LEN = NAME_VISIBLE_LEN
OLD_NAME_WORK_ADDR = 0x0093
NEW_NAME_WORK_ADDR = 0x07e0
# CM_EX's "SPACE CUT" start pointer (CMAKE.ASM: MOV DI,OF USER_NAME+6), patched at
# CMAKE 0x613: one past the last visible character. It walks backwards turning blank
# (22) bytes into terminators.
NEW_NAME_TRIM_ADDR = NEW_NAME_WORK_ADDR + NAME_VISIBLE_LEN
MAIN_WORK_TEMPLATE_DELTA = 0x0200
MAIN_NEW_NAME_OFFSET = NEW_NAME_WORK_ADDR + MAIN_WORK_TEMPLATE_DELTA
# K_STR's [PlayerName] case (WINDOW.ASM: MOV DX,USER_NAME / JMP CS_STR). Only the
# MOV's 2-byte address operand is replaced; the JMP right after it must survive.
MAIN_NAME_HOOK_OFFSET = 0x49e2
TALK_SCAN_WINDOW = 0x2000  # GET_TALK/CHECK_TALK's GTG1, widened from the original 0x1000 (4096)
CMAKE_SEGMENT_BASE = 0xa000
CMAKE_ORG_NAME_OFFSET = 0x1026
CMAKE_BACK_NAME_OFFSET = 0x1036
CMAKE_ORG_NAME_ADDR = CMAKE_SEGMENT_BASE + CMAKE_ORG_NAME_OFFSET
CMAKE_BACK_NAME_ADDR = CMAKE_SEGMENT_BASE + CMAKE_BACK_NAME_OFFSET
NAME_GRID_WINDOW_HEIGHT = 7  # text rows; grid itself is 6 rows (CL 0-5)
STOCKMAN = b'\xb3\xd4\xcf\xc3\xcb\xcd\xc1\xce'
STOCKMAN_BUFFER = STOCKMAN + b'\x00\x00'
FORCE_TEST_TEXT_SPEED = True
FASTEST_TEXT_SPEED = b'[Spd28]'
# Blocks where inserting a [SpdXX] control code (or any byte) would be actively
# harmful, not just pointless: CM_NAM (CMAKE.ASM), the name-entry letter grid,
# selects a character by reading a raw byte at a HARDCODED offset --
# code_top + 3 + row*22 + column -- computed from wherever this exact block's
# text starts in memory (see CTRL's [Color7]/space-prefix handling for why
# "+3" and "22" are exactly right for the *unmodified* text). The block has no
# scrolling text to speed up in the first place (it's a static grid, not
# dialogue), so excluding it costs nothing and any byte inserted before or
# within it -- including a test-speed code -- shifts every row after it out
# of alignment with the cursor math. Translation objects don't carry a block
# number (only .location, the workbook's Offset column, parsed as an int) --
# 0x076a is HELP.TOS block 12's offset, stable since it's recorded once at
# dump time against the original Japanese text, not recomputed on edits.
TEXT_SPEED_EXEMPT = {('HELP.TOS', 0x076a)}  # HELP.TOS block 12: name-entry grid
# An English cell of exactly this text means "ship this block as empty", distinct from
# a blank/empty English cell, which means "not translated yet -- leave the Japanese in
# place". Without a distinct marker there's no way to say "translate this to nothing"
# for a block that's confirmed dead/unreachable but still needs to shrink to fit a
# fixed-size buffer (see TALK_PACK_BUDGETS).
BLANK_MARKER = b'[BLANK]'
OLD_NAME_SLOT_LEN = 8
SAVE_PATH_IN_DISK = os.path.join('REALM', 'SAVE')
# COMM.H's memory map packs MAIN.EXE's whole 64KB segment (0x6000) back to back with
# zero free space: ...1800-97FF MAIN.EXE code, 9800-9FFF MCT_T, A000-BFFF SUB_PRO (the
# *currently executing* overlay, e.g. CMAKE.BIN), C000-CFFF SYS_T, D000-DFFF SUB_T,
# E000-FFFF I_WORK. PRINTM (HELP.TOS, via CM_HELP) loads into MCT_T; PRINTS (SYSTEM.TOS)
# loads into SYS_T. TOS_ENTRY (WORK.ASM: TALK_TOP defaults to SUB_T, and SUB.ASM's
# TOS_PACK/TALK_IVENT_EXEC -- ordinary NPC/event dialogue -- calls it with no explicit
# buffer) reads regular talk-pack files like AT01.TOS/AT02.TOS from SUB_T. Either
# overflowing its fixed buffer overwrites whatever sits right after it in the segment --
# MCT_T's neighbor is SUB_PRO, so an oversized HELP.TOS directly corrupts the live
# executing program; SUB_T's neighbor is I_WORK. There's no slack to grow into, so a
# translation that doesn't fit is a real (if often silent) memory-corruption bug, not
# just a cosmetic overflow -- hence this is a hard failure, not a --allow-validation-
# warnings-style advisory.
# SUB_T: D000-DFFF (4k). Confirmed universal by checking every original TALK\*.TOS file
# (73 of them): none exceed 4096 bytes, and several (AT01/AT04/AT07/AT19/BT20/CT03/
# ST09/SYSTEM) sit within ~150 bytes of it -- every one was clearly hand-fit to this
# exact ceiling. SYSTEM.TOS/HELP.TOS get their own dedicated buffers below (SYS_T/MCT_T)
# and override this default; every other TALK\*.TOS file uses SUB_T (see should_check
# usage at the encode-size check, in reinsert()).
SUB_T_BUDGET = 0x1000
TALK_PACK_BUDGETS = {
    'HELP.TOS': 0x0800,    # MCT_T: 9800-9FFF (2k)
    'SYSTEM.TOS': 0x1000,  # SYS_T: C000-CFFF (4k)
}

# Cheat: force the game's built-in debug mode on (see the "Cool! Set 6000:c00 to
# FF to enable debug mode" note in todo.md -- D_FLAG, WORK.ASM: "DB 0 ; 製品 = 00
# / Debug = -1"). Every debug-gated code path checks it the same way, "CMP BYTE
# PTR [D_FLAG], 0xFF" immediately followed by a conditional branch (confirmed
# for all 16 occurrences in the compiled binary, one of them a shared "is debug
# mode?" subroutine reached via CALL/RET rather than an inline check -- same
# shape either way: the flags CMP sets are read immediately after).
#
# D_FLAG itself was NOT a viable patch target: unlike every address patched
# elsewhere in this file, its file offset does not equal its runtime offset --
# it lives in an early bootstrap region that loads under the ordinary DOS EXE
# header rule (file_offset = runtime_offset + header_size, confirmed by finding
# a literal "GLODIA." string 0x200 bytes into the file at the bootstrap's own
# runtime offset 0, and by a write to DOS_F at runtime 0xc04 landing exactly
# where WORK.ASM declares it relative to D_FLAG). MAIN.EXE-code proper (where
# T_ENTER and everything else this file patches lives) does NOT follow that
# rule -- file_offset equals runtime_offset directly there, no header added --
# meaning the two regions are related by different constants and a stub placed
# in one to write into the other needs both worked out correctly. Confirmed
# the hard way: an initial version hooked the bootstrap's own DOS_F-init
# instruction to also set D_FLAG, and it hung at a black screen forever (the
# working build boots to the main menu in ~4s; that one never did).
#
# Patching every CMP's own immediate operand instead sidesteps all of that:
# each one becomes "CMP [D_FLAG], 0x00", which is always true (D_FLAG is
# always 0x00 in the shipped game unless something writes it, and nothing
# does), so every debug-gated branch always takes the "debug mode is on" side
# -- without ever touching D_FLAG's storage or its cross-region bootstrap
# write, or needing new code/spare space at all.
ENABLE_DEBUG_MODE = '--enable-debug-mode' in sys.argv
DEBUG_MODE_CHECK_SITES = [
    0x1cf7, 0x1ef8, 0x1f37, 0x2018, 0x202e, 0x2047, 0x2067, 0x208c,
    0x267e, 0x26dc, 0x2bd7, 0x2c35, 0x2d48, 0x327c, 0x629b, 0x905d,
]

ALLOW_VALIDATION_WARNINGS = '--allow-validation-warnings' in sys.argv
# Debug aid: still run every file through the full decode/encode round-trip and all ASM
# patches, but skip substituting any English text, so the shipped text stays the original
# Japanese. Used to isolate whether a bug is in the ASM patches / re-encoding pipeline
# itself, versus specific to translated content (e.g. length-driven overflow bugs).
NO_TRANSLATIONS = '--no-translations' in sys.argv
# Debug aid: skip the GTG1-widening patch specifically, to isolate whether it (vs. some
# other ASM patch, or something unrelated) is responsible for the map-load corruption bug.
SKIP_GTG1_PATCH = '--skip-gtg1-patch' in sys.argv
# Debug aid: --translate-only=AT01.TOS,SYSTEM.TOS reinserts English only into the named
# files (matched against just_filename, e.g. 'AM01.TOS') and leaves every other file's
# text as the original Japanese, same as --no-translations would. Lets us bisect which
# specific file's translated content triggers a bug by growing this set one file at a
# time from an empty (all-Japanese, known-good) baseline, instead of guessing.
_translate_only_arg = next((a for a in sys.argv if a.startswith('--translate-only=')), None)
TRANSLATE_ONLY = (
    set(_translate_only_arg.split('=', 1)[1].split(',')) if _translate_only_arg else None
)
# Any ordinary TALK\*.TOS file that ends up too big for its fixed buffer gets
# split automatically -- new files are picked via tos.find_free_pack_slot() and
# must not collide with each other within one reinsert() run, hence the shared
# set threaded through every call. On by default; --no-talk-autosplit turns it
# off to isolate whether a bug is related to a split file specifically.
ENABLE_TALK_AUTOSPLIT = '--no-talk-autosplit' not in sys.argv
_autosplit_used_slots = set()


def should_translate(just_filename):
    if NO_TRANSLATIONS:
        return False
    if TRANSLATE_ONLY is not None:
        return just_filename in TRANSLATE_ONLY
    return True

_VALIDATION_TRANSLATIONS = None

assert len(STOCKMAN) == NAME_VISIBLE_LEN
assert len(STOCKMAN_BUFFER) == NAME_BUFFER_LEN
assert FASTEST_TEXT_SPEED in SPEED_INCREASES

FILES_TO_REINSERT = ['databin_files\\NAME.TOS', 'MAIN.EXE', 'TALK\\AT01.TOS', 'TALK\\AT02.TOS', 'TALK\\SYSTEM.TOS', 'TALK\\HELP.TOS',
                     'MAP\\AM01.TOS',  'databin_files\\WORD.TOS',
                     'CMAKE.BIN']
#FILES_TO_REINSERT = ['MAP\\AM01.TOS']
#DIETED_FILES = []


def word(value):
    return value.to_bytes(2, byteorder='little', signed=False)


def save_slot_names():
    save_dir = Path('original') / 'REALM' / 'SAVE'
    return sorted(path.name for path in save_dir.glob('SAVE*.DAT'))


def get_validation_translations():
    global _VALIDATION_TRANSLATIONS
    if _VALIDATION_TRANSLATIONS is None:
        _VALIDATION_TRANSLATIONS = load_translations(DUMP_XLS_PATH)
    return _VALIDATION_TRANSLATIONS


def iter_parsed_blocks(parsed_filename):
    with open(parsed_filename, 'rb') as f:
        for line in f:
            line = line.rstrip(b'\n')
            if not line or line[:1] != b'{':
                continue

            try:
                brace_end = line.index(b'}')
                block_num = int(line[1:brace_end])
            except (ValueError, IndexError):
                continue

            yield block_num, line[brace_end + 1:]


def is_blocking_validation_issue(issue):
    severity = issue.get('severity', 'warning')
    return severity == 'error' or (severity == 'warning' and not ALLOW_VALIDATION_WARNINGS)


def format_validation_failures(filename, failures):
    total_errors = sum(
        1 for failure in failures for issue in failure['issues']
        if issue.get('severity') == 'error'
    )
    total_warnings = sum(
        1 for failure in failures for issue in failure['issues']
        if issue.get('severity') == 'warning'
    )

    lines = [
        f'{filename}: reinsertion blocked by validation '
        f'({len(failures)} block(s), {total_errors} error(s), {total_warnings} warning(s)).'
    ]

    if total_warnings and not ALLOW_VALIDATION_WARNINGS:
        lines.append('Re-run with --allow-validation-warnings only after manually reviewing those warnings.')

    for failure in failures[:20]:
        lines.append(f"  Block {failure['block']}:")
        for issue in failure['issues'][:3]:
            lines.append(f"    [{issue.get('severity', 'warning')}] {issue['message']}")
        if len(failure['issues']) > 3:
            lines.append(f"    … plus {len(failure['issues']) - 3} more issue(s)")

    if len(failures) > 20:
        lines.append(f'  … plus {len(failures) - 20} more block(s)')

    return '\n'.join(lines)


def validate_parsed_translations(parsed_filename, workbook_filename):
    translations = get_validation_translations()
    failures = []

    for block_num, content in iter_parsed_blocks(parsed_filename):
        key = (workbook_filename, block_num)
        if key not in translations:
            continue

        raw = bytes_to_unicode_tagged(content)
        english_raw, translation_issues = reconstruct_english_block(raw, translations[key])
        english_text = strip_tags_for_display(english_raw, player_name=PLAYER_NAME_EN) if english_raw else '\n'.join(
            entry['english'] + entry['suffix'] for entry in translations[key]
        )
        tags = extract_tags(raw)
        portrait, _, _ = extract_metadata(tags)
        validation = build_validation(raw, english_raw, english_text, tags, portrait, translation_issues)
        blocking_issues = [issue for issue in validation['issues'] if is_blocking_validation_issue(issue)]

        if blocking_issues:
            failures.append({
                'block': block_num,
                'issues': blocking_issues,
            })

    if failures:
        raise ValueError(format_validation_failures(workbook_filename, failures))


def source_path_for(filename):
    if filename == 'MAIN.EXE':
        source_path = os.path.join('original', 'MAIN.EXE')
        if not os.path.isfile(source_path):
            OriginalDiffRealm.extract(filename, path_in_disk='REALM', dest_path='original')
        return source_path

    if filename == 'CMAKE.BIN':
        for candidate in [os.path.join('original', 'decompressed', filename),
                          os.path.join('original', filename)]:
            if os.path.isfile(candidate):
                return candidate
        raise FileNotFoundError('Need a decompressed original\\CMAKE.BIN before patching CMAKE.BIN')

    return os.path.join('original', 'REALM', filename)


def patched_path_for(filename):
    return os.path.join('patched', filename)




def patch_main_exe(gf):
    gf.edit(0x48b8, b'\x1a\x00')  # Read cursor incrementer from static 01
    gf.edit(0x4bb5, b'\x3c\x80')  # Compare to 0x80 instead of 0xad
    gf.edit(0x4bba, b'\x5a\x29')  # Change font table math for lowercase
    gf.edit(0x4bc3, b'\x90\x90\xbb\xa0\x29')  # Change font table math for uppercase
    gf.edit(0x4bd8, b'\xbb\x32\x21')  # Change font table math for something else??

    gf.edit(0x296, STOCKMAN)  # Legacy work-template name used by old saves and migration.
    gf.edit(MAIN_NEW_NAME_OFFSET, STOCKMAN_BUFFER)

    # GET_TALK/CHECK_TALK (SUB.ASM) only scan GTG1=4096 bytes into a loaded talk-pack
    # before giving up with error 165 ("No designated line number of the TALK"). English
    # translations can make a TOS file (e.g. SYSTEM.TOS) larger than the original Japanese,
    # pushing later blocks past that scan window and making them unreachable. Both compiled
    # copies of the "ADD BP,0x1000" scan-limit check get the same widened value.
    if not SKIP_GTG1_PATCH:
        for offset in [0x2ad2, 0x2af9]:
            gf.edit(offset + 2, word(TALK_SCAN_WINDOW))  # +2 skips the "ADD BP," opcode (81 C5)

    # Point [PlayerName] at the relocated 8-char name buffer. This used to jump to an
    # old-save fallback stub at file 0x54f2, but that "free" all-zeros area is a runtime
    # lookup table (ADD BX,0x52f2 at runtime 0x51c0/0x5271): the table overwrote the
    # stub, whose garbage then left an unbalanced PUSH BX and crashed the Status screen.
    assert bytes(gf.filestring[MAIN_NAME_HOOK_OFFSET:MAIN_NAME_HOOK_OFFSET + 5]) == b'\xba\x96\x00\xeb\x3a'
    gf.edit(MAIN_NAME_HOOK_OFFSET + 1, word(NEW_NAME_WORK_ADDR))

    if ENABLE_DEBUG_MODE:
        patch_debug_mode(gf)


def patch_debug_mode(gf):
    for site in DEBUG_MODE_CHECK_SITES:
        original = bytes(gf.filestring[site:site + 5])
        assert original == b'\x80\x3e\x00\x0c\xff', f'{hex(site)}: {original.hex()}'
        gf.edit(site + 4, b'\x00')  # CMP [D_FLAG],0xFF -> CMP [D_FLAG],0x00 (always true)


def patch_cmake_bin(gf):
    for offset in [0x5df, 0x5f9]:
        gf.edit(offset, b'\xbe' + word(CMAKE_ORG_NAME_ADDR))

    for offset in [0x5e2, 0x5fc, 0xa95, 0xaa4, 0xab5]:
        gf.edit(offset, b'\xbf' + word(NEW_NAME_WORK_ADDR))

    gf.edit(0x5e5, b'\xb9' + word(NAME_BUFFER_LEN))
    gf.edit(0x5ff, b'\xb9' + word(NAME_VISIBLE_LEN))
    gf.edit(0x613, b'\xbf' + word(NEW_NAME_TRIM_ADDR))
    gf.edit(0x6aa, b'\xba' + word(NEW_NAME_WORK_ADDR))
    gf.edit(0x94c, b'\xbe' + word(NEW_NAME_WORK_ADDR))
    gf.edit(0x9ef, b'\x3d' + word(NAME_VISIBLE_LEN))
    gf.edit(0xa80, b'\xbe' + word(NEW_NAME_WORK_ADDR))
    gf.edit(0xa83, b'\xbf' + word(CMAKE_BACK_NAME_ADDR))
    gf.edit(0xa86, b'\xb9' + word(NAME_BUFFER_LEN // 2))
    gf.edit(0xa92, b'\xbe' + word(CMAKE_BACK_NAME_ADDR))
    gf.edit(0xa98, b'\xb9' + word(NAME_BUFFER_LEN // 2))
    gf.edit(0xaa9, b'\xb9' + word(NAME_CLEAR_LEN))
    gf.edit(0xaba, b'\xb9' + word(NAME_CLEAR_LEN))
    gf.edit(0xaeb, b'\x3c' + bytes([NAME_VISIBLE_LEN]))
    # NOTE: 0xb28/0xb2a/0xb2e look like the same "6/8" shape as the name-length
    # checks above (ADD/CMP/SUB AL,imm8) and were previously patched to
    # NAME_VISIBLE_LEN here too, but they're actually NM_MOVE's row (CL) wrap
    # boundary, not a name-length check -- confirmed live: with the 8 patched
    # in, DOWN cycles through 8 rows (0-7) instead of wrapping at the grid's
    # real 6 (CL 0-5), letting the cursor scroll below the last drawn row and
    # off the bottom of the window. Leaving these three alone keeps the
    # original wrap-at-6.

    gf.edit(CMAKE_ORG_NAME_OFFSET, STOCKMAN_BUFFER)
    gf.edit(CMAKE_BACK_NAME_OFFSET, STOCKMAN_BUFFER)

    # CM_NAM opens its window via WIN_WID 42,7 (`MOV CX,0x2A07`; WIN_OPEN reads
    # CH=width, CL=height directly in text rows -- confirmed via WINDOW.ASM's
    # WK_INT, which stores CL straight into TXS_Y). 7 rows of height for 6
    # rows of grid content leaves visible empty space the cursor can still be
    # scrolled into below the last real row. Trim it to the 6 rows actually
    # used.
    gf.edit(0x940, bytes([NAME_GRID_WINDOW_HEIGHT]))

    gf.edit(0xda9, b'\xbf')      # Use "_" as blank character, not "I"
    gf.edit(0xdad, b'\x00')      # Fix invisible "J"
    # BAR_SPACE, SPACE_BAR's inverse (run when the name is confirmed), must convert the
    # same "_" back to a blank (22). Left at the original 169 it never matched the new
    # blank -- so trailing blanks weren't trimmed and an all-blank name didn't fall back
    # to the previous name -- and since 169 is our "I", it blanked every typed I.
    assert bytes(gf.filestring[0xdc3:0xdc5]) == b'\x3c\xa9'
    gf.edit(0xdc4, b'\xbf')
    gf.edit(0xaef, b'\x90\x90')  # Fix "creeping underscore" bug

    gf.edit(0x9fd, b'\x02\xdd\x02\xdd\x66\x91\xb1\x29\xf6\xe1\x03\xd8\x90')
    # Cursor-to-character math edit.
    # Basically we want to add 2(ch) + 0x29(cl) to ebx
    #
    # add bl, ch
    # add bl, ch
    # xchg eax, ecx
    # mov cl, 0x29
    # mul cl
    # add bx, ax
    # nop


def apply_test_text_speed(text):
    if not FORCE_TEST_TEXT_SPEED or not text:
        return text

    for spd in SPEED_INCREASES:
        text = text.replace(spd, FASTEST_TEXT_SPEED)

    if not text.startswith(FASTEST_TEXT_SPEED):
        text = FASTEST_TEXT_SPEED + text

    return text


def migrate_save_name_buffer(data):
    current = data[NEW_NAME_WORK_ADDR:NEW_NAME_WORK_ADDR + NAME_BUFFER_LEN]
    old_name = data[OLD_NAME_WORK_ADDR:OLD_NAME_WORK_ADDR + OLD_NAME_SLOT_LEN]

    if current == old_name + b'\x00\x00':
        return data, False

    if current[0] != 0 and current[-1] == 0:
        return data, False

    updated = bytearray(data)
    updated[NEW_NAME_WORK_ADDR:NEW_NAME_WORK_ADDR + NAME_BUFFER_LEN] = old_name + b'\x00\x00'
    return bytes(updated), True


def migrate_save_name_buffers():
    changed = 0

    for save_copy in Path('patched').glob('SAVE*.DAT'):
        migrated, did_change = migrate_save_name_buffer(save_copy.read_bytes())
        if did_change:
            save_copy.write_bytes(migrated)
            changed += 1

    with tempfile.TemporaryDirectory() as temp_dir:
        for save_name in save_slot_names():
            TargetDiffRealm.extract(save_name, path_in_disk=SAVE_PATH_IN_DISK, dest_path=temp_dir)
            extracted_path = Path(temp_dir) / save_name
            migrated, did_change = migrate_save_name_buffer(extracted_path.read_bytes())
            if did_change:
                extracted_path.write_bytes(migrated)
                TargetDiffRealm.insert(str(extracted_path), path_in_disk=SAVE_PATH_IN_DISK)
                changed += 1

    return changed

def reinsert(filename):
    path_in_disk = os.path.join('REALM', filename)
    dir_in_disk, just_filename = os.path.split(path_in_disk)
    gf_path = source_path_for(filename)
    #if not os.path.isfile(gf_path):
    #    OriginalDiffRealm.extract(filename, path_in_disk='REALM', dest_path='original')
    gf = Gamefile(gf_path, disk=OriginalDiffRealm, dest_disk=TargetDiffRealm)

    if filename == 'MAIN.EXE':
        patch_main_exe(gf)
        gf.write(path_in_disk=dir_in_disk, dest_path=patched_path_for(filename))

    elif filename == 'CMAKE.BIN':
        patch_cmake_bin(gf)
        gf.write(path_in_disk=dir_in_disk, dest_path=patched_path_for(filename))

    elif filename.split('\\')[-1] in DATA_BIN_FILES:
        parsed_filename = gf_path.replace('.TOS', '_parsed.TOS')
        validate_parsed_translations(parsed_filename, just_filename)

        parsed_gf = Gamefile(parsed_filename, disk=OriginalDiffRealm, dest_disk=TargetDiffRealm)
        print(filename)
        for t in Dump.get_translations(just_filename, include_blank=True):
            assert parsed_gf.filestring.count(t.japanese) >= 1
            #print(t.english)
            if should_translate(just_filename):
                if t.english == BLANK_MARKER:
                    parsed_gf.filestring = parsed_gf.filestring.replace(t.japanese, b'', 1)
                elif t.english:
                    #print("There's English here")
                    parsed_gf.filestring = parsed_gf.filestring.replace(t.japanese, t.english, 1)

        # Write changes to the file, but not the disk. Still needs encoding
        translated_parsed_filename = parsed_gf.write(skip_disk=True)

        encoded_filename = os.path.join('patched', filename)
        #print(encoded_filename)
        tos.encode_data_tos(translated_parsed_filename, encoded_filename)
        #tos.reinsert_data_tos(encoded_filename, 0x89b, 'patched\\ETC\\DATA.BIN')

    elif 'DATA.BIN' in filename:
        tos.write_data_tos('original\\REALM\\ETC\\DATA.BIN', 'patched\\ETC\\DATA.BIN')
        dest_filename = os.path.join('patched', filename)
        gf = Gamefile(dest_filename, disk=OriginalDiffRealm, dest_disk=TargetDiffRealm)
        gf.write(path_in_disk='REALM\\ETC')

    elif filename.endswith('.TOS'):
        parsed_filename = gf_path.replace('.TOS', '_parsed.TOS')
        dest_filename = os.path.join('patched', filename)
        dest_parsed_filename = os.path.join('patched', filename.replace('.TOS', '_parsed.TOS'))
        validate_parsed_translations(parsed_filename, just_filename)

        #copyfile(parsed_filename, dest_parsed_filename)

        # "Reinsert stuff"
        parsed_gf = Gamefile(parsed_filename, disk=OriginalDiffRealm, dest_disk=TargetDiffRealm)
        print(filename)
        for t in Dump.get_translations(just_filename, include_blank=True):
            #print(filename, t.location, t.japanese)
            if parsed_gf.filestring.count(t.japanese) < 1:
                # WORD.TOS's workbook sheet was dumped against the old, structurally
                # wrong decode_data_tos()-based parse (see rominfo.py's DATA_BIN_FILES
                # comment); until it's re-dumped with decode_tos(), its rows won't match
                # and can't be safely substituted. Skip rather than corrupt or crash.
                if just_filename == 'WORD.TOS':
                    continue
                raise AssertionError(
                    f'{just_filename}: workbook Japanese text not found in parsed source '
                    f'(block {t.location}): {t.japanese!r}'
                )

            if t.english == BLANK_MARKER and should_translate(just_filename):
                parsed_gf.filestring = parsed_gf.filestring.replace(t.japanese, b'', 1)
            elif t.english and should_translate(just_filename):
                if t.suffix:
                    t.english += bytes(t.suffix, encoding='shift_jis')

                if (just_filename, t.location) not in TEXT_SPEED_EXEMPT:
                    t.english = apply_test_text_speed(t.english)

                parsed_gf.filestring = parsed_gf.filestring.replace(t.japanese, t.english, 1)

        budget = TALK_PACK_BUDGETS.get(just_filename)
        if budget is None and filename.startswith('TALK\\'):
            # ordinary NPC/event dialogue: TOS_ENTRY's default TALK_TOP=SUB_T
            budget = SUB_T_BUDGET

        # Ordinary TALK\*.TOS dialogue (not SYSTEM.TOS/HELP.TOS, which load into
        # their own dedicated fixed buffers rather than the shared SUB_T one) can
        # be split automatically across multiple files -- see
        # split_oversized_talk_file()'s docstring for the mechanism. Any file this
        # produces beyond the base one is itself a full-fledged dialogue file with
        # no separate translation step: its content is exactly the (already-
        # translated) blocks that got moved out of the original.
        can_auto_split = (
            filename.startswith('TALK\\')
            and just_filename not in TALK_PACK_BUDGETS
            and ENABLE_TALK_AUTOSPLIT
        )
        if can_auto_split and budget is not None:
            results = tos.split_oversized_talk_file(
                just_filename, parsed_gf.filestring, budget,
                os.path.join('original', 'REALM', 'TALK'), _autosplit_used_slots,
            )
        else:
            results = {just_filename: parsed_gf.filestring}

        subdir = filename.split('\\')[0]  # e.g. 'TALK' -- matches dest_filename's own convention
        for result_filename, result_parsed in results.items():
            # Parsed intermediates live flat in patched/ (matching Gamefile.write()'s
            # own convention for the base file); only final encoded files go in the
            # per-type subdirectory (patched/TALK/, patched/MAP/, ...).
            result_parsed_path = os.path.join('patched', result_filename.replace('.TOS', '_parsed.TOS'))
            with open(result_parsed_path, 'wb') as f:
                f.write(result_parsed)

            result_dest_filename = os.path.join('patched', subdir, result_filename)
            tos.encode(result_parsed_path, result_dest_filename)

            if budget is not None:
                actual = os.path.getsize(result_dest_filename)
                if actual > budget:
                    raise ValueError(
                        f'{result_filename}: encoded size {actual} bytes exceeds its fixed '
                        f'talk-pack buffer ({budget} bytes) by {actual - budget} bytes. This '
                        'is not cosmetic -- the game loads this file into a fixed-size buffer '
                        'with no slack (see TALK_PACK_BUDGETS comment), and overflow corrupts '
                        'adjacent memory (for HELP.TOS, the live executing overlay program). '
                        + ('Shorten the English translation for this file until it fits.'
                           if not can_auto_split else
                           'Automatic splitting already ran and still couldn\'t make it fit -- '
                           'shorten the English translation for this file.')
                    )

            encoded_gf = Gamefile(result_dest_filename, disk=OriginalDiffRealm,
                                  dest_disk=TargetDiffRealm)
            if encoded_gf.filename[1] == 'T' or encoded_gf.filename in ['SYSTEM.TOS', 'HELP.TOS']:
                encoded_gf.write(path_in_disk='REALM\\TALK')
            elif encoded_gf.filename[1] == 'M':
                encoded_gf.write(path_in_disk='REALM\\MAP')
            elif encoded_gf.filename in ['WORD.TOS', 'MONSTER.TOS']:
                # DATA.BIN segment, not a standalone disk file -- write_data_tos() picks
                # this up from patched/databin_files/ and concatenates it in directly.
                pass
            else:
                print(encoded_gf.filename)
                raise Exception

#def reinsert_dieted(df):
#    """
#        DIETED_FILES are compressed with DIETX.EXE, a DOS utility.
#        They need to be edited (manually or with a script) and placed in DRSource/PROJECT/HD-DosRL.thd.
#        There, run:
#            DIETX filename
#        Now extract the compressed file and add it to patched/dieted_edited.
#        It will be inserted as is at runtime.
#    """
#    gf_path = os.path.join('patched', 'dieted_edited', df)
#
#    gf = Gamefile(gf_path, disk=OriginalDiffRealm, dest_disk=TargetDiffRealm)
#    gf.write(path_in_disk='REALM')


if __name__ == '__main__':
    copyfile('original/REALM/ETC/DATA.BIN', 'patched\\ETC\\DATA.BIN')
    migrate_save_name_buffers()

    for f in FILES_TO_REINSERT:
        reinsert(f)

    reinsert('ETC\\DATA.BIN')

    #for df in DIETED_FILES:
    #    reinsert_dieted(df)

    #gf.insert('patched/DATA.BIN', path_in_disk='REALM/ETC')
