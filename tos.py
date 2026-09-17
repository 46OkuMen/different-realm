# .TOS file parser, based on documentation from Hoee Qwata

import os
import re
import sys
from shutil import copyfile
from romtools.utils import SJIS_FIRST_BYTES
from rominfo import CTRL, inverse_CTRL, MARKS, inverse_MARKS, DATA_BIN_MAP, SPEED_INCREASES
from jis_x_0208 import jis_to_sjis, sjis_to_jis
import binascii

# Standard SJIS lead byte ranges (not the romtools constant, which includes false positives)
def is_sjis_lead(b):
    return (0x81 <= b <= 0x9F) or (0xE0 <= b <= 0xEF)

control_words = (b'Voice', b'Anime', b'Face', b'Mouth', b'Spaces', b'FW',
                 b'Wait', b'Input', b'Switch', b'Spd', b'Clear', b'Color',
                 b'LN', b'MapName', b'Portrait', b'Window')

# SUB.ASM's GET_TALK-adjacent text reader has a word-dictionary shorthand: control
# codes 2/3 followed by one more byte expand to a whole literal word or phrase
# (character names, common verb endings, etc.) instead of spelling it out
# character-by-character. decode_tos() expands these into plain SJIS text with no
# bracket markup, so on the way back encode() has to recognize a run of characters
# that matches one of these words and re-emit the 2-byte token, or it'll silently
# spell every occurrence out long-hand (inflating -- and byte-shifting -- any TOS
# file that happens to contain one, independent of any translation).
_LITERAL_DICT_WORDS = sorted(
    (k for k in inverse_CTRL if k and not k.startswith(b'[')),
    key=len, reverse=True,
)

# NAME.TOS *is* that word-dictionary's backing table -- decode_data_tos()'s Nth entry
# (0-indexed) is exactly what CTRL's 0x02xx tokens above decode to (entry 0 is always
# [PlayerName], a special case; entries 1+ line up as token = bytes([2, 0x16 + i]),
# confirmed against the original Japanese CTRL entries for i in 0..5). Since we
# translate NAME.TOS's entries to English, the *same* 2-byte tokens can compress
# matching English phrases elsewhere (character names most usefully, since those
# repeat constantly in dialogue) -- but only once we know what English text each
# index currently holds, which _LITERAL_DICT_WORDS (built from the static, Japanese-
# only CTRL table) can't tell us. Loaded lazily since it depends on NAME.TOS's current
# translated state, which doesn't exist until reinsert.py has processed that file.
_NAME_DICT_TOKEN_BASE = 0x16
_NAME_DICT_PLAYER_NAME_INDEX = 0
_english_dict_words_cache = None


def load_english_dict_words(name_parsed_path='patched/NAME_parsed.TOS'):
    """{english_phrase_bytes: token_bytes}, longest-key-first, built from NAME.TOS's
    *currently translated* entries. Skips blanks and single-character entries (too
    likely to false-positive-match inside ordinary words for the 2-byte savings to be
    worth it). Returns {} if NAME.TOS hasn't been translated/encoded yet this run."""
    global _english_dict_words_cache
    if _english_dict_words_cache is not None:
        return _english_dict_words_cache

    words = {}
    if os.path.isfile(name_parsed_path):
        with open(name_parsed_path, 'rb') as f:
            lines = [l.rstrip(b'\n') for l in f.readlines()]
        for i, line in enumerate(lines):
            if i == _NAME_DICT_PLAYER_NAME_INDEX or len(line) < 2:
                continue
            token = bytes([2, _NAME_DICT_TOKEN_BASE + i])
            # First (shortest-index/highest-priority) entry wins on an exact-text dupe.
            words.setdefault(line, token)

    _english_dict_words_cache = dict(
        sorted(words.items(), key=lambda kv: len(kv[0]), reverse=True)
    )
    return _english_dict_words_cache


