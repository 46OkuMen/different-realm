jis_to_sjis = {}

with open('jis_x_0208.txt', 'rb') as f:
    for lin in f.readlines():
        if lin.startswith("#") or len(lin.strip()) == 0:
            continue
        lin = lin.replace('0 x', '0x')   # one kind of weird row here
        if len(lin.split('\t')) == 1:
            clean = lin.split('0x')[1:]
        else:
            clean = lin.split('\t')

        sjis = clean[0].replace(' ', '').replace('0x', '')
        jis = clean[1].replace(' ', '').replace('0x', '')

        sjis_string = chr(int(sjis[:2], 16)) + chr(int(sjis[2:], 16))
        jis_string = chr(int(jis[:2], 16)) + chr(int(jis[2:], 16))

        jis_to_sjis[jis_string] = sjis_string