import os

SRC_DISK = os.path.join('original', 'Different Realm - Kuon no Kenja.hdi')
DEST_DISK = os.path.join('patched', 'Different Realm - Kuon no Kenja.hdi')

from romtools.disk import Disk, Gamefile, Block
from romtools.dump import DumpExcel, PointerExcel


DUMP_XLS_PATH = 'DiffRealm_Text.xlsx'
Dump = DumpExcel(DUMP_XLS_PATH)

OriginalDiffRealm = Disk(SRC_DISK)
TargetDiffRealm = Disk(DEST_DISK)

FILES_TO_REINSERT = ['MAIN.EXE', 'TALK\\AT01.TOS']
DIETED_FILES = ['CMAKE.BIN',]

for filename in FILES_TO_REINSERT:
    path_in_disk = os.path.join('REALM', filename)
    dir_in_disk, just_filename = os.path.split(path_in_disk)
    gf_path = os.path.join('original', 'REALM', filename)
    #if not os.path.isfile(gf_path):
    #    OriginalDiffRealm.extract(filename, path_in_disk='REALM', dest_path='original')
    gf = Gamefile(gf_path, disk=OriginalDiffRealm, dest_disk=TargetDiffRealm)

    if filename == 'MAIN.EXE':
        gf.edit(0x48b8, b'\x1a\x00')  # Read cursor incrementer from static 01
        gf.edit(0x4887, b'\x90\x90')  # Nop out branch, free up 21-4f
        gf.edit(0x487f, b'\x16')      # Change comparison, free up 16-20
        gf.edit(0x4bab, b'\x16')      # Change comparison, free up 16-59
        gf.edit(0x4bba, b'\x5a\x29')  # Change font table math, free up 5a-ff

        #gf.edit(0x2f5d, b'\x10\xeb\x90')  # Name entry cursor illusion

    else:
        parsed_gf = Gamefile(gf_path.replace('.TOS', '_parsed.TOS'))

        for t in Dump.get_translations(just_filename, include_blank=True):
            print(parsed_gf.filestring.count(t.japanese))


    """
    if filename == 'ORTITLE.EXE':
        for block in FILE_BLOCKS[filename]:
            print(block)
            block = Block(gf, block)
            previous_text_offset = block.start
            diff = 0
            #print(repr(block.blockstring))
            for t in Dump.get_translations(block):
                print(t)
                if t.en_bytestring != t.jp_bytestring and len(t.en_bytestring) - len(t.jp_bytestring) == 0:   # TODO: Obviously temporary
                    print(t)
                    loc_in_block = t.location - block.start + diff

                    #print(t.jp_bytestring)
                    i = block.blockstring.index(t.jp_bytestring)
                    j = block.blockstring.count(t.jp_bytestring)

                    index = 0
                    while index < len(block.blockstring):
                        index = block.blockstring.find(t.jp_bytestring, index)
                        if index == -1:
                            break
                        #print('jp bytestring found at', index)
                        index += len(t.jp_bytestring) # +2 because len('ll') == 2

                    #if j > 1:
                    #    print("%s multiples of this string found" % j)
                    assert loc_in_block == i, (hex(loc_in_block), hex(i))

                    block.blockstring = block.blockstring.replace(t.jp_bytestring, t.en_bytestring, 1)

                    gf.edit_pointers_in_range((previous_text_offset, t.location), diff)
                    previous_text_offset = t.location

                    this_diff = len(t.en_bytestring) - len(t.jp_bytestring)
                    diff += this_diff


            block_diff = len(block.blockstring) - len(block.original_blockstring)
            if block_diff < 0:
                block.blockstring += (-1)*block_diff*b'\x00'
            block_diff = len(block.blockstring) - len(block.original_blockstring)
            assert block_diff == 0, block_diff

            block.incorporate()
    """

    gf.write(path_in_disk=dir_in_disk)

for filename in DIETED_FILES:
    pass