def encode_block_body(block_body, filename=''):
    """
        Encodes one block's already-substituted text (everything after the
        '{N}' prefix) to TOS bytes, same logic encode() uses per block. Split
        out so callers (e.g. a spreadsheet budget check) can get the real
        encoded byte length of a candidate translation without writing a file.
    """
    out = bytearray()

    while len(block_body) > 0:
        if block_body[0].to_bytes(1, 'little') == b'[':
            # Literal code command.
            if block_body.startswith(b'[weird JIS '):
                # decode_tos() emits this for a 2-byte JIS sequence not in
                # jis_to_sjis, recording the raw original bytes as decimal so
                # a round-trip re-encode can restore them exactly even though
                # we don't know what character they represent.
                tag = block_body.split(b']')[0] + b']'
                block_body = block_body[len(tag):]
                n1, n2 = (int(x) for x in tag[len(b'[weird JIS '):-1].split(b' '))
                out += bytes([n1, n2])
            elif block_body.startswith(b'[Cmd'):
                block_body = block_body[4:]
                cmd = b''
                # Read until the end of the [CmdABCDEF], two bytes at a time.
                while block_body[0].to_bytes(1, 'little') != b']':
                    # Read two more bytes
                    cmd += block_body[0].to_bytes(1, 'little')
                    cmd += block_body[1].to_bytes(1, 'little')
                    block_body = block_body[2:]

                # Get rid of that last end-bracket
                block_body = block_body[1:]
                #print("Cmd", cmd)
                out += bytearray.fromhex(cmd.decode())
                out += b'\xff'

            elif block_body.startswith(b'[Ctrl'):
                # Unknown control code — raw hex bytes
                block_body = block_body[5:]  # skip '[Ctrl'
                hex_data = b''
                while block_body[0].to_bytes(1, 'little') != b']':
                    hex_data += block_body[0].to_bytes(1, 'little')
                    block_body = block_body[1:]
                block_body = block_body[1:]  # skip ']'
                out += bytearray.fromhex(hex_data.decode())

            elif block_body.startswith(b'[Portrait'):
                # One lone portrait in SYSTEM causes problems
                if 'SYSTEM' in filename:
                    out += b'\x0a\x09\xfd\x0f\xff'
                    block_body = b''

                else:
                    block_body = block_body[9:]
                    out += b'\x0a'
                    if block_body.startswith(b'Up'):
                        out += b'\x08'
                        block_body = block_body[2:]
                    elif block_body.startswith(b'Down'):
                        out += b'\x09'
                        block_body = block_body[4:]

                    portrait_num = block_body[0].to_bytes(1, 'little') + block_body[1].to_bytes(1, 'little')
                    block_body = block_body[2:]

                    #print(portrait_num)
                    out += bytearray.fromhex(portrait_num.decode())
                    out += b'\xff'
                    # Get that last ]
                    block_body = block_body[1:]

            elif block_body.startswith(b'[WindowUp') or block_body.startswith(b'[WindowDown'):
                out += b'\x09'
                if block_body.startswith(b'[WindowUp'):
                    out += b'\x0a'
                    block_body = block_body[9:]  # skip '[WindowUp'
                else:
                    out += b'\x0b'
                    block_body = block_body[11:]  # skip '[WindowDown'
                # Read optional hex parameters until ']'
                hex_params = b''
                while block_body[0].to_bytes(1, 'little') != b']':
                    hex_params += block_body[0].to_bytes(1, 'little')
                    block_body = block_body[1:]
                block_body = block_body[1:]  # skip ']'
                if hex_params:
                    out += bytearray.fromhex(hex_params.decode())
                out += b'\xff'
            # Control code
            else:
                ctrl = block_body.split(b']')[0] + b']'
                #print("Ctrl:", ctrl)
                block_body = block_body[len(ctrl):]

                if any([c in ctrl for c in control_words]):
                    #print(ctrl)
                    out += inverse_CTRL[ctrl]

        else:
            while len(block_body) > 0 and block_body[0].to_bytes(1, 'little') != b'[':
                english_dict_word = next(
                    (w for w in load_english_dict_words() if block_body.startswith(w)),
                    None,
                )
                if english_dict_word is not None:
                    out += load_english_dict_words()[english_dict_word]
                    block_body = block_body[len(english_dict_word):]
                    continue

                if is_sjis_lead(block_body[0]):
                    dict_word = next(
                        (w for w in _LITERAL_DICT_WORDS if block_body.startswith(w)),
                        None,
                    )
                    if dict_word is not None:
                        out += inverse_CTRL[dict_word]
                        block_body = block_body[len(dict_word):]
                        continue

                    sjis_b1 = block_body[0]
                    sjis_b2 = block_body[1]
                    sjis_pair = bytes([sjis_b1, sjis_b2])
                    block_body = block_body[2:]

                    if sjis_pair in inverse_MARKS:
                        out += bytes([inverse_MARKS[sjis_pair]])
                    elif sjis_b1 == 0x82 and 0x9F <= sjis_b2 <= 0xF1:
                        # Hiragana: SJIS 82 9F-F1 → TOS 5A-AC
                        out += bytes([sjis_b2 - 69])
                    elif sjis_b1 == 0x82 and 0x4F <= sjis_b2 <= 0x58:
                        # Numbers: SJIS 82 4F-58 → TOS 50-59
                        out += bytes([sjis_b2 + 1])
                    elif sjis_b1 == 0x83 and 0x40 <= sjis_b2 <= 0x96:
                        # Katakana: SJIS 83 40-96 → TOS AD-FF
                        adjusted = sjis_b2
                        if adjusted >= 0x80:
                            adjusted -= 1
                        out += bytes([adjusted + 109])
                    elif sjis_pair in sjis_to_jis:
                        # JIS kanji
                        out += sjis_to_jis[sjis_pair]
                    else:
                        raise ValueError("Unknown SJIS pair: %s" % sjis_pair.hex())
                elif block_body[0] == 0x20:
                    # ASCII space → TOS halfwidth space
                    out += b'\x04'
                    block_body = block_body[1:]
                else:
                    # ASCII → game font table offset
                    try:
                        out += (block_body[0] + 0x60).to_bytes(1, 'little')
                    except OverflowError:
                        out += block_body[0].to_bytes(1, 'little')
                    block_body = block_body[1:]

    return bytes(out)


