import os

SRC_DISK = os.path.join('original', 'Different Realm - Kuon no Kenja.hdi')
DEST_DIR = 'patched'
DEST_DISK = os.path.join(DEST_DIR, 'Different Realm - Kuon no Kenja.hdi')

FILES = ['MAIN.EXE',]

FILE_BLOCKS = {}

DATA_BIN_FILES = ['ITEM.TOS', 'MONSTER.TOS', 'NAME.TOS', 'WORD.TOS']

DATA_BIN_MAP = {
    'beginning': 0x0,
    'NAME.TOS': 0x89b,
    'ITEM.TOS': 0xba7,
    'unknown': 0x1392,
    'unknown2': 0x18f5,
    'WORD.TOS': 0x1987,
    'MONSTER.TOS': 0x1b07,
}

"""
    TOS Specification
        2,N     : replaced by strings-table'[N]' (NAME.TOS)
        3,3     : Switch string size Half/Wide
        3,4     : Wait Any Key
        3,22-24 : Mouth set
        3,29    : Switch target window
        3,30-39 : Voice Tone set
        3,40-59 : Text Speed
        3,60-79 : Text Space(wide) (60:3space .. 79:22space)
        3,80    : Order Text Clear
        3,81-87 : Set Text Color
        3,88    : Set Anime Skip
        3,90-255: Wait time
"""

MARKS = {
    22: b'\x81\x40',  # space
    23: b'\x81\x41',  # comma
    24: b'\x81\x42',  # hollow period
    25: b'\x81\x43',  # comma
    26: b'\x81\x44',  # period
    27: b'\x81\x45',  # middle dot
    28: b'\x81\x46',  # colon
    29: b'\x81\x47',  # semicolon
    30: b'\x81\x48',  # question mark
    31: b'\x81\x49',  # exclamation mark
    32: b'\x81\x5b',  # dash thingy TODO: Get the real SJIS code for this
}

CTRL = {
    b'\x01':     b'[LN]',
    b'\x04':     b' ',

    b'\x03\x03': b'[FW]',
    b'\x03\x04': b'[Input]',
    b'\x03\x16': b'[Mouth16]',
    b'\x03\x17': b'[Mouth17]',
    b'\x03\x18': b'[Mouth18]',
    b'\x03\x1d': b'[SwitchTargetWindow]',

    b'\x03\x1e': b'[Voice1E]',
    b'\x03\x1f': b'[Voice1F]',
    b'\x03\x20': b'[Voice20]',
    b'\x03\x21': b'[Voice21]',
    b'\x03\x22': b'[Voice22]',
    b'\x03\x23': b'[Voice23]',
    b'\x03\x24': b'[Voice24]',
    b'\x03\x25': b'[Voice25]',
    b'\x03\x26': b'[Voice26]',
    b'\x03\x27': b'[Voice27]',

    # Lower is faster. 28 is instantaneous
    b'\x03\x28': b'[Spd28]',
    b'\x03\x29': b'[Spd29]',
    b'\x03\x2a': b'[Spd2a]',
    b'\x03\x2b': b'[Spd2b]',
    b'\x03\x2c': b'[Spd2c]',
    b'\x03\x2d': b'[Spd2d]',
    b'\x03\x2e': b'[Spd2e]',
    b'\x03\x2f': b'[Spd2f]',
    b'\x03\x30': b'[Spd30]',
    b'\x03\x31': b'[Spd31]',
    b'\x03\x32': b'[Spd32]',
    b'\x03\x33': b'[Spd33]',
    b'\x03\x34': b'[Spd34]',
    b'\x03\x35': b'[Spd35]',
    b'\x03\x36': b'[Spd36]',
    b'\x03\x37': b'[Spd37]',
    b'\x03\x38': b'[Spd38]',
    b'\x03\x39': b'[Spd39]',
    b'\x03\x3a': b'[Spd3a]',
    b'\x03\x3b': b'[Spd3b]',

    # Note that these are decimal, for easier use
    b'\x03\x3c': b'[Spaces03]',
    b'\x03\x3d': b'[Spaces04]',
    b'\x03\x3e': b'[Spaces05]',
    b'\x03\x3f': b'[Spaces06]',
    b'\x03\x40': b'[Spaces07]',
    b'\x03\x41': b'[Spaces08]',
    b'\x03\x42': b'[Spaces09]',
    b'\x03\x43': b'[Spaces10]',
    b'\x03\x44': b'[Spaces11]',
    b'\x03\x45': b'[Spaces12]',
    b'\x03\x46': b'[Spaces13]',
    b'\x03\x47': b'[Spaces14]',
    b'\x03\x48': b'[Spaces15]',
    b'\x03\x49': b'[Spaces16]',
    b'\x03\x4a': b'[Spaces17]',
    b'\x03\x4b': b'[Spaces18]',
    b'\x03\x4c': b'[Spaces19]',
    b'\x03\x4d': b'[Spaces20]',
    b'\x03\x4e': b'[Spaces21]',
    b'\x03\x4f': b'[Spaces22]',

    b'\x03\x50': b'[Clear]',
    b'\x03\x51': b'[Color1]',
    b'\x03\x52': b'[Color2]',
    b'\x03\x53': b'[Color3]',
    b'\x03\x54': b'[Color4]',
    b'\x03\x55': b'[Color5]',
    b'\x03\x56': b'[Color6]',
    b'\x03\x57': b'[Color7]',
    b'\x03\x58': b'[AnimeSkip]',

    b'\x05\x39': b'[MapName]',
    b'\x00':     b'[MapNameEnd]',

    b'\x09\x0a\xff': b'[WindowUp]',
    b'\x09\x0b\xff': b'[WindowDown]',
    #b'\x0a\x08\x0a\xff': b'[PortraitUp]',
    #b'\x0a\x09\x0a\xff': b'[PortraitDown]',
}


