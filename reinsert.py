import os
from shutil import copyfile
from rominfo import SRC_DISK, DEST_DISK, DEST_DIR, INITIAL_DOS_AUTOEXEC
from romtools.disk import Disk, Gamefile, Block
from romtools.dump import DumpExcel, PointerExcel


DUMP_XLS_PATH = 'DiffRealm_Text.xlsx'
Dump = DumpExcel(DUMP_XLS_PATH)

OriginalDiffRealm = Disk(SRC_DISK)
TargetDiffRealm = Disk(DEST_DISK)

FILES_TO_REINSERT = ['MAIN.EXE']
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
        parsed_gf = Gamefile(gf_path.replace(b'.TOS', b'_parsed.TOS'))

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




#    Some files are compressed with DIET.EXE, a DOS executable compressor.
#    To edit these files:
#        1) Edit the decompressed version, which is already in 'original'.
#        2) Load them into a DOS HDI with DIET.XEXE in the root.
#        3) Add a DIET.EXE command to an AUTOEXEC.BAT script, which is loaded onto the HDI.
#        4) Open the HDI in Neko Project II, which compresses them.
#        5) Extract them from the DOS HDI to the 'patched' folder.
#        6) Insert them into the final Different Realm HDI.


# TODO: Need to use DIETX.COM, which only works on the provided THD image.
#   Modify this code to use that disk instead.
    # The new issue here is that the disk won't seem to open in NDC...

DOS = Disk('Different Realms Source\\PROJECT\\HD-DosRL-NHC.hdi')
with open('np2\\AUTOEXEC.BAT', 'w') as f:
    f.write(INITIAL_DOS_AUTOEXEC)
    for df in DIETED_FILES:
        f.write('DIETX %s' % df)

DOS.insert('np2\\AUTOEXEC.BAT', path_in_disk='', delete_necessary=False)

for filename in DIETED_FILES:
    original_decompressed_file = os.path.join('original', 'decompressed', filename)
    edited_decompressed_file = os.path.join('patched', 'decompressed', filename)
    edited_compressed_file = os.path.join('patched', filename)

    copyfile(original_decompressed_file, edited_decompressed_file)

    gf = Gamefile(edited_decompressed_file, dest_disk=TargetDiffRealm)

    if filename == 'CMAKE.BIN':
        gf.edit(0xa07, b'\x10\xeb\x90')     # name entry cursor illusion
    gf.write(skip_disk=True)

    DOS.insert(edited_decompressed_file, path_in_disk='', delete_necessary=False)

os.system('Different Realms Source\\PROJECT\\np2nt.exe')
os.system('taskkill /IM np2nt.exe')

for filename in DIETED_FILES:
    DOS.extract(filename, dest_path='patched')
    TargetDiffRealm.insert(edited_compressed_file, path_in_disk='REALM')

