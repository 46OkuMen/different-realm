# TODO

## Testing reinsertion with the better dumper
* Mouth control codes are probably getting messed up during encoding - people end lines with their mouths open.
	* Does every line have to be even??
* How should I handle line breaks where it's one JP string that auto-breaks in the middle, and I've split it into two strings in the dump?
	* Can't put a [LN] in the JP string, since it doesn't reflect what's in the decoded file.
	* Would be annoying to have a comment that says "put an [LN] here".
	* Maybe an extra column that just holds [LN]s or terminal control codes?
		* Investigate the mouth thing, this might help that too.
* Really need to capture all the [FlipWidth] codes, since if I'm not aware of them, I can't get rid of them/cancel them out.

## Name entry
* Move the letters to get 13, 13, 13, 13.
* "I is always capital" bug is back, or was never fixed?
* 7th character doesn't get highlighted when it's up next to get written.
* "StockmanF " is the default name due to the 6->8 char change, gotta fix that.
	* That a6 byte appears to be part of the save file. What does it mean? Can I replace it with a hard-coded thing?
		* All sorts of things go wrong when I change the value. Instant game over on entering battle, sprites change, cut scenes are misaligned, etc.
		* It has something to do with the party composition I think.
	* What comes in the buffer right before the name? 
* All-blank letters should return Stockman rather than continue to be all-underscores.
* 

## General
* It'd be nice to double all the text speeds.
	* Current implementation: Every text speed is set to the maximum non-instantaneous speed.
	* But the default speed is kinda slow... No control code to alter it. I'd need to insert them before each string...

## Fun stuff
* How about that debug mode?
	* D_FLAG is 00 in production, -1 (FF?) in debug mode.
		* This segment is at 6000:c00.
		* c00: D_FLAG (yep)
		* c01: DEMO_MODE 
		* c02-c03: CPU_
		* c04: DOS_F
		* c05: _CYCLE SCR_CYCLE
		* c06: INTER
		* c07: TIMEC
		* c08: directional keys (KEYBUF)
		* c09: 40 on space      (SPACE)
	* Cool! Set 6000:c00 to FF to enable debug mode.
		* All Items lets you add any item to the inventory, one at a time.
		* Variables... AAA-ZZZ are all set to 0. Any way to edit these rather than just view them?
			* Their meaning is probably the one described in one of the docs. AAA-ZZZ list looks familiar. Same for Noise Pollution.