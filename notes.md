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