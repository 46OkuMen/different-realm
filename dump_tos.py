import re
import os
import xlsxwriter
from tos import decode

workbook_FILENAME = 'DiffRealm_workbook.xlsx'

workbook = xlsxwriter.Workbook(workbook_FILENAME)
header = workbook.add_format({'bold': True, 'align': 'center', 'bottom': True, 'bg_color': 'gray'})

tos_paths = []

for p in os.walk('original\\DIFFEREN'):
    for filename in p[2]:
        if filename.endswith(".TOS") and "parsed" not in filename:
            tos_paths.append(os.path.join(p[0], filename))

### testing
#tos_paths = ['original\\DIFFEREN\\TALK\\AT01.TOS']

for t in tos_paths:
    print t
    decode(t)

    with open(t.replace('.TOS', '_parsed.TOS'), 'rb') as f:
        parsed_tos_blocks = f.readlines()

    sjis_strings = []

    for p in parsed_tos_blocks:
        try:
            block_num = int(p.split("}")[0].lstrip('{'))
        except ValueError:
            block_num = "?"

        sjis_buffer = ''
        cursor = 0

        comment = None
        if '[weird JIS' in p:
            comment = "Weird JIS in this block"

        while cursor < len(p):
            # First byte of SJIS text. Read the next one, too
            if 0x80 <= ord(p[cursor]) & 0Xf0 <= 0x9f:
                #print hex(ord(p[cursor]))
                sjis_buffer += p[cursor]
                cursor += 1
                sjis_buffer += p[cursor]

            # End of continuous SJIS string, so add the buffer to the strings and reset buffer
            else:
                if sjis_buffer:
                    print sjis_buffer
                    sjis_strings.append((block_num, sjis_buffer, comment))
                sjis_buffer = ""
                sjis_buffer_start = cursor+1
            cursor += 1

        # Catch anything left after exiting the loop
        if sjis_buffer:
            sjis_strings.append((sjis_buffer_start, sjis_buffer))

    try:
        worksheet = workbook.add_worksheet(os.path.split(t)[1])
    except AttributeError:
        _ = input("You have the sheet open, close it and hit Enter")
        worksheet = workbook.add_worksheet(GF.filename)

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
        #loc = '0x' + hex(s[0]).lstrip('0x').zfill(4)
        block = s[0]
        jp = s[1].decode('shift-jis')
        worksheet.write(row, 1, block)
        worksheet.write(row, 2, jp)
        if s[2] is not None:
            worksheet.write(row, 4, s[2])
        row += 1

workbook.close()

# TODO:
# 1) What is with the block-100 "te" in a bunch of the AM.TOS files?
# 2) Need to identify mystery kanji.
# 3) Need to dump stuff from DATA.BIN as well.
# 4) Would be nice to calculate offsets too.