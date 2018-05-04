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

## Fun stuff
* /home/TTT/rlmdb.exe has lots of debug menus for editing item, monster data, etc.