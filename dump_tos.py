import re
import os
import sys
import xlsxwriter
from tos import decode_tos, decode_data_tos

workbook_FILENAME = 'DiffRealm_Text.xlsx'

workbook = xlsxwriter.Workbook(workbook_FILENAME)
header = workbook.add_format({'bold': True, 'align': 'center', 'bottom': True, 'bg_color': 'gray'})

useful_ctrl_codes = [b'LN', b'Wait', b'Color', b'PlayerName', b'TxtSpd',
                     b'Spaces', b'Voice', b'Toggle', b'Mouth', b'weird']

garbage = ['て[LN]', 'て', 'てン', 'て[LN]巧砂ン', 'て[LN]沙執ン', 'ン', 'て[LN]患偽ン',
           'て[LN]慨偽ン', 'て[LN]係妓ン', 'て[LN]偽係ン', 'て[LN]品僕ン', 'て[LN]緬様ン',
           'て[LN]８９７６ン', 'て[LN]６７８９ン', 'て[LN]ぁ９８７ン', 'て[LN]７８９ぁン', 
           'て[LN]ぃあぁ９ン', 'てフェダイン特務隊唾', 'ンでユン', 'ヰでヱン', 'ンでャン', '[LN]力０１ン',
           '[LN]０１２３ン', '[LN]５３４２ン', 'ンでデン', 'て[LN]渦', 'て[PlayerName]、。　ン',
           '渦ン', '[VoiceTone1E][TxtSpd2f][Spaces05]', '[VoiceTone1E][TxtSpd2f][Spaces04]',
           '[Color7]', 'て[LN]渦[weird JIS 47 48]ン', 'て[LN][weird JIS 47 48]渦ン',
           'て[LN][weird JIS 46 46][weird JIS 47 48]ン', 'て[LN][weird JIS 45 45][weird JIS 45 45]ン',
           'てフェダイン特務隊唾[weird JIS 68 255]', 'でンでンでンン', 'でパ[weird JIS 39 21]ン',]

if __name__ == '__main__':
    tos_paths = []
    for p in os.walk('original\\REALM'):
        for filename in p[2]:
            if filename.endswith(".TOS") and "parsed" not in filename and "encoded" not in filename and 'unknown' not in filename and 'beginning' not in filename:
                tos_paths.append(os.path.join(p[0], filename))

    file_count = 0

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
                block_num = 0

            if b'wei' in p:
                print("Weird JIS in %s %s" % (t, block_num))

            sjis_buffer = b''
            cursor = 0

            comment = None
            split_here = False

            while cursor < len(p):
                # First byte of SJIS text. Read the next one, too
                if 0x80 <= p[cursor] <= 0x9f or 0xe0 <= p[cursor] <= 0xef:
                    sjis_buffer += bytes([p[cursor]])
                    cursor += 1
                    total_cursor += 1
                    sjis_buffer += bytes([p[cursor]])

                # TODO: Would be nice to include color control codes and such
                elif bytes([p[cursor]]) == b'[':
                    ctrl_code = b''
                    while bytes([p[cursor]]) != b']':
                        ctrl_code += bytes([p[cursor]])
                        cursor += 1
                        total_cursor += 1
                    ctrl_code += bytes([p[cursor]])
                    if any([cc in ctrl_code for cc in useful_ctrl_codes]):
                        sjis_buffer += ctrl_code
                    else:
                        #print("Splitting at %s" % ctrl_code)
                        split_here = True

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
                        sjis_strings.append((total_cursor, block_num, sjis_buffer, comment))
                    sjis_buffer = b""
                    sjis_buffer_start = cursor+1

                # Ran into an unimportant control code
                if split_here:
                    if len(sjis_buffer.strip(b'\x81\x40 ')) > 0:
                        sjis_strings.append((total_cursor, block_num, sjis_buffer, comment))
                    sjis_buffer = b""
                    sjis_buffer_start = cursor+1
                    split_here = False

                cursor += 1
                total_cursor += 1

            # Catch anything left after exiting the loop
            if sjis_buffer:
                sjis_strings.append((total_cursor, block_num, sjis_buffer, comment))

        sjis_strings = [s for s in sjis_strings if s[2].decode('shift_jis_2004') not in garbage]


        if sjis_strings:
            worksheet = workbook.add_worksheet(os.path.split(t)[1])
            file_count += 1

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
            
                if jp in garbage:
                    continue

                worksheet.write(row, 0, loc)
                worksheet.write(row, 1, block)
                worksheet.write(row, 2, jp)
                if s[3] is not None:
                    worksheet.write(row, 6, s[2])
                row += 1
        else:
            print("%s has no game text" % t)

    workbook.close()
    print("%s files" % file_count)

    # TODO:
    # 7) Why the initial hirigana "ka" at the beginning of the databin TOS files?
    # 11) I need to spend more time with the NAMEs to make sure they are accurate.