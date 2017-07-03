import os
from tos import decode

tos_paths = []

for p in os.walk('original\\DIFFEREN'):
    for filename in p[2]:
        if filename.endswith(".TOS") and "parsed" not in filename:
            tos_paths.append(os.path.join(p[0], filename))

## testing
#tos_paths = ['original\\DIFFEREN\\MAP\\AM02.TOS']

for t in tos_paths:
    print t
    decode(t)