for x in range(90, 256):
    code = b'\x03' + bytes([x])
    CTRL[code] = b'[Wait%i]' % (x - 90)

with open('names-edit.pac', 'rb') as f:
    NAMES = [l.split(b'\x81\x97')[0] for l in f.readlines()]
NAMES[21] = b'[PlayerName]'

#for i, n in enumerate(NAMES):
#    print(i, n.decode('shift-jis'))


for x in range(0, 153):
    code = b'\x02' + bytes([x])
    CTRL[code] = NAMES[x-1]


inverse_CTRL = {v: k for k, v in CTRL.items()}
inverse_MARKS = {v: k for k, v in MARKS.items()}

# (Lower speed number = faster)
SPEED_INCREASES = {
    b'[Spd28]': b'[Spd28]',  # Instant
    b'[Spd29]': b'[Spd29]',
    b'[Spd2a]': b'[Spd29]',
    b'[Spd2b]': b'[Spd29]',
    b'[Spd2c]': b'[Spd29]',
    b'[Spd2d]': b'[Spd29]',
    b'[Spd2e]': b'[Spd29]',
    b'[Spd2f]': b'[Spd29]',
    b'[Spd30]': b'[Spd29]',
    b'[Spd31]': b'[Spd29]',
    b'[Spd32]': b'[Spd29]',
    b'[Spd33]': b'[Spd29]',
    b'[Spd34]': b'[Spd29]',
    b'[Spd35]': b'[Spd29]',
    b'[Spd36]': b'[Spd29]',
    b'[Spd37]': b'[Spd29]',
    b'[Spd38]': b'[Spd29]',
    b'[Spd39]': b'[Spd29]',
    b'[Spd3a]': b'[Spd29]',
    b'[Spd3b]': b'[Spd29]',
}

WINDOW_WIDTH = {
    'FULL':     32,  # 34 with punctuation
    'PORTRAIT': 28,  # 28 with punctuation
}
