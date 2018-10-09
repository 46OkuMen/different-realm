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
* Strongly consider re-using the old dump's version of the name entry screen string... it just works(TM).
	* Nope, it is broken with that too.
* "I is always capital" bug is back, or was never fixed?
* 7th character doesn't get highlighted when it's up next to get written.
* "StockmanF " is the default name due to the 6->8 char change, gotta fix that.
	* That a6 byte appears to be part of the save file. What does it mean? Can I replace it with a hard-coded thing?
		* All sorts of things go wrong when I change the value. Instant game over on entering battle, sprites change, cut scenes are misaligned, etc.

## General
* It'd be nice to double all the text speeds.
	* Speeds go from [Spd28] to [Spd3b]. Maybe:
		* 28 -> 32 (+10)
		* 29 -> 32 (+9)
		* 2a -> 33 (+9)
		* 2b -> 33 (+8)
		* 2c -> 34 (+8)
		* 2d -> 34 (+7)
		* 2e -> 35 (+7)
		* 2f -> 35 (+6)
		* 30 ->
		* 31 ->
		* 32 ->
		* 33 ->
		* 34 ->
		* 35 ->
		* 36 ->
		* 37 ->
		* 38 -> 3a (+2)
		* 39 -> 3a (+1)
		* 3a -> 3b (+1)
		* 3b -> 3b (+0)