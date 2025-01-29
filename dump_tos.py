import os
import xlsxwriter
from tos import decode_tos, decode_data_tos
from rominfo import WINDOW_WIDTH, inverse_MARKS


class RealmString:
    def __init__(self, string, suffix, location, block_num, window_width, window_position, comment):
        self.string = string
        self.suffix = suffix
        self.location = location
        self.block_num = block_num
        self.window_width = window_width
        self.window_position = window_position
        self.comment = comment


class WindowLayout:
    """
        Keeps track of which type of window is being written to.
    """
    def __init__(self):
        self.upper = WINDOW_WIDTH["FULL"]
        self.lower = 99

        self.current_window = self.upper
        self.char_width = 2

    def switchCurrentWindow(self):
        #print("switchCurrentWindow called")
        if self.current_window == self.upper:
            self.current_window = self.lower
        elif self.current_window == self.lower:
            self.current_window = self.upper

    def getCurrentWidth(self):
        #print(self.upper, self.lower)
        if self.current_window == self.upper:
            return self.upper
        elif self.current_window == self.lower:
            return self.lower

    def getCurrentWindow(self):
        #print(self.upper, self.lower)
        if self.current_window == self.upper:
            return "upper"
        elif self.current_window == self.lower:
            return "lower"
        else:
            return None

    def createWindow(self, location, portrait=False):
        #print("Creating window")
        if portrait:
            width = WINDOW_WIDTH["PORTRAIT"]
        else:
            width = WINDOW_WIDTH["FULL"]

        if location == "upper":
            self.upper = width
            self.current_window = self.upper
        else:
            self.lower = width
            self.current_window = self.lower

    def switchCharWidth(self):
        if self.char_width == 2:
            self.char_width = 1
        elif self.char_width == 1:
            self.char_width = 2

    def getCharWidth(self):
        return self.char_width


def rchop(s, sub):
    return s[:-len(sub)] if s.endswith(sub) else s


def strip_terminal_codes(s):
    """
        Remove all ctrl codes from the end of a string.
    """
    while s.endswith(b']'):
        #print(s)
        s = b'['.join(s.split(b'[')[0:-1])
        #print(s)
    return s


def get_terminal_codes(s):
    result = b''
    while s.endswith(b']'):
        #print(s)
        last_code = b'[' + s.split(b'[')[-1]
        result = last_code + result  # Append to beginning
        s = rchop(s, last_code)
        #print(s)
    #print(result)
    return result


def is_natural_ending(s):
    """
        Does this string have a control code that naturally ends it?
    """
    termcodes = get_terminal_codes(s)
    for code in (b'[LN]', b'[Clear]', b'[Input]', b'[WindowUp]', b'[WindowDown]',
                 b'[PortraitUp]', b'[PortraitDown]'):
        if code in termcodes:
            #print(s, "has a natural ending with", code)
            #input()
            return True
    return False


workbook_FILENAME = 'DiffRealm_Text.xlsx'

workbook = xlsxwriter.Workbook(workbook_FILENAME)
header = workbook.add_format({'bold': True, 'align': 'center', 'bottom': True, 'bg_color': 'gray'})

useful_ctrl_codes = [b'Color', b'PlayerName', b'Spd', b'Voice', b'Mouth', b'Wait', b'LN', b'Input', b'Clear',
                     b'Spaces', b'FW', b'weird']

system_files = ['SYSTEM.TOS', 'HELP.TOS', 'INFO.TOS', 'INFP.TOS']

