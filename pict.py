"""
    Utilities for encoding images as PICT/.IMG files.
    Based on png2win.cpp.
"""

from romtools.disk import Disk
from rominfo import DEST_DISK
from PIL import Image
from bitstring import BitArray
from random import randint

NAMETAG_PALETTE = b'\x00\x03\x33\x38\x40\xf4\x4d\x94\xfb\xac\xb9\xfd\x80\x21\x57\xd0\x66\x87\x3a\xcf\x8b\xff\xff\xff\x00'
TITLE_PALETTE =   b'\x00\x01\x11\x38\x40\xD4\x5C\x94\xFC\xAC\xB9\xEC\x80\x21\x57\xE1\x76\x87\x29\xBC\x7C\xFF\xFF\xFF\x00'
TEFF_PALETTE =    b'\x00\x03\x33\x38\x40\xf4\x4d\x94\xfb\xac\xb9\xfd\x80\x21\x57\xd0\x66\x87\x3a\xcf\x8b\xa6\xaf\xff\x32\x33\x00'
                  # TODO: Why is this longer than the others??

NAMETAG_PALETTE_RGB = [(0x00, 0x00, 0x00),
               (0x33, 0x33, 0x33),
               (0x88, 0x44, 0x33),
               (0xff, 0x44, 0x00),
               (0xdd, 0x99, 0x44),
               (0xff, 0xbb, 0x44),
               (0xcc, 0xbb, 0xaa),
               (0xff, 0xdd, 0x99),
               (0x00, 0x22, 0x88),
               (0x55, 0x77, 0x11),
               (0x00, 0x66, 0xdd),
               (0x88, 0x77, 0x66),
               (0xaa, 0xcc, 0x33),
               (0x88, 0xbb, 0xff),
               (0x00, 0x77, 0x88),
               (0xff, 0xff, 0xff),]

TITLE_PALETTE_RGB = [(0x00, 0x00, 0x00),
               (0x11, 0x11, 0x11),
               (0x88, 0x44, 0x33),     # also 88 44 33,  84 46 38
               (0xdd, 0x44, 0x00),
               (0xcc, 0x99, 0x55),
               (0xff, 0xcc, 0x44),
               (0xcc, 0xbb, 0xaa),
               (0xee, 0xcc, 0x99),
               (0x00, 0x22, 0x88),
               (0x55, 0x77, 0x11),
               (0x11, 0x77, 0xee),
               (0x88, 0x77, 0x66),
               (0x99, 0xbb, 0x22),
               (0x77, 0xcc, 0xcc),
               (0xfa, 0xfa, 0xfa),
               (0xff, 0xff, 0xff),]

TEFF_PALETTE_RGB = [(0x00, 0x00, 0x00),
               (0x33, 0x33, 0x33),
               (0x88, 0x44, 0x33),
               (0xff, 0x44, 0x00),
               (0xdd, 0x99, 0x44),
               (0xff, 0xbb, 0x44),
               (0xcc, 0xbb, 0xaa),
               (0xff, 0xdd, 0x99),
               (0x00, 0x22, 0x88),
               (0x55, 0x77, 0x11),
               (0x00, 0x66, 0xdd),
               (0x88, 0x77, 0x66),
               (0xaa, 0xcc, 0x33),
               (0x88, 0xbb, 0xff),
               (0x66, 0xaa, 0xaa),
               (0xff, 0xff, 0xff),]

def get_closest_color_index(palette, rgb):
    hammings = [255]*16
    for i, color in enumerate(palette):
        hamming = 0
        for val in range(3):
            hamming += abs(color[val] - rgb[val])
        hammings[i] = hamming
    return hammings.index(min(hammings))



NAMETAG_PALETTE_IMAGES = ['BENIMARU', 'GENNAI', 'GENTO', 'HANZOU', 'HEILEE', 'MEIRIN', 'OUGI', 'TAMAMO']
TITLE_PALETTE_IMAGES = ['ORTITLE',]
TEFF_PALETTE_IMAGES = ['TEFF_00A', 'TEFF_0AA', 'TEFF_0BA', 'TEFF_01A', 'TEFF_02A', 'TEFF_03A', 'TEFF_04A', 'TEFF_05A',
                       'TEFF_06A', 'TEFF_07A', 'TEF_08A', 'TEFF_09A', 'TEFF_12A', 'TEFF_13A', 'TEFF_14A', 'TEFF_15A',
                       'TEFF_16A', 'TEFF_17A',]