def encode(filename, dest_filename=None):
    """
        Re-encodes a parsed TOS file.
    """
    if dest_filename is None:
        dest_filename = filename.replace('_parsed.TOS', '_encoded.TOS')

    with open(filename, 'rb') as f:
        blocks = [l.rstrip(b'\n') for l in f.readlines()]

    block_count = 0
    for b in blocks:
        #print(b)
        try:
            block_num = b.split(b'}')[0]
            block_num = block_num.lstrip(b'{')
            int(block_num)
        except ValueError:
            continue
        block_count += 1

    if 'WORD' in filename:
        # WORD.TOS is a DATA.BIN segment, not a real SPACK_READ/DIET_RD_MD file load --
        # whatever reads its entries doesn't consult this header field (the original is
        # always 0 regardless of its real block count). Match that instead of guessing.
        block_count = 0

    with open(dest_filename, 'wb+') as f:
        # Write header
        f.write(b'tmp.PA')
        f.write(bytes([(block_count)]))
        f.write(bytes([0]))

        for b in blocks:
            block_num = int(b.split(b'}')[0].lstrip(b'{'))
            #print("Block", block_num)
            f.write(bytes([block_num]))

            # Gotta join the pieces with } again, or some SJIS will be disrupted
            block_body = b'}'.join(b.split(b'}')[1:])
            #print("Block body:", block_body)

            f.write(encode_block_body(block_body, filename))
            f.write(bytes([0]))


def encode_data_tos(filename, dest_filename=None):
    """
        Encodes a parsed file from DATA.BIN.
    """
    if dest_filename is None:
        dest_filename = filename.replace('_parsed.TOS', '_encoded.TOS')

    with open(filename, 'rb') as f:
        blocks = [l.rstrip(b'\n') for l in f.readlines()]

    #for b in blocks:
    #    print("B is:", b)

    with open(dest_filename, 'wb+') as f:
        f.write(b'name.P')
        f.write(b'\x01\x00')  # 8-byte header total, matching decode_data_tos's f.read(8)

        for i, b in enumerate(blocks):
            while len(b) > 0:

                if b.startswith(b'[weird JIS '):
                    # decode_data_tos()/decode_tos() emit this for a 2-byte JIS
                    # sequence not in jis_to_sjis, recording the raw original bytes
                    # as decimal so a round-trip re-encode can restore them exactly
                    # even though we don't know what character they represent.
                    tag = b.split(b']')[0] + b']'
                    b = b[len(tag):]
                    n1, n2 = (int(x) for x in tag[len(b'[weird JIS '):-1].split(b' '))
                    f.write(bytes([n1, n2]))
                elif is_sjis_lead(b[0]):
                    sjis_b1 = b[0]
                    sjis_b2 = b[1]
                    sjis_pair = bytes([sjis_b1, sjis_b2])
                    b = b[2:]

                    if sjis_pair in inverse_MARKS:
                        f.write(bytes([inverse_MARKS[sjis_pair]]))
                    elif sjis_b1 == 0x82 and 0x9F <= sjis_b2 <= 0xF1:
                        f.write(bytes([sjis_b2 - 69]))
                    elif sjis_b1 == 0x82 and 0x4F <= sjis_b2 <= 0x58:
                        f.write(bytes([sjis_b2 + 1]))
                    elif sjis_b1 == 0x83 and 0x40 <= sjis_b2 <= 0x96:
                        adjusted = sjis_b2
                        if adjusted >= 0x80:
                            adjusted -= 1
                        f.write(bytes([adjusted + 109]))
                    elif sjis_pair in sjis_to_jis:
                        f.write(sjis_to_jis[sjis_pair])
                    else:
                        raise ValueError("Unknown SJIS pair: %s" % sjis_pair.hex())
                else:
                    if b[0] == 0x20:
                        f.write(b'\x04')
                    else:
                        f.write((b[0] + 0x60).to_bytes(1, 'little'))
                    b = b[1:]
            f.write(b'\x00')

def reinsert_data_tos(segment_filename, segment_offset, databin_filename):
    with open(segment_filename, 'rb') as f:
        segment = f.read()

    with open(databin_filename, 'rb+') as f:
        f.seek(segment_offset)
        f.write(segment)


def write_data_tos(src_filename, dest_filename):
    # Paste together all the DATA.BIN segments end to end in a new DATA.BIN file
    with open(dest_filename, 'wb') as f:
        segment_locations = []
        cursor = 0
        for component in [os.path.join('patched\\databin_files', s) for s in ['beginning.TOS', 'NAME.TOS',
             'ITEM.TOS', 'unknown.TOS', 'unknown2.TOS', 'WORD.TOS', 'MONSTER.TOS']]:
            print(component)
            with open(component, 'rb') as g:
                segment = g.read()
            f.write(segment)
            cursor += len(segment)
            segment_locations.append(cursor)

    print([hex(s) for s in segment_locations])

    # Update the pointers to each segment
    with open(dest_filename, 'rb+') as f:
        f.seek(0x2)
        f.write(segment_locations[0].to_bytes(2, 'little'))

        f.seek(0x8)
        f.write(segment_locations[1].to_bytes(2, 'little'))

        f.seek(0xa)
        f.write(segment_locations[2].to_bytes(2, 'little'))

        f.seek(0xc)
        f.write(segment_locations[3].to_bytes(2, 'little'))

        f.seek(0xe)
        f.write(segment_locations[4].to_bytes(2, 'little'))

        f.seek(0x10)
        f.write(segment_locations[5].to_bytes(2, 'little'))

        # Pointer values in header:
        # 89b, 46, 1c6, ba7, 1392, 18f5, 1987, 1b07