garbage = ['て[LN]', 'て', 'てン', 'て[LN]巧砂ン', 'て[LN]沙執ン', 'ン', 'て[LN]患偽ン',
           'て[LN]慨偽ン', 'て[LN]係妓ン', 'て[LN]偽係ン', 'て[LN]品僕ン', 'て[LN]緬様ン',
           'て[LN]８９７６ン', 'て[LN]６７８９ン', 'て[LN]ぁ９８７ン', 'て[LN]７８９ぁン', 
           'て[LN]ぃあぁ９ン', 'てフェダイン特務隊唾', 'ンでユン', 'ヰでヱン', 'ンでャン', '[LN]力０１ン',
           '[LN]０１２３ン', '[LN]５３４２ン', 'ンでデン', 'て[LN]渦', 'て[PlayerName]、。　ン',
           '渦ン', '[Voice1E][Spd2f][Spaces05]', '[Voice1E][Spd2f][Spaces04]',
           '[Color7]', 'て[LN]渦[weird JIS 47 48]ン', 'て[LN][weird JIS 47 48]渦ン',
           'て[LN][weird JIS 46 46][weird JIS 47 48]ン', 'て[LN][weird JIS 45 45][weird JIS 45 45]ン',
           'てフェダイン特務隊唾[weird JIS 68 255]', 'でンでンでンン', 'でパ[weird JIS 39 21]ン',]

