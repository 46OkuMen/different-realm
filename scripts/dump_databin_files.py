import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # project root, for rominfo

from rominfo import DATA_BIN_MAP as DBM

with open('original\\REALM\\ETC\\DATA.BIN', 'rb') as f:
	original = f.read()

	beginning = original[0:DBM['NAME.TOS']]
	name = original[DBM['NAME.TOS']:DBM['ITEM.TOS']]
	item = original[DBM['ITEM.TOS']:DBM['unknown']]
	unknown = original[DBM['unknown']:DBM['unknown2']]
	unknown2 = original[DBM['unknown2']:DBM['WORD.TOS']]
	word = original[DBM['WORD.TOS']:DBM['MONSTER.TOS']]
	monster = original[DBM['MONSTER.TOS']:]
	
with open('original\\REALM\\databin_files\\beginning.TOS', 'wb+') as f:
	f.write(beginning)

with open('original\\REALM\\databin_files\\NAME.TOS', 'wb+') as f:
	f.write(name)

with open('original\\REALM\\databin_files\\ITEM.TOS', 'wb+') as f:
	f.write(item)

with open('original\\REALM\\databin_files\\unknown.TOS', 'wb+') as f:
	f.write(unknown)

with open('original\\REALM\\databin_files\\unknown2.TOS', 'wb+') as f:
	f.write(unknown2)

with open('original\\REALM\\databin_files\\WORD.TOS', 'wb+') as f:
	f.write(word)

with open('original\\REALM\\databin_files\\MONSTER.TOS', 'wb+') as f:
	f.write(monster)