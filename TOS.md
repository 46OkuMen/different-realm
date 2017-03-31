File Format
-----------------------
Header

BlockNo:
        Command Param1 Param2 .. 0xff (Terminate of Command)
        Message ...
        | (command or messages)
        0x00 (Terminate of Block)
|

Elements
-----------------------
Header : 8bytes
   char[6]  head of src file name
   u8       block total {1-255}
   u8       0

BlockNo : 1 byte
   1-255

Command : 1 or 2 byte
   5, 1-255  2byte command
   6-21        1byte command

Param : 1 or 2 byte (or filename)
   0-127                1byte param or ASCII chara
   128-254, 0-255  2byte param ({128-254} - 128)<<8 | {0-255}
   255(0xff)            End of Command

※ Command must be terminated by 0xff even without params.

Message : 1 or 2 byte code (contains control code)
        1       : Order Return
        2,N     : replaced by strings-table[N] (NAME.TOS)
        3,3     : Switch string size Half/Wide
        3,4     : Wait Any Key
        3,22-24 : Mouth set
        3,29    : Switch target window
        3,30-39 : Voice Tone set
        3,40-59 : Text Speed
        3,60-79 : Text Space(wide) (60:3space .. 79:22space)
        3,80    : Order Text Clear
        3,81-87 : Set Text Color
        3,88    : Set Anime Skip
        3,90-255: Wait time
        4       : a Half size space

        (5-21)..: regard as command until 0xff.

        22-32   : Marks
            :  22   23   24   25   26   27   28   29   30   31   32
            : (spc)  、   。   ，   ．   ・   ：　　；  ？   ！   ー


        33(0x21)-79(0x4f), 0x21-0x7e : 2byte JIS 1st/2nd code
            : This is not Shift-JIS. Legacy JP 2bytes code
                        : http://charset.7jp.net/jis.html

        80-89   : Number (Wide size) '０'-'９'
        90-172  : Hiragana 90:'ぁ'(0x2421), 91:'あ'(0x2422), 92:'ぃ'(0x2423).. 172:'ん'(0x2473)
        173-255 : Katakana 173:'ァ'(0x2521), 174:'ア'(0x2522), 175:'ィ'(0x2523).. 255:'ン'(0x2573)

※ Messages are terminated by Command code or 0(End of block)


ex.)

15:                    -> 15 (Block No.)
        CRES:              -> 21, 255  (1byte command. terminated by 0xff)
        OPEN 1:            -> 5,72, 1, 255    (2byte command)
        PACK [AT01],24:    -> 8, 'A','T','0','1',0, 24, 255  (1 byte command and name params)
        BG_ANI 100,200,300:-> 5,63, 100, 128,200, 0x81,0x2c, 255  (with 2byte param)
        あいうえお@         -> 91,93,95,97,99, 1   (@ is Return)
        #5桑田              -> 3,85,(#5 is Color-5) 0x37,0x2c, 0x45,0x44,(桑)
        INPUT:             -> 3,4, (INPUT is not command. Control code of Wait any Key)
        \                  -> 0 (End of Block)

Algorithm
-----------------------
skip Header 8 bytes
while (end of file) {
  Get Block No (1 byte)
  while (get 1 byte is not 0) {
    if (is 5-21) {  This is command. skip unitl 0xff }
    else if (1-4) { Control Code 1 or 2 bytes }
    else if (22-32) { Mark }
    else if (33-79) { 2bytes JIS Code }
    else if (80-89) { Number }
    else if (90-172) { Hiragana }
    else if (173-255) { Katakana }
  }
}