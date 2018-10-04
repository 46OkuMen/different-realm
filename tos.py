# .TOS file parser, based on documentation from Hoee Qwata

import os
import sys
from shutil import copyfile
from romtools.utils import SJIS_FIRST_BYTES
from rominfo import CTRL, inverse_CTRL, MARKS, DATA_BIN_MAP
from jis_x_0208 import jis_to_sjis
import binascii

control_words = (b'Voice', b'Anime', b'Face', b'Mouth', b'Spaces', b'FlipWidth',
                 b'Wait', b'Input', b'Switch', b'Spd', b'Clear', b'Color',
                 b'LN', b'MapName')


def encode(filename, dest_filename=None):
    """
        Re-encodes a parsed TOS file.
    """
    if dest_filename is None:
        dest_filename = filename.replace('_parsed.TOS', '_encoded.TOS')

    with open(filename, 'rb') as f:
        blocks = [l.rstrip(b'\n') for l in f.readlines()]

    for b in blocks:
        #print(b)
        try:
            block_num = b.split(b'}')[0]
            block_num = block_num.lstrip(b'{')
            block_num = int(block_num)
        except ValueError:
            continue

    block_count = block_num

    with open(dest_filename, 'wb+') as f:
        # Write header
        f.write(b'tmp.PA')
        f.write(bytes([(block_count)]))
        f.write(bytes([0]))

        for b in blocks:
            block_num = int(b.split(b'}')[0].lstrip(b'{'))
            print("Block", block_num)
            f.write(bytes([block_num]))

            # Gotta join the pieces with } again, or some SJIS will be disrupted
            block_body = b'}'.join(b.split(b'}')[1:])
            print("Block body:", block_body)

            while len(block_body) > 0:
                if block_body[0].to_bytes(1, 'little') == b'[':
                    # Literal code command.
                    if block_body.startswith(b'[Cmd'):
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
                        print("Cmd", cmd)
                        f.write(bytearray.fromhex(cmd.decode()))
                        f.write(b'\xff')
                    # Control code
                    else:
                        ctrl = block_body.split(b']')[0] + b']'
                        print("Ctrl:", ctrl)
                        block_body = block_body[len(ctrl):]

                        if any([c in ctrl for c in control_words]):
                            f.write(inverse_CTRL[ctrl])

                else:
                    text = b''
                    is_sjis = False
                    #print([hex(b) for b in block_body])
                    while len(block_body) > 0 and block_body[0].to_bytes(1, 'little') != b'[':
                        # Fullwidth text/SJIS should be read 2 bytes at a time.
                        if block_body[0] in SJIS_FIRST_BYTES:
                            is_sjis = True
                            text += block_body[0].to_bytes(1, 'little')
                            text += block_body[1].to_bytes(1, 'little')
                            block_body = block_body[2:]
                        else:
                            is_sjis = False
                            try:
                                text += (block_body[0] + 0x60).to_bytes(1, 'little')
                            except OverflowError:
                                text += block_body[0].to_bytes(1, 'little')
                            block_body = block_body[1:]

                    #print("Text:", text.decode('shift-jis'))
                    if is_sjis:
                        f.write(b"text")   # "Text"
                        f.write(bytes([s + 0x60 for s in str(block_num).encode('ascii')]))
                        # Nope, need to increase all the bytes by 20.
                    else:
                        f.write(text)
            f.write(bytes([0]))


def encode_data_tos(filename, dest_filename=None):
    """
        Encodes a parsed file from DATA.BIN.
    """
    if dest_filename is None:
        dest_filename = filename.replace('_parsed.TOS', '_encoded.TOS')

    with open(filename, 'rb') as f:
        blocks = [l.rstrip(b'\n') for l in f.readlines()]

    for b in blocks:
        print("B is:", b)

    with open(dest_filename, 'wb+') as f:
        f.write(b'name.P')
        f.write(b'\x01')  # ??

        for i, b in enumerate(blocks):
            while len(b) > 0:

                if b[0] in SJIS_FIRST_BYTES:
                    # THe normal thing to do: Write the SJIS
                    #f.write(b[0].to_bytes(1, 'little'))
                    #f.write(b[1].to_bytes(1, 'little'))
                    #b = b[2:]
                    # what I'm doing instead: Print a short thing
                    f.write(b'\xae')
                    break
                else:
                    f.write((b[0] + 0x60).to_bytes(1, 'little'))
                    b = b[1:]
            # TODO: Not getting quite the result I want. How about I just try reinserting actual text?
            #try:
            #    f.write((i + 0x60).to_bytes(1, 'little'))
            #except:
            #    f.write(b'text')
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

        f.seek(0xf)
        f.write(segment_locations[4].to_bytes(2, 'little'))

        f.seek(0x11)
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
                        block += CTRL[b + b2]
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
                    b = f.read(1)
                    block += b'[MapNameEnd]'
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
            blocks.append(block)

    with open(filename.replace('.TOS', '_parsed.TOS'), 'wb+') as f:
        #print "writing to file"
        for b in blocks:
            f.write(b)
            f.write(b'\n')


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
