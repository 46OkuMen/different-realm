import os

SRC_DISK = os.path.join('original', 'Different Realm - Kuon no Kenja.hdi')
DEST_DISK = os.path.join('patched', 'Different Realm - Kuon no Kenja.hdi')

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
    22: '\x81\x40', # space
    23: '\x81\x41', # comma
    24: '\x81\x42', # hollow period
    25: '\x81\x43', # comma
    26: '\x81\x44', # period
    27: '\x82\x45', # middle dot
    28: '\x82\x46', # colon
    29: '\x82\x47', # semicolon
    30: '\x82\x48', # question mark
    31: '\x82\x49', # exclamation mark
    32: '\x82\x4a', # dash thingy TODO: Get the real SJIS code for this
}

CTRL = {
    '\x03\x03': '[ToggleStrWidth]',
    '\x03\x04': '[Wait]',
    '\x03\x16': '[Mouth16]',
    '\x03\x17': '[Mouth17]',
    '\x03\x18': '[Mouth18]',
    '\x03\x1d': '[SwitchTargetWindow]',

    '\x03\x1e': '[VoiceTone1E]',
    '\x03\x1f': '[VoiceTone1F]',
    '\x03\x20': '[VoiceTone20]',
    '\x03\x21': '[VoiceTone21]',
    '\x03\x22': '[VoiceTone22]',
    '\x03\x23': '[VoiceTone23]',
    '\x03\x24': '[VoiceTone24]',
    '\x03\x25': '[VoiceTone25]',
    '\x03\x26': '[VoiceTone26]',
    '\x03\x27': '[VoiceTone27]',

    '\x03\x28': '[TxtSpd28]',
    '\x03\x29': '[TxtSpd29]',
    '\x03\x2a': '[TxtSpd2a]',
    '\x03\x2b': '[TxtSpd2b]',
    '\x03\x2c': '[TxtSpd2c]',
    '\x03\x2d': '[TxtSpd2d]',
    '\x03\x2e': '[TxtSpd2e]',
    '\x03\x2f': '[TxtSpd2f]',
    '\x03\x30': '[TxtSpd30]',
    '\x03\x31': '[TxtSpd31]',
    '\x03\x32': '[TxtSpd32]',
    '\x03\x33': '[TxtSpd33]',
    '\x03\x34': '[TxtSpd34]',
    '\x03\x35': '[TxtSpd35]',
    '\x03\x36': '[TxtSpd36]',
    '\x03\x37': '[TxtSpd37]',
    '\x03\x38': '[TxtSpd38]',
    '\x03\x39': '[TxtSpd39]',
    '\x03\x3a': '[TxtSpd3a]',
    '\x03\x3b': '[TxtSpd3b]',

    '\x03\x3c': '[Spaces03]',
    '\x03\x3d': '[Spaces04]',
    '\x03\x3e': '[Spaces05]',
    '\x03\x3f': '[Spaces06]',
    '\x03\x40': '[Spaces07]',
    '\x03\x41': '[Spaces08]',
    '\x03\x42': '[Spaces09]',
    '\x03\x43': '[Spaces10]',
    '\x03\x44': '[Spaces11]',
    '\x03\x45': '[Spaces12]',
    '\x03\x46': '[Spaces13]',
    '\x03\x47': '[Spaces14]',
    '\x03\x48': '[Spaces15]',
    '\x03\x49': '[Spaces16]',
    '\x03\x4a': '[Spaces17]',
    '\x03\x4b': '[Spaces18]',
    '\x03\x4c': '[Spaces19]',
    '\x03\x4d': '[Spaces20]',
    '\x03\x4e': '[Spaces21]',
    '\x03\x4f': '[Spaces22]',

    '\x03\x50': '[Clear]',
    '\x03\x51': '[Color1]',
    '\x03\x52': '[Color2]',
    '\x03\x53': '[Color3]',
    '\x03\x54': '[Color4]',
    '\x03\x55': '[Color5]',
    '\x03\x56': '[Color6]',
    '\x03\x57': '[Color7]',
    '\x03\x58': '[AnimeSkip]',
}

for x in range(90, 256):
    code = '\x03' + chr(x)
    CTRL[code] = '[Wait%s]' % (x - 90)

for x in range(0, 256):
    code = '\x02' + chr(x)
    CTRL[code] = '[Name%s]' % x
