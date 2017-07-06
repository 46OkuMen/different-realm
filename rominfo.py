import os

SRC_DISK = os.path.join('original', 'Different Realm - Kuon no Kenja.hdi')
DEST_DIR = 'patched'
DEST_DISK = os.path.join(DEST_DIR, 'Different Realm - Kuon no Kenja.hdi')

FILES = ['MAIN.EXE',]

FILE_BLOCKS = {}


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
    22: b'\x81\x40', # space
    23: b'\x81\x41', # comma
    24: b'\x81\x42', # hollow period
    25: b'\x81\x43', # comma
    26: b'\x81\x44', # period
    27: b'\x81\x45', # middle dot
    28: b'\x81\x46', # colon
    29: b'\x81\x47', # semicolon
    30: b'\x81\x48', # question mark
    31: b'\x81\x49', # exclamation mark
    32: b'\x81\x5b', # dash thingy TODO: Get the real SJIS code for this
}

CTRL = {
    b'\x01':     '[LN]',
    b'\x04':     ' ',

    b'\x03\x03': b'[ToggleStrWidth]',
    b'\x03\x04': b'[Wait]',
    b'\x03\x16': b'[Mouth16]',
    b'\x03\x17': b'[Mouth17]',
    b'\x03\x18': b'[Mouth18]',
    b'\x03\x1d': b'[SwitchTargetWindow]',

    b'\x03\x1e': b'[VoiceTone1E]',
    b'\x03\x1f': b'[VoiceTone1F]',
    b'\x03\x20': b'[VoiceTone20]',
    b'\x03\x21': b'[VoiceTone21]',
    b'\x03\x22': b'[VoiceTone22]',
    b'\x03\x23': b'[VoiceTone23]',
    b'\x03\x24': b'[VoiceTone24]',
    b'\x03\x25': b'[VoiceTone25]',
    b'\x03\x26': b'[VoiceTone26]',
    b'\x03\x27': b'[VoiceTone27]',

    b'\x03\x28': b'[TxtSpd28]',
    b'\x03\x29': b'[TxtSpd29]',
    b'\x03\x2a': b'[TxtSpd2a]',
    b'\x03\x2b': b'[TxtSpd2b]',
    b'\x03\x2c': b'[TxtSpd2c]',
    b'\x03\x2d': b'[TxtSpd2d]',
    b'\x03\x2e': b'[TxtSpd2e]',
    b'\x03\x2f': b'[TxtSpd2f]',
    b'\x03\x30': b'[TxtSpd30]',
    b'\x03\x31': b'[TxtSpd31]',
    b'\x03\x32': b'[TxtSpd32]',
    b'\x03\x33': b'[TxtSpd33]',
    b'\x03\x34': b'[TxtSpd34]',
    b'\x03\x35': b'[TxtSpd35]',
    b'\x03\x36': b'[TxtSpd36]',
    b'\x03\x37': b'[TxtSpd37]',
    b'\x03\x38': b'[TxtSpd38]',
    b'\x03\x39': b'[TxtSpd39]',
    b'\x03\x3a': b'[TxtSpd3a]',
    b'\x03\x3b': b'[TxtSpd3b]',

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
}


for x in range(90, 256):
    code = b'\x03' + bytes([x])
    CTRL[code] = b'[Wait%i]' % (x - 90)

with open('names-edit.pac', 'rb') as f:
    NAMES = [l.split(b'\x81\x97')[0] for l in f.readlines()]

for x in range(0, 153):
    code = b'\x02' + bytes([x])
    CTRL[code] = NAMES[x-1]


inverse_CTRL = {v: k for k, v in CTRL.items()}

INITIAL_DOS_AUTOEXEC = """PATH A:\DOS;A:\
SET TEMP=A:\DOS
SET DOSDIR=A:\DOS
"""