UNCLASSIFIED = ['SHIROU', 'GENNAIJ', 'GOEMONJ', 'HANZOJ', 'SHIROUJ', 'CHAR_32A', 'NRCHR_99', 'SFCHR_99', 'SFFONT',
                'SFMAP_A', 'SFMAP_B', 'TMAP_01B', 'TMAP_32A', 'XMAP_19']


# Plane activation for each color in the palette.
# Which bit is active there
PLANE_COLORS = [(1, 3, 5, 7, 9, 0xb, 0xd, 0xf),
                (2, 3, 6, 7, 0xa, 0xb, 0xe, 0xf),
                (4, 5, 6, 7, 0xc, 0xd, 0xe, 0xf),
                (8, 9, 0xa, 0xb, 0xc, 0xd, 0xe, 0xf)]


def encode(filename):
    """Encode an image file as GEM and reinsert it."""
    just_filename = filename.split('.')[0]
    img_filename = filename.replace('.png', '.IMG')

    png = Image.open(filename)
    width, height = png.size
    pix = png.load()

    blocks = width // 8


    with open(img_filename, 'wb') as f:
        # PICT header is 16 bytes.
        attr = 0
        f.write(b'PICT ')
        f.write(blocks.to_bytes(1, 'little'))
        if height > 256:
            height_byte = height - 256
            attr |= 0x80
        else:
            height_byte = height
        f.write(height_byte.to_bytes(1, 'little'))
        # color
        f.write(b'\x0f')
        # attr
        #attr = attr | 0x40 | 10
        attr = 0xc5
        f.write(attr.to_bytes(1, 'little'))
        # 9-15: 0, 0, 8, 0, 0, 0, 0
        f.write(b'\x00\x00\x08\x00\x00\x00\x00')

        # Write random garbage
        for x in range(256):
            f.write(x.to_bytes(1, 'little'))

    d = Disk(DEST_DISK)
    d.insert(img_filename, path_in_disk='REALM\\ETC')


    # DEBUG: Insert the one in patched/ instead
    #d.insert('patched\\RLMFR.IMG', path_in_disk='REALM\\ETC')
