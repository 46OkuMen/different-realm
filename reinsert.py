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
                     'databin_files\\NAME.TOS']
DIETED_FILES = ['CMAKE.BIN']

def reinsert(filename):
    path_in_disk = os.path.join('REALM', filename)
    dir_in_disk, just_filename = os.path.split(path_in_disk)
    gf_path = os.path.join('original', 'REALM', filename)
    #if not os.path.isfile(gf_path):
    #    OriginalDiffRealm.extract(filename, path_in_disk='REALM', dest_path='original')
    gf = Gamefile(gf_path, disk=OriginalDiffRealm, dest_disk=TargetDiffRealm)

    # TODO: This currently only inserts MAIN.EXE and nothing else.
    # TOS files get parsed and then inserted. But beware when you add more files.

    if filename == 'MAIN.EXE':
        gf.edit(0x48b8, b'\x1a\x00')  # Read cursor incrementer from static 01
        gf.edit(0x4bb5, b'\x3c\x80')  # Compare to 0x80 instead of 0xad
        gf.edit(0x4bba, b'\x5a\x29')  # Change font table math for lowercase
        gf.edit(0x4bc3, b'\x90\x90\xbb\xa0\x29')  # Change font table math for uppercase
        gf.edit(0x4bd8, b'\xbb\x32\x21')  # Change font table math for something else??

        # TODO: This is actually a change in CMAKE.BIN, right?
        #gf.edit(0x2f5d, b'\x10\xeb\x90')  # Name entry cursor illusion

        gf.write(path_in_disk=dir_in_disk)


    elif filename.split('\\')[-1] in DATA_BIN_FILES:
        parsed_filename = gf_path.replace('.TOS', '_parsed.TOS')
        encoded_filename = parsed_filename.replace('_parsed', '_encoded')
        tos.encode_data_tos(parsed_filename)
        tos.reinsert_data_tos(encoded_filename, 0x89b, 'patched\\ETC\\DATA.BIN')

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

def reinsert_dieted(df):
    """
        DIETED_FILES are compressed with DIETX.EXE, a DOS utility.
        They need to be edited (manually or with a script) and placed in DRSource/PROJECT/HD-DosRL.thd.
        There, run:
            DIETX filename
        Now extract the compressed file and add it to patched/dieted_edited.
        It will be inserted as is at runtime.
    """
    gf_path = os.path.join('patched', 'dieted_edited', df)

    gf = Gamefile(gf_path, disk=OriginalDiffRealm, dest_disk=TargetDiffRealm)
    gf.write(path_in_disk='REALM')


if __name__ == '__main__':
    copyfile('original/REALM/ETC/DATA.BIN', 'patched\\ETC\\DATA.BIN')
    for f in FILES_TO_REINSERT:
        reinsert(f)

    reinsert('ETC\\DATA.BIN')

    for df in DIETED_FILES:
        reinsert_dieted(df)

    #gf.insert('patched/DATA.BIN', path_in_disk='REALM/ETC')