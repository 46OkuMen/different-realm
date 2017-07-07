import re
import os
import xlsxwriter
from tos import decode_tos, decode_data_tos

workbook_FILENAME = 'DiffRealm_Text.xlsx'

workbook = xlsxwriter.Workbook(workbook_FILENAME)
header = workbook.add_format({'bold': True, 'align': 'center', 'bottom': True, 'bg_color': 'gray'})

tos_paths = []

for p in os.walk('original\\REALM'):
    for filename in p[2]:
        if filename.endswith(".TOS") and "parsed" not in filename:
            tos_paths.append(os.path.join(p[0], filename))

### testing
#tos_paths = ['original\\REALM\\MAP\\AM04.TOS',]

#tos_paths += 'original\\'

for t in tos_paths:
    print(t)
    if any([d in t for d in ('NAME.TOS', 'ITEM.TOS', 'MONSTER.TOS', 'WORD.TOS')]):
        decode_data_tos(t)
    else:
        decode_tos(t)

    with open(t.replace('.TOS', '_parsed.TOS'), 'rb') as f:
        parsed_tos_blocks = f.readlines()

    sjis_strings = []
    total_cursor = 0

    for p in parsed_tos_blocks:

        try:
            block_num = int(p.split(b"}")[0].lstrip(b'{'))
        except ValueError:
            block_num = b"?"

        if b'wei' in p:
            print("Weird JIS in %s %s" % (t, block_num))

        sjis_buffer = b''
        cursor = 0

        comment = None

        while cursor < len(p):
            # First byte of SJIS text. Read the next one, too
            #print(sjis_buffer)
            if 0x80 <= p[cursor] <= 0x9f or 0xe0 <= p[cursor] <= 0xef:
                # TODO: Need to do some better type conversions starting here.
                sjis_buffer += bytes([p[cursor]])
                cursor += 1
                total_cursor += 1
                sjis_buffer += bytes([p[cursor]])

            # TODO: Would be nice to include color control codes and such
            ## Control code, 1 or 2 bytes
            #elif 1 <= p[cursor] <= 4:
            #    if p[cursor] == 1:
            #        sjis_buffer += b'[LN]'
            #    elif p[cursor] == 4:
            #        p[cursor] += b' '
            #    else:
            #        sjis_buffer += CTRL[bytes([p[cursor]]) + bytes([p[cursor+1]])]
            #        cursor += 1

            # ASCII space, too
            elif p[cursor] == 0x20:
                sjis_buffer += bytes([p[cursor]])

            elif p[cursor:cursor+4] == b'[wei':
                while bytes([p[cursor]]) != b']':
                    sjis_buffer += bytes([p[cursor]])
                    cursor += 1
                    total_cursor += 1
                sjis_buffer += b']'

            # End of continuous SJIS string, so add the buffer to the strings and reset buffer
            else:
                if len(sjis_buffer.strip(b'\x81\x40 ')) > 0:
                    sjis_strings.append((total_cursor, block_num, sjis_buffer))
                sjis_buffer = b""
                sjis_buffer_start = cursor+1
            cursor += 1
            total_cursor += 1

        # Catch anything left after exiting the loop
        if sjis_buffer:
            sjis_strings.append((sjis_buffer_start, sjis_buffer))

    if sjis_strings:
        worksheet = workbook.add_worksheet(os.path.split(t)[1])

        worksheet.set_column('B:B', 5)
        worksheet.set_column('C:C', 60)
        worksheet.set_column('E:E', 60)
        worksheet.write(0, 0, 'Offset', header)
        worksheet.write(0, 1, 'Block', header)
        worksheet.write(0, 2, 'Japanese', header)
        worksheet.write(0, 3, 'JP_Len', header)
        worksheet.write(0, 4, 'English', header)
        worksheet.write(0, 5, 'EN_Len', header)
        worksheet.write(0, 6, 'Comments', header)
        row = 1
        for s in sjis_strings:
            loc = '0x' + hex(s[0]).lstrip('0x').zfill(4)
            block = str(s[1])
            jp = s[2].decode('shift_jis_2004')
            #print(type(loc), type(block), type(jp))
            worksheet.write(row, 0, loc)
            worksheet.write(row, 1, block)
            worksheet.write(row, 2, jp)
            #if s[2] is not None:
            #    worksheet.write(row, 4, s[2])
            row += 1
    else:
        print("%s has no game text" % t)

workbook.close()

# TODO:
# 1) What is with the block-100 "te" in a bunch of the AM.TOS files?
    # It's "te"[LN], which is the interpreted bytes 7f 01.
# 2) Still need to identify mystery kanji.
# 7) Why the initial hirigana "ka" at the beginning of the databin TOS files?
# 8) Some stuff in the .PAC doesn't match what's in the final .TOS.
    # 特ッジ (from TOS) vs. 特務隊バッジ (from PAC)
        # Whoops, that's just from when I forgot to include NAMEs in the data tos's.

# 9) Some numbers are getting dropped in HELP.TOS. What's going on there?
    # Those are fine, all the ones that matter have made it in.

# Weird JIS in BT14.TOS:
    # The commands in BT14 are a bit strangely formed.
    # 00 06 - block 06
    # 05 21 80 FF - some commmand
    # 80 DD 27 15 FF - 
        # "FIGHT OFF,BOSS+93,39,21:" has 27 15 as two of its numbers.
# Weird JIS in BM12.TOS:
