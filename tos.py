# .TOS file parser, based on documentation from Hoee Qwata

import codecs
import sys
from rominfo import CTRL, inverse_CTRL, MARKS
from jis_x_0208 import jis_to_sjis

control_words = ('Voice', 'Anime', 'Face', 'Mouth', 'Spaces', 'Toggle', 'Wait', 'Switch', 'TxtSpd', 'Clear', 'Color', 'LN')

placeholder = 'Placeholder, placeholder, placeholder, placeholder'


def encode(filename):
    with codecs.open(filename, 'r', encoding='shift_jis') as f:
        blocks = [b.rstrip() for b in f.readlines()]

    for b in blocks:
        #print b
        try:
            block_num = b.split('}')[0].lstrip('{')
            block_num = int(block_num)
        except ValueError:
            continue

    block_count = block_num

    with open(filename.replace('_parsed.TOS', '_encoded.TOS'), 'wb+') as f:
        # Write header
        f.write('tmp.PA')
        f.write(chr(block_count))
        f.write(chr(0))

        for b in blocks:
            block_num = int(b.split('}')[0].lstrip('{'))
            print "Block", block_num
            f.write(chr(block_num))

            block_body = ''.join(b.split('}')[1:])

            while len(block_body) > 0:
                if block_body[0] == '[':
                    ctrl = block_body.split(']')[0] + ']'
                    block_body = block_body[len(ctrl):]
                    print "ctrl:", ctrl
                    if 'Cmd' in ctrl:
                        ctrl = ctrl.strip('[]Cmd')
                        while ctrl:
                            f.write(chr(int(ctrl[:2], 16)))
                            ctrl = ctrl[2:]
                        f.write(chr(0xff))
                    elif any([c in ctrl for c in control_words]):
                        f.write(inverse_CTRL[ctrl])
                else:
                    # All the text should be double-width.
                    text = ''
                    while len(block_body) > 0 and block_body[0] != '[':
                        #print "block_body[0], %s, is not [" % block_body[0]
                        text += block_body[0]
                        block_body = block_body[1:]
                        #print block_body
                    print "text:", text
                    f.write("Text")

            f.write(chr(0))

def decode_data_tos(filename):
    with open(filename, 'rb') as f:
        blocks = []
        header = f.read(8)
        file_over = False
        while True:
            block = ''
            b = f.read(1)

            while b != '\x00' and b != '':
                if 22 <= ord(b) <= 32:
                    block += MARKS[ord(b)]
                elif 33 <= ord(b) <= 79:
                    b2 = f.read(1)
                    jis_string = b + b2
                    try:
                        sjis_string = jis_to_sjis[jis_string]
                    except KeyError:
                        print "Couldn't find this char:", hex(ord(jis_string[0])), hex(ord(jis_string[1]))
                        sjis_string = "[weird JIS %s %s]" % (hex(ord(jis_string[0])), hex(ord(jis_string[1])))
                    #sjis_string = "jis"
                    block += sjis_string
                elif 80 <= ord(b) <= 89:
                    # We want to convert it to SJIS, where the numbers start at 82 4f
                    # So, prepend 82 and add 0x31 to the byte value here
                    sjis_string = '\x82' + chr(ord(b) - 1)
                    block += sjis_string
                # Hirigana
                elif 90 <= ord(b) <= 172:
                    # SJIS hirigana are 82 9f - f1.
                    # So, prepend 82 and add 69 to the b value.
                    # 90 + 69 = 159 (0x9f)
                    sjis_string = '\x82' + chr(ord(b) + 69)
                    assert 0x9f <= ord(sjis_string[1]) <= 0xf1
                    block += sjis_string
                elif 173 <= ord(b) <= 255:
                    # SJIS katakana starts at 83 40.
                    # So, prepend 83 and subtract 109 from the b value.
                    # 173 - 109 = 0x40
                    second_byte_value = ord(b) - 109
                    # If it's above 7f, add 1. (JIS -> SJIS bug)
                    if second_byte_value >= 0x7f:
                        second_byte_value += 1
                    sjis_string = '\x83' + chr(second_byte_value)
                    assert 0x40 <= ord(sjis_string[1]) <= 0x96
                    block += sjis_string

                b = f.read(1)

            blocks.append(block)
            if b == '':
                break
    with open(filename.replace('.TOS', '_parsed.TOS'), 'wb') as f:
        for b in blocks:
            f.write(b)
            f.write('\n')