if __name__ == '__main__':
    tos_paths = []
    for p in os.walk('original\\REALM'):
        for filename in p[2]:
            if filename.endswith(".TOS") and "parsed" not in filename and "encoded" not in filename and 'unknown' not in filename and 'beginning' not in filename:
                tos_paths.append(os.path.join(p[0], filename))

    testing = False

    if testing:
        tos_paths = ['original\\REALM\\TALK\\AT01.TOS',]
    else:
        # Put the system files at the front of the dump
        for sysfile in ['original\\REALM\\TALK\\' + s for s in ('HELP.TOS', 'INFP.TOS', 'INFO.TOS', 'SYSTEM.TOS')]:
            tos_paths.remove(sysfile)
            tos_paths.insert(0, sysfile)

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
            onscreen_length = 0
            suffix = b''

            window_layout = WindowLayout()

            #window = WINDOW_WIDTH["FULL"]
            comment = None
            split_here = False

            while cursor < len(p):

                # First byte of SJIS text. Read the next one, too
                if 0x80 <= p[cursor] <= 0x9f or 0xe0 <= p[cursor] <= 0xef:
                    sjis_buffer += bytes([p[cursor]])
                    cursor += 1
                    total_cursor += 1
                    sjis_buffer += bytes([p[cursor]])
                    onscreen_length += window_layout.getCharWidth()

                elif bytes([p[cursor]]) == b'[':
                    ctrl_code = b''
                    # Read the entire control code (to the terminal ])
                    while bytes([p[cursor]]) != b']':
                        ctrl_code += bytes([p[cursor]])
                        cursor += 1
                        total_cursor += 1
                    ctrl_code += bytes([p[cursor]])

                    """
                    Nametags start with one of these:
                    [SwitchTargetWindow], [WindowUp], [WindowDown], 
                    [Clear], [PortraitUpXX], [PortraitDownXX] 
                    or they just start immediately in a text block.

                    They are always followed by [LN][VoiceXX]
                    """

                    # Important, common control codes get put in, and need a split possibly
                    if any([cc in ctrl_code for cc in useful_ctrl_codes]):
                        # Don't put control codes at the beginning
                        if len(sjis_buffer) > 0:
                            sjis_buffer += ctrl_code
                            if ctrl_code == b'[LN]':
                                #print(p[cursor+1:cursor+30])
                                # Lookahead - if the next one is [VoiceXX], this is a nametag
                                if p[cursor+1:].startswith(b"[Voice"):
                                    # Lookbehind - if the text right before the [LN] was SJIS
                                    #print(p[cursor-5:cursor])
                                    #print(hex(p[cursor-5]))
                                    if 0x80 <= p[cursor-5] <= 0x9f or 0xe0 <= p[cursor-5] <= 0xef:
                                        print("Nametag")
                                        split_here = True

                                        lookahead_cursor = cursor + 1

                                        # Add the rest of the control codes via a lookahead, so they get put in the suffix column
                                        while bytes([p[lookahead_cursor]]) == b'[':
                                            ctrl_code = b''
                                            while bytes([p[lookahead_cursor]]) != b']':
                                                ctrl_code += bytes([p[lookahead_cursor]])
                                                lookahead_cursor += 1

                                            ctrl_code += bytes([p[lookahead_cursor]])
                                            sjis_buffer += ctrl_code

                                            lookahead_cursor += 1
                                        print(sjis_buffer)
                                        print("")
                                    else:
                                        split_here = False
                                else:
                                    split_here = False
                            elif ctrl_code == b'[Input]':
                                split_here = True
                            elif ctrl_code == b'[Clear]':
                                split_here = True
                            elif ctrl_code == b'[FW]':
                                window_layout.switchCharWidth()

                    # Window control codes
                    # "WIN 10"
                    elif b'WindowUp' in ctrl_code:
                        window_layout.createWindow(location="upper", portrait=False)
                        sjis_buffer += ctrl_code
                        split_here = True

                    # "WIN 11"
                    elif b'WindowDown' in ctrl_code:
                        window_layout.createWindow(location="lower", portrait=False)
                        sjis_buffer += ctrl_code
                        split_here = True

                    # "PICT UP" (10?)
                    elif b'PortraitUp' in ctrl_code:
                        window_layout.createWindow(location="upper", portrait=True)
                        sjis_buffer += ctrl_code
                        split_here = True

                    # "PICT LOW" (8?)
                    elif b'PortraitDown' in ctrl_code:
                        window_layout.createWindow(location="lower", portrait=True)
                        sjis_buffer += ctrl_code
                        split_here = True

                    elif b'SwitchTargetWindow' in ctrl_code:
                        window_layout.switchCurrentWindow()
                        sjis_buffer += ctrl_code
                        split_here = True
                    else:
                        #print("Splitting at %s" % ctrl_code)
                        split_here = True

                # ASCII space, too
                elif p[cursor] == 0x20:
                    sjis_buffer += bytes([p[cursor]])
                    onscreen_length += 1

                elif p[cursor:cursor+4] == b'[wei':
                    while bytes([p[cursor]]) != b']':
                        sjis_buffer += bytes([p[cursor]])
                        cursor += 1
                        total_cursor += 1
                    sjis_buffer += b']'

                # End of continuous SJIS string, so add the buffer to the strings and reset buffer
                else:
                    if is_natural_ending(sjis_buffer):
                        suffix = get_terminal_codes(sjis_buffer)
                    sjis_buffer = strip_terminal_codes(sjis_buffer)
                    if len(sjis_buffer.strip(b'\x81\x40 ')) > 0:
                        sjis_strings.append(RealmString(string=sjis_buffer, location=total_cursor,
                                                        block_num=block_num, window_width=window_layout.getCurrentWidth(),
                                                        window_position=window_layout.getCurrentWindow(), comment=comment,
                                                        suffix=suffix))

                    # Clear buffer, etc
                    sjis_buffer = b""
                    sjis_buffer_start = cursor+1
                    onscreen_length = 0
                    suffix = b''

                # If it's not a system file, break after (window) characters

                if not any([s in t for s in system_files]):
                    if window_layout.getCurrentWindow() is not None:
                        if onscreen_length >= window_layout.getCurrentWidth():
                            #print(p[cursor+1:cursor+20])
                            if p[cursor+1:cursor+3] in inverse_MARKS:
                                #print(p[cursor+1:cursor+3])
                                #print("Next char is a mark, so it gets one more character")
                                #print(onscreen_length)
                                pass
                            elif p[cursor+1:cursor+8] == b'[Input]':
                                # Don't try to typeset before an [Input] code
                                #print("It's an Input, so continuing")
                                pass
                            elif p[cursor+1:cursor+6] == b'[Wait':
                                #print("It's a wait, so continuing")
                                pass
                            elif p[cursor+1:cursor+8] == b'[Window':
                                #print("It's a window, so continuing")
                                pass
                            elif p[cursor+1:cursor+10] == b'[Portrait':
                                #print("It's a portrait, so continuing")
                                pass
                            elif p[cursor+1:].startswith(b'[LN][Voice'):
                                #print("It's a nametag")
                                #print("")
                                split_here = True
                                suffix = p[cursor+1:cursor+14]
                            #else:
                            #    split_here = True
                            #    suffix += b'[LN]'

                # Ran into an unimportant control code
                if split_here:
                    if is_natural_ending(sjis_buffer):
                        suffix = get_terminal_codes(sjis_buffer)
                    sjis_buffer = strip_terminal_codes(sjis_buffer)
                    if len(sjis_buffer.strip(b'\x81\x40 ')) > 0:
                        sjis_strings.append(RealmString(string=sjis_buffer, location=total_cursor,
                                                        block_num=block_num, window_width=window_layout.getCurrentWidth(),
                                                        window_position=window_layout.getCurrentWindow(), comment=comment,
                                                        suffix=suffix))
                    sjis_buffer = b""
                    sjis_buffer_start = cursor+1
                    onscreen_length = 0
                    split_here = False
                    suffix = b''

                cursor += 1
                total_cursor += 1

            # Catch anything left after exiting the loop
            if sjis_buffer:
                if is_natural_ending(sjis_buffer):
                    suffix = get_terminal_codes(sjis_buffer)
                sjis_buffer = strip_terminal_codes(sjis_buffer)
                sjis_strings.append(RealmString(string=sjis_buffer, location=total_cursor,
                                                block_num=block_num, window_width=window_layout.getCurrentWidth(),
                                                window_position=window_layout.getCurrentWindow(), comment=comment,
                                                suffix=suffix))

        sjis_strings = [s for s in sjis_strings if s.string.decode('shift_jis_2004') not in garbage]

        if sjis_strings:
            worksheet = workbook.add_worksheet(os.path.split(t)[1])
            file_count += 1

            worksheet.write(0, 0, 'Offset', header)

            # Block column should be narrow
            worksheet.set_column('B:B', 5)
            worksheet.write(0, 1, 'Block', header)

            # Window column should be narrow
            worksheet.set_column('C:C', 5)
            worksheet.write(0, 2, 'Width', header)

            worksheet.set_column('D:D', 7)
            worksheet.write(0, 3, "Window", header)

            # JP column should be wide
            worksheet.set_column('E:E', 60)
            worksheet.write(0, 4, 'Japanese', header)

            # JP_LEN column
            worksheet.set_column('F:F', 5)
            worksheet.write(0, 5, 'JP_Len', header)

            # EN column
            worksheet.set_column('G:G', 60)
            worksheet.write(0, 6, 'English', header)

            # EN_LEN column
            worksheet.set_column('H:H', 5)
            worksheet.write(0, 7, 'EN_Len', header)

            # Suffix column
            worksheet.write(0, 8, 'Suffix', header)

            # Comments column
            worksheet.write(0, 9, 'Comments', header)
            row = 1
            for s in sjis_strings:

                loc = '0x' + hex(s.location).lstrip('0x').zfill(4)
                block = str(s.block_num)
                jp = s.string.decode('shift_jis_2004')
                width = str(s.window_width)
                window = str(s.window_position)
                comment = str(s.comment)
                suffix = s.suffix.decode('shift_jis_2004')

                if jp in garbage:
                    continue

                worksheet.write(row, 0, loc)
                worksheet.write(row, 1, block)
                worksheet.write(row, 2, width)
                worksheet.write(row, 3, window)
                worksheet.write(row, 4, jp)

                # Also write JP to the EN column, per kuoushi request
                worksheet.write(row, 6, jp)

                # Add the JP/EN length formulas.
                # TODO: Get a regex for this to ignore bracketed stuff
                # Excel can't do regex like GSheets...
                worksheet.write(row, 5, "=LEN(E%s)" % str(row+1))
                worksheet.write(row, 7, "=LEN(G%s)" % str(row+1))

                worksheet.write(row, 8, suffix)

                if s.comment is not None:
                    worksheet.write(row, 9, comment)
                row += 1
        else:
            print("%s has no game text" % t)

    workbook.close()
    print("%s files" % file_count)

    # TODO:
    # 7) Why the initial hirigana "ka" at the beginning of the databin TOS files?
    # 11) I need to spend more time with the NAMEs to make sure they are accurate.