"""
    if just_filename in NAMETAG_PALETTE_IMAGES:
        print("Using nametag palette")
        palette_bytes = NAMETAG_PALETTE
        palette_rgb = NAMETAG_PALETTE_RGB
    elif just_filename in TITLE_PALETTE_IMAGES:
        print("Using title palette")
        palette_bytes = TITLE_PALETTE
        palette_rgb = TITLE_PALETTE_RGB
    elif just_filename in TEFF_PALETTE_IMAGES:
        print("Using text effect palette")
        palette_bytes = TEFF_PALETTE
        palette_rgb = TEFF_PALETTE_RGB
    else:
        raise Exception

    img = Image.open(filename)
    width, height = img.size
    pix = img.load()

    blocks = img.size[0]//8
    total_rows = blocks*height
    unique_patterns = []
    pattern_locations = {}

    row_cursor = 0
    for b in range(blocks):
        for row in range(height):
            rowdata =[pix[col, row][0:3] for col in range(b*8, (b*8)+8)]

            pattern = []

            for plane in range(4):

                for p in rowdata:
                    try:
                        palette_index = palette_rgb.index(p)
                    except ValueError:
                        palette_index = get_closest_color_index(palette_rgb, p)
                    pattern.append(palette_index in PLANE_COLORS[plane])

            pattern = BitArray(pattern).bytes

            if pattern in unique_patterns:
                pattern_locations[pattern].append(row_cursor)
            else:
                unique_patterns.append(pattern)
                pattern_locations[pattern] = [row_cursor,]

            row_cursor += 1

    IMAGE_DATA_LOCATION = 0x10 + len(palette_bytes) + (len(unique_patterns)*4)

    with open(gem_filename, 'wb') as f:
        f.write(b'Gem')
        f.write(b'\x02\x04\x00\x0e\x00')
        f.write(b'\x30\x00') # not sure what these bytes do. 18 for nametag, 30 for teff, doesn't seem to matter
        f.write(height.to_bytes(2, byteorder='little'))
        f.write(IMAGE_DATA_LOCATION.to_bytes(2, byteorder='little'))
        f.write(b'\x00\x00') # not sure about these either
        f.write(palette_bytes)
        for p in unique_patterns:
            print(p)
            f.write(p)

        row_cursor = 0
        starting_row_cursor = 0

        for i, pattern in enumerate(unique_patterns):
            row_cursor = starting_row_cursor
            chain_count = 0
            print("Start pattern %s. row_cursor: %s" % (pattern, row_cursor))
            for loc in pattern_locations[pattern]:
                if pattern == unique_patterns[0] and loc == 0:
                    row_cursor += 1
                    row_cursor %= total_rows
                    continue

                if loc == row_cursor:
                    chain_count += 1
                else:
                    while chain_count > 31:
                        f.write(b'\x5f')
                        chain_count -= 31
                    while chain_count > 0:
                        chain = 0x40 + chain_count
                        f.write(chain.to_bytes(1, byteorder='little'))
                        chain_count = 0

                    if loc - row_cursor > 16065: # above far skip "ff ff"
                        first_byte = 0x80
                        second_byte = ((loc - row_cursor) + 1) // 256
                        third_byte = ((loc - row_cursor) + 1) % 256
                        f.write(first_byte.to_bytes(1, byteorder='little'))
                        f.write(second_byte.to_bytes(1, byteorder='little'))
                        f.write(third_byte.to_bytes(1, byteorder='little'))


                        if loc == pattern_locations[pattern][0]:
                            starting_row_cursor = loc
                        row_cursor = loc
                        print("Ultra skip: %s %s %s, row_cursor after: %s" % (hex(first_byte), hex(second_byte), hex(third_byte), row_cursor))

                    elif loc - row_cursor >= 63:
                        first_byte = 0xc0 + ((loc - row_cursor) + 1) // 256
                        second_byte = ((loc - row_cursor) + 1) % 256
                        f.write(first_byte.to_bytes(1, byteorder='little'))
                        f.write(second_byte.to_bytes(1, byteorder='little'))

                        if loc == pattern_locations[pattern][0]:
                            starting_row_cursor = loc
                        row_cursor = loc
                        print("Far skip: %s %s, row_cursor after: %s" % (hex(first_byte), hex(second_byte), row_cursor))
                        assert row_cursor == loc
                    elif loc - row_cursor < 63:
                        skip_and_write_code = 0x81 + ((loc - row_cursor) % total_rows)
                        if loc == pattern_locations[pattern][0]:
                            starting_row_cursor = loc
                        f.write(skip_and_write_code.to_bytes(1, byteorder='little'))
                        print("Short skip: %s, row_cursor after: %s" % (hex(skip_and_write_code), row_cursor))
                        row_cursor = loc
                    else:
                        raise Exception

                row_cursor += 1
                row_cursor %= total_rows

            # Catch the last chain
            while chain_count > 31:
                f.write(b'\x5f')
                chain_count -= 31
            while chain_count > 0:
                chain = 0x40 + chain_count
                f.write(chain.to_bytes(1, byteorder='little'))
                chain_count = 0

            f.write(b'\x00')
            starting_row_cursor += 1
            starting_row_cursor %= total_rows

        f.write(b'\x00'*80)  # for good measure. TODO: Still necessary?
    """




if __name__ == '__main__':
    #encode('TEFF_00A.png')
    encode('RLMFR.png')
    #write_spz('TEFF_00A.png', 6)
    #decode_spz('SFCHR_99.SPZ', 'SFCHR_99.png')    # Much more complex
    #decode_spz('TEFF_00A.SPZ', 'TEFF_00A.png')   # Simple and already documented