def decode_data_tos(filename):
    """
        Parses a TOS file from DATA.BIN.
        Simpler than other TOS - it's just the text part, sep'd by 00s.
    """
    with open(filename, 'rb') as f:
        blocks = []
        header = f.read(8)
        file_over = False
        while True:
            block = b''
            b = f.read(1)
            if b == b'':
                break

            while b != b'\x00' and b != b'':
                # NAMES
                if ord(b) == 2:
                    b2 = f.read(1)
                    block += CTRL[b + b2]
                # MARKS
                elif 22 <= ord(b) <= 32:
                    block += MARKS[ord(b)]
                # JIS
                elif 33 <= ord(b) <= 79:
                    b2 = f.read(1)
                    jis_string = b + b2
                    try:
                        sjis_string = jis_to_sjis[jis_string]
                    except KeyError:
                        #print("Couldn't find this char:", hex(ord(jis_string[0])), hex(ord(jis_string[1])))
                        sjis_string = b"[weird JIS %i %i]" % (jis_string[0], jis_string[1])
                    #sjis_string = "jis"
                    block += sjis_string
                # Numbers
                elif 80 <= ord(b) <= 89:
                    # We want to convert it to SJIS, where the numbers start at 82 4f
                    # So, prepend 82 and add 0x31 to the byte value here
                    sjis_string = b'\x82' + bytes([(ord(b) - 1)])
                    block += sjis_string
                # Hirigana
                elif 90 <= ord(b) <= 172:
                    # SJIS hirigana are 82 9f - f1.
                    # So, prepend 82 and add 69 to the b value.
                    # 90 + 69 = 159 (0x9f)
                    sjis_string = b'\x82' + bytes([(ord(b) + 69)])
                    assert 0x9f <= sjis_string[1] <= 0xf1
                    block += sjis_string
                # Katakana
                elif 173 <= ord(b) <= 255:
                    # SJIS katakana starts at 83 40.
                    # So, prepend 83 and subtract 109 from the b value.
                    # 173 - 109 = 0x40
                    second_byte_value = ord(b) - 109
                    # If it's above 7f, add 1. (JIS -> SJIS bug)
                    if second_byte_value >= 0x7f:
                        second_byte_value += 1
                    sjis_string = b'\x83' + bytes([(second_byte_value)])
                    assert 0x40 <= sjis_string[1] <= 0x96
                    block += sjis_string

                b = f.read(1)

            blocks.append(block)
            if b == b'':
                break
    with open(filename.replace('.TOS', '_parsed.TOS'), 'wb') as f:
        for b in blocks:
            f.write(b)
            f.write(b'\n')