def decode(filename):
    """Decode an open TOS file object and write a parsed one."""
    with open(filename, 'rb') as f:
        blocks = []
        header = f.read(8)
        file_over = False
        while not file_over:
            try:
                block_num = ord(f.read(1))
            except TypeError:
                break
            block = '{%s}' % block_num
            b = f.read(1)
            while b != '\x00':
                try:
                    _ = ord(b)
                except TypeError:
                    file_over = True
                    break
                # Command, so skip until 21
                if 5 <= ord(b) <= 21:
                    block += '[Cmd'
                    while b != '\xff':
                        block += '%02x' % ord(b)
                        b = f.read(1)
                    block += ']'
                # Control code, 1 or 2 bytes
                elif 1 <= ord(b) <= 4:
                    if ord(b) == 1:
                        block += '[LN]'
                    elif ord(b) == 4:
                        block += ' '
                    else:
                        b2 = f.read(1)
                        block += CTRL[b + b2]
                # Punctuation marks
                elif 22 <= ord(b) <= 32:
                    block += MARKS[ord(b)]
                # Two-byte JIS sequences
                elif 33 <= ord(b) <= 79:
                    # The JIS here is JIS X 0208, which is not in Python's supported encodings...?
                    b2 = f.read(1)
                    jis_string = b + b2
                    try:
                        sjis_string = jis_to_sjis[jis_string]
                    except KeyError:
                        print "Couldn't find this char:", hex(ord(jis_string[0])), hex(ord(jis_string[1]))
                        sjis_string = "[weird JIS %s %s]" % (hex(ord(jis_string[0])), hex(ord(jis_string[1])))
                    #sjis_string = "jis"
                    block += sjis_string
                # Numbers
                elif 80 <= ord(b) <= 89:
                    # We want to convert it to SJIS, where the numbers start at 82 4f
                    # So, prepend 82 and add 0x31 to the byte value here
                    sjis_string = '\x82' + chr(ord(b) - 1)
                    block += sjis_string
                # Hirigana
                elif 90 <= ord(b) <= 172:
                    # SJIS hirigana are 82 9f - f1.
                    # So, prepend 82 and add 69 to the b value.
                    # 90 + 69 = 159 (0x9f)
                    sjis_string = '\x82' + chr(ord(b) + 69)
                    assert 0x9f <= ord(sjis_string[1]) <= 0xf1
                    block += sjis_string
                elif 173 <= ord(b) <= 255:
                    # SJIS katakana starts at 83 40.
                    # So, prepend 83 and subtract 109 from the b value.
                    # 173 - 109 = 0x40
                    second_byte_value = ord(b) - 109
                    # If it's above 7f, add 1. (JIS -> SJIS bug)
                    if second_byte_value >= 0x7f:
                        second_byte_value += 1
                    sjis_string = '\x83' + chr(second_byte_value)
                    assert 0x40 <= ord(sjis_string[1]) <= 0x96
                    block += sjis_string
                b = f.read(1)
            #print "Block %s" % block_num, block
            blocks.append(block)

    with open(filename.replace('.TOS', '_parsed.TOS'), 'wb+') as f:
        #print "writing to file"
        for b in blocks:
            f.write(b)
            f.write('\n')


if __name__ == '__main__':
    if len(sys.argv) < 3:
        print "Usage: python tos.py decode file.tos"
        sys.exit()

    if sys.argv[1] == 'decode':
        print('NAME.TOS' in sys.argv[2])
        if any([t in sys.argv[2] for t in ('NAME.TOS', 'ITEM.TOS', 'MONSTER.TOS', 'WORD.TOS')]):
            decode_data_tos(sys.argv[2])
        else:
            decode(sys.argv[2])
    elif sys.argv[1] == 'encode':
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

# NAME.TOS seems difficult to edit, since it's in DATA.BIN and pretty strict.
# I could just dump the names as plaintext...

# Name24 = Ri-zennha, or row 24 in NAME.PAC
# Name118 = ..., or row 118 in NAME.PAC
# Name130 = pa-rai-

# Decoding stuff in DATA.BIN is simpler - it is just text, encoded the same way, separated by 00s.