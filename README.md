# glodia
Repository for 46 OkuMen's fan translation of `Different Realm`.

## Progress
* Just getting started here.

## Usage
* To decode and dump the text from the TOS files and put them in an Excel sheet:
```python dump_tos.py```

* To merge translator updates from a shared Google Sheet export into the local workbook:
```python sync_google_sheet.py path\to\downloaded_google_sheet.xlsx```

  This updates the local `DiffRealm_Text.xlsx` English column while preserving the workbook structure used by the tools.
  If the Google Sheet is public or anonymous-link accessible, you can also pass the sheet URL directly:
```python sync_google_sheet.py "https://docs.google.com/spreadsheets/d/<ID>/edit"```

  If Google returns an access error, download the sheet from Google Sheets with `File -> Download -> Microsoft Excel (.xlsx)` and pass that file path instead.

* To reinsert the text and apply ASM hacks:
```python reinsert.py```

* To rebuild the script viewer data after importing new translations:
```python build_script_viewer_data.py```