def decode_tos(filename):
    """
        Decode an open TOS file object and write a parsed one.
    """
    with open(filename, 'rb') as f:
        blocks = []
        header = f.read(8)
        file_over = False
        map_name = False
        while not file_over:
            try:
                block_num = ord(f.read(1))
            except TypeError:
                break
            block = b'{%i}' % block_num
            b = f.read(1)
            while b != b'\x00' or map_name:
                try:
                    _ = ord(b)
                except TypeError:
                    file_over = True
                    break
                # Control code, 1 or 2 bytes
                if 1 <= ord(b) <= 4:
                    if ord(b) == 1:
                        block += b'[LN]'
                    elif ord(b) == 4:
                        block += b' '
                    else:
                        b2 = f.read(1)
                        key = b + b2
                        if key in CTRL:
                            ctrl_val = CTRL[key]
                            # Strip CR/LF to prevent line-splitting in parsed output
                            ctrl_val = ctrl_val.replace(b'\r', b'').replace(b'\n', b'')
                            block += ctrl_val
                        else:
                            block += b'[Ctrl' + binascii.hexlify(key) + b']'
                # Window control code
                elif 9 <= ord(b) <= 10:
                    window_base = ord(b)
                    next_b = ord(f.read(1))

                    known_subtype = False
                    if window_base == 9:
                        if next_b == 10:
                            block += b'[WindowUp'
                            known_subtype = True
                        elif next_b == 11:
                            block += b'[WindowDown'
                            known_subtype = True
                    elif window_base == 10:
                        if next_b == 8:
                            block += b'[PortraitUp'
                            known_subtype = True
                        elif next_b == 9:
                            block += b'[PortraitDown'
                            known_subtype = True

                    if known_subtype:
                        b = f.read(1)
                        while b != b'\xff':
                            block += binascii.hexlify(b)
                            b = f.read(1)
                        block += b']'
                    else:
                        # Unknown subtype — emit as generic Cmd with full hex
                        block += b'[Cmd'
                        block += binascii.hexlify(bytes([window_base, next_b]))
                        b = f.read(1)
                        while b != b'\xff':
                            block += binascii.hexlify(b)
                            b = f.read(1)
                        block += b']'

                # Command, so skip until 21
                elif 5 <= ord(b) <= 21:
                    cmd_base = ord(b)
                    next_b = f.read(1)

                    if cmd_base == 0x5 and ord(next_b) == 0x39:
                        block += b'[MapName'
                        map_name = True
                    else:
                        block += b'[Cmd'
                        # Gotta include that first byte of the command
                        block += binascii.hexlify(b)
                        b = next_b
                        while b != b'\xff':
                            block += binascii.hexlify(b)
                            b = f.read(1)

                    block += b']'
                # Punctuation marks
                elif 22 <= ord(b) <= 32:
                    block += MARKS[ord(b)]
                # Two-byte JIS sequences
                elif 33 <= ord(b) <= 79:
                    # The JIS here is JIS X 0208, which is not in Python's supported encodings
                    b2 = f.read(1)
                    jis_string = b + b2
                    try:
                        sjis_string = jis_to_sjis[jis_string]
                    except KeyError:
                        #print("Couldn't find this char:", hex(ord(jis_string[0])), hex(ord(jis_string[1])))
                        sjis_string = b"[weird JIS %i %i]" % (jis_string[0], jis_string[1])
                    #sjis_string = "jis"
                    block += sjis_string
                # Numbers
                elif 80 <= ord(b) <= 89:
                    # We want to convert it to SJIS, where the numbers start at 82 4f
                    # So, prepend 82 and add 0x31 to the byte value here
                    sjis_string = b'\x82' + bytes([(ord(b) - 1)])
                    block += sjis_string
                # Hirigana
                elif 90 <= ord(b) <= 172:
                    # SJIS hirigana are 82 9f - f1.
                    # So, prepend 82 and add 69 to the b value.
                    # 90 + 69 = 159 (0x9f)
                    sjis_string = b'\x82' + bytes([(ord(b) + 69)])
                    #print(sjis_string[1])
                    assert 0x9f <= sjis_string[1] <= 0xf1
                    block += sjis_string
                elif 0 == ord(b) and map_name:
                    # The 0x00 map-name terminator is immediately followed by one more
                    # byte before normal dispatch resumes (observed as 0xFF, but nothing
                    # guarantees that's universal) that the old code read and discarded
                    # without ever representing in the parsed text -- silently losing it
                    # on every round-trip. Preserve it explicitly via the already-
                    # supported raw-byte-passthrough tag instead of assuming its value.
                    trailing = f.read(1)
                    block += b'[MapNameEnd][Ctrl' + binascii.hexlify(trailing) + b']'
                    map_name = False
                elif 173 <= ord(b) <= 255:
                    # SJIS katakana starts at 83 40.
                    # So, prepend 83 and subtract 109 from the b value.
                    # 173 - 109 = 0x40
                    second_byte_value = ord(b) - 109
                    # If it's above 7f, add 1. (JIS -> SJIS bug)
                    if second_byte_value >= 0x7f:
                        second_byte_value += 1
                    sjis_string = b'\x83' + bytes([(second_byte_value)])
                    assert 0x40 <= sjis_string[1] <= 0x96
                    block += sjis_string
                b = f.read(1)
            #print "Block %s" % block_num, block
            #print(block)
            
            # Quickly swap out that "II" for a fullwidth "2"
            if b'\x87\x55' in block:
                block = block.replace(b'\x87\x55', b'\x82\x51', 1)

            blocks.append(block)

    with open(filename.replace('.TOS', '_parsed.TOS'), 'wb+') as f:
        #print "writing to file"
        for b in blocks:
            f.write(b)
            f.write(b'\n')


## ===========================================================================
## Automatic file-splitting for oversized talk-pack files.
##
## The engine has a built-in "load a different file and jump into it"
## instruction, PACK_T (opcode 0x08), embedded directly in the dialogue byte
## stream -- and the original game already leans on it constantly to keep
## individual files under their fixed load buffer. Its exact wire format,
## confirmed against real game data:
##   [08] [drive-letter][4-char filename][00] [target-block] [terminator 0xFF]
## decode_tos() already represents any command byte it doesn't specifically
## understand (values 5-21) as a generic [Cmd<hex>] passthrough tag, and
## encode_block_body() already writes one back out byte-for-byte -- so no
## format changes were needed to make PACK_T round-trip; only this module,
## which decides *when* and *how* to introduce new ones.
##
## Two opcodes reference another block NUMBER within the *same* file:
## JUMP_T (0x07) and CALL_T (0x10), both via a single PARAM_-encoded value
## (see _decode_param below). PACK_T (0x08) always names a different file and
## is therefore never an internal reference. This was verified empirically,
## not just from the source: every [Cmd05xx] sub-command actually used
## anywhere in the shipped game was enumerated, and the one other opcode that
## could reference a block conditionally (IF_TK, sub-command 0x26) never
## appears in the data at all; CHRJUMP_T/MYJUMP_T (sub-commands 0x41/0x42)
## are unrelated (sprite movement, and an unimplemented no-op respectively).
## ===========================================================================

_JUMP_LIKE_OPCODES = {0x07, 0x10}  # JUMP_T, CALL_T
_TALK_HEADER_SIZE = 8  # 'tmp.PA' + block-count byte + reserved byte, per encode()


