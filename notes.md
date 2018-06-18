## win2png
* STEPS TO EDIT AN IMAGE
	* Open the Mac VM.
	* ```./win2png data/realm/RLMFR.img -p 2```
	* Email it to Windows.
	* Edit the resulting PNG in GIMP. Don't touch it with Paint or it will expand a lot and produce incorrect results.
	* Email it back to the Mac.
	* ```./png2win -c 6 RLMFR.png```
	* Email it to Windows.
	* Put it on the disk.

## .IMG
* So, there are some .ZIM files that appear to be image sources. They are allegedly created with KID98 but I can't get them to show up/load in KID98.
* You can view .IMG files by using Hoee's 'winp.exe' utility. ("WinPac")
	* ```winp opc01.img```
	* Just like MLD, puts it in the top left.
	* ``` winp opc01.img```
		* Displays compression info, how many images are packed into it, etc.
* You can view .ZIM files with kload.exe:
	* ```kload realm01.zim```
		* Kload and zimload appear to just be renamed versions of each other.
* What is /home/tool/IMAGE.EXE?
* The "Diffelent Realm" frame is the file 'etc/rlmfr.img'.
* How to open DiffRealm .ZIM files in KID98:
	* 1) Open the build environment disk.
	* 2) Insert KID98 system disk into first floppy drive.
	* 3) B:/
	* 4) KID98 \N
	* 5) Navigate to .ZIM files (WATASU1.ZIM, WATASU3.ZIM)
* png2win output (compression type 10) doesn't want to show up ingame, even if WINP can read it...
	* Can't seem to get anything with compression type 10 to show up ingame, anyway.
* The original RLMFR.IMG is dieted, should I try doing that?
	* The game seems to accept RLMFR.IMG both dieted and undieted...

## Numbers
* Currently all numbers are showing up as Q, R, S, etc.
* Numbers are coded to show up as 82 4f - 82 58. 4f - 58 are letters of course.
	* TOS number codes are 0x80-89, which are above the ASCII range. THe problem just comes from trying to display the fullwidth numbers...
	* Let's see if this is something hackable.

* 5a = 90, or space, 39, 30.
6000:a6e1: mov al, [si+33] (the value for that stat, which will be displayed as _ _ 8)
call a0fe
...
mov di, 25f3
mov dl, 98
mov cx, 9680
call 25fd

(does some math and feeds it into [1153], then back into EAX)

stosb            ; store AL at address ES:DI, which is 6000:25f3
mov dl, 0f
mov cx, 4240
call 25fd

stosb

there are at least 2 spots where 4f gets moved somewhere. Numbers are 50-5f. Coincidence? I think not.
6000:25fd c60653114f -> c606531150
6000:25a3 b64f -> b650


6000:25f3 is PPPPP. The next 3 are buffers for a stat being edited.



cmp al, 16
jnb 4685
jmp 4766

Shorter version:

cmp al, 16
jge 4766 = 0f 8d f2 00 (90)

## Name Entry
mov al, [bx]
stosb                ; store AL at address ES:DI, which is 6000:96

...

6000:ada4
cmp al, 16
jnz adac
...
cmp al, aa
jnz adb2
stosb                ; 6000:96 again

* The underscores are the value a9 6 times.
* Left/right cursor arrows decrement/increment EDI.


## DIETing
*    Some files are compressed with DIET.EXE, a DOS executable compressor.
*    To edit these files:
*        1) Edit the decompressed version, which is already in 'original'.
*        2) Load them into a DOS HDI with DIET.XEXE in the root.
*        3) Add a DIET.EXE command to an AUTOEXEC.BAT script, which is loaded onto the HDI.
*        4) Open the HDI in Neko Project II, which compresses them.
*        5) Extract them from the DOS HDI to the 'patched' folder.
*        6) Insert them into the final Different Realm HDI.

## Fun stuff
* /home/TTT/rlmdb.exe has lots of debug menus for editing item, monster data, etc.

## DATA.BIN
DATA.BIN appears to have some important .TOS files squished together.

0x89b: name.tos, length is 0x30b
0xba7: item.tos, length is 0x7eb
0x1392: something unique to DATA.BIN?
0x1987: word.tos, length is 0x17f
0x1b07: monster.tos, length is 0x37f
End

Pointers at the top. 12 00, then (little-endian pointer, then 4 bytes of ??, then another pointer, etc)

|   |-SYSTEM.PAC          ; Message & Control Talk for System Program
|   |-FMENU.PAC           ; Message & Control Talk for Battle Program
|   |-WORD.PAC            ; 
|   |-HELP.PAC            ; Help Message
|   |-INFO.PAC            ; Explain of Item
|   |-INFP.PAC            ; Explain of Psyonics
|   |-ITEM.PAC            ; Armor or Item Name
|   |-MONSTER.PAC         ; Enemy Name
|   |-NAME.PAC            ; Party Name etc.

Files that remain separate .TOS files:
SYSTEM.TOS (in TALK)
FMENU.TOS (in TALK)
INFO.TOS (in TALK)
INFP.TOS (in TALK)
HELP.TOS (in TALK)

Files in DATA.BIN:
NAME.TOS
ITEM.TOS
WORD.TOS
MONSTER.TOS


Mystery files:
TMP.TOS is just ST16.TOS.
There are TMP.TOS files in the rest of the SRC folders, they are probably other various TOS files...

## Editing dieted files
* Even if I can't DIET stuff automatically, I should at least have an automated way of doing the edits just in case I lose something.
* CMAKE.BIN
	* 0xb47, a9 -> bf     # Chnage placeholder letter from 'I' to "_"_
	* 0xb4c, aa -> 00     # Remove whatever the "J" control code is so it displays correclty
	* 0x4ee  06 -> 08     # Change the 6-character "_"_ fill to an 8-character one 
	* 0x524  b3 d4 cf c3 cb cd   # eto[ -> Stockm
	* some unknown other change. Need to do a binary diff, TODO
	* Hm, I am confused. CMAKE.BIN might not be dieted at all?? It's equal in patched/ and patched/dieted_edited...

## TODO
* Remind SkyeWelse to scan the demo envelope & Popcom magazine it came with.
* Name entry screen problems:
	* Highlighted character advances 2 characters over instead of 1, and disappears when it gets past character 6