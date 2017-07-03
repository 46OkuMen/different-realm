# .TOS file parser, based on documentation from Hoee Qwata

import sys
from rominfo import CTRL, MARKS
from jis_x_0208 import jis_to_sjis

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
                    sjis_string = '\x82' + chr(ord(b) + 0x31)
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
                    sjis_string = '\x83' + chr(ord(b) - 109)
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
        decode(sys.argv[2])
    elif sys.argv[1] == 'encode':
        print("Not yet implemented.")
    


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