def parse_blocks(parsed_bytes):
    """({block_num: body_bytes}, [block_num, ...]) -- the file's blocks and
    their original on-disk order, from a _parsed.TOS file's raw bytes."""
    lines = [l for l in parsed_bytes.split(b'\n') if l]
    order = []
    blocks = {}
    for l in lines:
        num = int(l.split(b'}')[0].lstrip(b'{'))
        body = b'}'.join(l.split(b'}')[1:])
        order.append(num)
        blocks[num] = body
    return blocks, order


def _decode_param(raw, start):
    """Decode one PARAM_-style value from `raw` starting at `start`. Returns
    (value_or_None, next_index); None means the parameter is a runtime
    variable (0xFF marker) or the byte stream ran out -- not statically
    resolvable, so callers should treat it as "no reference found" rather
    than guess."""
    if start >= len(raw):
        return None, start
    b0 = raw[start]
    if b0 == 0xFF:
        return None, start + 1
    if b0 & 0x80 == 0:
        return b0, start + 1
    if start + 1 >= len(raw):
        return None, start + 1
    return ((b0 & 0x7F) << 8) | raw[start + 1], start + 2


def _encode_param(value):
    """Inverse of _decode_param for a literal (non-variable) value."""
    if value < 0x80:
        return bytes([value])
    return bytes([0x80 | (value >> 8), value & 0xFF])


def internal_references(block_body):
    """Block numbers this block's JUMP_T/CALL_T commands target within the
    same file. PACK_T (opcode 8) names a different file and is never one of
    these, even when its own target block number happens to collide."""
    refs = set()
    for m in re.finditer(rb'\[Cmd([0-9a-f]{2})([0-9a-f]*)\]', block_body):
        opcode = int(m.group(1), 16)
        if opcode not in _JUMP_LIKE_OPCODES:
            continue
        raw = bytes.fromhex(m.group(2).decode())
        target, _ = _decode_param(raw, 0)
        if target is not None:
            refs.add(target)
    return refs


def connected_components(blocks, order):
    """Group blocks that reference each other (directly or transitively) via
    JUMP_T/CALL_T into units that must move together -- splitting one apart
    would leave an internal jump pointing at a block that's no longer there.
    Returns a list of block-number lists."""
    parent = {n: n for n in order}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb

    for n in order:
        for target in internal_references(blocks[n]):
            if target in blocks:
                union(n, target)

    groups = {}
    for n in order:
        groups.setdefault(find(n), []).append(n)
    return list(groups.values())


def internal_indegree(blocks, order):
    """{block_num: count of other blocks in this file whose JUMP_T/CALL_T
    targets it}. A block with in-degree 0 might still be an entry point --
    referenced by another file's PACK_T, or by game data outside any TOS
    script entirely -- so callers should treat 0 as "possibly external",
    not "definitely unreachable"."""
    indeg = {n: 0 for n in order}
    for n in order:
        for target in internal_references(blocks[n]):
            if target in indeg:
                indeg[target] += 1
    return indeg


def encoded_block_size(body, filename=''):
    """Bytes this block occupies in a final encoded .TOS file: the block-
    number prefix, its encoded body, and the terminator byte -- matching
    encode()'s own per-block layout exactly."""
    return 1 + len(encode_block_body(body, filename)) + 1


def build_pack_stub_tag(dest_filename_4char, target_block):
    """The [Cmd...] text tag for a PACK_T redirect to `dest_filename_4char`
    (e.g. 'AT14'), landing on `target_block` there. The drive-letter byte is
    the destination's own first letter -- the convention observed throughout
    every PACK_T call in the original game data (e.g. 'AT03' is always
    preceded by a second 'A'), though nothing suggests the engine actually
    checks it against anything on this single hard-disk image."""
    assert len(dest_filename_4char) == 4
    assert 0 <= target_block <= 255
    drive = dest_filename_4char[0]
    payload = bytes([0x08]) + (drive + dest_filename_4char).encode('ascii') + b'\x00' + _encode_param(target_block)
    return b'[Cmd' + binascii.hexlify(payload) + b']'


def find_free_pack_slot(family_letter, directory, used_slots):
    """Lowest unused NN such that '<family_letter>T<NN>.TOS' doesn't already
    exist in `directory` and isn't already claimed this run (`used_slots`,//
    a set shared across every split happening in the same reinsert pass, so
    two oversized files never grab the same new name)."""
    pattern = re.compile(r'^%sT(\d\d)\.TOS$' % re.escape(family_letter))
    existing = set()
    for f in os.listdir(directory):
        m = pattern.match(f)
        if m:
            existing.add(int(m.group(1)))
    for n in range(1, 100):
        if n not in existing and n not in used_slots:
            used_slots.add(n)
            return '%sT%02d' % (family_letter, n)
    raise RuntimeError('No free %sT## slot available in %s' % (family_letter, directory))


