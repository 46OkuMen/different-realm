# coding: shift_jis
jis_to_sjis = {}

with open('jis_x_0208.txt', 'rb') as f:
    for lin in f.readlines():
        if lin.startswith(b'#') or len(lin.strip()) == 0:
            continue
        lin = lin.replace(b'0 x', b'0x')   # one kind of weird row here
        if len(lin.split(b'\t')) == 1:
            clean = lin.split(b'0x')[1:]
        else:
            clean = lin.split(b'\t')

        sjis = clean[0].replace(b' ', b'').replace(b'0x', b'')
        jis = clean[1].replace(b' ', b'').replace(b'0x', b'')

        sjis_string = bytes([(int(sjis[:2], 16))]) + bytes([(int(sjis[2:], 16))])
        jis_string = bytes([(int(jis[:2], 16))]) + bytes([(int(jis[2:], 16))])

        jis_to_sjis[jis_string] = sjis_string

#jis_to_sjis[b'\x43\xdc'] = b'\x93\xc1'  # 特, but more like 特務隊バッジ in ITEM.TOS entry 92
#jis_to_sjis[b'\x2a\x87'] = b'\x'

jis_to_sjis[b'\x2d\x36'] = b'\x87\x55'   #  roman numeral two, specific to sjis 2003