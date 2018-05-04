import os
from shutil import copyfile
from rominfo import SRC_DISK, DEST_DISK
from romtools.disk import Disk, Gamefile, Block
from romtools.dump import DumpExcel
from glodia import tos

DUMP_XLS_PATH = 'DiffRealm_Text.xlsx'
Dump = DumpExcel(DUMP_XLS_PATH)

OriginalDiffRealm = Disk(SRC_DISK)
TargetDiffRealm = Disk(DEST_DISK)

FILES_TO_REINSERT = ['MAIN.EXE', 'TALK\\AT01.TOS', 'TALK\\SYSTEM.TOS']
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

        pass

    elif filename.endswith('.TOS'):
        parsed_filename = gf_path.replace('.TOS', '_parsed.TOS')
        dest_filename = os.path.join('patched', filename)
        dest_parsed_filename = os.path.join('patched', filename.replace('.TOS', '_parsed.TOS'))

        #copyfile(parsed_filename, dest_parsed_filename)

        # "Reinsert stuff"
        # Really, just make sure the JP strings are in there
        parsed_gf = Gamefile(parsed_filename, disk=OriginalDiffRealm, dest_disk=TargetDiffRealm)
        for t in Dump.get_translations(just_filename, include_blank=True):
            assert parsed_gf.filestring.count(t.japanese) >= 1
            print(t.english)

            if t.english:
                print("There's English here")
                parsed_gf.filestring = parsed_gf.filestring.replace(t.japanese, t.english, 1)

        # Write changes to the file, but not the disk. Still needs encoding
        translated_parsed_filename = parsed_gf.write(skip_disk=True)

        # Now encode the translated result file.
        tos.encode(translated_parsed_filename, dest_filename)

        encoded_gf = Gamefile(dest_filename, disk=OriginalDiffRealm,
                              dest_disk=TargetDiffRealm)
        encoded_gf.write(path_in_disk='REALM\\TALK')


    #gf.write(path_in_disk=dir_in_disk)

"""
    DIETED_FILES are compressed with DIETX.EXE, a DOS utility.
    They need to be edited (manually or with a script) and placed in DRSource/PROJECT/HD-DosRL.thd.
    There, run:
        DIETX filename
    Now extract the compressed file and add it to patched/dieted_edited.
    It will be inserted as is at runtime.
"""
for filename in DIETED_FILES:
    gf_path = os.path.join('patched', 'dieted_edited', filename)

    gf = Gamefile(gf_path, disk=OriginalDiffRealm, dest_disk=TargetDiffRealm)
    gf.write(path_in_disk='REALM')