def _is_simple_chain(comp, blocks):
    """True if every block in `comp` has at most one internal outgoing
    reference (a straight path with no branching) -- the one shape that's
    safe to cut apart at an arbitrary point, by turning the JUMP_T/CALL_T
    into that point into a PACK_T instead. Checked empirically across every
    TALK/MAP file in the game: 11 of the 13 large (>2000 byte) connected
    components are exactly this shape; the two that aren't (a 14-way
    fan-in and a branching dialogue router) are left as atomic units --
    see the module docstring above for why that's a safe fallback."""
    for n in comp:
        if len(set(internal_references(blocks[n])) & comp) > 1:
            return False
    return True


def _chain_order(comp, blocks, indeg):
    """A simple chain's blocks in head-to-tail order."""
    head = next((n for n in comp if indeg.get(n, 0) == 0), next(iter(comp)))
    order = []
    seen = set()
    current = head
    while current is not None and current not in seen:
        order.append(current)
        seen.add(current)
        refs = list(set(internal_references(blocks[current])) & comp)
        current = refs[0] if refs else None
    return order


def _fragment_chain(chain_order, blocks, filename, max_fragment_size):
    """Split a simple chain into consecutive fragments, each under
    `max_fragment_size` once encoded. Returns a list of
    {'blocks': [...], 'entry_blocks': [...], 'cut_predecessor': n_or_None}:
    the first fragment's entry is the chain's real head (indegree 0 in the
    whole file -- might be referenced from outside, so it needs a stub if
    moved); every later fragment's entry has no such stub, since nothing
    but the fragment before it ever reaches it -- instead, `cut_predecessor`
    names the block (the previous fragment's last one) whose JUMP_T/CALL_T
    must be rewritten into a PACK_T pointing at this fragment."""
    fragments = []
    current, current_size, predecessor = [], 0, None
    for n in chain_order:
        block_size = encoded_block_size(blocks[n], filename)
        if current and current_size + block_size > max_fragment_size:
            fragments.append({'blocks': current, 'entry_blocks': [] if predecessor else [current[0]],
                               'cut_predecessor': predecessor})
            predecessor = current[-1]
            current, current_size = [], 0
        current.append(n)
        current_size += block_size
    if current:
        fragments.append({'blocks': current, 'entry_blocks': [] if predecessor else [current[0]],
                           'cut_predecessor': predecessor})
    return fragments


def _replace_internal_jump_with_pack(body, old_target, dest_filename_4char):
    """Replace whichever JUMP_T/CALL_T command in `body` targets `old_target`
    with a PACK_T redirect to (dest_filename_4char, old_target)."""
    for m in re.finditer(rb'\[Cmd([0-9a-f]{2})([0-9a-f]*)\]', body):
        if int(m.group(1), 16) not in _JUMP_LIKE_OPCODES:
            continue
        raw = bytes.fromhex(m.group(2).decode())
        target, _ = _decode_param(raw, 0)
        if target == old_target:
            return body[:m.start()] + build_pack_stub_tag(dest_filename_4char, old_target) + body[m.end():]
    raise ValueError('no JUMP_T/CALL_T targeting block %d found to cut' % old_target)


