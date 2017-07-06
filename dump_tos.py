import re
import os
import xlsxwriter
from tos import decode, decode_data_tos

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
        decode(t)

    with open(t.replace('.TOS', '_parsed.TOS'), 'rb') as f:
        parsed_tos_blocks = f.readlines()

    sjis_strings = []
    total_cursor = 0

    for p in parsed_tos_blocks:
        try:
            block_num = int(p.split(b"}")[0].lstrip(b'{'))
        except ValueError:
            block_num = b"?"

        sjis_buffer = b''
        cursor = 0

        comment = None
        #if '[weird JIS' in p:
        #    comment = "Weird JIS in this block"
        print(p)

        while cursor < len(p):
            # First byte of SJIS text. Read the next one, too
            print(sjis_buffer)
            if 0x80 <= p[cursor] & 0Xf0 <= 0x9f:
                print(hex(p[cursor]))
                # TODO: Need to do some better type conversions starting here.
                sjis_buffer += bytes([p[cursor]])
                cursor += 1
                total_cursor += 1
                sjis_buffer += bytes([p[cursor]])

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
                if sjis_buffer:
                    print(sjis_buffer)
                    sjis_strings.append((total_cursor, block_num, sjis_buffer))
                sjis_buffer = ""
                sjis_buffer_start = cursor+1
            cursor += 1
            total_cursor += 1

        # Catch anything left after exiting the loop
        if sjis_buffer:
            sjis_strings.append((sjis_buffer_start, sjis_buffer))

    worksheet = workbook.add_worksheet(os.path.split(t)[1])

    worksheet.set_column('B:B', 5)
    worksheet.set_column('C:C', 60)
    worksheet.set_column('D:D', 60)
    worksheet.write(0, 0, 'Offset', header)
    worksheet.write(0, 1, 'Block', header)
    worksheet.write(0, 2, 'Japanese', header)
    worksheet.write(0, 3, 'English', header)
    worksheet.write(0, 4, 'Comments', header)
    row = 1
    for s in sjis_strings:
        loc = '0x' + hex(s[0]).lstrip('0x').zfill(4)
        block = s[1]
        jp = s[2].decode('shift-jis')
        worksheet.write(row, 0, loc)
        worksheet.write(row, 1, block)
        worksheet.write(row, 2, jp)
        #if s[2] is not None:
        #    worksheet.write(row, 4, s[2])
        row += 1

workbook.close()

# TODO:
# 1) What is with the block-100 "te" in a bunch of the AM.TOS files?
    # It's "te"[LN], which is the interpreted bytes 7f 01.
# 2) Need to identify mystery kanji.
# 4) Would be nice to calculate offsets too.