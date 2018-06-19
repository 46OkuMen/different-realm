import os
from shutil import copyfile
from rominfo import SRC_DISK, DEST_DISK, DATA_BIN_FILES
from romtools.disk import Disk, Gamefile, Block
from romtools.dump import DumpExcel
from glodia import tos

DUMP_XLS_PATH = 'DiffRealm_Text.xlsx'
Dump = DumpExcel(DUMP_XLS_PATH)

OriginalDiffRealm = Disk(SRC_DISK)
TargetDiffRealm = Disk(DEST_DISK)

FILES_TO_REINSERT = ['MAIN.EXE', 'TALK\\AT01.TOS', 'TALK\\SYSTEM.TOS', 'TALK\\HELP.TOS',
                     'MAP\\AM01.TOS', 'databin_files\\NAME.TOS', 'CMAKE.BIN']
#FILES_TO_REINSERT = ['MAP\\AM01.TOS']
#DIETED_FILES = []

def reinsert(filename):
    path_in_disk = os.path.join('REALM', filename)
    dir_in_disk, just_filename = os.path.split(path_in_disk)
    gf_path = os.path.join('original', 'REALM', filename)
    #if not os.path.isfile(gf_path):
    #    OriginalDiffRealm.extract(filename, path_in_disk='REALM', dest_path='original')
    gf = Gamefile(gf_path, disk=OriginalDiffRealm, dest_disk=TargetDiffRealm)

    if filename == 'MAIN.EXE':
        gf.edit(0x48b8, b'\x1a\x00')  # Read cursor incrementer from static 01
        gf.edit(0x4bb5, b'\x3c\x80')  # Compare to 0x80 instead of 0xad
        gf.edit(0x4bba, b'\x5a\x29')  # Change font table math for lowercase
        gf.edit(0x4bc3, b'\x90\x90\xbb\xa0\x29')  # Change font table math for uppercase
        gf.edit(0x4bd8, b'\xbb\x32\x21')  # Change font table math for something else??

        gf.edit(0x296, b'\xb3\xd4\xcf\xc3\xcb\xcd\xc1\xce')  # eto[ -> Stockman

        # TODO: This is actually a change in CMAKE.BIN, right?
        #gf.edit(0x2f5d, b'\x10\xeb\x90')  # Name entry cursor illusion

        gf.write(path_in_disk=dir_in_disk)

    elif filename == 'CMAKE.BIN':
        gf.edit(0xaaa, b'\x08')      # Init name with 8 underscores, not 6
        gf.edit(0x624, b'\xb3\xd4\xcf\xc3\xcb\xcd\xc1\xce')  # Stockman replacement when re-entering menu
        gf.edit(0x5e6, b'\x08')      # Copy all 8 chars of "Stockman" when re-entering menu
        gf.edit(0x9f0, b'\x08')      # Enable entry past 6 characters to 8
        gf.edit(0xda9, b'\xbf')      # Use "_" as blank character, not "I"
        gf.edit(0xdad, b'\x00')      # Fix invisible "J"
        gf.edit(0xaef, b'\x90\x90')  # Fix "creeping underscore" bug

        gf.edit(0x9fd, b'\x02\xdd\x02\xdd\x66\x91\xb1\x1c\xf6\xe1\x03\xd8\x90') 
        # Cursor-to-character math edit.
        # Basically we want to add 2(ch) + 1c(cl) to ebx
        # 
        # add bl, ch
        # add bl, ch
        # xchg eax, ecx
        # mov cl, 1c
        # mul cl
        # add bx, ax
        # nop

        #gf.edit(0xa07, b'\x10\xeb\x90')  # Cursor illusion (Superceded by bigger math edit)

        # Other things that were edited in the dieted file but don't seem to affect anything
        #gf.edit(0x600, b'\x08')      # ?
        #gf.edit(0x633, b'\x08')      # ?
        #gf.edit(0x64f, b'\x08')      # ?
        #gf.edit(0xabb, b'\x08')      # ?

        #gf.edit(0x84d, b'\x08')      # ?
        #gf.edit(0x850, b'\x08')      # ?

        gf.write(path_in_disk=dir_in_disk)

    elif filename.split('\\')[-1] in DATA_BIN_FILES:
        parsed_filename = gf_path.replace('.TOS', '_parsed.TOS')

        parsed_gf = Gamefile(parsed_filename, disk=OriginalDiffRealm, dest_disk=TargetDiffRealm)
        print(filename)
        for t in Dump.get_translations(just_filename, include_blank=True):
            assert parsed_gf.filestring.count(t.japanese) >= 1
            print(t.english)
            if t.english:
                print("There's English here")
                parsed_gf.filestring = parsed_gf.filestring.replace(t.japanese, t.english, 1)

        # Write changes to the file, but not the disk. Still needs encoding
        translated_parsed_filename = parsed_gf.write(skip_disk=True)

        encoded_filename = os.path.join('patched', filename)
        print(encoded_filename)
        tos.encode_data_tos(translated_parsed_filename, encoded_filename)
        #tos.reinsert_data_tos(encoded_filename, 0x89b, 'patched\\ETC\\DATA.BIN')

    elif 'DATA.BIN' in filename:
        tos.write_data_tos('original\\REALM\\ETC\\DATA.BIN', 'patched\\ETC\\DATA.BIN')
        dest_filename = os.path.join('patched', filename)
        gf = Gamefile(dest_filename, disk=OriginalDiffRealm, dest_disk=TargetDiffRealm)
        gf.write(path_in_disk='REALM\\ETC')

    elif filename.endswith('.TOS'):
        parsed_filename = gf_path.replace('.TOS', '_parsed.TOS')
        dest_filename = os.path.join('patched', filename)
        dest_parsed_filename = os.path.join('patched', filename.replace('.TOS', '_parsed.TOS'))

        #copyfile(parsed_filename, dest_parsed_filename)

        # "Reinsert stuff"
        parsed_gf = Gamefile(parsed_filename, disk=OriginalDiffRealm, dest_disk=TargetDiffRealm)
        print(filename)
        for t in Dump.get_translations(just_filename, include_blank=True):
            print(filename, t.location, t.japanese)
            assert parsed_gf.filestring.count(t.japanese) >= 1
            print(t.english)

            if t.english:
                print("There's English here")
                parsed_gf.filestring = parsed_gf.filestring.replace(t.japanese, t.english, 1)

        # Write changes to the file, but not the disk. Can only reinsert after encoding
        translated_parsed_filename = parsed_gf.write(skip_disk=True)

        # Now encode the translated result file.
        tos.encode(translated_parsed_filename, dest_filename)

        encoded_gf = Gamefile(dest_filename, disk=OriginalDiffRealm,
                              dest_disk=TargetDiffRealm)
        if encoded_gf.filename[1] == 'T' or encoded_gf.filename in ['SYSTEM.TOS', 'HELP.TOS']:
            encoded_gf.write(path_in_disk='REALM\\TALK')
        elif encoded_gf.filename[1] == 'M':
            encoded_gf.write(path_in_disk='REALM\\MAP')
        else:
            print(encoded_gf.filename)
            raise Exception

#def reinsert_dieted(df):
#    """
#        DIETED_FILES are compressed with DIETX.EXE, a DOS utility.
#        They need to be edited (manually or with a script) and placed in DRSource/PROJECT/HD-DosRL.thd.
#        There, run:
#            DIETX filename
#        Now extract the compressed file and add it to patched/dieted_edited.
#        It will be inserted as is at runtime.
#    """
#    gf_path = os.path.join('patched', 'dieted_edited', df)
#
#    gf = Gamefile(gf_path, disk=OriginalDiffRealm, dest_disk=TargetDiffRealm)
#    gf.write(path_in_disk='REALM')


if __name__ == '__main__':
    copyfile('original/REALM/ETC/DATA.BIN', 'patched\\ETC\\DATA.BIN')
    for f in FILES_TO_REINSERT:
        reinsert(f)

    reinsert('ETC\\DATA.BIN')

    #for df in DIETED_FILES:
    #    reinsert_dieted(df)

    #gf.insert('patched/DATA.BIN', path_in_disk='REALM/ETC')