def split_oversized_talk_file(base_filename, parsed_bytes, budget, directory, used_slots):
    """
    If `parsed_bytes` (a translated _parsed.TOS file's raw bytes) would
    exceed `budget` once encoded, split it into the base file -- trimmed,
    with a tiny PACK_T redirect stub left at any block that might be an
    external entry point (zero internal in-degree; a genuinely-interior
    block of a moved chain is dropped outright, since nothing but its own
    predecessor -- now relocated alongside it -- ever reaches it) -- plus as
    many new, freshly-numbered files as needed to fit everything. A single
    connected component too big to fit in one file by itself (the entire
    rest of the game is one long JUMP_T chain in some files -- see
    _is_simple_chain's docstring) gets cut into several smaller pieces
    first, each linked back to the one before it via a PACK_T in place of
    what was a same-file JUMP_T/CALL_T.

    Returns {filename: parsed_bytes} for every resulting file (base_filename
    always included, even when no split was needed). New files use the same
    family letter as the base file (e.g. splitting AT01.TOS produces
    AT##.TOS names), picked via find_free_pack_slot.
    """
    family_letter = base_filename[0]
    blocks, order = parse_blocks(parsed_bytes)
    components = connected_components(blocks, order)
    indeg = internal_indegree(blocks, order)

    def block_size(n):
        return encoded_block_size(blocks[n], base_filename)

    def unit_size(unit):
        return sum(block_size(n) for n in unit['blocks'])

    total = _TALK_HEADER_SIZE + sum(sum(block_size(n) for n in c) for c in components)
    if total <= budget:
        return {base_filename: parsed_bytes}

    max_unit_size = budget - _TALK_HEADER_SIZE
    units = []
    for comp in components:
        comp = set(comp)
        comp_size = sum(block_size(n) for n in comp)
        if comp_size <= max_unit_size:
            entry_blocks = [n for n in comp if indeg[n] == 0]
            units.append({'blocks': list(comp), 'entry_blocks': entry_blocks, 'cut_predecessor': None})
        elif _is_simple_chain(comp, blocks):
            units.extend(_fragment_chain(_chain_order(comp, blocks, indeg), blocks, base_filename, max_unit_size))
        else:
            # Not reducible by this algorithm (a branching/converging shape
            # too big to fit as one piece -- rare; none of the currently
            # translated files are this shape). Keep it whole so the normal
            # per-file budget check surfaces a clear "shorten this" error
            # downstream, instead of retrying forever to relocate something
            # that never actually gets smaller.
            units.append({'blocks': list(comp), 'entry_blocks': [n for n in comp if indeg[n] == 0],
                           'cut_predecessor': None})

    # Greedily extract the largest units first until the base file fits.
    stub_cost_estimate = encoded_block_size(build_pack_stub_tag(base_filename[:4] or 'XXXX', 0))
    base_size = total
    extracted = []
    for unit in sorted(units, key=unit_size, reverse=True):
        if base_size <= budget:
            break
        base_size = base_size - unit_size(unit) + stub_cost_estimate * (
            len(unit['entry_blocks']) + (1 if unit['cut_predecessor'] else 0))
        extracted.append(unit)

    if not extracted:
        return {base_filename: parsed_bytes}

    # Bin-pack the extracted units (largest first) into as few new files as
    # possible. A unit whose own size already exceeds what's left in every
    # open bin, and every fresh one too, just starts its own bin -- the
    # per-file budget check downstream will flag it if that's still over.
    bins, bin_sizes = [], []
    for unit in sorted(extracted, key=unit_size, reverse=True):
        sz = unit_size(unit)
        for i in range(len(bins)):
            if bin_sizes[i] + sz <= max_unit_size:
                bins[i].append(unit)
                bin_sizes[i] += sz
                break
        else:
            bins.append([unit])
            bin_sizes.append(sz)

    new_names = [find_free_pack_slot(family_letter, directory, used_slots) for _ in bins]

    # cut_predecessor edits are applied wherever that block ends up -- which
    # might be the base file, or another extracted unit entirely.
    pending_cuts = {}  # predecessor_block_num -> (dest_filename_4char, target_block)
    entry_to_name = {}
    for name, group in zip(new_names, bins):
        for unit in group:
            for n in unit['entry_blocks']:
                entry_to_name[n] = name
            if unit['cut_predecessor'] is not None:
                # cut_predecessor is only ever set on a chain fragment (see
                # _fragment_chain), whose blocks list is in chain order --
                # blocks[0] is exactly the entry this predecessor used to
                # JUMP_T/CALL_T straight into.
                pending_cuts[unit['cut_predecessor']] = (name, unit['blocks'][0])

    def emit_body(n):
        body = blocks[n]
        if n in pending_cuts:
            dest_name, target = pending_cuts[n]
            body = _replace_internal_jump_with_pack(body, target, dest_name)
        return body

    result = {}
    for name, group in zip(new_names, bins):
        lines = []
        for unit in group:
            for n in sorted(unit['blocks']):
                lines.append(b'{%d}' % n + emit_body(n))
        result[name + '.TOS'] = b'\n'.join(lines) + b'\n'

    extracted_block_nums = {n for unit in extracted for n in unit['blocks']}
    base_lines = []
    for n in order:
        if n not in extracted_block_nums:
            base_lines.append(b'{%d}' % n + emit_body(n))
        elif n in entry_to_name:
            base_lines.append(b'{%d}' % n + build_pack_stub_tag(entry_to_name[n], n))
        # else: interior block of an extracted unit -- dropped, only ever
        # reachable via its unit's own entry block(s) / cut predecessor,
        # which now redirect to wherever the whole unit landed.
    result[base_filename] = b'\n'.join(base_lines) + b'\n'

    # Recurse on every resulting file, base included: bin-packing and the
    # stub-cost estimate above are heuristics, not guarantees, so a leftover
    # overflow just gets split further the same way.
    final = {}
    for filename, content in result.items():
        final.update(split_oversized_talk_file(filename, content, budget, directory, used_slots))
    return final


if __name__ == '__main__':
    if len(sys.argv) < 3:
        print("Usage: python tos.py decode file.tos")
        sys.exit()

    if sys.argv[1] == 'decode':
        if any([t in sys.argv[2] for t in ('NAME.TOS', 'ITEM.TOS', 'MONSTER.TOS', 'WORD.TOS')]):
            decode_data_tos(sys.argv[2])
        else:
            decode_tos(sys.argv[2])
    elif sys.argv[1] == 'encode':
        if any([t in sys.argv[2] for t in ('NAME_parsed.TOS', 'ITEM_parsed.TOS', 'MONSTER_parsed.TOS', 'WORD_parsed.TOS')]):
            encode_data_tos(sys.argv[2])
            copyfile('original/DATA.BIN', 'patched/DATA.BIN')
            reinsert_data_tos(sys.argv[2].replace('_parsed.TOS', '_encoded.TOS'), 0x89b, 'patched/DATA.BIN')
        else:
            encode(sys.argv[2])
    


        """
        skip Header 8 bytes
while (end of file) {
  Get Block No (1 byte)
  while (get 1 byte is not 0) {
    if (is 5-21) {  This is command. skip unitl 0xff }
    else if (1-4) { Control Code 1 or 2 bytes }
    else if (22-32) { Mark }
    else if (33-79) { 2bytes JIS Code }
    else if (80-89) { Number }
    else if (90-172) { Hiragana }
    else if (173-255) { Katakana }
  }
}"""
